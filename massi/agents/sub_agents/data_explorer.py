import logging
import shutil
import tempfile
from functools import partial
from pathlib import Path
from typing import Literal, TypedDict

import duckdb
import pandas as pd
from langchain.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

logger = logging.getLogger(__name__)


# Interface
# ---------
class DataExplorerProps(TypedDict):
    llm_client: BaseChatModel | None = None
    recursion_limit: int = 15


class DataExplorerRequest(TypedDict):
    file_paths: list[str]
    """Path to the source files"""
    instruction: str
    """The specific task from the parent graph"""


class DataExplorerResponse(TypedDict):
    success: bool
    status: Literal["rejected", "completed"]
    outcome: str


# State
# -----


class DataExplorerState(MessagesState, total=False):
    request: DataExplorerRequest
    """The request sent to the data explorer"""
    workspace_path: str | None
    """Path to the standardized CSV files ready for analysis"""
    file_map: dict[str, str]
    """Map of original input files to their workspace copies"""
    exploration_result: BaseMessage
    """Final result of the exploration."""
    final_output: DataExplorerResponse
    """Well-formatted response."""


# System Prompts
# --------------


class PromptBuilder:
    @staticmethod
    def sytem_prompt(
        workspace_manifest: str,
        db_dialect: str = "DuckDB",
        db_top_k: int = 10000,
        current_turn: int = 0,
        recursion_limit: int = 25,
    ) -> str:
        return f"""
### ROLE
You are the _massi_ Data Explorer Agent, a specialist in high-performance metadata analysis using {db_dialect} SQL. 

### OPERATIONAL MANIFEST
You MUST use these absolute paths in your SQL 'FROM' clauses:
{workspace_manifest}

### DATABASE DETAILS
You are an expert data analyst interacting with a {db_dialect} database.
Given an input question, create a syntactically correct {db_dialect} SQL query to run, then look at the results and return the answer.

{db_dialect} Specifics:
- Use {db_dialect}-specific functions where appropriate (e.g., EPOCH for scalar time extraction, STRFTIME for formatting).
- {db_dialect} supports reading directly from Parquet/CSVs.
- Never use PostgreSQL-specific functions that do not exist in {db_dialect}.
- Use ONLY Data Query Language (DQL) statements like SELECT. 
- Never modify stored data.
- ALWAYS append `LIMIT {db_top_k}` to your queries unless you are aggregating data, to prevent pulling too many rows.

Only use the tables available to you. Do NOT hallucinate table names.

### RECURSION & BUDGET REFLECTION
- **Current Turn Depth**: {current_turn}
- **Maximum Depth**: {recursion_limit} turns
- Before every tool call, self-reflect: "Is this query likely to succeed, or am I repeating a failure?"
- If you have reached Turn 8 or higher and still haven't found the answer, DO NOT continue guessing. 
- If you cannot find the output due to schema issues, missing data, or repeated SQL errors, STOP immediately.
- In case of failure to find a value, report the following default error message in the relevant field: "ERROR: Analysis exceeded budget or data structure is incompatible."

### TOOL GUIDELINES
1. **Schema First**: Always call `query_dataset` with `DESCRIBE SELECT * FROM '/path/to/file.csv'` to verify structure.
2. **Explicit Joins**: Use the absolute paths provided above. Use aliases for clarity.
3. **Sampling**: Use `LIMIT 5` if you need to see the actual data content to understand the context.

### ANALYSIS PROTOCOL
1. **Discovery**: Check schemas of relevant files.
2. **Execution**: Run SQL to extract metadata or perform aggregations.
3. **Validation**: If a query returns 0 rows, refine your filters.
4. **Finalization**: When the instruction is met, or if you are stuck in a loop, terminate and provide your final report.

### CONSTRAINTS
- Only use SQL.
- Use `ILIKE` for case-insensitive text search.
- Detect and flag PII for the `contains_pii` boolean.
""".strip()

    @staticmethod
    def refuse_processing_prompt(request: DataExplorerRequest) -> str:
        # Extract details for the prompt context
        file_paths = request.get("file_paths", [])
        instruction = request.get("instruction", "")

        return f"""
### ROLE
You are the _massi_ Data Explorer Agent. You have been invoked, but the incoming request is **MALFORMED** or **INCOMPLETE**.

### DIAGNOSTICS
The following request parameters were received:
- **File Paths Provided**: {file_paths if file_paths else "NONE"}
- **Instruction Provided**: "{instruction if instruction else "EMPTY"}"

### REFUSAL PROTOCOL
You must refuse to process this request. Your goal is to provide a structured refusal that identifies the missing requirements so the parent system or user can rectify the input.

**Reason for Refusal:**
{'- Missing file paths: No data source was provided for analysis.' if not file_paths else ''}
{'- Missing instruction: No analytical task was defined.' if not instruction else ''}

### OUTPUT REQUIREMENTS
Do NOT attempt to call any SQL tools. Generate a final response that follows this structure:
1. **Status**: REJECTED
2. **Reason**: A concise explanation of why the input is invalid (e.g., "The request lacks source file paths").
3. **Default Error Message**: "ERROR: Analysis halted due to malformed request parameters."
4. **Action Required**: Advise the caller to provide both a valid `file_path` list and a specific `instruction`.

### Received request:
{request}

Return your response as a clear, technical summary.
""".strip()


# Toolkit
# -------


@tool
def query_dataset(sql_query: str):
    """
    Executes a DuckDB SQL query.
    You must use the absolute paths provided in your instructions for the FROM clause.
    Example: SELECT * FROM '/tmp/massi_123/users.csv' LIMIT 5
    """
    try:
        result = duckdb.query(sql_query).to_df()
        return result.to_markdown()
    except Exception as e:
        return f"SQL Error: {str(e)}.\nEnsure you are using the full absolute paths provided."


