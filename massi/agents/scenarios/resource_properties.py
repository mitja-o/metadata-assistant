import json
from functools import partial
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from massi.agents.constructs import (
    BaseMetadataState,  # Or a specific ResourceMetadataState if defined
    MessageBuilder,
    MetadataUpdate,
    QueryPlan,
    QueryPlanExecutionState,
    QueryStepId,
    GisResourceGroup,
    ResourcePropertiesState,
)
from massi.agents.inquiry_engine import get_next_step, is_plan_completed
from massi.agents.interfaces import Dependencies, PromptClient
from jsonschema.validators import Draft202012Validator

# UC3: Resource Specific Properties
# =================================


class Defaults:
    # Adapted from MIAGIS JSON Schema
    # @see: https://moseleybioinformaticslab.github.io/miagis/jsonschema.html
    resource_properties_metadata_json_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "location": {"type": "string", "minLength": 1},
            "alternate_locations": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
                "minItems": 1,
            },
            "type": {"type": "string", "minLength": 1},
            "format": {"type": "string", "minLength": 1},
            "schema": {"type": ["string", "object"], "minLength": 1},
            "sources": {"type": "array", "items": {"type": "string", "minLength": 1}},
            "description": {"type": "string", "minLength": 1},
            "creator": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "type": {
                            "type": "string",
                            "minLength": 1,
                            "enum": ["URL", "organization", "author", "DOI"],
                        },
                    },
                    "required": ["name", "type"],
                },
            },
            # "spatial_metadata": {
            #     "type": "object",
            #     "properties": {
            "geography_name": {"type": "string", "minLength": 1},
            "bbox": {
                "type": "array",
                "items": {"type": "number"},
                "maxItems": 4,
                "minItems": 4,
                "description": "[min_lon, min_lat, max_lon, max_lat]",
            },
            "crs": {"type": "string", "minLength": 1},
            "update_frequency": {
                "type": "string",
                "enum": ["daily", "monthly", "annually", "as_needed", "static"],
            },
            # },
            # "required": ["geography_name", "bbox", "crs", "update_frequency"],
            # },
        },
        "required": [
            "location",
            "type",
            "format",
            "schema",
            "sources",
            "description",
            "creator",
            "spatial_metadata",
            "geography_name",
            "bbox",
            "crs",
            "update_frequency",
        ],
    }
    resource_properties_metadata_json_schema_validator = Draft202012Validator(
        resource_properties_metadata_json_schema
    )


def validate_resource_metadata(
    state: ResourcePropertiesState,
) -> ResourcePropertiesState:
    """
    Validates the current resource properties against the JSON schema.
    """
    print(state)

    try:
        resource = state["resource"]
    except KeyError as e:
        raise RuntimeError("`resource` must be present in the graph state") from e

    resource_context = resource.model_dump()
    resource_metadata = {}

    return {
        "schema_validation_errors": [
            {
                "message": e.message,
                "encountered_value": e.validator_value,
                "json_path": e.json_path,
                "failed_key": e.validator,
            }
            for e in Defaults.resource_properties_metadata_json_schema_validator.iter_errors(
                resource_metadata
            )
        ]
        or [],
        "original_metadata": resource_metadata,
        "resource_context": resource_context,
    }


def interpret_metadata_checks(
    state: BaseMetadataState, llm: BaseChatModel | None = None
) -> BaseMetadataState:
    assert "schema_validation_errors" in state, str(state)
    assert llm, "LLM chat Model must be provided!"

    response = llm.invoke(
        [
            SystemMessage(
                content=MessageBuilder.resoure_property_error_validation_system_message(
                    state
                )
            ),
            HumanMessage(
                content=MessageBuilder.error_to_model_request(
                    state, Defaults.resource_properties_metadata_json_schema
                )
                + "\n\n Please explain what went wrong"
            ),
        ]
    )
    return {"messages": response, "errors_summary": response}


