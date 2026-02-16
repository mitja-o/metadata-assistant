from functools import partial
from statistics import fmean
from typing import Any

import pandas as pd
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import Send
from langgraph.graph import END, START, StateGraph

# Local library implementing business-logic and project-subjective structures.
from massi.agents.constructs import (
    GisResourceGroup,
    GISScoringCollection,
    GISScoringCollectionResponse,
    MessageBuilder,
    ResourceFile,
    ResourcePropertyInferenceState,
)
from massi.agents.interfaces import Dependencies
from massi.agents.tools import walk_working_dir_for_files

# UC2: Resource Properties
# ========================


def scan_directory(
    _: ResourcePropertyInferenceState, seed_path: str = "."
) -> ResourcePropertyInferenceState:
    """
    Walk the current directory and instantiate ResourceFile objects.
    """
    files = walk_working_dir_for_files(seed_path)
    gis_files = [ResourceFile.from_path(p) for p in files]
    return {"files": gis_files}


def score_relevancy(
    state: ResourcePropertyInferenceState, llm: BaseChatModel | None = None
) -> ResourcePropertyInferenceState:
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
    state: ResourcePropertyInferenceState, chunk_file_limit: int = 50
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
    state: ResourcePropertyInferenceState,
) -> ResourcePropertyInferenceState:
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
    state: ResourcePropertyInferenceState,
    destination_file: str = "resource_properties.csv",
) -> ResourcePropertyInferenceState:
    groups = [g.model_dump() for g in state["gis_resource_groups"]]
    groupds_df = pd.DataFrame.from_records(groups)
    groupds_df.to_csv(destination_file, index=False)
    return {"groups_dataframe_file": destination_file}


def build_graph(dependencies: Dependencies):
    llm = dependencies.llm_client

    n: Any = None
    builder = StateGraph(ResourcePropertyInferenceState)
    (
        builder.add_node(n.__name__, np)
        # FIXME(configurability): make the seed path (data directory) configurable externally
        if (n := scan_directory) and (np := partial(n, seed_path="./data"))
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
        # FIXME(configurability): make the resource destination file configurable externally
        and (np := partial(n, destination_file="resource_properties.csv"))
        else ...
    )

    builder.add_edge(START, scan_directory.__name__)
    builder.add_conditional_edges(
        scan_directory.__name__,
        partial(
            prepare_naive_score_batches,
            # FIXME(configurability): make the chunk size configurable externally
            chunk_file_limit=15,
        ),
        [score_relevancy.__name__],
    )
    builder.add_edge(score_relevancy.__name__, group_resources.__name__)
    builder.add_edge(group_resources.__name__, resources_to_description_file.__name__)
    builder.add_edge(resources_to_description_file.__name__, END)

    memory = MemorySaver()
    return builder.compile(checkpointer=memory)
