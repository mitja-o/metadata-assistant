import logging
import operator
from dataclasses import dataclass
from enum import StrEnum
from functools import partial
from pathlib import Path
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send

from massi.agents.team._dto import (
    CSVOverview,
    DatasetFileCollection,
    FileOverview,
    GapTaskValidation,
    MetadataBlueprint,
    MetadataGapDerivationPlan,
    MetadataGapTask,
    MetadataGapTaskOutcome,
    MetadataGoal,
    SupportedMetadataGoals,
    VerifiedMetadataGapDerivationPlan,
    VerifiedMetadataGapTask,
)
from massi.agents.team.architect import ArchitectContextProps, MetadataArchitect
from massi.agents.team.managers import GapDerivationManager
from massi.agents.team.operators import GapDerivationOperator
from massi.agents.team.planner import MetadataBlueprintPlanner
from massi.agents.tools import (
    get_file_stats,
    get_xmlschema_validator,
    safe_get_csv_details,
    walk_working_dir_for_files,
)

# Logger
# ------

# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)


# Configurations
# --------------


class MassiRuntimeConfiguration(TypedDict):
    working_directory: str = "."
    output_directory: str = "."


# Workflow state
# --------------


class MassiExecutionMode(StrEnum):
    HUMAN_INQUIRY = "human"
    """Focuses on human inquiry - interview the user about their dataset."""

    DATA_INQUIRY = "data"
    """Focuses on automated data exploration - derive metadata from the dataset autonomously."""


# TODO(refactor): consider using LangGraph context for this or make immutable
class MassiRuntimeSettings(TypedDict):
    """Top-level, static settings, consistent throughout the workflow graph."""

    runtime_config: MassiRuntimeConfiguration = None


class MassiGoalResolutionState(MessagesState, total=False):
    # external static configuration
    settings: MassiRuntimeSettings
    # resolution inputs
    dataset: DatasetFileCollection
    goal: MetadataGoal
    # working data
    context_blocks: str
    architect_prompt: str
    architect_xml_blueprint: MetadataBlueprint
    working_copy_xml_blueprint: MetadataBlueprint
    gap_derivation_plan: MetadataGapDerivationPlan
    verified_gap_derivation_plan: VerifiedMetadataGapDerivationPlan
    # TODO: make a better plan execution engine
    current_gap_task_pointer: int
    current_gap_instruction_prompt: str
    last_gap_derivation_result: MetadataGapTaskOutcome


class MassiCoreState(MessagesState, total=False):
    # external static configuration
    settings: MassiRuntimeSettings
    goals: list[MetadataGoal]
    # working data
    dataset: DatasetFileCollection
    resolutions: Annotated[list[MassiGoalResolutionState], operator.add]


# Workflow Protocol
# -----------------

type MassiCoreWorkflowGraph = CompiledStateGraph[
    MassiCoreState, None, MassiCoreState, MassiCoreState
]
type MassiResolutionWorkflowGraph = CompiledStateGraph[
    MassiGoalResolutionState, None, MassiGoalResolutionState, MassiGoalResolutionState
]


@dataclass
class MassiWorkflow[T]:
    graph: T
    execution_settings: dict[str, any]


# Dependencies
# ------------


@dataclass
class Dependencies:
    execution_mode: MassiExecutionMode = MassiExecutionMode.HUMAN_INQUIRY

    architect_map: dict[SupportedMetadataGoals, MetadataArchitect] | None = None
    planner_map: dict[SupportedMetadataGoals, MetadataBlueprintPlanner] | None = None
    gap_derivation_manager_map: (
        dict[MassiExecutionMode, GapDerivationManager] | None
    ) = None
    derivation_map: dict[MassiExecutionMode, GapDerivationOperator] | None = None

    metadata_resolution_subgraph: MassiWorkflow[MassiResolutionWorkflowGraph] | None = (
        None
    )


# Data Mappers
# ------------


def normalize_gap_file_paths(
    gap_task: MetadataGapTask, state: MassiGoalResolutionState | None = None
) -> MetadataGapTask:
    state_file_path_maps = {
        p["location"].name: str(p["location"]) for p in state["dataset"]["files"]
    }
    normalised_files = [
        state_file_path_maps.get(Path(f).name, f) for f in gap_task["gap_scope_files"]
    ]
    return {**gap_task, "gap_scope_files": normalised_files}


