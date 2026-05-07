from contextlib import contextmanager
import json
import os
from pathlib import Path
import random
from time import perf_counter, time
from typing import Any, Callable, Generator, Literal, TypedDict
from dotenv import load_dotenv
from langchain.chat_models import BaseChatModel
from langchain.embeddings import Embeddings
from lmnr import Laminar
import pandas as pd


import logging

import pytest

from massi.agents.interfaces import Config, create_openai_llm, create_uva_llm
from massi.agents.team._dto import (
    MassiExecutionMode,
    MetadataGoal,
    MetadataLevel,
    MetadataScope,
)
from massi.agents.team.architect import DarwinCoreArchitect, EMLArchitect
from massi.agents.team.instructors import (
    AuthorGapDerivationInstructor,
    DataGapDerivationInstructor,
)
from massi.agents.team.operators import (
    AuthorGapDervationOperator,
    DataGapDervationOperator,
)
from massi.agents.team.planner import DarwinCorePlanner, EMLPlanner
from massi.agents.team.telecom.author_proxy import (
    RagAuthorProxyQueryClient,
    create_openai_embeddings,
)
from massi.agents.workflow import (
    Dependencies,
    MassiCoreState,
    MassiResolutionWorkflowGraph,
    MassiWorkflow,
    _build_goal_resolution_graph,
    build_graph,
)

logger = logging.getLogger(__name__)

load_dotenv()


class DEFAULTS:
    lmnr_base_url = "http://0.0.0.0"
    recursion_limit = 30
    turn_limit = 5

    @staticmethod
    def ground_experiment_path(path_suffix: str | Path) -> Path:
        return Path("_data/gbif_data_archive") / path_suffix

    @staticmethod
    def default_embeddings(model_name: str) -> Embeddings:
        return create_openai_embeddings(
            Config(model_name=model_name, api_key=os.environ["OPENAI_API_TOKEN"])
        )

    @staticmethod
    def openai_llm(model_name: str) -> BaseChatModel:
        return create_openai_llm(
            Config(
                api_key=os.environ["OPENAI_API_TOKEN"],
                model_name=model_name,
            )
        )

    @staticmethod
    def uva_surf_llm(model_name: str) -> BaseChatModel:
        return create_uva_llm(
            Config(
                api_key=os.environ["UVA_SURF_LLM_API_TOKEN"],
                model_url=os.environ["UVA_LLM_PROXY_URL"],
                model_name=model_name,
            )
        )

    @staticmethod
    def uva_ivi_llm(model_name: str) -> BaseChatModel:
        return create_uva_llm(
            Config(
                api_key=os.environ["UVA_IVI_LLM_API_TOKEN"],
                model_url=os.environ["UVA_LLM_PROXY_URL"],
                model_name=model_name,
            )
        )

    provider_to_llm_client_factory: dict[
        Literal["openai-platform", "openai", "surf", "ivi"],
        Callable[[str], BaseChatModel],
    ] = {
        "openai-platform": openai_llm,
        "openai": openai_llm,
        "surf": uva_surf_llm,
        "ivi": uva_ivi_llm,
    }

    schema_to_metadata_goal: dict[Literal["dwc", "eml"], MetadataGoal] = {
        "dwc": {
            "level": MetadataLevel.ITEM,
            "scopes": [
                MetadataScope.DESCRIPTIVE,
                MetadataScope.TECHNICAL,
                MetadataScope.USE,
            ],
            "target_filename": "meta.xml",
            "schema_source": "https://dwc.tdwg.org/text/tdwg_dwc_text.xsd",
            "description": (
                "This metadata file describes the archive and data file structure."
                "A descriptor metafile describes how the files in your archive are organized."
                "It describes the files in the archive and maps each data column to a corresponding standard Darwin Core or Extension term."
                "The metafile is a relatively simple XML file format."
            ),
            "metadata_goal_key": "darwin_core",
        },
        "eml": {
            "level": MetadataLevel.COLLECTION,
            "scopes": [
                MetadataScope.DESCRIPTIVE,
                MetadataScope.ADMINISTRATIVE,
                MetadataScope.PRESERVATION,
                MetadataScope.USE,
            ],
            "target_filename": "eml.xml",
            "schema_source": "https://eml.ecoinformatics.org/eml-2.2.0/eml.xsd",
            "description": (
                "This metadata file contains the dataset's aggregate metadata."
                "This is a resource metadata document that provides information about the dataset itself such as a description (abstract) of the dataset, the agents responsible for authorship, publication and documentation, bibliographic and citation information, collection methods and much more."
                "It is based on the Ecological Metadata Language."
            ),
            "metadata_goal_key": "eml",
        },
    }


