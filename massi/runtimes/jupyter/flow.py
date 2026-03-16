from warnings import deprecated

from langgraph.graph import StateGraph

import massi.runtimes.flow as mf


@deprecated("Use `stream_until_iterruption` from `massi.runtimes.flow` instead.")
def stream_until_iterruption(graph: StateGraph, *args, **kwargs):
    mf.stream_until_iterruption(graph, *args, vebose=True, **kwargs)
