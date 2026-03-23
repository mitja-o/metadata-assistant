import warnings
from functools import partial
from statistics import fmean
from typing import Any

import pandas as pd
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

# Local library implementing business-logic and project-subjective structures.
from massi.agents.constructs import (
    GisResourceGroup,
    GISScoringCollection,
    GISScoringCollectionResponse,
    MessageBuilder,
    QueryPlanExecutionState,
    ResourceFile,
    ResourcePropertyGroupingState,
    flatten_resource_groups,
)
from massi.agents.interfaces import Dependencies
from massi.agents.tools import walk_working_dir_for_files

# UC2: Resource Properties
# ========================


class Defaults:
    # FIXME(configurability): make the seed path (data directory) configurable externally
    seed_path = "./data"
    # FIXME(configurability): make the resource destination file configurable externally
    destination_file = "resource_properties.csv"
    # FIXME(configurability): make the chunk size configurable externally
    chunk_file_limit = 15


def scan_directory(
    _: ResourcePropertyGroupingState, seed_path: str = "."
) -> ResourcePropertyGroupingState:
    """
    Walk the current directory and instantiate ResourceFile objects.
    """
    files = walk_working_dir_for_files(seed_path)
    gis_files = [ResourceFile.from_path(p) for p in files]
    return {"files": gis_files}


def score_relevancy(
    state: ResourcePropertyGroupingState, llm: BaseChatModel | None = None
) -> ResourcePropertyGroupingState:
    """
    Pass the list of filenames/extensions to the LLM. The LLM returns a score (0.0 - 1.0) based on GIS signatures (e.g., .shp, .geojson).
    """
    messages = [
        HumanMessage(MessageBuilder.gis_file_relevancy_score_assessment_request(state))
    ]
    response = llm.with_structured_output(GISScoringCollectionResponse).invoke(messages)
    return {"messages": messages, "gis_scored_files": response.entries}


# Mapper Utility
# ~~~~~~~~~~~~~~
def prepare_naive_score_batches(
    state: ResourcePropertyGroupingState, chunk_file_limit: int = 50
):
    """
    This function chunks the discovered files into small (safe for common context window sizes) batches for LLM scoring.

    Notes:
        - Each chunk is configured to a conservative file count threshold, controlled by `chunk_file_limit`.
        - Each 'Send' object triggers a parallel instance of 'score_relevancy'.
    """
    return [
        Send(score_relevancy.__name__, {**state, "files": batch})
        for i in range(0, len(state["files"]), chunk_file_limit)
        if (batch := state["files"][i : i + chunk_file_limit])
    ]


# ~~~~~~~~~~~~~~


def group_resources(
    state: ResourcePropertyGroupingState,
) -> ResourcePropertyGroupingState:
    """Group resources by resource names"""
    scored_gis_files = state.get("gis_scored_files") or []
    resource_groups: dict[str, GISScoringCollection] = {}
    for f in scored_gis_files:
        resource_groups.setdefault(f.filename.split(".")[0], []).append(f)
    gis_resource_groups = [
        GisResourceGroup(resource_name=k, entries=vs, group_score=gs)
        for k, vs in resource_groups.items()
        if (gs := fmean((v.gis_relevancy_score for v in vs)))
    ]
    return {"gis_resource_groups": gis_resource_groups}


def resources_to_description_file(
    state: ResourcePropertyGroupingState,
    destination_file: str = "resource_properties.csv",
) -> ResourcePropertyGroupingState:
    groups = state["gis_resource_groups"]
    entries = flatten_resource_groups(groups)
    entries_ef = pd.DataFrame.from_records([e.model_dump() for e in entries])
    entries_ef.to_csv(destination_file, index=False)
    return {
        "grouped_resource_entries": entries,
        "resource_dataframe_file": destination_file,
    }


