import logging
import operator
import os
from abc import ABC
from dataclasses import dataclass
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import Annotated, Any, Callable, TypedDict

from langgraph.graph import MessagesState
from langgraph.types import Send

from massi.agents.tools import (
    AbstractXMLSchema,
    CSVDetails,
    get_csv_details,
    get_file_stats,
    walk_working_dir_for_files,
)

# Logger
# ------

logger = logging.getLogger(__name__)

# Data constructs
# ---------------


class MetadataScope(StrEnum):
    """REF: See Gilliland's "Setting the Stage" (2000)."""

    DESCRIPTIVE = "descriptive"
    """Citation and discovery data: DOI, creators, spatial/temporal coverage, and domain keywords."""

    ADMINISTRATIVE = "administrative"
    """Governance data: funding sources, PII handling, IP licenses, and data sharing agreements."""

    PRESERVATION = "preservation"
    """Fixity and integrity data: checksums, archival formats, and bit-level replication logs."""

    TECHNICAL = "technical"
    """Execution environment: sensor specs, software versions, CLI parameters, and schema definitions."""

    USE = "use"
    """Telemetry and impact: citation counts, download metrics, and re-analysis provenance logs."""


class MetadataLevel(IntEnum):
    """REF: See Gilliland's "Setting the Stage" (2000)."""

    COLLECTION = 0
    """Contextual schema for the entire study, campaign, or longitudinal dataset series."""

    ITEM = 1
    """Granular metadata for a single observation, file, sample, or granular data point."""


class MetadataArchitectPromptContext(TypedDict):
    xsd_schema: str
    file_overview: str
    csv_overview: str


class MetadataGoal(TypedDict):
    """A goal of Metadata construction.

    Examples:
        >>> import requests
        >>> from massi.agents.tools import get_xmlschema_validator

        >>> dwc_data_file_metadata_goal: MetadataGoal = {   # doctest:
        ...     "level": MetadataLevel.ITEM,
        ...     "scopes": [MetadataScope.DESCRIPTIVE, MetadataScope.TECHNICAL, MetadataScope.USE],
        ...     "target_filename": "meta.xml",
        ...     "schema": get_xmlschema_validator("https://dwc.tdwg.org/text/tdwg_dwc_text.xsd"),
        ...     "description": (
        ...         "This metadata file describes the archive and data file structure."
        ...         "A descriptor metafile describes how the files in your archive are organized."
        ...         "It describes the files in the archive and maps each data column to a corresponding standard Darwin Core or Extension term."
        ...         "The metafile is a relatively simple XML file format."
        ...     ),
        ...     "get_architect_agent_prompt": (
        ...         lambda _: "Generate a structural descriptor to map raw data columns to standardized Darwin Core terms, defining file encoding, delimiters, and extension relationships."
        ...     ),
        ... }
        >>> dwc_data_file_metadata_goal["schema"]           # doctest: +ELLIPSIS
        MassiXMLSchemaXmlschemalWrapper(schema=XMLSchema10...)

        >>> dwc_eml_metadata_goal: MetadataGoal = {         # doctest:
        ...     "level": MetadataLevel.COLLECTION,
        ...     "scopes": [
        ...         MetadataScope.DESCRIPTIVE,
        ...         MetadataScope.ADMINISTRATIVE,
        ...         MetadataScope.PRESERVATION,
        ...         MetadataScope.USE,
        ...     ],
        ...     "target_filename": "eml.xml",
        ...     "schema": get_xmlschema_validator("https://eml.ecoinformatics.org/eml-2.2.0/eml.xsd"),
        ...     "description": (
        ...         "This metadata file contains the dataset's aggregate metadata."
        ...         "This is a resource metadata document that provides information about the dataset itself such as a description (abstract) of the dataset, the agents responsible for authorship, publication and documentation, bibliographic and citation information, collection methods and much more."
        ...         "It is based on the Ecological Metadata Language."
        ...     ),
        ...     "get_architect_agent_prompt": (
        ...         lambda _: "Synthesize a comprehensive EML document capturing the study's scientific context, taxonomic coverage, provenance, and citations for global dataset indexing."
        ...     ),
        ... }
        >>> dwc_eml_metadata_goal["schema"]                 # doctest: +ELLIPSIS
        MassiXMLSchemaXmlschemalWrapper(schema=XMLSchema10...)
    """

    scopes: list[MetadataScope]
    level: MetadataLevel
    target_filename: str
    schema: AbstractXMLSchema
    description: str | None
    get_architect_agent_prompt: Callable[[MetadataArchitectPromptContext], str]


