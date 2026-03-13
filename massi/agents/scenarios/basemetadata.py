import json
import pathlib as pl
from functools import partial
from typing import Any

from jsonschema.validators import Draft202012Validator
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

import massi.agents.tools as massi_toolkit
from massi.agents.constructs import (
    BaseMetadataState,
    MessageBuilder,
    MetadataUpdate,
    QueryPlan,
    QueryPlanExecutionState,
    QueryStepId,
)
from massi.agents.interfaces import Dependencies, PromptClient

# UC1: Base Metadata
# ==================


class Defaults:
    base_metadata_file = "base_metadata.json"
    # Adapted from MIAGIS JSON Schema
    # @see: https://moseleybioinformaticslab.github.io/miagis/jsonschema.html
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


def _create_default_metadata() -> pl.Path:
    default_path = pl.Path(".") / Defaults.base_metadata_file
    default_path.write_text(json.dumps({}))
    return default_path


def ensure_metadata_file_presence(
    _: BaseMetadataState, root_dir: str = "."
) -> BaseMetadataState:
    n_state = {}
    found_files = massi_toolkit.glob_file_search(
        f"**/{Defaults.base_metadata_file}", root_dir
    )

    n_state = {
        "base_metadata_files": (
            list(map(str, found_files))
            if found_files
            else [str(_create_default_metadata())]
        )
    }
    assert (
        len(n_state["base_metadata_files"]) > 0
    ), "At least one base metadata file must be present"

    return n_state


def select_working_base_metadata_file(state: BaseMetadataState) -> BaseMetadataState:
    return {"selected_base_metadata_file": state["base_metadata_files"][0]}


def check_metadata_completion(state: BaseMetadataState) -> BaseMetadataState:
    with open(state["selected_base_metadata_file"], "r") as bmf:
        base_metadata = json.load(bmf)

    return {
        "schema_validation_errors": [
            {
                "message": e.message,
                "encountered_value": e.validator_value,
                "json_path": e.json_path,
                "failed_key": e.validator,
            }
            for e in Defaults.base_metadata_json_schema_validator.iter_errors(
                base_metadata
            )
        ]
        or [],
        "original_metadata": base_metadata,
    }


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
        SystemMessage(
            MessageBuilder.base_metadata_error_resolution_planning_system_message(state)
        ),
        HumanMessage(MessageBuilder.error_to_model_request(state)),
    ]
    response = llm.with_structured_output(QueryPlan).invoke(messages).model_dump()
    return {
        "messages": messages,
        "query_plan": response,
        "current_step_pointer": None,
        "query_plan_completed": False,
    }


def _is_last_query_step_reached(
    state: BaseMetadataState, taken_step_pointer: None | QueryStepId = None
) -> bool:
    """Determine if the last query step is reached

    Args:
        state (BaseMetadataState): the current state of the workflow
        taken_step_pointer (None | QueryStepId, optional): optional override of an intended taken step. If specified, used instead of `current_step_pointer` attribute of the state. Defaults to None.

    Returns:
        bool: whether the last query step is reached

    Examples:
        >>> _is_last_query_step_reached({})
        True
        >>> _is_last_query_step_reached({"query_plan": {"queries": [{"id": 1}]}})
        False
        >>> _is_last_query_step_reached({"query_plan": {"queries": [{"id": 1}]}, "current_step_pointer": 0})
        True
        >>> _is_last_query_step_reached({"query_plan": {"queries": [{"id": 1}, {"id": 2}]}, "current_step_pointer": 0}, taken_step_pointer=1)
        True
    """
    query_steps = state.get("query_plan", {}).get("queries", [])
    max_step_pointer = len(query_steps) - 1 if query_steps else None
    current_step_pointer = taken_step_pointer or state.get("current_step_pointer", None)
    # breakpoint()
    return max_step_pointer == current_step_pointer


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
        ...     is_query_plan_completed({"query_plan": {"queries": [{"id": 1}]}})
        ... )
        True
        >>> QueryPlanExecutionState.ACT == (
        ...     is_query_plan_completed({
        ...         "query_plan": {"queries": [{"id": 1}]},
        ...         "current_step_pointer": None,
        ...     })
        ... )
        True
        >>> QueryPlanExecutionState.ACT == (
        ...     is_query_plan_completed({
        ...         "query_plan": {"queries": [{"id": 1}]},
        ...         "current_step_pointer": None,
        ...         "query_plan_completed": False
        ...     })
        ... )
        True
        >>> QueryPlanExecutionState.ACT == (
        ...     is_query_plan_completed({
        ...         "query_plan": {"queries": [{"id": 1}]},
        ...         "current_step_pointer": None,
        ...         "query_plan_completed": True
        ...     })
        ... )
        True
        >>> QueryPlanExecutionState.STOP == (
        ...     is_query_plan_completed({
        ...         "query_plan": {"queries": [{"id": 1}]},
        ...         "current_step_pointer": 0,
        ...         "query_plan_completed": True
        ...     })
        ... )
        True
    """
    is_last_step_reached = _is_last_query_step_reached(state)

    return (
        QueryPlanExecutionState.STOP
        if (
            not state.get("query_plan", {}).get("queries", [])
            or (state.get("query_plan_completed", True) and is_last_step_reached)
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
        >>> # sequential pulling should reach the end of the query plan
        >>> query_plan = {"queries": [{"id": 1, "query": "What's the ID?"}, {"id": 2, "query": "What's the goal?"}]}
        >>> state = pull_ready_user_query({
        ...     "query_plan": query_plan,
        ...     "current_step_pointer": None,
        ...     "query_plan_completed": False
        ... })
        >>> state                                                               # state after the first execution
        {'current_step_pointer': 0, 'current_query_prompt': {'id': 1, 'query': "What's the ID?"}, 'query_plan_completed': False}
        >>> pull_ready_user_query({**state, "query_plan": query_plan})          # this should pull the final query prompt
        {'current_step_pointer': 1, 'current_query_prompt': {'id': 2, 'query': "What's the goal?"}, 'query_plan_completed': True}

        >>> # calling with an empty query plan should set the completed flag to True
        >>> pull_ready_user_query({"query_plan": {}, "current_step_pointer": None, "query_plan_completed": False })
        {'current_step_pointer': None, 'current_query_prompt': None, 'query_plan_completed': True}
    """
    assert "query_plan" in state, "query plan is not available!"

    query_steps = state.get("query_plan", {}).get("queries", [])
    min_step_pointer, max_step_pointer = (
        0 if query_steps else None,
        len(query_steps) - 1 if query_steps else None,
    )
    current_step_pointer = state.get("current_step_pointer", None)
    taken_step_id = None

    taken_step_id = (
        min_step_pointer
        if current_step_pointer is None
        else min(current_step_pointer + 1, max_step_pointer)
    )

    taken_query = query_steps[taken_step_id] if taken_step_id is not None else None
    is_last_step_reached = _is_last_query_step_reached(
        state, taken_step_pointer=taken_step_id
    )

    return {
        "current_step_pointer": taken_step_id,
        "current_query_prompt": taken_query,
        "query_plan_completed": is_last_step_reached,
    }


