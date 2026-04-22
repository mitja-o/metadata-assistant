import logging
import shutil
import tempfile
from functools import partial
from pathlib import Path

import duckdb
import pandas as pd
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
)
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from massi.agents.team.operators._interface import (
    OperatorProps,
    OperatorRequest,
    OperatorResponse,
)

logger = logging.getLogger(__name__)


# Interface
# ---------

type DataExplorerProps = OperatorProps
type DataExplorerRequest = OperatorRequest


class DataExplorerResponse(OperatorResponse):
    """A local copy of the general operator response."""

    ...


# State
# -----


class DEFAULTS:
    tabular_prefix = "tab_"
    plaintext_prefix = "ref_"


class DataExplorerState(MessagesState, total=False):
    request: DataExplorerRequest
    """The request sent to the data explorer"""
    workspace_path: str | None
    """Path to the standardized CSV files ready for analysis"""
    file_map: dict[str, str]
    """Map of original input files to their workspace copies"""
    current_turn: int = 0
    """Current turn of the exploration."""
    progress_summary: str
    """Summary of the progress and actions take so far"""
    exploration_result: BaseMessage
    """Final result of the exploration."""
    final_output: DataExplorerResponse
    """Well-formatted response."""


# System Prompts
# --------------


class PromptBuilder:
    @staticmethod
    def recursion_limit_context_rule(current_turn: int = 0, turn_limit: int = 5) -> str:
        return f"""
### RECURSION & BUDGET REFLECTION

**Current Turn Depth**: {current_turn}
**Maximum Depth**: {turn_limit} turns

- Before every tool call, self-reflect: "Is this query likely to succeed, or am I repeating a failure?"
- If you have reached Turn 8 or higher and still haven't found the answer, DO NOT continue guessing. 
- If you cannot find the output due to schema issues, missing data, or repeated SQL errors, STOP immediately.
- In case of failure to find a value, report the following default error message in the relevant field: "ERROR: Analysis exceeded budget or data structure is incompatible."

You MUST terminate if {current_turn} is larger than {turn_limit}.
"""

    @staticmethod
    def workspace_manifest_prompt(file_map: dict[str, str]) -> str:
        """
        Creates a strict mapping table to prevent the agent from using
        original file names in SQL queries.
        """
        tab_rows = [
            f"| `{k}` | **`{v}`** |"
            for k, v in file_map.items()
            if Path(v).name.startswith(DEFAULTS.tabular_prefix)
        ]
        ref_rows = [
            f"| `{k}` | **`{v}`** |"
            for k, v in file_map.items()
            if Path(v).name.startswith(DEFAULTS.plaintext_prefix)
        ]

        return f"""
### SQL DATA MANIFEST
**PRIMARY DATA TABLES** (Query these to answer the main instruction):
| Original File | SQL Path |
| :--- | :--- |
{"\n".join(tab_rows)}

**REFERENCE TABLES** (Query these if you need to look up definitions or logic):
| Original File | SQL Path |
| :--- | :--- |
{"\n".join(ref_rows)}
""".strip()

    @classmethod
    def sytem_prompt(
        cls,
        workspace_manifest: str,
        db_dialect: str = "DuckDB",
        db_top_k: int = 300,
        current_turn: int = 0,
        turn_limit: int = 5,
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

#### {db_dialect} Specifics:
- Use {db_dialect}-specific functions where appropriate (e.g., EPOCH for scalar time extraction, STRFTIME for formatting).
- {db_dialect} supports reading directly from Parquet/CSVs.
- Never use PostgreSQL-specific functions that do not exist in {db_dialect}.
- Use ONLY Data Query Language (DQL) statements like SELECT. 
- Never modify stored data.
- ALWAYS append `LIMIT {db_top_k}` to your queries unless you are aggregating data, to prevent pulling too many rows. If more rows are needed, perform subsequent pagination queries to iterative explore the content.

Only use the tables available to you. Do NOT hallucinate table names.

{cls.recursion_limit_context_rule(current_turn, turn_limit)}

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

### TOOL CALLS RESTRICTIONS
- You are an assistant with access to tools. Call at most one tool per turn. If multiple steps are needed, call one, wait for results, then continue.
- If after {turn_limit} turns you do not get a satisfactory answer, report the default error message: "ERROR: Analysis exceeded budget or data structure is incompatible."

### PATH DE-CONFLICTION
- The user instruction may contain local paths and/or plaintext files like: `/usr/foo/data.txt`.
- YOU MUST IGNORE THESE. They are environment-specific and can cause SQL errors.
- ALWAYS check the manifest first: e.g. if `data.txt` is listed under **PRIMARY DATA**, use the provided `.csv` path. 
- ONLY USE the safe standardised paths provided in the **OPERATIONAL MANIFEST**.
- If a file in the instruction is not in the manifest, report an error immediately.
""".strip()

    @staticmethod
    def summarise_progress_prompt(
        messages: list[BaseMessage], existing_summary: str
    ) -> str:
        return f"""
### ROLE
You are a Research Logger for a Data Explorer Agent. Your job is to update a running "Discovery Log" that tracks the technical progress of a data investigation.

### CURRENT LOG
{existing_summary if existing_summary else "No progress recorded yet."}

### NEW ACTIVITY TO INCORPORATE
{messages}

### INSTRUCTIONS
Update the Discovery Log by distilling the new activity into the following structure. Be concise but technically specific:

1. **Schema Knowledge**: List confirmed table names, columns, and data types found via `DESCRIBE` or sampling.
2. **Successful Queries**: Summarize what was learned from successful SQL executions (e.g., "Found that 'user_id' matches the 'id' column in file_B").
3. **Failed Attempts**: Explicitly note SQL errors or queries that returned 0 rows. State *why* they failed if known (e.g., "Case-sensitivity issue with 'Country' column").
4. **Current Status**: State exactly what part of the user's instruction remains unanswered.
5. **Forbidden Actions**: Based on failures, list what the agent MUST NOT try again (e.g., "Do not attempt to query the .txt extension; DuckDB requires the .csv path").

### CRITICAL RULES
- Do NOT repeat the entire history; append or update facts.
- Keep the summary focused on **data structure and content findings**.
- If a specific file path was found to be empty or missing, highlight it prominently.
- Format as a clean, bulleted technical brief.
""".strip()

    @staticmethod
    def refuse_processing_prompt(request: DataExplorerRequest) -> str:
        # Extract details for the prompt context
        plaintext_files = request.get("plaintext_files", [])
        tabular_files = request.get("tabular_files")
        instruction = request.get("instruction", "")
        miex_file_paths = plaintext_files + tabular_files

        return f"""
### ROLE
You are the _massi_ Data Explorer Agent. You have been invoked, but the incoming request is **MALFORMED** or **INCOMPLETE**.

### DIAGNOSTICS
The following request parameters were received:
- **Plaintext File Paths Provided**: {plaintext_files if plaintext_files else "NONE"}
- **Tabular File Paths Provided**: {tabular_files if tabular_files else "NONE"}
- **Instruction Provided**: "{instruction if instruction else "EMPTY"}"

### REFUSAL PROTOCOL
You must refuse to process this request. Your goal is to provide a structured refusal that identifies the missing requirements so the parent system or user can rectify the input.

**Reason for Refusal:**
{'- Missing file paths: No data source was provided for analysis.' if not miex_file_paths else ''}
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

    @staticmethod
    def summarize_exploration_prompt(exploration_outcome: str) -> str:
        return f"""
### ROLE
You are the _massi_ Output Formatter. Your task is to distill raw technical exploration logs into a structured JSON response.

### INPUT DATA
The raw outcome of the data exploration process is:
---
{exploration_outcome}
---

### EXTRACTION RULES
1. **success**: 
   - Set to `true` if a specific value, identifier, or answer requested in the instruction was found.
   - Set to `false` if the agent encountered a terminal error, reached a recursion limit, or explicitly stated the information is missing.
2. **status**: 
   - Use `"rejected"` ONLY if the initial request was malformed or lacked files/instructions.
   - Use `"completed"` for all other cases where an analysis was attempted.
3. **outcome**: 
   - Provide a concise (1-2 sentences) professional summary of the discovery path (e.g., "Identified column 'X' as the primary key and extracted the corresponding URI").
4. **result_value**:
   - This is the **Target Value**. It represents the specific "answer" to the query.
   - **Priority**: If the output contains a URI, a formal ID, a specific category label, or a calculated metric (sum/count), extract that value alone.
   - **Cleaning**: Remove ALL markdown formatting (backticks, bolding, italics).
   - **Constraint**: If the result is a description rather than a single value, provide the most significant keyword or identifier from that description.
   - Set to `null` if no definitive value could be isolated.
   - If the instruction provided a specific fallback (e.g., 'Use default value `X`), and the agent mentions it, use it.

### OUTPUT FORMAT
Return ONLY a valid JSON object.
{{
    "success": bool,
    "status": "rejected" | "completed",
    "outcome": "string", 
    "result_value": "string" | null
}}
""".strip()


# Toolkit
# -------


@tool
def query_dataset(sql_query: str) -> str:
    """
    Executes a DuckDB SQL query.

    Important:
        You must use the absolute paths provided in your instructions for the FROM clause.
        Example: SELECT * FROM '/tmp/massi_123/users.csv' LIMIT 5

    Args:
        sql_query (str): the query to be executed.

    Returns:
        str: result of the query execution:
            - If success, the result of the query formatted as a markdown table.
            - If errors occur, the error summary message.
    """
    try:
        result = duckdb.query(sql_query).to_df()
        return result.to_markdown()
    except Exception as e:
        return f"SQL Error: {str(e)}.\nEnsure you are using the full absolute paths provided."


TOOL_NODE = "tools"
"""A constant used to refer to the tool invocation node."""


# Workflow Actions
# ----------------


# *__Conditional__*
def check_for_usable_request(state: DataExplorerState) -> str:
    return (
        standardise_input_files.__name__
        if (
            (state["request"]["plaintext_files"] or state["request"]["tabular_files"])
            and state["request"]["instruction"]
        )
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


# FIXME(effeciency): delegate this task upstream to avoid reruns on each gap derivation
def standardise_input_files(state: DataExplorerState) -> DataExplorerState:
    """Standardizes tabular data into a consistent format and chunks plaintext files into queryable CSVs."""
    workspace = Path(tempfile.mkdtemp(prefix="massi_"))
    tabular_files = state["request"].get("tabular_files", [])

    # Standardise tabular files
    tabular_file_map = {
        Path(f).name: str(
            (workspace / f"{DEFAULTS.tabular_prefix}_{i}_{Path(f).stem}.csv").absolute()
        )
        for i, f in enumerate(tabular_files)
    }
    tabular_source_target_pairs = zip(tabular_files, tabular_file_map.values())
    for src, dst in tabular_source_target_pairs:
        try:
            pd.read_csv(src, sep=None, engine="python").to_csv(dst, index=False)
        except Exception as e:
            logger.error(f"Could not standardise tabular file `{src}` into `dst`: {e}")

    # Standardise tabular files
    plaintext_files = state["request"].get("plaintext_files", [])
    plaintext_file_map = {
        Path(f).name: str(
            (
                workspace / f"{DEFAULTS.plaintext_prefix}_{i}_{Path(f).stem}.csv"
            ).absolute()
        )
        for i, f in enumerate(plaintext_files)
    }
    plaintext_source_target_pairs = zip(plaintext_files, plaintext_file_map.values())
    for src, dst in plaintext_source_target_pairs:
        txt = Path(src).read_text(encoding="utf-8")
        chunks = [txt[i : i + 500] for i in range(0, len(txt), 500)]
        try:
            pd.DataFrame({"chunk_id": range(len(chunks)), "content": chunks}).to_csv(
                dst, index=False
            )
        except Exception as e:
            logger.error(
                f"Could not standardise plaintext file `{src}` into `dst`: {e}"
            )

    return {
        "workspace_path": str(workspace),
        "file_map": {**tabular_file_map, **plaintext_file_map},
    }


def call_explorer_agent(
    state: DataExplorerState, props: DataExplorerProps | None = None
) -> DataExplorerState:
    """Agent node that uses explicit paths in its SQL."""
    assert props
    model = props["llm_client"]
    assert model
    tools = [query_dataset]
    tool_using_agent = model.bind_tools(tools, parallel_tool_calls=False)

    workspace_manifest = PromptBuilder.workspace_manifest_prompt(state["file_map"])
    current_turn = state.get("current_turn", 0)
    turn_limit = props["turn_limit"]
    system_prompt = PromptBuilder.sytem_prompt(
        workspace_manifest, current_turn=current_turn, turn_limit=turn_limit
    )
    system_input = SystemMessage(content=system_prompt)
    progress_summary = state.get("progress_summary", "")
    user_prompt = f"{PromptBuilder.recursion_limit_context_rule(current_turn=current_turn, turn_limit=turn_limit)}\n\n{state["request"]["instruction"]}"
    user_input = HumanMessage(content=user_prompt)

    inputs = (
        [system_input]
        + [SystemMessage(content=progress_summary)]
        + state["messages"]
        + [user_input]
    )
    response = tool_using_agent.invoke(inputs)

    return {"messages": [response], "current_turn": current_turn + 1}


# *__Conditional__*
def tool_or_cleanup(state: DataExplorerState) -> str:
    return TOOL_NODE if state["messages"][-1].tool_calls else cleanup.__name__


def summarize_progress(
    state: DataExplorerState, props: DataExplorerProps | None = None
) -> DataExplorerState:
    """
    Summarises the progress of the exploration in a form of a structured work log.
    Important: removes the message history up to the two last steps.
    """
    assert props
    model = props["llm_client"]
    assert model

    summarise_prompt = PromptBuilder.summarise_progress_prompt(
        state["messages"], state.get("progress_summary", "")
    )
    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]
    response = model.invoke(summarise_prompt)

    return {"progress_summary": response.content, "messages": delete_messages}


# *__Conditional__*
def check_turn_budget(state: DataExplorerState, props: DataExplorerProps) -> str:
    """Decides if we allow the agent another turn or force a halt."""
    current_turn = state.get("current_turn", 0)
    turn_limit = props.get("turn_limit", 7)

    if current_turn >= turn_limit:
        return halt_on_exceeded_budget.__name__

    return call_explorer_agent.__name__


def halt_on_exceeded_budget(
    state: DataExplorerState, props: DataExplorerProps | None = None
) -> DataExplorerState:
    """
    Final node when budget is spent.
    Combines the summary and the final tool result for the formatter.
    """
    assert props
    summary = state.get("progress_summary", "No summary available.")
    last_result = (
        state["messages"][-1].content if state["messages"] else "No final query result."
    )

    halt_content = (
        f"### HALTING CONDITION REACHED\n"
        f"The agent has reached the maximum turn limit ({props['turn_limit']}).\n\n"
        f"**Final Reached Result:**\n{last_result}\n\n"
        f"**Exploration Summary:**\n{summary}\n\n"
        f"**Final Status**: ERROR: Analysis exceeded budget or data structure is incompatible."
    )

    halt_message = SystemMessage(content=halt_content)
    return {"messages": [halt_message]}


def get_final_exploration_result(state: DataExplorerState) -> DataExplorerState:
    last_message = state["messages"][-1]
    return {"exploration_result": last_message}


def cleanup(state: DataExplorerState):
    """Removes temp files and prepares the final state."""
    path = state.get("workspace_path")
    if path and Path(path).exists():
        shutil.rmtree(path)
        logger.debug(f"massi cleanup: removed workspace: {path}")
    return {"workspace_path": None}


def summarise_output_result(
    state: DataExplorerState, props: DataExplorerProps | None = None
) -> DataExplorerState:
    assert props
    model = props["llm_client"]
    assert model
    result = state["exploration_result"]
    assessment_request = PromptBuilder.summarize_exploration_prompt(result)
    response: DataExplorerResponse = model.with_structured_output(
        DataExplorerResponse
    ).invoke(assessment_request)
    return {"final_output": response}


# Graph Builder
# -------------


def create_explorer_subgraph(props: DataExplorerProps):
    builder = StateGraph(DataExplorerState)

    builder.add_node(TOOL_NODE, ToolNode([query_dataset]))
    nodes = [
        (refuse_processing, {"props": props}),
        (standardise_input_files, {}),
        (call_explorer_agent, {"props": props}),
        (summarize_progress, {"props": props}),
        (halt_on_exceeded_budget, {"props": props}),
        (cleanup, {}),
        (get_final_exploration_result, {}),
        (summarise_output_result, {"props": props}),
    ]
    for fn, kwargs in nodes:
        node_name = fn.__name__
        node_func = partial(fn, **kwargs) if kwargs else fn
        builder.add_node(node_name, node_func)

    builder.add_conditional_edges(
        START,
        check_for_usable_request,
        [refuse_processing.__name__, standardise_input_files.__name__],
    )
    # Refusal branch
    builder.add_edge(refuse_processing.__name__, summarise_output_result.__name__)
    # Exploration branch
    builder.add_edge(standardise_input_files.__name__, call_explorer_agent.__name__)
    # Tool loop for the agent to iteratively perform analysis
    builder.add_conditional_edges(
        call_explorer_agent.__name__,
        tool_or_cleanup,
        [TOOL_NODE, cleanup.__name__],
    )
    builder.add_edge(TOOL_NODE, summarize_progress.__name__)
    builder.add_conditional_edges(
        summarize_progress.__name__,
        partial(check_turn_budget, props=props),
        [call_explorer_agent.__name__, halt_on_exceeded_budget.__name__],
    )
    builder.add_edge(halt_on_exceeded_budget.__name__, cleanup.__name__)
    builder.add_edge(cleanup.__name__, get_final_exploration_result.__name__)
    builder.add_edge(
        get_final_exploration_result.__name__, summarise_output_result.__name__
    )
    builder.add_edge(summarise_output_result.__name__, END)

    return builder.compile()


# Agent Client Interface
# ----------------------


class DataExplorerAgent:
    def __init__(self, props: DataExplorerProps):
        self._props = props
        self.client = create_explorer_subgraph(self._props)

    def invoke(self, request: DataExplorerRequest) -> DataExplorerState:
        runnable_config = {"recursion_limit": self._props.get("recursion_limit", 25)}
        try:
            return self.client.invoke(
                {"request": request},
                runnable_config={
                    "recursion_limit": self._props.get("recursion_limit", 25)
                },
            )
        except Exception as e:
            logger.error(e)
            return {
                **self.client.get_state(runnable_config).values,
                "request": request,
                "final_output": {
                    "outcome": str(e),
                    "result_value": None,
                    "status": "rejected",
                    "success": False,
                },
            }
