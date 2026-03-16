import pprint

from langgraph.graph import StateGraph


def stream_until_iterruption(graph: StateGraph, *args, verbose=False, **kwargs):
    for event in graph.stream(*args, **kwargs, stream_mode="values"):
        print("\n==== new event ====") if verbose else ...
        if verbose:
            for k, v in event.items():
                print(f"---- {k} ----")
                pprint.pp(v, indent=4)