def validate_gap_task(
    gap_task: MetadataGapTask, state: MassiGoalResolutionState | None = None
) -> VerifiedMetadataGapTask:
    blueprint: MetadataBlueprint = state["architect_xml_blueprint"]
    validation: GapTaskValidation = {
        "valid_pattern": gap_task["gap_replacement_pattern"] in blueprint["content"],
        "valid_files": all(
            (
                bool(gap_task["gap_scope_files"]),
                (
                    set(gap_task["gap_scope_files"])
                    <= set([str(f["location"]) for f in state["dataset"]["files"]])
                ),
            ),
        ),
    }
    return {
        **gap_task,
        "valid": all((validation["valid_files"], validation["valid_pattern"])),
        "validation": validation,
    }


def take_valid_plan_tasks(
    state: MassiGoalResolutionState,
) -> VerifiedMetadataGapDerivationPlan:
    return {
        **state["verified_gap_derivation_plan"],
        "gaps": [
            gt for gt in state["verified_gap_derivation_plan"]["gaps"] if gt["valid"]
        ],
    }


def patch_metadata(
    outcome: MetadataGapTaskOutcome, blueprint: MetadataBlueprint
) -> MetadataBlueprint:
    outcome_content = outcome["result"]["content"].strip('"')
    logger.debug(outcome_content)
    gap_replacement_tag = outcome["task"]["gap_replacement_pattern"]
    logger.debug(gap_replacement_tag)
    patched_content = blueprint["content"].replace(gap_replacement_tag, outcome_content)
    return {**blueprint, "content": patched_content}


# Workflow nodes
# --------------


def _refine_initalisation(state: MassiCoreState) -> MassiCoreState:
    settings = state.get("settings")
    goals = state.get("goals")

    assert settings is not None, "`settings` must be provided at the start."
    assert goals is not None, "`goals` must be provided at the start."

    return {"goals": sorted(goals, key=lambda g: g["level"])}


def inventorize_dataset(state: MassiCoreState) -> MassiCoreState:
    work_dir = state["settings"]["runtime_config"]["working_directory"]
    paths = map(get_file_stats, walk_working_dir_for_files(seed_path=work_dir))
    file_overviews: list[FileOverview] = [
        {"location": p, "stats": str(s)} for (p, s) in paths
    ]
    # FIXME(formats): Darwin Core also often uses `.txt` (TSV) files. I need to account for that too.
    tabular_file_overviews: list[CSVOverview] = [
        {**f, "details": details}
        for f in file_overviews
        if f["location"].suffix.lower() in (".csv", ".txt")
        and (details := safe_get_csv_details(f["location"]))
        and bool(details)
    ]
    return {"dataset": {"files": file_overviews, "csv_files": tabular_file_overviews}}


# -- Map
def map_goals(state: MassiCoreState) -> MassiCoreState:
    settings = state["settings"]
    dataset = state["dataset"]
    active_goal_pointer = len(state["resolutions"])
    if active_goal_pointer < len(state["goals"]):
        goal = state["goals"][active_goal_pointer]
        return [
            Send(
                run_metadata_derivation_goal.__name__,
                {"settings": settings, "goal": goal, "dataset": dataset},
            )
        ]
    else:
        return [Send(terminate.__name__, {**state})]


# -- Subgraph invokation
def run_metadata_derivation_goal(
    state: MassiGoalResolutionState, dependencies: Dependencies
) -> MassiCoreState:
    assert dependencies.metadata_resolution_subgraph
    resolution_subgraph: MassiResolutionWorkflowGraph = (
        dependencies.metadata_resolution_subgraph.graph
    )
    resolution: MassiGoalResolutionState = resolution_subgraph.invoke(state)
    logger.debug(resolution)
    return {"resolutions": [resolution]}


def terminate(state: MassiCoreState) -> MassiCoreState:
    logger.debug("Reached the end")
    logger.debug(f"{state=}")
    logger.info(f"Resolved: {len(state["resolutions"])} / {len(state["goals"])}")
    return {}


# Derivation subgraph
# -------------------


