from functools import partial

from jsonschema.validators import Draft202012Validator
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from massi.agents.constructs import (
    MessageBuilder,
    MetadataUpdate,
    QueryPlan,
    QueryPlanExecutionState,
    QueryStep,
    QueryStepId,
    ResourcePropertiesState,
)
from massi.agents.crafters.data_explorer import build_data_explorer_graph
from massi.agents.inquiry_engine import get_next_step, is_plan_completed
from massi.agents.interfaces import Dependencies

# UC3: Resource Specific Properties
# =================================


# TODO(refactor): start using a real DI solution
class Defaults:
    # Adapted from MIAGIS JSON Schema
    # @see: https://moseleybioinformaticslab.github.io/miagis/jsonschema.html
    resource_properties_metadata_json_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "minLength": 1,
                "description": "physical location of the digital resource: e.g. file path, URI",
            },
            "alternate_locations": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
                "minItems": 1,
                "description": "alternative physical locations of the digital resource: e.g. file paths, URIs",
            },
            "type": {"type": "string", "minLength": 1},
            "format": {"type": "string", "minLength": 1},
            "schema": {"type": ["string", "object"], "minLength": 1},
            "sources": {"type": "array", "items": {"type": "string", "minLength": 1}},
            "description": {
                "type": "string",
                "minLength": 1,
                "description": "a high-level summary of the resource",
            },
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
            "geography_name": {
                "type": "string",
                "minLength": 1,
                "description": "common name of the geographic area associated with the resource, empty string if not known",
            },
            "bbox": {
                "type": "array",
                "items": {"type": "number"},
                "maxItems": 4,
                "minItems": 4,
                "description": "bounding box specified as array: [min_lon, min_lat, max_lon, max_lat]",
            },
            "crs": {
                "type": "string",
                "description": "used coordinate reference system, empty string if not known",
            },
            "update_frequency": {
                "type": "string",
                "enum": ["daily", "monthly", "annually", "as_needed", "static"],
            },
        },
        "required": [
            "location",
            "type",
            "format",
            "schema",
            "sources",
            "description",
            "creator",
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
    state: ResourcePropertiesState, llm: BaseChatModel | None = None
) -> ResourcePropertiesState:
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
        "query_plan_completed": False,
    }


def pull_next_resource_query(state: ResourcePropertiesState) -> ResourcePropertiesState:
    """
    Selects the next step from the QueryPlan using the provided library.
    """
    plan_dict = state.get("query_plan")
    if (
        state.get("query_plan_completed")
        or not plan_dict
        or not plan_dict.get("queries")
    ):
        return {"query_plan_completed": True}

    current_step = state.get("current_query_step", None)
    current_id = QueryStep(**current_step).id if current_step else None

    next_step = get_next_step(QueryPlan(**plan_dict), current_id)

    return {
        "current_query_step": next_step.model_dump() if next_step else None,
        "query_plan_completed": next_step is None,
    }


def execute_resource_query(
    state: ResourcePropertiesState,
    dependencies: Dependencies | None = None,
) -> ResourcePropertiesState:
    """
    Interrupts/Prompts the user for the specific resource attribute.
    """
    assert (
        dependencies
    ), "dependencies need to be passed to instantiate the data explorer"
    data_explorer = build_data_explorer_graph(dependencies)

    exploration_result = data_explorer.invoke(
        {
            **state,
            "query": QueryStep(**state["current_query_step"]),
            "context": {
                "target_schema": Defaults.resource_properties_metadata_json_schema
            },
        }
    ).get("extraction_result", {})
    return {"current_query_response": exploration_result}


def register_resource_response(
    state: ResourcePropertiesState, llm: BaseChatModel | None = None
) -> ResourcePropertiesState:
    """Processes the user provided answer and updates the metadata.

    Args:
        state (BaseMetadataState): the agent's workflow execution state
        llm (BaseChatModel | None, optional): the configured LLM client. Defaults to None.

    Returns:
        BaseMetadataState: the updated workflow state.
    """
    current_metadata = state.get("updated_metadata", {})
    current_query = state.get("current_query_step", {}).get("query", "")
    given_response = state.get("current_query_response", "")
    messages = state.get("messages", [])

    update = None
    if current_query and given_response:

        update = llm.with_structured_output(MetadataUpdate).invoke(
            messages
            + [
                HumanMessage(
                    MessageBuilder.update_given_resource_properties_request(
                        state,
                        metadata=current_metadata,
                        context={
                            "target_schema": Defaults.resource_properties_metadata_json_schema
                        },
                    )
                )
            ]
        )

    return {"updated_metadata": update.model_dump(), "messages": messages}


def is_resource_plan_completed(
    state: ResourcePropertiesState,
) -> QueryPlanExecutionState:
    """
    Determines if the workflow should continue processing the query plan or stop.
    """
    plan: QueryPlan = QueryPlan(**state.get("query_plan"))
    current_id: QueryStepId | None = state.get("current_query_id")
    if is_plan_completed(plan, current_id):
        return QueryPlanExecutionState.STOP

    return QueryPlanExecutionState.ACT


def build_graph(dependencies: Dependencies):
    llm = dependencies.llm_client

    builder = StateGraph(ResourcePropertiesState)

    nodes = [
        (validate_resource_metadata, {}),
        (interpret_metadata_checks, dict(llm=llm)),
        (plan_resource_interview, dict(llm=llm)),
        (pull_next_resource_query, {}),
        (execute_resource_query, dict(dependencies=dependencies)),
        (register_resource_response, dict(llm=llm)),
    ]
    for func, kwargs in nodes:
        node_name = func.__name__
        node_func = partial(func, **kwargs) if kwargs else func
        builder.add_node(node_name, node_func)

    sequential_edges = [
        (START, validate_resource_metadata),
        (validate_resource_metadata, interpret_metadata_checks),
        (interpret_metadata_checks, plan_resource_interview),
        (plan_resource_interview, pull_next_resource_query),
        (pull_next_resource_query, execute_resource_query),
        (execute_resource_query, register_resource_response),
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
