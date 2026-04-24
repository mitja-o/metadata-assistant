import logging
from functools import partial

from langchain.messages import HumanMessage
from langchain_core.messages import (
    BaseMessage,
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
from massi.agents.team.telecom.author_proxy import IOAuthorQueryClient

logger = logging.getLogger(__name__)

# Interface
# ---------


class AuthorInterviewerProps(OperatorProps):
    io_author_client: IOAuthorQueryClient


type AuthorInterviewerRequest = OperatorRequest


class AuthorInterviewerResponse(OperatorResponse):
    """A local copy of the general operator response."""

    ...


# State
# -----


class AuthorReviewerState(MessagesState, total=False):
    request: AuthorInterviewerRequest
    """The request sent to the interviewer"""
    current_turn: int = 0
    """Current number of questions asked to the author."""
    exploration_result: BaseMessage
    """The raw outcome (AI conclusion or error message) before formal formatting."""
    final_output: AuthorInterviewerResponse
    """The final structured outcome of the interview."""


# System Prompts
# --------------


class AuthorPromptBuilder:
    @staticmethod
    def system_prompt(instruction: str, turn_limit: int, current_turn: int) -> str:
        return f"""
### ROLE
You are a Senior Metadata Specialist and Technical Interviewer. Your expertise lies in extracting precise, structured information from human experts to satisfy complex archival and documentation standards.

### OBJECTIVE
Your current mission is defined by this instruction:
"{instruction}"

### OPERATIONAL PROTOCOL
1. **Instruction-Led Inquiry**: Use the provided instruction as your primary source of truth for terminology and requirements. Do not assume a domain unless it is explicitly stated or implied by the instruction.
2. **Technical Grounding**: Ask well-grounded questions. Explain *why* a piece of information is required based on the instruction (e.g., "To complete the 'Temporal Coverage' section as requested, I need the start and end dates of your observation period").
3. **Efficiency**: Aim for high "Information Density." If an author's response is vague, follow up with clarifying constraints. If it is detailed, extract all relevant variables at once.
4. **Validation**: Check that the provided answers are logically consistent with the instruction's requirements.

### TURN BUDGET
- **Current Turn**: {current_turn} / {turn_limit}
- When the turn limit approaches, pivot to summarizing the best available information.

### CONSTRAINTS
- Rely solely on the dialogue; you cannot access external files.
- Avoid generic pleasantries; remain professional, direct, and helpful.
- Conclude the interview immediately once the specific gap described in the instruction is satisfied.
""".strip()

    @staticmethod
    def refuse_processing_prompt(request: AuthorInterviewerRequest) -> str:
        return f"""
### ROLE
You are the Metadata Interviewer. You cannot proceed because the request is malformed.

### DIAGNOSTICS
- Instruction: {request.get('instruction', 'MISSING')}
- Files Mentioned: {request.get('tabular_files', []) + request.get('plaintext_files', [])}

### MISSION
Explain to the user that you cannot start the interview without a specific instruction. 
Return a professional refusal.
""".strip()

    @staticmethod
    def progress_summary_prompt(
        messages: list[BaseMessage], existing_summary: str
    ) -> str:
        return f"""
### ROLE
You are an Interview Logger. Update the "Discussion Summary" based on the latest exchange.

### CURRENT SUMMARY
{existing_summary or "No progress yet."}

### NEW MESSAGES
{messages}

### INSTRUCTIONS
Update the summary. List:
1. Information already obtained.
2. Questions still pending.
3. User's tone or specific mentions of data unavailability.
Keep it concise.
""".strip()

    @staticmethod
    def format_output_prompt(last_message: str) -> str:
        return f"""
### ROLE
You are a Senior Metadata Synthesizer. Your goal is to transform a dialogue-based interview into a high-integrity, structured metadata record.

### INPUT
The following is the conclusion of a technical interview with a data author:
---
{last_message}
---

### EXTRACTION PROTOCOL
1. **Validation**: Assess if the author provided a definitive value. 
2. **Normalization**: Clean the value of any conversational "noise" (e.g., "The date is 2023-01-01" becomes "2023-01-01").
3. **Outcome Narrative**: Briefly describe the technical path taken to obtain this value (e.g., "The author confirmed the coordinate system as WGS84 after clarifying the sampling equipment used").
4. **Status Mapping**: 
   - Set `success` to `true` ONLY if a specific value satisfying the instruction was obtained.
   - Set `status` to `completed` if the interview reached a logical conclusion.

### CONSTRAINTS
- Return ONLY valid JSON matching the `OperatorResponse` schema.
- If the author was unable to provide the information, set `result_value` to `null` and explain the roadblock in the `outcome`.
- Ensure all technical terms are preserved exactly as provided by the author.

### OUTPUT SCHEMA
{{
    "success": bool,
    "status": "completed" | "rejected",
    "outcome": "string",
    "result_value": "string" | null
}}
""".strip()


# Toolkit
# -------


def make_author_query_tool(author_query_client: IOAuthorQueryClient):
    @tool
    def query_author(query_statement: str) -> str:
        """Asks the author for a specific piece of information via dialogue."""
        try:
            return author_query_client.ask(query_statement)
        except Exception as e:
            return f"Error: {str(e)}"

    return query_author


TOOL_NODE = "tools"
"""A constant used to refer to the tool invocation node."""


# Workflow Actions
# ----------------


# *__Conditional__*
def check_for_usable_request(state: AuthorReviewerState):
    if not state["request"]["instruction"]:
        return refuse_processing.__name__
    return call_interviewer_agent.__name__


def refuse_processing(
    state: AuthorReviewerState, props: AuthorInterviewerProps | None = None
) -> AuthorReviewerState:
    assert props
    model = props["llm_client"]
    assert model
    prompt = AuthorPromptBuilder.refuse_processing_prompt(state["request"])
    response = model.invoke(prompt)
    # We store the response in exploration_result to trigger the final formatter
    return {"exploration_result": response, "messages": [response]}


def call_interviewer_agent(
    state: AuthorReviewerState, props: AuthorInterviewerProps | None = None
) -> AuthorReviewerState:
    assert props
    model = props["llm_client"]
    assert model
    author_query_client = props["io_author_client"]
    assert author_query_client

    tools = [make_author_query_tool(author_query_client)]
    agent = model.bind_tools(tools)

    current_turn = state.get("current_turn", 0) + 1

    system_prompt = AuthorPromptBuilder.system_prompt(
        state["request"]["instruction"], props["turn_limit"], current_turn
    )
    progress_context = SystemMessage(
        content=f"Current Discovery Log:\n{state.get('progress_summary', 'Beginning interview.')}"
    )
    instruction = HumanMessage(content=f"New Task: {state['request']['instruction']}")

    messages = (
        [SystemMessage(content=system_prompt), progress_context]
        + state["messages"]
        + [instruction]
    )

    response = agent.invoke(messages)
    return {"messages": [response], "current_turn": current_turn}


# *__Conditional__*
def tool_or_finalize(state: AuthorReviewerState) -> str:
    return (
        TOOL_NODE
        if state["messages"][-1].tool_calls
        else get_final_exploration_result.__name__
    )


def summarise_progress(
    state: AuthorReviewerState, props: AuthorInterviewerProps | None = None
) -> AuthorReviewerState:
    assert props
    model = props["llm_client"]
    assert model

    prompt = AuthorPromptBuilder.progress_summary_prompt(
        state["messages"], state.get("progress_summary", "")
    )
    response = model.invoke(prompt)

    messages = state["messages"]
    delete_messages = (
        [RemoveMessage(id=m.id) for m in messages[:-2]] if len(messages) > 2 else []
    )

    return {"progress_summary": response.content, "messages": delete_messages}


# *__Conditional__*
def check_turn_budget(
    state: AuthorReviewerState, props: AuthorInterviewerProps | None = None
) -> str:
    """Decides if we allow the agent another turn or force a halt."""
    current_turn = state.get("current_turn", 0)
    turn_limit = props.get("turn_limit", 7)

    if current_turn >= turn_limit:
        return halt_on_exceeded_budget.__name__

    return call_interviewer_agent.__name__


def halt_on_exceeded_budget(
    state: AuthorReviewerState, props: AuthorInterviewerProps | None = None
) -> AuthorReviewerState:
    # Resolved FIXME: Elaborate halting message
    halt_content = (
        f"INTERVIEW HALTED: Maximum turn limit ({props['turn_limit']}) reached. "
        f"The metadata for '{state['request']['instruction']}' could not be finalized."
    )
    halt_msg = SystemMessage(content=halt_content)
    return {"messages": [halt_msg], "exploration_result": halt_msg}


def get_final_exploration_result(state: AuthorReviewerState) -> AuthorReviewerState:
    last_message = state["messages"][-1]
    return {"exploration_result": last_message}


def summarise_output_result(
    state: AuthorReviewerState, props: AuthorInterviewerProps | None = None
) -> AuthorReviewerState:
    assert props
    model = props["llm_client"]
    assert model
    raw_result = state["exploration_result"].content
    prompt = AuthorPromptBuilder.format_output_prompt(raw_result)
    response = model.with_structured_output(AuthorInterviewerResponse).invoke(prompt)
    return {"final_output": response}


# Graph Builder
# -------------


def create_interviewer_subgraph(props: AuthorInterviewerProps):
    builder = StateGraph(AuthorReviewerState)
    author_query_client = props["io_author_client"]

    nodes = [
        (refuse_processing, {}),
        (call_interviewer_agent, {"props": props}),
        (summarise_progress, {"props": props}),
        (halt_on_exceeded_budget, {"props": props}),
        (get_final_exploration_result, {}),
        (summarise_output_result, {"props": props}),
    ]

    for fn, kwargs in nodes:
        node_name = fn.__name__
        node_func = partial(fn, **kwargs) if kwargs else fn
        builder.add_node(node_name, node_func)

    builder.add_node(TOOL_NODE, ToolNode([make_author_query_tool(author_query_client)]))

    # --- Edges ---
    builder.add_conditional_edges(START, check_for_usable_request)

    # Refusal branch
    builder.add_edge(refuse_processing.__name__, summarise_output_result.__name__)

    # Interview branch
    builder.add_conditional_edges(
        call_interviewer_agent.__name__,
        tool_or_finalize,
        [TOOL_NODE, get_final_exploration_result.__name__],
    )

    builder.add_edge(TOOL_NODE, summarise_progress.__name__)

    builder.add_conditional_edges(
        summarise_progress.__name__,
        partial(check_turn_budget, props=props),
        [call_interviewer_agent.__name__, halt_on_exceeded_budget.__name__],
    )

    builder.add_edge(
        halt_on_exceeded_budget.__name__, get_final_exploration_result.__name__
    )
    builder.add_edge(
        get_final_exploration_result.__name__, summarise_output_result.__name__
    )
    builder.add_edge(summarise_output_result.__name__, END)

    return builder.compile()


class AuthorInterviewerAgent:
    def __init__(self, props: AuthorInterviewerProps):
        self._props = props
        self.client = create_interviewer_subgraph(self._props)

    def invoke(self, request: AuthorInterviewerRequest) -> AuthorReviewerState:
        runnable_config = {"recursion_limit": self._props.get("recursion_limit", 25)}
        try:
            return self.client.invoke({"request": request}, config=runnable_config)
        except Exception as e:
            logger.error(e)
            return {
                "request": request,
                "final_output": {
                    "outcome": str(e),
                    "result_value": None,
                    "status": "rejected",
                    "success": False,
                },
            }
