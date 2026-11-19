from collections.abc import Callable

from langgraph.graph.state import CompiledStateGraph

from massi_simple.config import MassiConfig
from massi_simple.dto import ArchitectInputs, Node, WorkflowInputs, WorkflowState
from massi_simple.utils import get_dataset_overview, get_metadata_schema_overview

# Common Graph Elements
# ---------------------


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


# Execution
# ---------


def initial_state(inputs: WorkflowInputs) -> WorkflowState:
    return {"workflow_inputs": inputs, "messages": []}


def build_and_invoke(
    graph_builder: Callable[[MassiConfig], CompiledStateGraph],
    config: MassiConfig,
    inputs: WorkflowInputs,
) -> WorkflowState:
    return graph_builder(config).invoke(initial_state(inputs))