def build_core_dependencies(
    execution_mode: MassiExecutionMode,
    ground_truth_paper: Path,
    core_llm: BaseChatModel,
    rag_llm: BaseChatModel,
    embedding_model: Embeddings,
) -> Dependencies:

    rag_author_proxy = RagAuthorProxyQueryClient.build_client(
        [ground_truth_paper],
        {"embedder": embedding_model},
        {"generator": rag_llm},
    )

    architect_map = {
        "darwin_core": DarwinCoreArchitect(core_llm),
        "eml": EMLArchitect(core_llm),
    }
    planner_map = {
        "darwin_core": DarwinCorePlanner(core_llm),
        "eml": EMLPlanner(core_llm),
    }
    derivation_instructors_map = {
        "data-focus": DataGapDerivationInstructor(core_llm),
        "author-focus": AuthorGapDerivationInstructor(core_llm),
    }
    derivation_map = {
        "data-focus": DataGapDervationOperator(
            core_llm, recursion_limit=25, turn_limit=5
        ),
        "author-focus": AuthorGapDervationOperator(
            core_llm, rag_author_proxy, recursion_limit=25, turn_limit=5
        ),
    }
    return dict(
        execution_mode=execution_mode,
        architect_map=architect_map,
        planner_map=planner_map,
        gap_derivation_instructor_map=derivation_instructors_map,
        derivation_map=derivation_map,
    )


def build_subgraph_dependencies(graph: MassiWorkflow[MassiResolutionWorkflowGraph]):
    return dict(metadata_resolution_subgraph=graph)


def merge_dependencies(dependencies: Dependencies, extras: Dependencies):
    return dict(**dependencies, **extras)


# Experiment Execution
# --------------------


@contextmanager
def timeit() -> Generator[Callable[[], float]]:
    t1 = t2 = perf_counter()
    yield lambda: t2 - t1
    t2 = perf_counter()


def evaluation_key(key: str) -> str:
    return f"evaluation-{key.lower().replace(' ', '-')}"


def evaluation_time_id(key: str) -> str:
    return f"{evaluation_key(key)}-{time()}"


@pytest.fixture()
def laminar_observer():
    load_dotenv()
    Laminar.initialize(
        base_url=os.getenv("LMNR_PROJECT_BASE_URL", DEFAULTS.lmnr_base_url),
        project_api_key=os.environ["LMNR_PROJECT_API_KEY"],
        http_port=int(os.environ["LMNR_PROJECT_HTTP_PORT"]),
        grpc_port=int(os.environ["LMNR_PROJECT_GRPC_PORT"]),
        metadata={"purpose": "experiment-run"},
    )


# Experiment Scenario Loading
# ---------------------------

# Scenario Constructs
# ===================


class ScenarioConfig(TypedDict, total=False):
    core_platform: str
    core_llm: str
    proxy_platform: str
    embedding_model: str
    rag_llm: str


class ScenarioSpec(TypedDict, total=False):
    # -- computed identifier
    scenario_id: int
    scenario_tag: str
    # -- provided spec details
    idx: int
    variant: str
    schema: str
    strategy: str
    provider: str
    config: ScenarioConfig