# -- Subgraph
def start_metadata_derivation(
    state: MassiGoalResolutionState, dependencies: Dependencies | None = None
) -> MassiGoalResolutionState:
    assert dependencies
    assert dependencies.architect_map
    goal_key = state["goal"]["metadata_goal_key"]
    architect_agent = dependencies.architect_map.get(goal_key)
    assert architect_agent

    # TODO(refactor): move this to a separate function
    csv_overview = "\n".join(
        [
            (
                f'==> {c["location"]} <==\n'
                f'-- head ({c["details"]["head_size"]} / {c["details"]["row_count"]} rows) --\n'
                f'```csv\n{c["details"]["raw_head"]}\n```'
                f'\n-- column descriptive statistics ({c["details"]["column_count"]} columns) --\n'
                f'```csv\n{c["details"]["descriptive_stats"]}\n```'
            )
            for c in state["dataset"]["csv_files"]
        ]
    )
    file_overvew = "\n".join(
        [
            f'==> {fl["location"]} <==\n-- file stats --\n{fl["stats"]}'
            for fl in state["dataset"]["files"]
        ]
    )
    architect_context: ArchitectContextProps = {
        "csv_overview": csv_overview,
        "file_overview": file_overvew,
        "xsd_schema": get_xmlschema_validator(
            state["goal"]["schema_source"]
        ).to_string(),
    }
    context_blocks = architect_agent.get_context_prompt_block(architect_context)
    architect_prompt = architect_agent.get_system_prompt(context_blocks)
    logger.debug(architect_prompt)
    return {
        "context_blocks": context_blocks,
        "architect_prompt": architect_prompt,
    }


def build_blueprint_xml(
    state: MassiGoalResolutionState, dependencies: Dependencies | None = None
) -> MassiGoalResolutionState:
    assert dependencies
    assert dependencies.architect_map
    goal_key = state["goal"]["metadata_goal_key"]
    architect_agent = dependencies.architect_map.get(goal_key)
    assert architect_agent

    result = architect_agent.invoke(state["architect_prompt"])
    logger.debug(result)
    return {"architect_xml_blueprint": result}


def make_gap_derivation_plan(
    state: MassiGoalResolutionState, dependencies: Dependencies | None = None
) -> MassiGoalResolutionState:
    assert dependencies
    assert dependencies.architect_map
    goal_key = state["goal"]["metadata_goal_key"]
    planner_agent = dependencies.planner_map.get(goal_key)
    assert planner_agent

    blueprint = state["architect_xml_blueprint"]
    planner_prompt = planner_agent.get_system_prompt(
        state["context_blocks"],
        state["architect_prompt"],
        blueprint["content"],
    )
    plan: MetadataGapDerivationPlan = planner_agent.invoke(planner_prompt)
    logger.debug(plan)

    normalised_plan: MetadataGapDerivationPlan = {
        **plan,
        "gaps": list(map(partial(normalize_gap_file_paths, state=state), plan["gaps"])),
    }
    logger.info(normalised_plan)

    return {
        "gap_derivation_plan": normalised_plan,
        "current_gap_task_pointer": 0,
        "working_copy_xml_blueprint": blueprint,
    }


def verify_gap_derivation_plan(
    state: MassiGoalResolutionState,
) -> MassiGoalResolutionState:
    plan = state["gap_derivation_plan"]
    gaps = plan["gaps"]
    verified_plan: VerifiedMetadataGapDerivationPlan = {
        **plan,
        "gaps": list(map(partial(validate_gap_task, state=state), gaps)),
    }

    return {"verified_gap_derivation_plan": verified_plan}


# *__Conditional__*
def check_is_plan_usable(state: MassiGoalResolutionState) -> str:
    valid_gap_tasks: VerifiedMetadataGapDerivationPlan = take_valid_plan_tasks(state)
    total_steps_count = len(valid_gap_tasks["gaps"])

    if total_steps_count < len(state["verified_gap_derivation_plan"]["gaps"]):
        logger.warning(
            "Some gap task are not valid and are not included for execution."
        )

    current_pointer = state["current_gap_task_pointer"]
    completed = total_steps_count <= current_pointer
    return (
        export_metadata.__name__
        if completed
        else prepare_derivation_instruction.__name__
    )


def prepare_derivation_instruction(
    state: MassiGoalResolutionState, dependencies: Dependencies | None = None
) -> MassiGoalResolutionState:
    assert dependencies
    assert dependencies.gap_derivation_manager_map
    execution_mode = dependencies.execution_mode
    manager = dependencies.gap_derivation_manager_map.get(execution_mode)
    assert manager

    valid_gap_tasks: VerifiedMetadataGapDerivationPlan = take_valid_plan_tasks(state)
    current_gap_task_pointer = state["current_gap_task_pointer"]
    current_gap_task = valid_gap_tasks["gaps"][current_gap_task_pointer]
    logger.debug(current_gap_task)

    instruction_prompt = manager.get_instruction_prompt(
        current_gap_task,
        state["architect_prompt"],
        state["working_copy_xml_blueprint"]["content"],
    )
    rich_instruction: str = manager.invoke(instruction_prompt)
    logger.debug(rich_instruction)

    return {"current_gap_instruction_prompt": rich_instruction}


