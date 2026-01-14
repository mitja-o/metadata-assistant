from abc import ABC, abstractmethod
from typing import Any, TypedDict

from pydantic import BaseModel

from langgraph.graph import MessagesState
from langchain_core.messages import AIMessage


# DTOs


class MetadataValidationError(TypedDict):
    message: str
    encountered_value: str
    json_path: str
    failed_key: str


type QueryStepId = int
type QueryPrompt = str
type Metadata = dict


class DictGetCompatibleModel(BaseModel):
    """An extension to the standard Pydantic BaseModel, making it compatible with the `dict::get` protocol."""

    def get(self, key: str, default: Any = None):
        return getattr(self, key, default)


class QueryStep(DictGetCompatibleModel):
    id: QueryStepId
    key: str
    json_path: str
    priority: int
    query: QueryPrompt


class QueryPlan(DictGetCompatibleModel):
    queries: list[QueryStep]


class MetadataUpdate(DictGetCompatibleModel):
    metadata: Metadata


# Dependencies


class PromptClient(ABC):
    @abstractmethod
    def prompt_user(
        self, queries: list[str] = [], prelude: list[str] = []
    ) -> list[str]: ...


# Langgraph execution states


class BaseMetadataState(MessagesState):
    base_metadata_files: list[str]
    selected_base_metadata_file: str
    schema_validation_errors: list[MetadataValidationError]
    errors_summary: AIMessage
    query_plan: QueryPlan
    query_plan_completed: bool
    current_step_pointer: None | int
    current_query_prompt: None | QueryPrompt
    current_query_response: None | str
    updated_metadata: None | Metadata
    original_metadata: None | Metadata


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
{"queries": [
    {
        "id": <natural number ID to uniquely identify the step>
        "key": <brief identifier of the purpose of the query, should be written in snake case: e.g. foo_baz>
        "json_path": <path of the json property that this query intends to complete>,
        "priority": <integer value from 0 to 5 indicating how high is the priority of this query, 5 - needs to be asked as soon as possible, 0 - can be asked later>,
        "query": <short but clear and sufficient human-readable query aimed to retrieve the value for the given key_path attribute in the error>
    }
]}
</format>
"""

    @staticmethod
    def update_given_metadata_request(state: BaseMetadataState, metadata: dict):
        current_query = state["current_query_prompt"]
        response = state["current_query_response"]

        return f"""
You are an experienced data steward collecting the base metadata for a MIAGIS file.
MIAGIS files organise the metadata for geospatial (GIS) data depositories.
Base metadata provides an overview of the overall project.

Given (a) the query for a missing piece of the metadata, (b) the user-provided response, and (c) current metadata file, you should:
1. Check the (b) user response quality and, if necessary, rephrase it to a most appropriate formulation according to the nature of (a).
2. Identify where in the (c) current metadata file the response fits according to the details of (a).
3. Update the (c) metadata file by adding the (b, rephrased after step 1.) improved user response as a field described by (a).

DO NOT change any existing metadata file details.

Here are the provided details:

(a)
<query-details>
{current_query}
</query-details>

(b)
<user-response>
{response}
</user-response>

(c)
<current-metadata>
{metadata}
</current-metadata>

In your response, you MUST only report the final metadata file, after performing all the required updates above.
"""