class MetadataConstructionStep(TypedDict):
    subject: str
    context: str
    instruction: str
    source_files: list[str]
    target_type: str
    target_attribute_xpath: str


class MetadataConstructionPlan(TypedDict):
    steps: list[MetadataConstructionStep]


class MetadataExport(TypedDict):
    destination_file: Path


class FileOverview(TypedDict):
    location: Path
    stats: os.stat_result


class CSVOverview(FileOverview):
    details: CSVDetails


class DatasetFileCollection(TypedDict):
    files: list[FileOverview]
    csv_files: list[CSVOverview]


class InquiryInput(TypedDict):
    prompt: str
    context: dict


class InquiryOutput(TypedDict):
    outcome: str


# Configurations
# --------------


class MassiRuntimeConfiguration(TypedDict):
    working_directory: str = "."
    output_directory: str = "."


# Workflow state
# --------------


class MassiExecutionMode(StrEnum):
    HUMAN_INQUIRY = "human-focused"
    """Focuses on human inquiry - interview the user about their dataset."""

    DATA_INQUIRY = "data-focused"
    """Focuses on automated data exploration - derive metadata from the dataset autonomously."""


# TODO(refactor): consider using LangGraph context for this or make immutable
class MassiRuntimeSettings(TypedDict):
    """Top-level, static settings, consistent throughout the workflow graph."""

    runtime_config: MassiRuntimeConfiguration = None
    execution_mode: MassiExecutionMode = MassiExecutionMode.HUMAN_INQUIRY


class MassiGoalResolutionState(MessagesState, total=False):
    # external static configuration
    settings: MassiRuntimeSettings
    # resolution inputs
    dataset: DatasetFileCollection
    goal: MetadataGoal
    # working data
    architect_prompt: str

    # draft
    original_metadata: dict
    validation_outcome: Any
    validation_summary: Any
    inquiry_plan: Any
    current_resolution_step: Any
    current_result: Any
    current_metadata: dict


class MassiCoreState(MessagesState, total=False):
    # external static configuration
    settings: MassiRuntimeSettings
    goals: list[MetadataGoal]
    # working data
    dataset: DatasetFileCollection
    resolutions: Annotated[MassiGoalResolutionState, operator.add]


# Service interfaces
# ------------------


class InquiryPlanner[P, M](ABC):
    _metadata_schema: type[M]
    _plan_schema: type[P]

    generate_plan: Callable[[Any], P]


class InquiryEngine[P](ABC):
    _plan_schema: type[P]

    is_completed: Callable[[P], bool]
    get_next_steps: Callable[[P], list[Any]]


class InquiryMechanism[P, M](TypedDict):
    planner: InquiryPlanner[P, M]
    engine: InquiryEngine[P]


class DataExplorer(ABC):
    explore: Callable[[InquiryInput], InquiryOutput]


class AuthorProxy(ABC):
    ask: Callable[[InquiryInput], InquiryOutput]


class MetadataBuilder[M](ABC):
    _metadata_schema: type[M]
    construct: Callable[[dict], M]


class MetadataExporter[M](ABC):
    _metadata_schema: type[M]
    export: Callable[[M], Path]


# Dependencies
# ------------


@dataclass
class Dependencies[T, M]:
    inquiry_mechanism: InquiryMechanism[T, M]
    data_explorer: DataExplorer
    author_proxy: AuthorProxy
    metadata_builder: MetadataBuilder[M]
    metadata_exporter: MetadataExporter[M]