def prompt_user_query(
    state: BaseMetadataState, prompt_client: PromptClient | None = None
) -> BaseMetadataState:
    planned_query_prompt = state.get("current_query_prompt", {}).get("query", None)
    responses = prompt_client.prompt_user(
        queries=[planned_query_prompt] if planned_query_prompt else [],
        prelude=["\n~~~"],
    )
    return {"current_query_response": responses[0]}


def register_user_query_response(
    state: BaseMetadataState, llm: BaseChatModel | None = None
) -> BaseMetadataState:
    """Processes the user provided answer and updates the metadata.

    Args:
        state (BaseMetadataState): the agent's workflow execution state
        llm (BaseChatModel | None, optional): the configured LLM client. Defaults to None.

    Returns:
        BaseMetadataState: the updated workflow state.
    """
    current_query = state.get("current_query_prompt", {})
    given_response = state.get("current_query_response", "")
    messages = state.get("messages", [])

    update = None
    if current_query and given_response:
        with open(state["selected_base_metadata_file"], "r") as bmf:
            base_metadata = json.load(bmf)

        update = llm.with_structured_output(MetadataUpdate).invoke(
            messages
            + [
                HumanMessage(
                    MessageBuilder.update_given_metadata_request(
                        state, metadata=base_metadata
                    )
                )
            ]
        )

        with open(state["selected_base_metadata_file"], "w") as bmf:
            json.dump(update.metadata, bmf)

    return {"updated_metadata": update.model_dump(), "messages": messages}


def build_graph(dependencies: Dependencies):
    llm = dependencies.llm_client
    prompt_client = dependencies.prompt_client

    n: Any = None
    builder = StateGraph(BaseMetadataState)
    (
        builder.add_node(n.__name__, np)
        if (n := ensure_metadata_file_presence)
        and (np := partial(n, dependencies.working_directory))
        else ...
    )
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
    (
        builder.add_node(n.__name__, np)
        if (n := prompt_user_query) and (np := partial(n, prompt_client=prompt_client))
        else ...
    )
    (
        builder.add_node(n.__name__, np)
        if (n := register_user_query_response) and (np := partial(n, llm=llm))
        else ...
    )

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
    builder.add_edge(pull_ready_user_query.__name__, prompt_user_query.__name__)
    builder.add_edge(prompt_user_query.__name__, register_user_query_response.__name__)
    # builder.add_edge(register_user_query_response.__name__, END)
    # # FIXME(rendering-display):
    builder.add_conditional_edges(
        register_user_query_response.__name__,
        is_query_plan_completed,
        {
            # FIXME(upstream-issue): when rendering mermaid, this should be wrapped in `"` because `.` in the key breaks mermaid rendering
            QueryPlanExecutionState.STOP: END,
            QueryPlanExecutionState.ACT: pull_ready_user_query.__name__,
        },
    )

    memory = MemorySaver()
    return builder.compile(
        interrupt_before=[register_user_query_response.__name__],
        interrupt_after=[
            pull_ready_user_query.__name__,
            register_user_query_response.__name__,
        ],
        checkpointer=memory,
    )
