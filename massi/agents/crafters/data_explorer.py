from functools import partial
from typing import Any, Dict, List, TypedDict

import pandas as pd
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from massi.agents.constructs import GroupedGisResourceFile, QueryStep
from massi.agents.interfaces import Dependencies

# --- Structured Output Models ---


class ExplorationPlan(BaseModel):
    plan: str = Field(description="Step-by-step logic to derive the metadata")
    python_code: str = Field(
        description="Python code using 'df' to extract the specific value"
    )


# --- State Definition ---


class DataExplorerState(TypedDict):
    """The state for the data exploration agent."""

    query: QueryStep
    resource: GroupedGisResourceFile
    context: Dict[str, Any] | None
    # Working memory
    df_preview: str  # String representation of CSV head/schema
    analysis_plan: ExplorationPlan
    extraction_result: str
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


# FIXME(feature): shortcut computation if answer is directly clear from the context
def plan_exploration(state: DataExplorerState, llm: BaseChatModel) -> DataExplorerState:
    """Asks the LLM how to find the specific metadata key in the CSV."""
    system_msg = SystemMessage(
        content=(
            "You are a data scientist. Given a CSV preview and a metadata requirement, "
            "write a short plan and the Python code to extract the value. "
            "Assume the dataframe is available as 'df'. "
        )
    )

    prompt = (
        f"Metadata Key to find: {state['query'].key}\n"
        f"Instruction: {state['query'].query}\n"
        f"Resource: {state['resource']}\n"
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
        llm,
        data,
        allow_dangerous_code=True,
        prefix=(
            "If you realise that it is not possible to extract the value from the provided file, report this realisation as your answer:\n"
            "```Thought: <reasoning that lead to the answer> \nFinal Answer: <explanation that the value can not be computed based on the given file>\n```\n"
            "If the context provides sufficient information to answer the question without any computation, provide the answer directly.\n"
            "Report the final result as ```\nThought: <reasoning that lead to the answer> \nFinal Answer: <value>\n```\n."
            "ALWAYS adhere to the required output formats: `Thought-Action-Action_Input` for intermediate steps, and `Thought-Final_Answer` for final answers.\n\n"
            f"Resource Context:\n<investigated-resource>\n{state.get("resource", {})}\n</investigated-resource>"
        ),
    )

    system_msg = SystemMessage(
        content="Extract the final value based on the data provided."
    )
    prompt = f"Based on the plan: {state['analysis_plan'].plan}, extract the value for {state['query'].key}. "
    response = pandas_executor.invoke(
        [
            system_msg,
            HumanMessage(content=prompt),
            HumanMessage(content=state["query"].query),
        ]
    )
    return {"extraction_result": response.get("output", "")}


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
