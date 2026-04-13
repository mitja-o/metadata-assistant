import getpass as gp
import operator
import os.path as op
import pathlib as pl
from typing import Annotated, Any, Self, TypedDict

from langchain_core.messages import AIMessage
from langgraph.graph import MessagesState
from pydantic import BaseModel

# DTOs
# ====


class MetadataValidationError(TypedDict):
    message: str
    encountered_value: str
    json_path: str
    failed_key: str


type QueryStepId = int
type QueryPrompt = str
type QueryStepDict = dict
type Metadata = dict
type QueryPlanDict = dict
type MetadataUpdateDict = dict


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


class MetadataUpdate(TypedDict):
    metadata: Metadata


class ResourceFile(BaseModel):
    """Details of a file that can be identified as a project's resoruce

    Examples:
        >>> ResourceFile(file_location="bar/foo.txt", filename="foo.txt", extension="txt", author="quack")
        ResourceFile(file_location='bar/foo.txt', filename='foo.txt', extension='txt', author='quack')
        >>> import tempfile
        >>> with tempfile.NamedTemporaryFile() as fp:
        ...     ResourceFile.from_path(pl.Path(fp.name)) # doctest: +ELLIPSIS
        ResourceFile(file_location='...', filename='...', extension='...', author='...')
    """

    file_location: str
    filename: str
    extension: str
    author: str | None

    @staticmethod
    def from_path(p: pl.Path) -> Self:
        try:
            author = p.owner()
        except (KeyError, AttributeError, NotImplementedError):
            try:
                author = gp.getuser()
            except OSError:
                author = None
        return ResourceFile(
            file_location=str(op.relpath(p)),
            filename=p.name,
            extension=p.suffix.lower(),
            author=author,
        )


class GISScoredFile(ResourceFile):
    gis_relevancy_score: float = 0.0


class GroupedGisResourceFile(GISScoredFile):
    resource_name: str
    group_score: float


class GroupedGisResourceFileWithMetadata(DictGetCompatibleModel):
    resource: GroupedGisResourceFile
    metadata: Metadata


class GISScoringCollectionResponse(DictGetCompatibleModel):
    entries: list[GISScoredFile]


class GisResourceGroup(DictGetCompatibleModel):
    resource_name: str
    """Specific resource identifier."""

    entries: list[GISScoredFile]
    """Individual files connected to the resource."""

    group_score: float
    """A mean-value score computed from all entries' relevances."""


def flatten_resource_groups(
    groups: list[GisResourceGroup],
) -> list[GroupedGisResourceFile]:
    """Flatten the files grouped by resources into individual entries

    Args:
        groups (list[GisResourceGroup]): scored resource groups

    Returns:
        list[GroupedGisResourceFile]: indivudual entries preserving assigned group details

    Examples:
        >>> groups = [GisResourceGroup(resource_name="test", group_score=0.2, entries=[GISScoredFile(gis_relevancy_score=0.2, file_location="test.csv", filename="test", extension="csv", author="tester")])]
        >>> flatten_resource_groups(groups)
        [GroupedGisResourceFile(file_location='test.csv', filename='test', extension='csv', author='tester', gis_relevancy_score=0.2, resource_name='test', group_score=0.2)]
    """
    return [
        GroupedGisResourceFile(**g.model_dump(), **e.model_dump())
        for g in groups
        for e in g.entries
    ]


# Langgraph execution states
# ==========================


type ResourceContext = dict
type GISScoringCollection = list[GISScoredFile]
type ResourceMetadataCollection = list[GroupedGisResourceFileWithMetadata]


class ResourcePropertiesState(MessagesState, total=False):
    resource: GroupedGisResourceFile
    schema_validation_errors: list[MetadataValidationError]
    resource_context: ResourceContext
    errors_summary: AIMessage
    query_plan: QueryPlanDict
    query_plan_completed: bool
    current_query_step: None | QueryStepDict
    current_query_response: None | str
    updated_metadata: None | MetadataUpdateDict
    original_metadata: None | Metadata


