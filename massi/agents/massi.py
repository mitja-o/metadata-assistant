from enum import Enum
from functools import partial
import json
import pathlib as pl
from dataclasses import dataclass

from jsonschema import ValidationError
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_ollama import ChatOllama
from langgraph.graph import START, END, StateGraph, MessagesState
from jsonschema.validators import Draft202012Validator


from massi.agents.constructs import QueryPlan, QueryStepId, QueryPrompt
import massi.agents.tools as massi_toolkit

# UC1: Base Metadata
# ==================


class BaseMetadataState(MessagesState):
    base_metadata_files: list[str]
    selected_base_metadata_file: str
    schema_validation_errors: list[ValidationError]
    errors_summary: AIMessage
    query_plan: QueryPlan
    query_plan_completed: bool
    current_step_id: None | QueryStepId
    current_query_prompt: None | QueryPrompt


class MessageBuilder:
    @staticmethod
    def error_validation_system_message(_: BaseMetadataState):
        return """
You are reviewing a set of JSON schema validator errors for a MIAGIS base metadata file.
You should translate ALL erors into a human-readable descriptions.

You MUST report the original errors as a human-friendly formatter bullet-point list in your response.
"""

    @staticmethod
    def error_to_model_request(state: BaseMetadataState):
        return f"""
Here are the received JSON schema validation errors:
{'\n-'.join([f'<Error>{str(e)}</Error>' for e in state["schema_validation_errors"]])}
"""

    @staticmethod
    def error_resolution_planning_system_message(_: BaseMetadataState):
        return """
You are an experienced data steward collecting the base metadata for a MIAGIS file.
MIAGIS files organise the metadata for geospatial (GIS) data depositories.
Base metadata provides an overview of the overall project.

You given the missing attributes specified as JSON schema validation errors, design the interview plan to retrieve the missing information from the user.
You should guide the users to be elaborate and non-ambiguous. Please rely on the fact that the data we are describing is used for GIS. Reflect this in the query you direct at the user.

The query plan should be an ordered sequence of queries you would like to ask to the data creator.
Example query plan can be: 
<example>
{"queries": {
    1: {"id": 1, "key": "unique-id", "json_path": "$.id", "priority": 5, "query": "Please provide a unique identifier for this data entry."},
    2: {"id": 2, "key": "final-outcomes", "json_path": "$.outcomes", "priority": 4, "query": "Please list all reusable outcomes of your data project. Think what is useful to know to the future users of your data."},
    # and so on ... 
}}
</example>


You MUST respond with a JSON-structure with the following format: 
<format required-output-format="application/json">
{"queries": {
    <id>: {
        "id": <natural number ID to uniquely identify the step>
        "key": <brief identifier of the purpose of the query, should be written in snake case: e.g. foo_baz>
        "json_path": <path of the json property that this query intends to complete>,
        "priority": <integer value from 0 to 5 indicating how high is the priority of this query, 5 - needs to be asked as soon as possible, 0 - can be asked later>,
        "query": <short but clear and sufficient human-readable query aimed to retrieve the value for the given key_path attribute in the error>
    }
}}
</format>
"""


# {"MODEL_URL": "http://host.docker.internal:11434", "MODEL_NAME": "granite4:3b"}
# base_config = dict(MODEL_URL="http://127.0.0.1:11434", MODEL_NAME="granite4:3b")


@dataclass
class Config:
    model_url: str
    model_name: str


class Defaults:
    base_metadata_file = "base_metadata.json"
    base_metadata_json_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "entry_version": {"type": "integer", "minimum": 1},
            "entry_id": {"type": "string", "minLength": 1},
            "description": {"type": "string", "minLength": 1},
            "products": {"type": "array", "items": {"type": "string", "minLength": 1}},
        },
        "required": [
            "entry_version",
            "entry_id",
            "description",
            "products",
        ],
    }
    base_metadata_json_schema_validator = Draft202012Validator(
        base_metadata_json_schema
    )


class QueryPlanExecutionState(Enum):
    STOP = 0
    ACT = 1


def create_ollama_llm(config: Config) -> ChatOllama:
    return ChatOllama(
        base_url=config.model_url,
        model=config.model_name,
        # format="json"  # forces structured JSON output
    )