# Message builders
# ----------------


class MetadataArchitectPrompts:

    @staticmethod
    def get_darwin_core_arhive_metadata_architect_prompt(
        context: MetadataArchitectPromptContext,
    ) -> str:
        return f"""
## **PROMPT FOR SUB-AGENT: DwC-A XML ARCHITECT**

### **Role**

You are a precision XML Developer specializing in Darwin Core Archive (DwC-A) structures. Your task is to generate a `meta.xml` file that accurately reflects a **Star Schema** organization derived from a set of provided CSV files and an XSD metadata schema.

### **Contextual Building Blocks**

* **XSD Schema:**
--- BEGIN: XSD Schema ---
{context["xsd_schema"]}
--- END: XSD Schema ---

* **Dataset file overview:**
--- BEGIN: Dataset file overview ---
{context["file_overview"]}
--- END: Dataset file overview ---

* **CSV Overview:**
--- BEGIN: CSV Overview ---
{context["csv_overview"]}
--- END: CSV Overview ---

### **Task: Star Schema Identification**

Before generating the XML, you must analyze the relationship between the provided CSV files to establish the Star Schema:

* **Identify the Core:** Locate the primary entity file (the "Core") which contains the base records (e.g., Events or Taxa) that other files reference.
* **Identify Extensions:** Locate subordinate files (the "Extensions") that provide many-to-one supplemental data to the Core records.
* **Identify the Linkage:** Determine the specific column (the foreign key) used to join Extension records back to the Core's unique identifier.

### **Technical Logic & Mapping Rules**

Generate the XML following the `<archive>` structure. Where metadata is missing or ambiguous, you must insert placeholders using the syntax: `{{{{GAP_XXX:TYPE:DESCRIPTION}}}}`.

**1. Disambiguation of Gap TYPEs:**

* **INDEX:** Use for `0-based` column positions.
* **URI:** Use for the `rowType` or `term` attributes.
* **STRING:** Use for general file attributes (e.g., `encoding`, `fieldsTerminatedBy`).

**2. Strict Mapping Rules:**

* **Term Mapping:** If a CSV header name matches a known Darwin Core term, use that URI for the `term` attribute; **otherwise**, generate a `{{{{GAP_XXX:URI:HEADER_NAME}}}}` placeholder.
* **Index Mapping:** If the column index can be provided with absolute certainty from the CSV header order, specify it directly (e.g., `index="0"`); **otherwise**, generate a `{{{{GAP_XXX:INDEX:COLUMN_NAME}}}}` placeholder.

### **Mapping Instructions**

1. **Archive Attributes:** Set the `metadata` attribute to a `URI` gap.
2. **Core Component:** * Identify the appropriate `rowType` URI.
    * Map the primary key to the `<id>` element.
    * Map all remaining columns to `<field>` elements using the Mapping Rules above.
3. **Extension Components:**
    * For each extension, map the foreign key to the `<coreid>` element.
    * Map extension columns to `<field>` elements using the Mapping Rules above.

### **Expected Output Format**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<archive xmlns="http://rs.tdwg.org/dwc/text/" metadata="{{{{GAP_001:URI:METADATA_LOCATION}}}}">
  <core rowType="[CORE_URI]" fieldsTerminatedBy="," fieldsEnclosedBy="&quot;" ignoreHeaderLines="1">
    <files>
      <location>[CORE_FILENAME]</location>
    </files>
    <id index="[PRIMARY_KEY_INDEX]" />
    <field index="1" term="http://rs.tdwg.org/dwc/terms/exampleTerm"/>
    <field index="{{{{GAP_002:INDEX:UNCERTAIN_COL}}}}" term="{{{{GAP_003:URI:UNMAPPED_HEADER}}}}"/>
  </core>
  <extension rowType="[EXTENSION_URI]">
    <files>
      <location>[EXTENSION_FILENAME]</location>
    </files>
    <coreid index="[FOREIGN_KEY_INDEX]" />
    </extension>
</archive>
```
""".strip()


# Workflow nodes
# --------------