def execute_gap_derivation(
    state: MassiGoalResolutionState, dependencies: Dependencies | None = None
) -> MassiGoalResolutionState:
    assert dependencies
    assert dependencies.derivation_map
    execution_mode = dependencies.execution_mode
    operator = dependencies.derivation_map.get(execution_mode)
    assert operator

    valid_gap_tasks: VerifiedMetadataGapDerivationPlan = take_valid_plan_tasks(state)
    current_task_pointer = state["current_gap_task_pointer"]
    current_gap_task = valid_gap_tasks["gaps"][current_task_pointer]
    current_gap_instruction = state["current_gap_instruction_prompt"]

    result = operator.invoke(current_gap_instruction, current_gap_task)

    return {"last_gap_derivation_result": result}


def synthesize_metadata(state: MassiGoalResolutionState) -> MassiGoalResolutionState:
    updated_blueprint = patch_metadata(
        state["last_gap_derivation_result"],
        state["working_copy_xml_blueprint"],
    )

    return {
        "working_copy_xml_blueprint": updated_blueprint,
        "current_gap_task_pointer": state["current_gap_task_pointer"] + 1,
    }


def export_metadata(state: MassiGoalResolutionState) -> MassiGoalResolutionState:
    logger.debug("Reached the end")
    logger.debug(f"{state=}")
    working_metadata = state["working_copy_xml_blueprint"]["content"]
    out_file = state["goal"]["target_filename"]
    out_dir = Path(state["settings"]["runtime_config"]["output_directory"])

    out_dir.mkdir(exist_ok=True)
    output_file = out_dir / out_file

    output_file.write_text(working_metadata)
    return {}


# Graph construction
# ------------------


def _build_goal_resolution_graph(
    dependencies: Dependencies,
) -> MassiWorkflow[MassiGoalResolutionState]:
    builder = StateGraph(MassiGoalResolutionState)

    nodes = [
        (start_metadata_derivation, {"dependencies": dependencies}),
        (build_blueprint_xml, {"dependencies": dependencies}),
        (make_gap_derivation_plan, {"dependencies": dependencies}),
        (verify_gap_derivation_plan, {}),
        (prepare_derivation_instruction, {"dependencies": dependencies}),
        (execute_gap_derivation, {"dependencies": dependencies}),
        (synthesize_metadata, {}),
        (export_metadata, {}),
    ]
    for fn, kwargs in nodes:
        node_name = fn.__name__
        node_func = partial(fn, **kwargs) if kwargs else fn
        builder.add_node(node_name, node_func)

    builder.add_edge(START, start_metadata_derivation.__name__)
    builder.add_edge(start_metadata_derivation.__name__, build_blueprint_xml.__name__)
    builder.add_edge(build_blueprint_xml.__name__, make_gap_derivation_plan.__name__)
    builder.add_edge(
        make_gap_derivation_plan.__name__, verify_gap_derivation_plan.__name__
    )
    # * export if completed, otherwise process
    builder.add_conditional_edges(
        verify_gap_derivation_plan.__name__,
        check_is_plan_usable,
        [prepare_derivation_instruction.__name__, export_metadata.__name__],
    )
    builder.add_edge(
        prepare_derivation_instruction.__name__, execute_gap_derivation.__name__
    )
    builder.add_edge(execute_gap_derivation.__name__, synthesize_metadata.__name__)
    # * loop back to verification
    builder.add_edge(synthesize_metadata.__name__, verify_gap_derivation_plan.__name__)
    builder.add_edge(export_metadata.__name__, END)

    return MassiWorkflow(
        graph=builder.compile(checkpointer=None),
        execution_settings=dict(),
    )


def build_graph(dependencies: Dependencies) -> MassiWorkflow[MassiCoreWorkflowGraph]:
    builder = StateGraph(MassiCoreState)

    nodes = [
        (_refine_initalisation, {}),
        (inventorize_dataset, {}),
        (run_metadata_derivation_goal, {"dependencies": dependencies}),
        (terminate, {}),
    ]
    for fn, kwargs in nodes:
        node_name = fn.__name__
        node_func = partial(fn, **kwargs) if kwargs else fn
        builder.add_node(node_name, node_func)

    builder.add_edge(START, _refine_initalisation.__name__)
    builder.add_edge(_refine_initalisation.__name__, inventorize_dataset.__name__)

    builder.add_conditional_edges(
        inventorize_dataset.__name__,
        map_goals,
        [run_metadata_derivation_goal.__name__, terminate.__name__],
    )

    builder.add_edge(terminate.__name__, END)

    # memory = None
    memory = MemorySaver()
    return MassiWorkflow(
        graph=builder.compile(checkpointer=memory),
        execution_settings=dict(),
    )
