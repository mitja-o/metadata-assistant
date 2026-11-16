from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from massi_simple.agents.architect import super_architect
from massi_simple.config import MassiConfig
from massi_simple.dto import (
    ArchitectInputs,
    Node,
    WorkflowInputs,
    WorkflowState,
)
from massi_simple.utils import get_dataset_overview, get_metadata_schema_overview

# Graph Elements
# --------------


def prepare_inputs(config: MassiConfig) -> Node:
    runtime_config = config["runtime_config"]

    def node(state: WorkflowState) -> WorkflowState:
        workflow_inputs = state["workflow_inputs"]
        architect_inputs: ArchitectInputs = {
            "dataset_overview": get_dataset_overview(
                workflow_inputs.dataset_path,
                csv_head_size=runtime_config["data_overview_csv_head_size"],
            ),
            "metadata_schema": get_metadata_schema_overview(
                workflow_inputs.metadata_schema
            ),
        }
        return {"architect_inputs": architect_inputs}

    return node


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


def initial_state(inputs: WorkflowInputs) -> WorkflowState:
    return {"workflow_inputs": inputs, "messages": []}


def run(config: MassiConfig, inputs: WorkflowInputs) -> WorkflowState:
    return build_graph(config).invoke(initial_state(inputs))
