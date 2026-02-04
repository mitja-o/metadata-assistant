from functools import partial
from typing import Any

from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from massi.agents.constructs import (
    GISScoringCollection,
    MessageBuilder,
    ResourceFile,
    ResourcePropertyInferenceState,
)
from massi.agents.interfaces import Dependencies
from massi.agents.tools import walk_working_dir_for_files

# UC2: Resource Properties
# ========================


def scan_directory() -> ResourcePropertyInferenceState:
    """
    Walk the current directory and instantiate ResourceFile objects.
    """
    files = walk_working_dir_for_files()
    gis_files = [ResourceFile.from_path(p) for p in files]
    return {"files": gis_files}


def score_relevancy(
    state: ResourcePropertyInferenceState, llm: BaseChatModel | None = None
) -> ResourcePropertyInferenceState:
    """
    Pass the list of filenames/extensions to the LLM. The LLM returns a score (0.0 - 1.0) based on GIS signatures (e.g., .shp, .geojson).
    """
    messages = [MessageBuilder.gis_file_relevancy_score_assessment_request(state)]
    response = llm.with_structured_output(GISScoringCollection).invoke(messages)
    return {"messages": messages, "gis_scored_files": response}


def build_graph(dependencies: Dependencies):
    llm = dependencies.llm_client

    n: Any = None
    builder = StateGraph(ResourcePropertyInferenceState)
    builder.add_node(n.__name__, n) if (n := scan_directory) else ...
    (
        builder.add_node(n.__name__, np)
        if (n := score_relevancy) and (np := partial(n, llm=llm))
        else ...
    )

    builder.add_edge(START, scan_directory.__name__)
    builder.add_edge(scan_directory.__name__, score_relevancy.__name__)
    builder.add_edge(score_relevancy.__name__, END)

    memory = MemorySaver()
    return builder.compile(checkpointer=memory)
