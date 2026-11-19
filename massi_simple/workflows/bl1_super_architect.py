from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from massi_simple.agents.architect import super_architect
from massi_simple.config import MassiConfig
from massi_simple.dto import (
    WorkflowInputs,
    WorkflowState,
)
from massi_simple.workflows.shared import build_and_invoke, prepare_inputs

# Graph Construction
# ------------------


def build_graph(config: MassiConfig) -> CompiledStateGraph:
    return (
        StateGraph(WorkflowState)
        # nodes
        .add_node("prepare_inputs", prepare_inputs(config))
        .add_node("super_architect", super_architect(config))
        # edges
        .add_edge(START, "prepare_inputs")
        .add_edge("prepare_inputs", "super_architect")
        .add_edge("super_architect", END)
        # finish
        .compile()
    )


# Invocation
# ----------


def run(config: MassiConfig, inputs: WorkflowInputs) -> WorkflowState:
    return build_and_invoke(build_graph, config, inputs)