# FIXME(implement): produce the nodes of the following graph
#   Inventory -> Plan -> (Execution -a-> (Operation => Execution) -b-> (Synthesis -> Export)) => Inventory


def _refine_initalisation(state: MassiCoreState) -> MassiCoreState:
    settings = state.get("settings")
    goals = state.get("goals")

    assert settings is not None, "`settings` must be provided at the start."
    assert goals is not None, "`goals` must be provided at the start."

    return {"goals": sorted(goals, lambda g: g["level"])}


def inventorize_dataset(state: MassiCoreState) -> MassiCoreState:
    work_dir = state["settings"]["runtime_config"]["working_directory"]
    paths = map(get_file_stats, walk_working_dir_for_files(seed_path=work_dir))
    file_overviews: list[FileOverview] = [
        {"location": p, "stats": s} for (p, s) in paths
    ]
    csv_overviews: list[CSVOverview] = [
        {**f, "details": get_csv_details(f["location"])}
        for f in file_overviews
        if f["location"].suffix == ".csv"
    ]
    return {"dataset": {"files": file_overviews, "csv_files": csv_overviews}}


def start_inquiry_cycle(state: MassiCoreState) -> MassiCoreState:
    settings = state["settings"]
    dataset = state["dataset"]
    active_goal_pointer = len(state["resolutions"])
    if active_goal_pointer < len(state["goals"]):
        goal = state["goals"][active_goal_pointer]
        return [
            Send(
                start_inquiry_planning.__name__,
                {"settings": settings, "goal": goal, "dataset": dataset},
            )
        ]
    else:
        return [Send(terminate.__name__, {**state})]


def start_inquiry_planning(state: MassiGoalResolutionState) -> MassiGoalResolutionState:
    csv_overview = "\n".join(
        [
            f'==> {c["location"]} <==\n-- head --\n{c["details"]["head"]}\n-- descriptive stats --\n{c["details"]["descriptive_stats"]}'
            for c in state["dataset"]["csv_files"]
        ]
    )
    file_overvew = "\n".join(
        [
            f'==> {fl["location"]} <==\n-- file stats --\n{fl["stats"]}'
            for fl in state["dataset"]["files"]
        ]
    )
    architect_context: MetadataArchitectPromptContext = {
        "csv_overview": csv_overview,
        "file_overview": file_overvew,
        "xsd_schema": state["goal"]["schema"].to_string(),
    }
    architect_prompt = state["goal"]["get_architect_agent_prompt"](architect_context)
    logger.debug(architect_prompt)
    return {"architect_prompt": architect_prompt}


def build_blueprint_xml(state: MassiGoalResolutionState) -> MassiGoalResolutionState:
    # FIXME(implement)
    ...


def fetch_placeholder_gaps(state: MassiGoalResolutionState) -> MassiGoalResolutionState:
    # FIXME(implement)
    ...


def produce_inquiry_plan(state: MassiGoalResolutionState) -> MassiGoalResolutionState:
    # FIXME(implement)
    ...


def execute_inquiry_plan(state: MassiGoalResolutionState) -> MassiGoalResolutionState:
    # FIXME(implement)
    ...


def perform_inquiry_step(state: MassiGoalResolutionState) -> MassiGoalResolutionState:
    # TODO(refactor): consider how to support potentially parallel processing, maybe a separate operator state?
    # FIXME(implement)
    ...


def synthesize_metadata(state: MassiGoalResolutionState) -> MassiGoalResolutionState:
    # FIXME(implement)
    ...


def export_metadata(state: MassiGoalResolutionState) -> MassiGoalResolutionState:
    # FIXME(implement)
    ...


def terminate(state: MassiCoreState) -> MassiCoreState:
    # FIXME(implement)
    ...


# Mapper utilities
# ----------------

# FIXME(implement): support map / reduce pattern

...

# Conditionals
# ------------

# FIXME(implement): routing and conditional transition checks

...

# Graph construction
# ------------------


def build_graph():
    # FIXME(implement): connect all nodes and edges together
    ...
