import json
import pathlib as pl
from functools import partial

from jsonschema.validators import Draft202012Validator
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

import massi.agents.tools as massi_toolkit
from massi.agents.constructs import (
    BaseMetadataState,
    MessageBuilder,
    MetadataUpdate,
    QueryPlan,
    QueryStep,
)
from massi.agents.inquiry_engine import (
    QueryPlanExecutionState,
    get_next_step,
    is_plan_completed,
)
from massi.agents.interfaces import Dependencies, PromptClient

# UC1: Base Metadata
# ==================


class Defaults:
    base_metadata_file = "base_metadata.json"
    # Adapted from MIAGIS JSON Schema
    # @see: https://moseleybioinformaticslab.github.io/miagis/jsonschema.html
    base_metadata_json_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "entry_version": {"type": "integer", "minimum": 1},
            "entry_id": {"type": "string", "minLength": 1},
            "description": {"type": "string", "minLength": 1},
            "products": {"type": "array", "items": {"type": "string", "minLength": 1}},
        },
        "required": [
            "entry_version",
            "entry_id",
            "description",
            "products",
        ],
    }
    base_metadata_json_schema_validator = Draft202012Validator(
        base_metadata_json_schema
    )


def _create_default_metadata() -> pl.Path:
    default_path = pl.Path(".") / Defaults.base_metadata_file
    default_path.write_text(json.dumps({}))
    return default_path


def ensure_metadata_file_presence(
    _: BaseMetadataState, root_dir: str = "."
) -> BaseMetadataState:
    n_state = {}
    found_files = massi_toolkit.glob_file_search(
        f"**/{Defaults.base_metadata_file}", root_dir
    )

    n_state = {
        "base_metadata_files": (
            list(map(str, found_files))
            if found_files
            else [str(_create_default_metadata())]
        )
    }
    assert (
        len(n_state["base_metadata_files"]) > 0
    ), "At least one base metadata file must be present"

    return n_state


def select_working_base_metadata_file(state: BaseMetadataState) -> BaseMetadataState:
    return {"selected_base_metadata_file": state["base_metadata_files"][0]}


def check_metadata_completion(state: BaseMetadataState) -> BaseMetadataState:
    with open(state["selected_base_metadata_file"], "r") as bmf:
        base_metadata = json.load(bmf)

    return {
        "schema_validation_errors": [
            {
                "message": e.message,
                "encountered_value": e.validator_value,
                "json_path": e.json_path,
                "failed_key": e.validator,
            }
            for e in Defaults.base_metadata_json_schema_validator.iter_errors(
                base_metadata
            )
        ]
        or [],
        "original_metadata": base_metadata,
    }


def interpret_metadata_checks(
    state: BaseMetadataState, llm: BaseChatModel | None = None
) -> BaseMetadataState:
    assert "schema_validation_errors" in state, str(state)
    assert llm, "LLM chat Model must be provided!"

    response = llm.invoke(
        [
            SystemMessage(
                content=MessageBuilder.base_metadata_error_validation_system_message(
                    state
                )
            ),
            HumanMessage(
                content=MessageBuilder.error_to_model_request(
                    state, Defaults.base_metadata_json_schema
                )
                + "\n\n Please explain what went wrong"
            ),
        ]
    )
    return {"messages": response, "errors_summary": response}


def plan_user_query(
    state: BaseMetadataState, llm: BaseChatModel | None = None
) -> BaseMetadataState:
    messages = [
        state["errors_summary"],
        SystemMessage(
            MessageBuilder.base_metadata_error_resolution_planning_system_message(state)
        ),
        HumanMessage(
            MessageBuilder.error_to_model_request(
                state, Defaults.base_metadata_json_schema
            )
        ),
    ]
    response = llm.with_structured_output(QueryPlan).invoke(messages).model_dump()
    return {
        "messages": messages,
        "query_plan": response,
        "query_plan_completed": False,
    }


def pull_ready_user_query(state: BaseMetadataState) -> dict:
    """Puts the user query ready for display using the functional Logic API.

    Examples:
        >>> step1 = QueryStep(id=1, key="v", json_path=".", priority=1, query="q1")
        >>> plan_dict = {"queries": [step1.model_dump()]}

        >>> # First query is pulled
        >>> res1 = pull_ready_user_query({"query_plan": plan_dict, "current_query_step": None})
        >>> res1["current_query_step"]["id"]
        1
        >>> res1["query_plan_completed"]
        False

        >>> # Final query is pulled
        >>> res2 = pull_ready_user_query({"query_plan": plan_dict, "current_query_step": step1.model_dump()})
        >>> res2["current_query_step"] == None
        True
        >>> res2["query_plan_completed"]
        True
    """
    plan_dict = state.get("query_plan")
    if (
        state.get("query_plan_completed")
        or not plan_dict
        or not plan_dict.get("queries")
    ):
        return {"query_plan_completed": True}

    current_step = state.get("current_query_step", None)
    current_id = QueryStep(**current_step).id if current_step else None

    next_step = get_next_step(QueryPlan(**plan_dict), current_id)

    return {
        "current_query_step": next_step.model_dump() if next_step else None,
        "query_plan_completed": next_step is None,
    }