def ensure_metadata_file_presence(_: BaseMetadataState) -> BaseMetadataState:
    n_state = {}
    found_files = massi_toolkit.glob_file_search(f"**/{Defaults.base_metadata_file}")

    if not found_files:
        default_path = pl.Path(".") / Defaults.base_metadata_file
        default_path.write_text(json.dumps({}))
        n_state["base_metadata_files"] = [str(default_path)]

    else:
        n_state["base_metadata_files"] = found_files

    assert (
        len(n_state["base_metadata_files"]) > 0
    ), "At least one base metadata file must be present"

    return n_state


def select_working_base_metadata_file(state: BaseMetadataState) -> BaseMetadataState:
    return {"selected_base_metadata_file": state["base_metadata_files"][0]}


def check_metadata_completion(state: BaseMetadataState) -> BaseMetadataState:
    n_state = {}
    with open(state["selected_base_metadata_file"], "r") as bmf:
        base_metadata = json.load(bmf)
        n_state["schema_validation_errors"] = [
            {
                "message": e.message,
                "encountered_value": e.validator_value,
                "json_path": e.json_path,
                "failed_key": e.validator,
            }
            for e in Defaults.base_metadata_json_schema_validator.iter_errors(
                base_metadata
            )
        ] or []
    assert "schema_validation_errors" in n_state, "Errors not set!"
    return n_state


def interpret_metadata_checks(
    state: BaseMetadataState, llm: BaseChatModel | None = None
) -> BaseMetadataState:
    assert "schema_validation_errors" in state, str(state)
    assert llm, "LLM chat Model must be provided!"

    response = llm.invoke(
        [
            SystemMessage(
                content=MessageBuilder.error_validation_system_message(state)
            ),
            HumanMessage(
                content=MessageBuilder.error_to_model_request(state)
                + "\n\n Please explain what went wrong"
            ),
        ]
    )
    return {"messages": response, "errors_summary": response}


def plan_user_query(
    state: BaseMetadataState, llm: BaseChatModel | None = None
) -> BaseMetadataState:
    messages = [
        state["errors_summary"],
        SystemMessage(MessageBuilder.error_resolution_planning_system_message(state)),
        HumanMessage(MessageBuilder.error_to_model_request(state)),
    ]
    response = llm.with_structured_output(QueryPlan).invoke(messages)
    return {
        "messages": messages,
        "query_plan": response,
        "current_step_id": None,
        "query_plan_completed": False,
    }


def _is_last_query_step_reached(
    state: BaseMetadataState, taken_step_id: None | QueryStepId = None
) -> bool:
    query_steps = state.get("query_plan", {}).get("queries", {})
    last_step_id = max(query_steps.keys(), default=None)
    current_step_id = taken_step_id or state.get("current_step_id", None)
    return last_step_id and current_step_id and (last_step_id == current_step_id)


def is_query_plan_completed(state: BaseMetadataState) -> QueryPlanExecutionState:
    """Checks if the plan is completed.

    Args:
        state (BaseMetadataState): current state of the Agent's execution graph

    Returns:
        QueryPlanExecutionState: decision about further actions

    Examples:
        >>> QueryPlanExecutionState.STOP == (
        ...     is_query_plan_completed({})
        ... )
        True
        >>> QueryPlanExecutionState.ACT == (
        ...     is_query_plan_completed({"query_plan": {"queries": {1: {"id": 1}}}})
        ... )
        True
        >>> QueryPlanExecutionState.ACT == (
        ...     is_query_plan_completed({
        ...         "query_plan": {"queries": {1: {"id": 1}}},
        ...         "current_step_id": None,
        ...     })
        ... )
        True
        >>> QueryPlanExecutionState.ACT == (
        ...     is_query_plan_completed({
        ...         "query_plan": {"queries": {1: {"id": 1}}},
        ...         "current_step_id": None,
        ...         "query_plan_completed": False
        ...     })
        ... )
        True
        >>> QueryPlanExecutionState.ACT == (
        ...     is_query_plan_completed({
        ...         "query_plan": {"queries": {1: {"id": 1}}},
        ...         "current_step_id": None,
        ...         "query_plan_completed": True
        ...     })
        ... )
        True
        >>> QueryPlanExecutionState.STOP == (
        ...     is_query_plan_completed({
        ...         "query_plan": {"queries": {1: {"id": 1}}},
        ...         "current_step_id": 1,
        ...         "query_plan_completed": True
        ...     })
        ... )
        True
    """
    is_last_step_reached = _is_last_query_step_reached(state)

    return (
        QueryPlanExecutionState.STOP
        if (
            not state.get("query_plan", {}).get("queries", {})
            or (state.get("query_plan_completed", False) and is_last_step_reached)
        )
        else QueryPlanExecutionState.ACT
    )