class DataCase(TypedDict, total=False):
    # -- computed identifier
    case_id: int
    # -- provided case details
    working_copy_data_dir: str
    ground_truth_paper_path: str
    ground_truth_metadata_dir: str
    ground_truth_metadata_eml: str
    ground_truth_metadata_dwc: str
    # --- case logging details
    success: bool = True
    outcome_json: str | None = None
    duration_ms: float
    timestamp: float | None = None


class ScenarioXCase(ScenarioSpec, DataCase):
    scenario_x_case_tag: str
    short_scenario_x_case_tag: str


type Scenario = tuple[int, ScenarioXCase]


# Scenario Loading and Logging
# ============================


def get_scenario_csv_path() -> Path:
    return Path("./_evaluation/runtime/experiment_scenarios.csv")


def get_cases_csv_path() -> Path:
    return Path("./_evaluation/runtime/gbif_cases.csv")


def get_scenario_x_case_log_csv_path() -> Path:
    return Path("./_evaluation/runtime/experiment_cross_scenarios_cases.log.csv")


def make_scenario_tag(idx: Any, spec: ScenarioSpec) -> str:
    return f"s_{idx}--{spec['variant']}-{spec['schema']}-{spec['strategy']}-{spec['provider']}-{spec['config']}"


def make_case_tag(scenario_tag: str, case_id: int) -> str:
    return f"c_{case_id}-x-{scenario_tag}"


def load_scenarios_x_cases(
    scenario_query: ScenarioSpec,
    case_head_limit: int | None = None,
) -> list[Scenario]:
    scenarios_csv = get_scenario_csv_path()
    cases_csv = get_cases_csv_path()
    scenario_x_case_log_csv = get_scenario_x_case_log_csv_path()

    scenarios = pd.read_csv(scenarios_csv)
    scenarios["config"] = scenarios["config"].apply(json.loads)
    cases = pd.read_csv(cases_csv)
    scenario_x_case_log = (
        pd.read_csv(scenario_x_case_log_csv)
        if scenario_x_case_log_csv.exists()
        else None
    )

    # -- select scenarios
    scenarios["scenario_id"] = scenarios.index
    selected_scenarios = scenarios[
        scenarios.apply(
            lambda s: all([s[qk] == qv for qk, qv in scenario_query.items()]), axis=1
        )
    ]
    selected_scenarios["scenario_tag"] = selected_scenarios.apply(
        lambda r: make_scenario_tag(r["scenario_id"], r), axis=1
    )

    # -- select cases
    cases["case_id"] = cases.index
    selected_cases = cases if case_head_limit is None else cases.head(case_head_limit)

    # -- generate selected scenario x case entries
    cross_scenario_cases = selected_scenarios.merge(selected_cases, how="cross")
    cross_scenario_cases["scenario_x_case_tag"] = cross_scenario_cases.apply(
        lambda r: make_case_tag(r["scenario_tag"], r["case_id"]), axis=1
    )
    cross_scenario_cases["short_scenario_x_case_tag"] = cross_scenario_cases.apply(
        lambda t: f"c_{t['case_id']}-x-s_{t['scenario_id']}", axis=1
    )

    # -- filter out the logged scenario x case entries
    remaining_sources = (
        cross_scenario_cases
        if not scenario_x_case_log_csv.exists()
        else (
            cross_scenario_cases[
                cross_scenario_cases["scenario_x_case_tag"].apply(
                    lambda t: t not in logged_case_tags
                )
            ]
            if (logged_case_tags := scenario_x_case_log["scenario_x_case_tag"].tolist())
            else []
        )
    )

    return [(i, r.to_dict()) for i, r in remaining_sources.iterrows()]


def build_log_entry(
    scenario_x_case: ScenarioXCase,
    duration_ms: float,
    success: bool = True,
    outcome_json: str | None = None,
) -> pd.DataFrame:
    return pd.DataFrame.from_records(
        [
            {
                **scenario_x_case,
                "success": success,
                "outcome_json": outcome_json,
                "duration_ms": duration_ms,
                "timestamp": time(),
            }
        ]
    )


# Scenario Suites
# ===============


class ScenarioBasedSuite:
    scenarios_x_cases: list[Scenario]