def plan_resource_interview(
    state: ResourcePropertiesState, llm: BaseChatModel | None = None
) -> ResourcePropertiesState:
    """
    Creates a QueryPlan specifically for the missing resource attributes.
    """
    messages = [
        state["errors_summary"],
        SystemMessage(
            MessageBuilder.base_metadata_error_resolution_planning_system_message(state)
        ),
        HumanMessage(
            MessageBuilder.error_to_model_request(
                state, Defaults.resource_properties_metadata_json_schema
            )
        ),
    ]
    response = llm.with_structured_output(QueryPlan).invoke(messages).model_dump()
    return {
        "messages": messages,
        "query_plan": response,
        "current_step_pointer": None,
        "query_plan_completed": False,
    }


def pull_next_resource_query(state: ResourcePropertiesState) -> ResourcePropertiesState:
    """
    Selects the next step from the QueryPlan using the provided library.
    """
    plan: QueryPlan = QueryPlan(**state.get("query_plan"))
    current_id: QueryStepId | None = state.get("current_query_id")

    if not plan or not plan.queries:
        return {"current_query_step": None}
    next_step = get_next_step(plan, current_id)

    return {
        "current_query_step": next_step,
        "current_query_id": next_step.id if next_step else current_id,
    }


def prompt_resource_query(
    state: ResourcePropertiesState, prompt_client: PromptClient | None = None
) -> ResourcePropertiesState:
    """
    Interrupts/Prompts the user for the specific resource attribute.
    """
    raise NotImplementedError("todo: implement user interaction")


def register_resource_response(
    state: ResourcePropertiesState, llm: BaseChatModel | None = None
) -> ResourcePropertiesState:
    """
    Updates the local metadata for the resource based on user input.
    Pseudo-code:
    1. Use llm.with_structured_output(MetadataUpdate).
    2. Provide current resource metadata and the user's answer.
    3. Update the state with the new metadata object.
    """
    raise NotImplementedError(
        "todo: implement response registration and metadata merging"
    )


def is_resource_plan_completed(
    state: ResourcePropertiesState,
) -> QueryPlanExecutionState:
    """
    Determines if the workflow should continue processing the query plan or stop.
    """
    if is_plan_completed(state.get("query_plan"), state.get("current_query_id")):
        return QueryPlanExecutionState.STOP

    return QueryPlanExecutionState.ACT


def build_graph(dependencies: Dependencies):
    llm = dependencies.llm_client
    prompt_client = dependencies.prompt_client

    builder = StateGraph(ResourcePropertiesState)

    nodes = [
        (validate_resource_metadata, {}),
        (interpret_metadata_checks, dict(llm=llm)),
        (plan_resource_interview, dict(llm=llm)),
        (pull_next_resource_query, {}),
        (prompt_resource_query, dict(prompt_client=prompt_client)),
        (register_resource_response, dict(llm=llm)),
    ]
    for func, kwargs in nodes:
        (
            builder.add_node(func.__name__, handler)
            if (handler := (partial(func, **kwargs) if kwargs else func))
            else ...
        )

    sequential_edges = [
        (START, validate_resource_metadata),
        (validate_resource_metadata, interpret_metadata_checks),
        (interpret_metadata_checks, plan_resource_interview),
        (plan_resource_interview, pull_next_resource_query),
        (pull_next_resource_query, prompt_resource_query),
        (prompt_resource_query, register_resource_response),
    ]
    for source, target in sequential_edges:
        builder.add_edge(
            source if isinstance(source, str) else source.__name__,
            target if isinstance(target, str) else target.__name__,
        )

    builder.add_conditional_edges(
        register_resource_response.__name__,
        is_resource_plan_completed,
        {
            QueryPlanExecutionState.STOP: END,
            QueryPlanExecutionState.ACT: pull_next_resource_query.__name__,
        },
    )

    memory = MemorySaver()
    return builder.compile(checkpointer=memory), dict(
        interrupt_before=[register_resource_response.__name__],
        interrupt_after=[
            pull_next_resource_query.__name__,
            register_resource_response.__name__,
        ],
    )
