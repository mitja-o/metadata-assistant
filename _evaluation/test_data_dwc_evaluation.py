from contextlib import contextmanager
import os
from pathlib import Path
import random
from time import perf_counter, time
from typing import Callable, Generator

from dotenv import load_dotenv
from langchain.chat_models import BaseChatModel
from lmnr import Laminar, observe
import pandas as pd
import pytest

from massi.agents.interfaces import Config, create_openai_llm
from massi.agents.team._dto import MetadataGoal, MetadataLevel, MetadataScope
from massi.agents.team.architect import DarwinCoreArchitect
from massi.agents.team.instructors import DataGapDerivationInstructor
from massi.agents.team.operators import DataGapDervationOperator
from massi.agents.team.planner import DarwinCorePlanner
from massi.agents.workflow import (
    Dependencies,
    MassiExecutionMode,
    MassiResolutionWorkflowGraph,
    MassiRuntimeSettings,
    MassiWorkflow,
    _build_goal_resolution_graph,
    build_graph,
)

import logging

logger = logging.getLogger(__name__)

load_dotenv()


class DEFAULTS:
    datasets_dir = "./datasets"
    reports_dir = "./reports"

    lmnr_base_url = "http://0.0.0.0"
    recursion_limit = 30
    turn_limit = 5

    @staticmethod
    def openai_config(model_name) -> Config:
        return Config(
            api_key=os.environ["OPENAI_API_TOKEN"],
            model_name=model_name,
        )

    @classmethod
    def openai_llm(cls, model_name) -> BaseChatModel:
        return create_openai_llm(cls.openai_config(model_name))


# Evaluation Execution
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
    )


@pytest.fixture()
def dwc_metadata_goals() -> list[MetadataGoal]:
    dwc_data_file_metadata_goal: MetadataGoal = {
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
    }
    return [dwc_data_file_metadata_goal]


# Preparation Utilities
# ---------------------


def build_core_dependencies(
    architect_llm: BaseChatModel,
    planner_llm: BaseChatModel,
    operator_llm: BaseChatModel,
    instructor_llm: BaseChatModel,
) -> Dependencies:
    execution_mode: MassiExecutionMode = "data-focus"
    return dict(
        execution_mode=execution_mode,
        architect_map={"darwin_core": DarwinCoreArchitect(architect_llm)},
        planner_map={"darwin_core": DarwinCorePlanner(planner_llm)},
        gap_derivation_instructor_map={
            execution_mode: DataGapDerivationInstructor(instructor_llm)
        },
        derivation_map={
            execution_mode: DataGapDervationOperator(
                operator_llm,
                recursion_limit=DEFAULTS.recursion_limit,
                turn_limit=DEFAULTS.turn_limit,
            )
        },
    )


def build_subgraph_dependencies(graph: MassiWorkflow[MassiResolutionWorkflowGraph]):
    return dict(metadata_resolution_subgraph=graph)


def merge_dependencies(dependencies: Dependencies, extras: Dependencies):
    return dict(**dependencies, **extras)


# Evaluation Scenarios
# --------------------


@observe(session_id=evaluation_time_id(f"run-{__name__}-dwc-X-data"))
@pytest.mark.parametrize(
    "source_dataset,target_dataset,masked_files,target_report,llms",
    [
        (
            "https://dataverse.nl/dataset.xhtml?persistentId=doi:10.34894/72GQ4C",
            "masked-ds1",
            ["meta.xml", "eml.xml"],
            f"{evaluation_key(f"run-{__name__}-dwc-X-data")}-report.csv",
            ([DEFAULTS.openai_llm("gpt-5.4-mini")] * 4),
        ),
        (
            "https://www.kaggle.com/datasets/mpwolke/mammal-collection-bdcj",
            "masked-ds2",
            ["meta.xml", "eml.xml"],
            f"{evaluation_key(f"run-{__name__}-dwc-X-data")}-report.csv",
            ([DEFAULTS.openai_llm("gpt-5.4-mini")] * 4),
        ),
        (
            "https://www.kaggle.com/datasets/nikitamanaenkov/long-term-whale-and-dolphin-observations-in-azores",
            "masked-ds3",
            ["meta.xml", "eml.xml"],
            f"{evaluation_key(f"run-{__name__}-dwc-X-data")}-report.csv",
            ([DEFAULTS.openai_llm("gpt-5.4-mini")] * 4),
        ),
    ],
)
def test_goal_dwc_mode_data_from_empty_metadata(
    source_dataset,
    target_dataset,
    masked_files,
    target_report,
    llms,
    dwc_metadata_goals,
    laminar_observer,
):
    # --- Arrange ---
    eval_id = evaluation_time_id(test_goal_dwc_mode_data_from_empty_metadata.__name__)
    target_dataset_dir = (
        Path(__file__).parent / Path(DEFAULTS.datasets_dir) / target_dataset
    )
    target_report_file = (
        Path(__file__).parent / Path(DEFAULTS.reports_dir) / target_report
    )
    for f in masked_files:
        masked_path = target_dataset_dir / f
        masked_path.unlink() if masked_path.exists() else ...
        logger.info(f">>> Removed {masked_path} <<<")

    settings: MassiRuntimeSettings = {
        "runtime_config": {
            "output_directory": str(target_dataset_dir),
            "working_directory": str(target_dataset_dir),
        }
    }

    core_dependencies = build_core_dependencies(*llms)
    goal_workflow = _build_goal_resolution_graph(core_dependencies)
    full_dependencies = merge_dependencies(
        core_dependencies, build_subgraph_dependencies(goal_workflow)
    )
    workflow = build_graph(full_dependencies)
    graph = workflow.graph

    thread_config = {"configurable": {"thread_id": str(random.randint(1, 100))}}
    input_state = {"settings": settings, "goals": dwc_metadata_goals}

    # --- Act ---
    with timeit() as timer:
        try:
            outcome, success = (graph.invoke(input_state, thread_config), True)
        except Exception as e:
            outcome, success = (
                {
                    "status": "exception",
                    "error_content": str(e),
                    "error_trace": str(e.__traceback__),
                },
                False,
            )
    execution_time = timer()
    logger.info(f"{outcome=}")

    # --- Assert ---
    target_report_exists = target_report_file.exists()
    pd.DataFrame.from_records(
        [
            dict(
                evaluation_timestamp=time(),
                evaluation_id=eval_id,
                success=success,
                target_dataset=target_dataset,
                execution_time_seconds=execution_time,
                source_dataset=f"[]({source_dataset})",
                **outcome,
            )
        ]
    ).to_csv(
        target_report_file,
        mode="a",
        index=False,
        header=(not target_report_exists),
    )

    # -*- Report the evaluation failure to the test runner -*-
    assert success, f"Evaluation failed on exception: {outcome}"