class MetaScenarioSuite:
    cls: type[ScenarioBasedSuite]


def pytest_generate_tests(metafunc: MetaScenarioSuite):
    """A Pytest hook that parametrises the test suite from the loaded scenarios.

    Args:
        metafunc (n/a): the test function picked up by pytest
    """
    run_ids = []
    input_arguments = []
    input_values = []
    for id, scenario_x_case in metafunc.cls.scenarios_x_cases:
        input_arguments = ["id", "tag", "scenario_x_case"]
        input_values.append(
            (
                id,
                scenario_x_case["scenario_x_case_tag"],
                scenario_x_case,
            )
        )
        run_ids.append(scenario_x_case["scenario_x_case_tag"])
    metafunc.parametrize(input_arguments, input_values, ids=run_ids, scope="class")


# Test Suites
# -----------


class Test_Massi_GBIF_Scenarios_X_Cases(ScenarioBasedSuite):
    scenarios_x_cases = load_scenarios_x_cases(
        {
            "variant": "full",
            "provider": "openai-platform",
            "schema": "dwc",
        },
        case_head_limit=200,
    )

    def test_scenario(self, id, tag, scenario_x_case, laminar_observer):
        # --- Arrange ---
        test_record = ScenarioXCase(**scenario_x_case)
        log_csv = get_scenario_x_case_log_csv_path()
        log_exists = Path(log_csv).exists()

        # setup the dependencies
        core_llm_builder = DEFAULTS.provider_to_llm_client_factory[
            test_record["provider"]
        ]
        rag_llm_builder = DEFAULTS.provider_to_llm_client_factory[
            test_record["config"]["proxy_platform"]
        ]
        core_dependencies = build_core_dependencies(
            test_record["strategy"],
            DEFAULTS.ground_experiment_path(test_record["ground_truth_paper_path"]),
            core_llm_builder(test_record["config"]["core_llm"]),
            rag_llm_builder(test_record["config"]["rag_llm"]),
            DEFAULTS.default_embeddings(test_record["config"]["embedding_model"]),
        )

        # build the graph
        goal_workflow = _build_goal_resolution_graph(core_dependencies)
        full_dependencies = merge_dependencies(
            core_dependencies, build_subgraph_dependencies(goal_workflow)
        )
        workflow = build_graph(full_dependencies)
        graph = workflow.graph

        # prepare inputs
        base_state: MassiCoreState = {
            "settings": {
                "runtime_config": {
                    "output_directory": str(
                        DEFAULTS.ground_experiment_path(
                            Path("out") / test_record["short_scenario_x_case_tag"]
                        )
                    ),
                    "working_directory": str(
                        DEFAULTS.ground_experiment_path(
                            test_record["working_copy_data_dir"]
                        )
                    ),
                },
            },
            "goals": [DEFAULTS.schema_to_metadata_goal[test_record["schema"]]],
        }

        # --- Act ---
        thread_config = {"configurable": {"thread_id": str(random.randint(1, 100))}}
        with Laminar.start_as_current_span(
            session_id=test_record["scenario_x_case_tag"],
            name=test_record["short_scenario_x_case_tag"],
            metadata={
                "evaluation_id": evaluation_time_id(f"run-{__name__}"),
                "run_id": id,
                "tag": tag,
            },
        ) as _span:
            with timeit() as timer:
                try:
                    outcome, success = (graph.invoke(base_state, thread_config), True)
                except Exception as e:
                    outcome, success = (
                        {
                            "status": "exception",
                            "error_content": str(e),
                            "error_trace": str(e.__traceback__),
                        },
                        False,
                    )
                Laminar.set_span_output(outcome)
        execution_time = timer()
        logger.info(f"{outcome=}")

        # --- Log ---
        build_log_entry(
            test_record,
            execution_time,
            success=success,
            outcome_json=json.dumps(outcome),
        ).to_csv(log_csv, mode="a", index=False, header=not log_exists)

        # --- Assert ---
        assert success, f"Failed to terminate properly: {str(outcome)}"