# Query Planning and Execution
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def plan_metadata_inference(
    state: ResourcePropertyGroupingState, llm: BaseChatModel | None = None
) -> ResourcePropertyGroupingState:
    # FIXME: implement
    warnings.warn("Planning is not yet implemented", RuntimeWarning)
    return state


def pull_next_metadata_inference_step(
    state: ResourcePropertyGroupingState,
) -> ResourcePropertyGroupingState:
    # FIXME: implement
    warnings.warn("Metadata inference execution is not yet implemented", RuntimeWarning)
    return state


def execute_metadata_inference_step(
    state: ResourcePropertyGroupingState, llm: BaseChatModel | None = None
) -> ResourcePropertyGroupingState:
    # FIXME: implement
    warnings.warn("Metadata inference is not yet implemented", RuntimeWarning)
    return state


def register_metadata_inference_step(
    state: ResourcePropertyGroupingState, llm: BaseChatModel | None = None
) -> ResourcePropertyGroupingState:
    # FIXME: implement
    warnings.warn("Metadata inference is not yet implemented", RuntimeWarning)
    return state


def is_query_plan_completed(
    state: ResourcePropertyGroupingState,
) -> QueryPlanExecutionState:
    # FIXME: implement
    warnings.warn("Metadata inference is not yet implemented", RuntimeWarning)
    return QueryPlanExecutionState.STOP


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def build_graph(dependencies: Dependencies):
    llm = dependencies.llm_client

    n: Any = None
    builder = StateGraph(ResourcePropertyGroupingState)
    (
        builder.add_node(n.__name__, np)
        if (n := scan_directory) and (np := partial(n, seed_path=Defaults.seed_path))
        else ...
    )
    (
        builder.add_node(n.__name__, np)
        if (n := score_relevancy) and (np := partial(n, llm=llm))
        else ...
    )
    builder.add_node(n.__name__, n) if (n := group_resources) else ...
    (
        builder.add_node(n.__name__, np)
        if (n := resources_to_description_file)
        and (np := partial(n, destination_file=Defaults.destination_file))
        else ...
    )
    (
        builder.add_node(n.__name__, np)
        if (n := plan_metadata_inference) and (np := partial(n, llm=llm))
        else ...
    )
    builder.add_node(n.__name__, n) if (n := pull_next_metadata_inference_step) else ...
    (
        builder.add_node(n.__name__, np)
        if (n := execute_metadata_inference_step) and (np := partial(n, llm=llm))
        else ...
    )
    (
        builder.add_node(n.__name__, np)
        if (n := register_metadata_inference_step) and (np := partial(n, llm=llm))
        else ...
    )

    builder.add_edge(START, scan_directory.__name__)
    builder.add_conditional_edges(
        scan_directory.__name__,
        partial(
            prepare_naive_score_batches, chunk_file_limit=Defaults.chunk_file_limit
        ),
        [score_relevancy.__name__],
    )
    builder.add_edge(score_relevancy.__name__, group_resources.__name__)
    builder.add_edge(group_resources.__name__, resources_to_description_file.__name__)
    builder.add_edge(
        resources_to_description_file.__name__, plan_metadata_inference.__name__
    )
    builder.add_edge(
        plan_metadata_inference.__name__, pull_next_metadata_inference_step.__name__
    )
    builder.add_edge(
        pull_next_metadata_inference_step.__name__,
        execute_metadata_inference_step.__name__,
    )

    builder.add_edge(
        execute_metadata_inference_step.__name__,
        register_metadata_inference_step.__name__,
    )
    builder.add_conditional_edges(
        register_metadata_inference_step.__name__,
        is_query_plan_completed,
        {
            # FIXME(upstream-issue): when rendering mermaid, this should be wrapped in `"` because `.` in the key breaks mermaid rendering
            QueryPlanExecutionState.STOP: END,
            QueryPlanExecutionState.ACT: pull_next_metadata_inference_step.__name__,
        },
    )

    memory = MemorySaver()
    return builder.compile(checkpointer=memory), dict()
