from functools import partial

import pandas as pd
from typing import Any, Dict, List, TypedDict
from pydantic import BaseModel, Field
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent

from massi.agents.interfaces import Dependencies
from massi.agents.constructs import QueryStep, GroupedGisResourceFile


# --- Structured Output Models ---


class ExplorationPlan(BaseModel):
    plan: str = Field(description="Step-by-step logic to derive the metadata")
    python_code: str = Field(
        description="Python code using 'df' to extract the specific value"
    )


class ExtractionOutput(BaseModel):
    value: Any = Field(description="The extracted metadata value")
    confidence: float = Field(ge=0, le=1)


# --- State Definition ---


class DataExplorerState(TypedDict):
    """The state for the data exploration agent."""

    query: QueryStep
    resource: GroupedGisResourceFile
    context: Dict[str, Any] | None
    # Working memory
    df_preview: str  # String representation of CSV head/schema
    analysis_plan: ExplorationPlan
    extraction_result: ExtractionOutput
    messages: List[BaseMessage]
    error: str | None


# --- Nodes ---


def load_csv_preview(state: DataExplorerState) -> DataExplorerState:
    """Loads the CSV and creates a summary for the LLM context."""
    path = state["resource"].file_location
    try:
        df = pd.read_csv(path, nrows=5)
        preview = (
            f"Columns: {list(df.columns)}\n"
            f"Types: \n{df.dtypes.to_string()}\n"
            f"Head: \n{df.head(10).to_string()}"
        )
        return {"df_preview": preview, "error": None}
    except Exception as e:
        return {"error": f"Failed to load CSV: {str(e)}"}


def plan_exploration(state: DataExplorerState, llm: BaseChatModel) -> DataExplorerState:
    """Asks the LLM how to find the specific metadata key in the CSV."""
    system_msg = SystemMessage(
        content=(
            "You are a data scientist. Given a CSV preview and a metadata requirement, "
            "write a short plan and the Python code to extract the value. "
            "Assume the dataframe is available as 'df'."
        )
    )

    prompt = (
        f"Metadata Key to find: {state['query'].key}\n"
        f"Instruction: {state['query'].query}\n"
        f"Context: {state['context']}\n\n"
        f"CSV Preview:\n{state['df_preview']}"
    )

    response = llm.with_structured_output(ExplorationPlan).invoke(
        [system_msg, HumanMessage(content=prompt)]
    )
    return {"analysis_plan": response, "messages": [HumanMessage(content=prompt)]}


def execute_extraction(
    state: DataExplorerState, llm: BaseChatModel
) -> DataExplorerState:
    """A call to a data exploration sub-agent

    Args:
        state (DataExplorerState): input state
        llm (BaseChatModel): the llm that will power the agent

    Returns:
        Dict: outcome state with the result of the value computation
    """
    data = pd.read_csv(state["resource"].file_location)
    pandas_executor = create_pandas_dataframe_agent(
        llm.with_structured_output(ExtractionOutput), data, allow_dangerous_code=True
    )

    system_msg = SystemMessage(
        content="Extract the final value based on the data provided."
    )
    prompt = (
        f"Based on the plan: {state['analysis_plan'].plan}, extract the value for {state['query'].key}."
        f"\nHere is a proposed Python code snippet for inspiration:\n{state['analysis_plan'].python_code}"
    )
    response = pandas_executor.invoke([system_msg, HumanMessage(content=prompt)])
    return {"extraction_result": response}


# --- Graph Construction ---


def build_data_explorer_graph(deps: Dependencies):
    llm = deps.llm_client
    builder = StateGraph(DataExplorerState)

    builder.add_node(load_csv_preview.__name__, load_csv_preview)
    builder.add_node(plan_exploration.__name__, partial(plan_exploration, llm=llm))
    builder.add_node(execute_extraction.__name__, partial(execute_extraction, llm=llm))

    builder.add_edge(START, load_csv_preview.__name__)
    builder.add_edge(load_csv_preview.__name__, plan_exploration.__name__)
    builder.add_edge(plan_exploration.__name__, execute_extraction.__name__)
    builder.add_edge(execute_extraction.__name__, END)

    return builder.compile()