class ResourcePropertyGroupingState(MessagesState, total=False):
    base_metadata: None | Metadata
    files: list[ResourceFile]
    gis_scored_files: Annotated[GISScoringCollection, operator.add]
    user_approved: bool
    gis_resource_groups: list[GisResourceGroup]
    grouped_resource_entries: list[GroupedGisResourceFile]
    raw_resource_dataframe_file: str
    metadata_enriched_resources: Annotated[ResourceMetadataCollection, operator.add]
    processed_resource_dataframe_file: str


class ResourcePropertyGroupMetadataInferenceState(MessagesState, total=False):
    resource: GroupedGisResourceFile


class BaseMetadataState(MessagesState, total=False):
    base_metadata_files: list[str]
    selected_base_metadata_file: str
    schema_validation_errors: list[MetadataValidationError]
    errors_summary: AIMessage
    query_plan: QueryPlanDict
    query_plan_completed: bool
    current_query_step: None | QueryStepDict
    current_query_response: None | str
    updated_metadata: None | MetadataUpdateDict
    original_metadata: None | Metadata


# State -> LLM message templates
# ==============================
# TODO(refactor): this should be pulled out into a separate module


class MessageBuilder:

    @staticmethod
    def gis_file_relevancy_score_assessment_request(
        state: ResourcePropertyGroupingState,
    ):
        preamble = (
            f"""
Given the current available base metadata of this GIS application:

<metadata>
{state["base_metadata"]}
</metadata>
"""
            if ("base_metadata" in state and state["base_metadata"])
            else ""
        )

        request = f"""
These are the files discovered in the working directory:

<file-input>
{'\n- '.join(map(str,state['files']))}
</file-input>

Given these files, please assess these files relevancy for to a GIS application.
Rely on the name, extension, and location of the file.
Assign the score in range [0.0; 1.0].

Some examples:
<example-score-derivation>
- foo.geojson               |=> score: 1.0
- Makefile                  |=> score: 0.0
- ./resources/bar.tiff      |=> score: 1.0
- ./scripts/analysis.py     |=> score: 1.0
- ./bin/package.py          |=> score: 0.2
</example-score-derivation>

You MUST preserve and give grade to each given file. 
DO NOT remove, modify, or otherwise temper any information about the files that was provided.
The ONLY CHANGE you should do is adding the score attribute `gis_relevancy_score`.
Adhere to the structured response type provided.
"""

        return preamble + request

    @staticmethod
    def base_metadata_error_validation_system_message(_: BaseMetadataState):
        return """
You are reviewing a set of JSON schema validator errors for a MIAGIS base metadata file.
You should translate ALL erors into a human-readable descriptions.

You MUST report the original errors as a human-friendly formatter bullet-point list in your response.
"""

    @staticmethod
    def resoure_property_error_validation_system_message(_: BaseMetadataState):
        return """
You are reviewing a set of JSON schema validator errors for a single entry of a MIAGIS resource properties metadata file.
You should translate ALL erors into a human-readable descriptions.

You MUST report the original errors as a human-friendly formatter bullet-point list in your response.
"""

    @staticmethod
    def error_to_model_request(
        state: BaseMetadataState | ResourcePropertiesState, json_schema: dict = {}
    ):
        return f"""
<json-schema>
{str(json_schema)}
</json-schema>

Here are the received JSON schema validation errors:
{'\n-'.join([f'<Error>{str(e)}</Error>' for e in state["schema_validation_errors"]])}
"""

    @staticmethod
    def base_metadata_error_resolution_planning_system_message(_: BaseMetadataState):
        return """
You are an experienced data steward collecting the base metadata for a MIAGIS file.
MIAGIS files organise the metadata for geospatial (GIS) data depositories.
Base metadata provides an overview of the overall project.

You given the missing attributes specified as JSON schema validation errors, design the interview plan to retrieve the missing information from the user.
You should guide the users to be elaborate and non-ambiguous. Please rely on the fact that the data we are describing is used for GIS. Reflect this in the query you direct at the user.

The query plan should be an ordered sequence (stack, first-in-first-out) of queries you would like to ask to the data creator.
The order should allow for growth of contextual information. 
The earlier questions focusing on most atomic (or basic) details, the later should focus on most elaborate and free-form information.
Example query plan is: 
<example>
{"queries": {
    1: {"id": 1, "key": "id", "json_path": "$.id", "priority": 5, "query": "Please provide a unique identifier for this data entry."},
    2: {"id": 2, "key": "outcomes", "json_path": "$.outcomes", "priority": 4, "query": "Please list all reusable outcomes of your data project. Think what is useful to know to the future users of your data."},
    # and so on ... 
}}
</example>


You MUST respond with a JSON-structure with the following format: 
<format required-output-format="application/json">
{"queries": [
    {
        "id": <natural number ID to uniquely identify the step>
        "key": <identifier of the attribute that needs to be filled in. e.g. in a json path '$.foo.baz', the `key` is 'baz'>
        "json_path": <path of the json property that this query intends to complete, e.g. '$.foo.baz'>,
        "priority": <integer value from 0 to 5 indicating how high is the priority of this query, 5 - needs to be asked as soon as possible, 0 - can be asked later>,
        "query": <short but sufficiently clear and human-readable query aimed to retrieve the value for the given key_path attribute in the error from an interviewee, it should be elaborate enough to guide the interviewee to provide a clear and comprehensive response>
    }
]}
</format>
"""

    @staticmethod
    def resource_property_error_resolution_planning_system_message(
        _: BaseMetadataState,
    ):
        return """
You are an experienced data steward collecting the base metadata for a MIAGIS file.
MIAGIS files organise the metadata for geospatial (GIS) data depositories.
Resource property metadata provides an overview of each resource included in the dataset associated with this MIAGIS manifest.

You are focusing on the resource property metadata and are going to communicate to an AI agent assisting you to retrieve this information.
Therefore, you are creating a metadata retrieval plan for an AI Agent skilled in data exploration.
You given the missing attributes specified as JSON schema validation errors, design the inquiry plan to retrieve the missing attributes by delegation to an AI Agent skilled in data exploration.
You should guide the agent by providing a concrete and non-ambiguous description of the target attribute.
Provide a brief suggestion of the retrieval approach and examples of what the retrieved information could look like to.
Please rely on the fact that the data we are describing is used for GIS. 
Reflect this in the query you direct at the data exploration agent.

The query plan should be an ordered sequence (stack, first-in-first-out) of requests you want to pass to a data exploration agent.
The order should allow for growth of contextual information. 
The earlier questions focusing on most atomic (or basic) details, the later should focus on most elaborate and free-form information.
Example query plan is: 
<example>
{"queries": {
    1: {"id": 1, "key": "id", "bbox": "$.spatial_metadata.bbox", "priority": 5, "query": "<context><file-path>foo/baz.csv</file><target-attribute>bbox</target-attribute></context>Please retrieve the bounding box - `bbox` -  of the observations contained in the `foo/baz.csv` file. Compute the bounding box by the farthest extends of the geographic coordinates present in the data. Report them as a list with four floatin-point values: [minX, minY, maxX, maxY]. If no geographic coordinates are present, return an empty list: []."},
    2: {"id": 2, "key": "description", "json_path": "$.description", "priority": 4, "query": "<context><file-path>foo/baz.csv</file><target-attribute>description</target-attribute></context>Please derive a concise but comprehensive description of the `foo/baz.csv` file. - `bbox` -  of the observations contained in the `foo/baz.csv` file. Summarise the present columns and the purpose of the data. Reflect on the geographic location of the observations."},
    # and so on ... 
}}
</example>


You MUST respond with a JSON-structure with the following format: 
<format required-output-format="application/json">
{"queries": [
    {
        "id": <natural number ID to uniquely identify the step>
        "key": <identifier of the attribute that needs to be filled in. e.g. in a json path '$.foo.baz', the `key` is 'baz'>
        "json_path": <path of the json property that this query intends to complete, e.g. '$.foo.baz'>,
        "priority": <integer value from 0 to 5 indicating how high is the priority of this query, 5 - needs to be asked as soon as possible, 0 - can be asked later>,
        "query": <short but sufficiently clear prompt for the data exploration AI-agent, to retrieve the value for the given key_path attribute in the error from the data, it should be elaborate enough to guide the data exploration AI agent to provide a clear and comprehensive response>
    }
]}
</format>
"""

    @staticmethod
    def update_given_base_metadata_request(state: BaseMetadataState, metadata: dict):
        current_query = state["current_query_step"]
        response = state["current_query_response"]

        return f"""
You are an experienced data steward collecting the base metadata for a MIAGIS file.
MIAGIS files organise the metadata for geospatial (GIS) data depositories.
Base metadata provides an overview of the overall project.

Given (a) the query for a missing piece of the metadata, (b) the user-provided response, and (c) current metadata file, you should:
1. Check the (b) user response quality and, if necessary, rephrase it to a most appropriate formulation according to the nature of (a) and contents of (c).
2. Identify where in the (c) current metadata file the response fits according to the details of (a).
3. Update the (c) metadata file by adding the (b, rephrased after step 1.) improved user response as a field described by (a).

YOU SHOULD MODIFY ONLY ONE ATTRIBUTE AS SPECIFIED IN THE QUERY DETAILS AND USER RESPONSE.
DO NOT CHANGE ANY ADDITIONAL ATTRIBUTES IN THE METADATA FILE.

Here are the provided details:

(a)
<query-details>
{current_query}
</query-details>

(b)
<user-response>
{response}
</user-response>

The attributes already present in the current metadata MUST be preserved, only append new attribute from the query and response above.

(c)
<current-metadata>
{metadata}
</current-metadata>

In your response, you MUST only report the final metadata file, with the added metadata attributes.
For example, if the <query-details> request input for an attribute `description`, and the <user-response> is `this is my response`, the updated metadata should contain contain a new attribute: `{{"description": "this is my response", <remaining attributes are unchanged>}}.
"""

    @staticmethod
    def update_given_resource_properties_request(
        state: BaseMetadataState, metadata: dict, context: dict
    ):
        current_query = state["current_query_step"]
        response = state["current_query_response"]

        return f"""
Context:
{context}

You are an experienced data steward collecting the resource properties for a MIAGIS file.
MIAGIS files organise the metadata for geospatial (GIS) data depositories.
Resource properties collect metadata about a specific resource included in the dataset.

Given (a) the query for a missing piece of the metadata, (b) the data explorer-provided response, and (c) current resource properties metadata, you should:
1. Check the (b) user response quality and, if necessary, rephrase it to a most appropriate formulation according to the nature of (a) and contents of (c).
2. Identify where in the (c) current metadata file the response fits according to the details of (a).
3. Update the (c) metadata file by adding the (b, rephrased after step 1.) improved user response as a field described by (a).

YOU SHOULD MODIFY ONLY ONE ATTRIBUTE AS SPECIFIED IN THE QUERY DETAILS AND USER RESPONSE.
DO NOT CHANGE ANY ADDITIONAL ATTRIBUTES IN THE METADATA FILE.

Here are the provided details:

(a)
<query-details>
{current_query}
</query-details>

(b)
<user-response>
{response}
</user-response>

The attributes already present in the current metadata MUST be preserved, only append new attribute from the query and response above.

(c)
<current-metadata>
{metadata}
</current-metadata>

In your response, you MUST only report the final metadata file, with the added metadata attributes.
For example, if the <query-details> request input for an attribute `description`, and the <user-response> is `this is my response`, the updated metadata should contain contain a new attribute: `{{"description": "this is my response", <remaining attributes are unchanged>}}.
"""