# Workflow Actions
# ----------------


# *__Conditional__*
def check_for_usable_request(state: DataExplorerState) -> str:
    return (
        standardise_input_files.__name__
        if (state["request"]["file_paths"] and state["request"]["instruction"])
        else refuse_processing.__name__
    )


def refuse_processing(
    state: DataExplorerState, props: DataExplorerProps | None = None
) -> DataExplorerState:
    assert props
    model = props["llm_client"]
    assert model
    request = state["request"]
    refusal_prompt = PromptBuilder.refuse_processing_prompt(request)
    response = model.invoke(refusal_prompt)
    return {"messages": [response], "exploration_result": response}


def standardise_input_files(state: DataExplorerState) -> DataExplorerState:
    """
    Creates a temporary directory for this specific run and standardizes files.
    """
    tmp_dir = tempfile.mkdtemp(prefix="massi_")
    workspace = Path(tmp_dir)
    file_map: dict[str, str] = {}

    for idx, path_str in enumerate(state["request"]["file_paths"]):
        source = Path(path_str)

        target_name = f"data_{idx}_{source.name.replace('.txt', '.csv')}"
        target_path = workspace / target_name

        if source.suffix.lower() in [".csv"]:
            df = pd.read_csv(source)
            df.to_csv(target_path, index=False)
        else:
            text = source.read_text(encoding="utf-8")
            chunks = [text[i : i + 500] for i in range(0, len(text), 500)]
            pd.DataFrame(
                {"content": chunks, "source": [source.name] * len(chunks)}
            ).to_csv(target_path, index=False)

        file_map[source.name] = str(target_path.absolute())

    return {"workspace_path": str(workspace), "file_map": file_map}


def call_explorer_agent(
    state: DataExplorerState, props: DataExplorerProps | None = None
) -> DataExplorerState:
    """Agent node that uses explicit paths in its SQL."""
    assert props
    model = props["llm_client"]
    assert model
    tools = [query_dataset]
    tool_using_agent = model.bind_tools(tools)

    current_turn = len(
        [m for m in state["messages"] if isinstance(m, HumanMessage)]
    ) + (len(state["messages"]) // 2)
    workspace_manifest = "\n".join(
        [
            f"- {source}: Use path '{workspace_path}'"
            for source, workspace_path in state["file_map"].items()
        ]
    )

    system_prompt = PromptBuilder.sytem_prompt(
        workspace_manifest,
        current_turn=current_turn,
        recursion_limit=props["recursion_limit"],
    )
    system_input = SystemMessage(content=system_prompt)
    user_input = HumanMessage(content=state["request"]["instruction"])

    inputs = [system_input] + state["messages"] + [user_input]
    response = tool_using_agent.invoke(inputs)

    return {"messages": [response]}


def cleanup(state: DataExplorerState):
    """Removes temp files and prepares the final state."""
    path = state.get("workspace_path")
    if path and Path(path).exists():
        shutil.rmtree(path)
        logger.debug(f"massi cleanup: removed workspace: {path}")
    return {"workspace_path": None}


def get_final_exploration_result(state: DataExplorerState) -> DataExplorerState:
    last_message = state["messages"][-1]
    return {"exploration_result": last_message}


def summarise_output_result(
    state: DataExplorerState, props: DataExplorerProps | None = None
) -> DataExplorerState:
    assert props
    model = props["llm_client"]
    assert model
    result = state["exploration_result"]
    assessment_request = PromptBuilder.request_output_assessment(result)
    response: DataExplorerResponse = model.with_structured_output(
        DataExplorerResponse
    ).invoke(assessment_request)
    return {"final_output": response}


# Conditions
# ----------

TOOL_NODE = "tools"


def tool_or_cleanup(state: DataExplorerState) -> str:
    return TOOL_NODE if state["messages"][-1].tool_calls else cleanup.__name__


# Graph Builder
# -------------


def create_explorer_subgraph(props: DataExplorerProps):
    builder = StateGraph(DataExplorerState)

    builder.add_node(TOOL_NODE, ToolNode([query_dataset]))
    nodes = [
        (standardise_input_files, {}),
        (call_explorer_agent, {"props": props}),
        (cleanup, {}),
        (get_final_exploration_output, {}),
    ]
    for fn, kwargs in nodes:
        node_name = fn.__name__
        node_func = partial(fn, **kwargs) if kwargs else fn
        builder.add_node(node_name, node_func)

    builder.add_edge(START, standardise_input_files.__name__)
    builder.add_edge(standardise_input_files.__name__, call_explorer_agent.__name__)
    # Tool loop for the agent to iteratively perform analysis
    builder.add_conditional_edges(
        call_explorer_agent.__name__,
        tool_or_cleanup,
        [TOOL_NODE, cleanup.__name__],
    )
    builder.add_edge(TOOL_NODE, call_explorer_agent.__name__)
    builder.add_edge(cleanup.__name__, get_final_exploration_output.__name__)
    builder.add_edge(get_final_exploration_output.__name__, END)

    return builder.compile()


# Agent Client Interface
# ----------------------


class DataExplorerAgent:
    def __init__(self, model: BaseChatModel, recursion_limit: int = 10):
        self._model = model
        self._recursion_limit = recursion_limit
        self.client = create_explorer_subgraph(
            {"llm_client": self._model, "recursion_limit": recursion_limit}
        )

    def invoke(self, request: DataExplorerRequest) -> DataExplorerState:
        return self.client.invoke(
            {"request": request},
            {"recursion_limit": self._recursion_limit},
        )