def prompt_user_query(
    state: BaseMetadataState, prompt_client: PromptClient | None = None
) -> BaseMetadataState:
    # TODO(feature): reformulate the query based on the surrounding context
    planned_query_prompt = state.get("current_query_step", {}).get("query", None)
    responses = prompt_client.prompt_user(
        queries=[planned_query_prompt] if planned_query_prompt else []
    )
    return {"current_query_response": responses[0]}


def register_user_query_response(
    state: BaseMetadataState, llm: BaseChatModel | None = None
) -> BaseMetadataState:
    """Processes the user provided answer and updates the metadata.

    Args:
        state (BaseMetadataState): the agent's workflow execution state
        llm (BaseChatModel | None, optional): the configured LLM client. Defaults to None.

    Returns:
        BaseMetadataState: the updated workflow state.
    """
    current_query = state.get("current_query_step", {}).get("query", "")
    given_response = state.get("current_query_response", "")
    messages = state.get("messages", [])

    update = None
    if current_query and given_response:
        with open(state["selected_base_metadata_file"], "r") as bmf:
            base_metadata = json.load(bmf)

        update = llm.with_structured_output(MetadataUpdate).invoke(
            messages
            + [
                HumanMessage(
                    MessageBuilder.update_given_base_metadata_request(
                        state, metadata=base_metadata
                    )
                )
            ]
        )

        with open(state["selected_base_metadata_file"], "w") as bmf:
            json.dump(update.metadata, bmf)

    return {"updated_metadata": update.model_dump(), "messages": messages}


def is_query_plan_completed(state: BaseMetadataState) -> QueryPlanExecutionState:
    """Checks if the plan is completed.

    Examples:
        >>> step1 = QueryStep(id=1, key="v", json_path=".", priority=1, query="q1")
        >>> plan_dict = {"queries": [step1.model_dump()]}

        >>> # Query is not finished yet
        >>> is_query_plan_completed({"query_plan": plan_dict, "current_query_step": None})
        <QueryPlanExecutionState.ACT: 1>

        >>> # Query is finished
        >>> is_query_plan_completed({"query_plan": plan_dict, "current_query_step": step1.model_dump()})
        <QueryPlanExecutionState.STOP: 0>
    """
    plan_dict = state.get("query_plan")
    current_step = state.get("current_query_step", None)
    current_id = QueryStep(**current_step).id if current_step else None

    if not plan_dict or is_plan_completed(QueryPlan(**plan_dict), current_id):
        return QueryPlanExecutionState.STOP

    return QueryPlanExecutionState.ACT


def build_graph(dependencies: Dependencies):
    llm = dependencies.llm_client
    prompt_client = dependencies.prompt_client
    working_dir = dependencies.working_directory

    builder = StateGraph(BaseMetadataState)

    nodes = [
        (ensure_metadata_file_presence, {"root_dir": working_dir}),
        (select_working_base_metadata_file, {}),
        (check_metadata_completion, {}),
        (interpret_metadata_checks, {"llm": llm}),
        (plan_user_query, {"llm": llm}),
        (pull_ready_user_query, {}),
        (prompt_user_query, {"prompt_client": prompt_client}),
        (register_user_query_response, {"llm": llm}),
    ]
    for func, kwargs in nodes:
        node_name = func.__name__
        node_func = partial(func, **kwargs) if kwargs else func
        builder.add_node(node_name, node_func)

    sequential_edges = [
        (START, ensure_metadata_file_presence),
        (ensure_metadata_file_presence, select_working_base_metadata_file),
        (select_working_base_metadata_file, check_metadata_completion),
        (check_metadata_completion, interpret_metadata_checks),
        (interpret_metadata_checks, plan_user_query),
        (plan_user_query, pull_ready_user_query),
        (pull_ready_user_query, prompt_user_query),
        (prompt_user_query, register_user_query_response),
    ]
    for source, target in sequential_edges:
        builder.add_edge(
            source if isinstance(source, str) else source.__name__,
            target if isinstance(target, str) else target.__name__,
        )

    # # FIXME(rendering-display):
    builder.add_conditional_edges(
        register_user_query_response.__name__,
        is_query_plan_completed,
        {
            # FIXME(upstream-issue): when rendering mermaid, this should be wrapped in `"` because `.` in the key breaks mermaid rendering
            QueryPlanExecutionState.STOP: END,
            QueryPlanExecutionState.ACT: pull_ready_user_query.__name__,
        },
    )

    memory = MemorySaver()
    return builder.compile(checkpointer=memory), dict(
        interrupt_before=[register_user_query_response.__name__],
        interrupt_after=[
            pull_ready_user_query.__name__,
            register_user_query_response.__name__,
        ],
    )
