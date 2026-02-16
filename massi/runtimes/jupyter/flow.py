import pprint

from langgraph.graph import StateGraph


def stream_until_iterruption(graph: StateGraph, *args):
    for event in graph.stream(*args, stream_mode="values"):
        print("\n==== new event ====")
        for k, v in event.items():
            print(f"---- {k} ----")
            pprint.pp(v, indent=4)