def pull_ready_user_query(state: BaseMetadataState) -> BaseMetadataState:
    """Puts the user query ready for display.
    IMPORTANT: should be followed by an interrup/user answer request

    Args:
        state (BaseMetadataState): state of the Agent's graph execution

    Returns:
        BaseMetadataState: modified state of the Agent's graph execution

    Examples:
        >>> query_plan = {"queries": {1: {"id": 1, "query": "What's the ID?"}, 2: {"id": 2, "query": "What's the goal?"}}}
        >>> state = pull_ready_user_query({
        ...     "query_plan": query_plan,
        ...     "current_step_id": None,
        ...     "query_plan_completed": False
        ... })
        >>> state                           # state after the first execution
        {'current_step_id': 1, 'current_query_prompt': {'id': 1, 'query': "What's the ID?"}, 'query_plan_completed': False}
        >>> pull_ready_user_query({**state, "query_plan": query_plan})    # this should pull the final query prompt
        {'current_step_id': 2, 'current_query_prompt': {'id': 2, 'query': "What's the goal?"}, 'query_plan_completed': True}
        >>> pull_ready_user_query({
        ...     "query_plan": {},
        ...     "current_step_id": None,
        ...     "query_plan_completed": False
        ... })
        {'current_step_id': None, 'current_query_prompt': None, 'query_plan_completed': False}
    """
    assert "query_plan" in state, "query plan is not available!"

    query_steps = state.get("query_plan", {}).get("queries", {})
    first_step_id = min(query_steps.keys(), default=None)
    last_step_id = max(query_steps.keys(), default=None)
    current_step_id = state.get("current_step_id", None)

    if (
        all([first_step_id, last_step_id, current_step_id])
        and current_step_id >= first_step_id
        and current_step_id < last_step_id
    ):
        taken_step_id = current_step_id + 1
    elif current_step_id == last_step_id:
        taken_step_id = current_step_id
    else:
        taken_step_id = first_step_id

    taken_query = query_steps.get(taken_step_id)
    is_last_step_reached = _is_last_query_step_reached(
        state, taken_step_id=taken_step_id
    ) or False

    return {
        "current_step_id": taken_step_id,
        "current_query_prompt": taken_query,
        "query_plan_completed": is_last_step_reached,
    }


def build_graph(config: Config):
    llm = create_ollama_llm(config)

    builder = StateGraph(BaseMetadataState)
    builder.add_node(n.__name__, n) if (n := ensure_metadata_file_presence) else ...
    builder.add_node(n.__name__, n) if (n := select_working_base_metadata_file) else ...
    builder.add_node(n.__name__, n) if (n := check_metadata_completion) else ...
    (
        builder.add_node(n.__name__, np)
        if (n := interpret_metadata_checks) and (np := partial(n, llm=llm))
        else ...
    )
    (
        builder.add_node(n.__name__, np)
        if (n := plan_user_query) and (np := partial(n, llm=llm))
        else ...
    )
    builder.add_node(n.__name__, n) if (n := pull_ready_user_query) else ...

    builder.add_edge(START, ensure_metadata_file_presence.__name__)
    builder.add_edge(
        ensure_metadata_file_presence.__name__,
        select_working_base_metadata_file.__name__,
    )
    builder.add_edge(
        select_working_base_metadata_file.__name__, check_metadata_completion.__name__
    )
    builder.add_edge(
        check_metadata_completion.__name__, interpret_metadata_checks.__name__
    )
    builder.add_edge(interpret_metadata_checks.__name__, plan_user_query.__name__)
    builder.add_edge(plan_user_query.__name__, pull_ready_user_query.__name__)
    builder.add_conditional_edges(
        pull_ready_user_query.__name__,
        is_query_plan_completed,
        {
            QueryPlanExecutionState.STOP: END,
            QueryPlanExecutionState.ACT: pull_ready_user_query.__name__,
        },
    )

    memory = MemorySaver()
    return builder.compile(
        interrupt_before=[interpret_metadata_checks.__name__, plan_user_query.__name__],
        checkpointer=memory,
    )
