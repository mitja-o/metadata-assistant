import logging
import operator
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum, StrEnum
from functools import partial
from pathlib import Path
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send

from massi.agents.tools import (
    CSVDetails,
    get_csv_details,
    get_file_stats,
    get_xmlschema_validator,
    walk_working_dir_for_files,
)

# Logger
# ------

# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
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
        ...     "schema_source": "https://dwc.tdwg.org/text/tdwg_dwc_text.xsd",
        ...     "description": (
        ...         "This metadata file describes the archive and data file structure."
        ...         "A descriptor metafile describes how the files in your archive are organized."
        ...         "It describes the files in the archive and maps each data column to a corresponding standard Darwin Core or Extension term."
        ...         "The metafile is a relatively simple XML file format."
        ...     ),
        ...     "metadata_goal_key": "darwin_core",
        ... }
        >>> get_xmlschema_validator(dwc_data_file_metadata_goal["schema_source"]) # doctest: +ELLIPSIS
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
        ...     "schema_source": "https://eml.ecoinformatics.org/eml-2.2.0/eml.xsd",
        ...     "description": (
        ...         "This metadata file contains the dataset's aggregate metadata."
        ...         "This is a resource metadata document that provides information about the dataset itself such as a description (abstract) of the dataset, the agents responsible for authorship, publication and documentation, bibliographic and citation information, collection methods and much more."
        ...         "It is based on the Ecological Metadata Language."
        ...     ),
        ...     "metadata_goal_key": "eml",
        ... }
        >>> get_xmlschema_validator(dwc_eml_metadata_goal["schema_source"]) # doctest: +ELLIPSIS
        MassiXMLSchemaXmlschemalWrapper(schema=XMLSchema10...)
    """

    scopes: list[MetadataScope]
    level: MetadataLevel
    target_filename: str
    # schema: AbstractXMLSchema
    schema_source: str
    description: str | None
    metadata_goal_key: str


class MetadataBlueprint(TypedDict):
    content: str


class MetadataGapTask(TypedDict):
    gap_id: str
    gap_type: str
    gap_description: str
    gap_replacement_pattern: str
    """Exact match match of how the gap appears in the blueprint."""
    gap_scope_files: list[str]
    """List of file paths relevant for filling in the gap"""
    gap_derivation_request: str
    """A prompt aimed at a Gap Derivation Agent, to request the derivation of the needed information. Prompt should include sufficient context and give a clear derivation instruction. The prompt should include a strategy for a 'meaningful default' if a reliable value can not be derived."""


class MetadataGapDerivationPlan(TypedDict):
    gaps: list[MetadataGapTask]


class GapTaskValidation(TypedDict):
    valid_pattern: bool
    valid_files: bool


class VerifiedMetadataGapTask(MetadataGapTask):
    valid: bool
    validation: GapTaskValidation


class VerifiedMetadataGapDerivationPlan(TypedDict):
    gaps: list[VerifiedMetadataGapTask]


class MetadataGapDerivationResult(TypedDict):
    content: str


class MetadataGapTaskOutcome(TypedDict):
    task: MetadataGapTask
    result: MetadataGapDerivationResult


class MetadataExport(TypedDict):
    destination_file: Path


class FileOverview(TypedDict):
    location: Path
    stats: str


class CSVOverview(FileOverview):
    details: CSVDetails


class DatasetFileCollection(TypedDict):
    files: list[FileOverview]
    csv_files: list[CSVOverview]


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


class MassiGoalResolutionState(MessagesState, total=False):
    # external static configuration
    settings: MassiRuntimeSettings
    # resolution inputs
    dataset: DatasetFileCollection
    goal: MetadataGoal
    # working data
    context_blocks: str
    architect_prompt: str
    architect_xml_blueprint: MetadataBlueprint
    working_copy_xml_blueprint: MetadataBlueprint
    gap_derivation_plan: MetadataGapDerivationPlan
    verified_gap_derivation_plan: VerifiedMetadataGapDerivationPlan
    # TODO: make a better plan execution engine
    current_gap_task_pointer: int
    current_gap_instruction_prompt: str
    last_gap_derivation_result: MetadataGapTaskOutcome


class MassiCoreState(MessagesState, total=False):
    # external static configuration
    settings: MassiRuntimeSettings
    goals: list[MetadataGoal]
    # working data
    dataset: DatasetFileCollection
    resolutions: Annotated[list[MassiGoalResolutionState], operator.add]


# Data Mappers
# ------------


def validate_gap_task(
    gap_task: MetadataGapTask, state: MassiGoalResolutionState | None = None
) -> VerifiedMetadataGapTask:
    blueprint: MetadataBlueprint = state["architect_xml_blueprint"]
    validation: GapTaskValidation = {
        "valid_pattern": gap_task["gap_replacement_pattern"] in blueprint["content"],
        "valid_files": all(
            (
                bool(gap_task["gap_scope_files"]),
                (
                    set(gap_task["gap_scope_files"])
                    <= set([str(f["location"]) for f in state["dataset"]["files"]])
                ),
            ),
        ),
    }
    return {
        **gap_task,
        "valid": all((validation["valid_files"], validation["valid_pattern"])),
        "validation": validation,
    }


def take_valid_plan_tasks(
    state: MassiGoalResolutionState,
) -> VerifiedMetadataGapDerivationPlan:
    return {
        **state["verified_gap_derivation_plan"],
        "gaps": [
            gt for gt in state["verified_gap_derivation_plan"]["gaps"] if gt["valid"]
        ],
    }


# Message builders
# ----------------


class XMLBlueprint:
    @staticmethod
    def get_gap_pattern(
        gap_id: str = "GAP_XXX",
        gap_type: str = "TYPE",
        gap_description: str = "DESCRIPTION",
    ) -> str:
        return f"{{{{{gap_id}:{gap_type}:{gap_description}}}}}"

    @staticmethod
    def get_gap_type_description() -> str:
        return """
* **INDEX:** Use for `0-based` column positions.
* **URI:** Use for the `rowType` or `term` attributes.
* **STRING:** Use for general file attributes (e.g., `encoding`, `fieldsTerminatedBy`).
""".strip()

    @classmethod
    def get_mapping_rules(cls) -> str:
        return f"""
* **Term Mapping:** If a CSV header name matches a known Darwin Core term, use that URI for the `term` attribute; **otherwise**, generate a `{cls.get_gap_pattern(gap_type="URI", gap_description="HEADER_NAME")}` placeholder.
* **Index Mapping:** If the column index can be provided with absolute certainty from the CSV header order, specify it directly (e.g., `index="0"`); **otherwise**, generate a `{cls.get_gap_pattern(gap_type="INDEX", gap_description="COLUMN_NAME")}` placeholder.
""".strip()


class MetadataAgentPromptBuilder(ABC):
    @abstractmethod
    def get_context_blocks(self, context: MetadataArchitectPromptContext) -> str: ...
    @abstractmethod
    def get_architect_prompt(self, context: str) -> str: ...
    @abstractmethod
    def get_reviewer_prompt(self, architect_prompt: str, xml_blueprint: str) -> str: ...


class MetadataArchitectPrompts(MetadataAgentPromptBuilder):

    def get_context_blocks(self, context):
        return f"""
* **XSD Schema:**
--- BEGIN: XSD Schema ---
```xml
{context["xsd_schema"]}
```
--- END: XSD Schema ---

* **Dataset file overview:**
--- BEGIN: Dataset file overview ---
{context["file_overview"]}
--- END: Dataset file overview ---

* **CSV Overview:**
--- BEGIN: CSV Overview ---
{context["csv_overview"]}
--- END: CSV Overview ---
""".strip()

    def get_architect_prompt(
        self,
        context: MetadataArchitectPromptContext,
    ) -> str:
        return f"""
## **PROMPT FOR SUB-AGENT: DwC-A XML ARCHITECT**

### **Role**

You are a precision XML Developer specializing in Darwin Core Archive (DwC-A) structures. Your task is to generate a `meta.xml` file that accurately reflects a **Star Schema** organization derived from a set of provided CSV files and an XSD metadata schema.

### **Contextual Building Blocks**

{context}

### **Task: Star Schema Identification**

Before generating the XML, you must analyze the relationship between the provided CSV files to establish the Star Schema:

* **Identify the Core:** Locate the primary entity file (the "Core") which contains the base records (e.g., Events or Taxa) that other files reference.
* **Identify Extensions:** Locate subordinate files (the "Extensions") that provide many-to-one supplemental data to the Core records.
* **Identify the Linkage:** Determine the specific column (the foreign key) used to join Extension records back to the Core's unique identifier.

### **Technical Logic & Mapping Rules**

Generate the XML following the `<archive>` structure. Where metadata is missing or ambiguous, you must insert placeholders using the syntax: `{XMLBlueprint.get_gap_pattern()}`.

**1. Disambiguation of Gap TYPEs:**

{XMLBlueprint.get_gap_type_description()}

**2. Strict Mapping Rules:**

{XMLBlueprint.get_mapping_rules()}

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
<archive xmlns="http://rs.tdwg.org/dwc/text/" metadata="{XMLBlueprint.get_gap_pattern(gap_id="GAP_001", gap_type="URI", gap_description="METADATA_LOCATION")}">
  <core rowType="[CORE_URI]" fieldsTerminatedBy="," fieldsEnclosedBy="&quot;" ignoreHeaderLines="1">
    <files>
      <location>[CORE_FILENAME]</location>
    </files>
    <id index="[PRIMARY_KEY_INDEX]" />
    <field index="1" term="http://rs.tdwg.org/dwc/terms/exampleTerm"/>
    <field index="{XMLBlueprint.get_gap_pattern(gap_id="GAP_002", gap_type="INDEX", gap_description="UNCERTAIN_COL")}" term="{XMLBlueprint.get_gap_pattern(gap_id="GAP_003", gap_type="URI", gap_description="UNMAPPED_HEADER")}"/>
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

    def get_reviewer_prompt(
        self, context_blocks: str, architect_prompt: str, xml_blueprint: str
    ) -> str:
        return f"""
## System Prompt: XML Blueprint Reviewer

### Role

You are a **Technical Metadata Analyst** specializing in Darwin Core (DwC) standards and XML Schema validation. Your purpose is to bridge the gap between a high-level XML blueprint and actionable data exploration tasks.

### Input Context

You will be provided with:

1. **The Original Design Context:** The XSD schema goals and high-level overviews of the available CSV datasets (columns and headers).
2. **The XML Blueprint:** A draft `meta.xml` or DwC-Archive metadata file containing placeholders in the format `{{GAP_ID:GAP_TYPE:GAP_DESCRIPTION}}`.

### Instructions

1. **Analyze the Blueprint:** Locate every placeholder matching the pattern `{{GAP_ID:GAP_TYPE:GAP_DESCRIPTION}}`.
2. **Scope Determination:** For each gap, identify which CSV file(s) from the Dataset Inventory contain the raw data necessary to resolve it (e.g., if the gap is in `dwc:scientificName`, scope it to the file containing taxonomic strings).
3. **Draft Derivation Requests:** Write a specific, standalone instruction for the **Gap Derivation Agent**. This agent can execute Python/SQL to explore CSVs. Your instruction must:
    * State exactly what to look for.
    * Provide logic for handling anomalies (e.g., "If `eventDate` is null, use the file's 'Date Collected' column").
    * Define a **Meaningful Default** (e.g., "If no coordinate system is found, default to 'WGS84'").
4. **Output Format:** Return a valid JSON list of objects matching the `MetadataGap` schema.

---

### Extraction Schema

Return the data in this structure:

```json
{{"gaps": [
  {{
    "gap_id": "Unique string from the gap pattern",
    "gap_type": "The category (e.g., Attribute, Element, Mapping)",
    "gap_description": "Brief explanation of what is missing",
    "gap_replacement_pattern": "The exact full string to be replaced (e.g., '{XMLBlueprint.get_gap_pattern(gap_id="GAP_001", gap_type="URI", gap_description="METADATA_LOCATION")}')",
    "gap_scope_files": ["list_of_relevant_filenames.csv"],
    "gap_derivation_request": "Detailed prompt for the execution agent. Include: 1. Goal 2. Column logic 3. Transformation rules (if any) 4. Fallback/Default value strategy."
  }}
]}}
```

### Constraints & Quality Gates

* **No Hallucinations:** Only include gaps explicitly marked in the Blueprint.
* **Atomicity:** Each `gap_derivation_request` must be a self-contained prompt. Do not refer to "the previous message" or "other gaps."
* **Grounding:** The `gap_scope_files` must be given and can not be empty. Specify the files that are most relevant based on the context and the blueprint structure. Only use the files specified in the Data Context section.
* **Precision:** The `gap_replacement_pattern` must be an **exact string match** to allow for programmatic `string.replace()` operations later.
* **Summary:** The `gap_description` must be concise and summarise the context in which the gap is found.

### Data Context

{context_blocks}

---

## Review Execution

**Please process the following input:**

**[ORIGINAL CONTEXT]**
{architect_prompt}

**[XML BLUEPRINT]**
{xml_blueprint}
"""


METADATA_AGENT_PROMPT_BUILDER_REGISTRY: dict[str, MetadataAgentPromptBuilder] = {
    "darwin_core": MetadataArchitectPrompts()
}


# Service interfaces
# ------------------


class MetadataArchitect(ABC):
    @abstractmethod
    def invoke(self, prompt: str) -> MetadataBlueprint: ...


class MetadataBlueprintReviewer(ABC):
    @abstractmethod
    def invoke(self, prompt: str) -> MetadataGapDerivationPlan: ...


class MetadataGapDerivationManager(ABC):
    @abstractmethod
    def invoke(
        self,
        task: MetadataGapTask,
        execution_mode: MassiExecutionMode,
        architect_prompt: str,
        xml_blueprint: str,
    ) -> str: ...


class MetadataGapDerivationExecutor(ABC):
    @abstractmethod
    def invoke(
        self,
        prompt: str,
        task: MetadataGapTask,
    ) -> MetadataGapTaskOutcome: ...


class MetadataGapPatcher(ABC):
    @abstractmethod
    def invoke(
        self,
        outcome: MetadataGapTaskOutcome,
        blueprint: MetadataBlueprint,
    ) -> MetadataBlueprint: ...


# Workflow implementation
# -----------------------

type MassiCoreWorkflowGraph = CompiledStateGraph[
    MassiCoreState, None, MassiCoreState, MassiCoreState
]
type MassiResolutionWorkflowGraph = CompiledStateGraph[
    MassiGoalResolutionState, None, MassiGoalResolutionState, MassiGoalResolutionState
]


@dataclass
class MassiWorkflow[T]:
    graph: T
    execution_settings: dict[str, any]


# Dependencies
# ------------


@dataclass
class Dependencies:
    execution_mode: MassiExecutionMode = MassiExecutionMode.HUMAN_INQUIRY

    architect_client: MetadataArchitect | None = None
    reviewer_client: MetadataBlueprintReviewer | None = None
    gap_derivation_manager_client: MetadataGapDerivationManager | None = None
    data_explorer_client: MetadataGapDerivationExecutor | None = None
    author_interviewer_client: MetadataGapDerivationExecutor | None = None
    metadata_gap_patcher_client: MetadataGapPatcher | None = None

    metadata_resolution_subgraph: MassiWorkflow[MassiResolutionWorkflowGraph] | None = (
        None
    )


# Workflow nodes
# --------------


# FIXME(implement): produce the nodes of the following graph
#   Inventory -> Plan -> (Execution -a-> (Operation => Execution) -b-> (Synthesis -> Export)) => Inventory


def _refine_initalisation(state: MassiCoreState) -> MassiCoreState:
    settings = state.get("settings")
    goals = state.get("goals")

    assert settings is not None, "`settings` must be provided at the start."
    assert goals is not None, "`goals` must be provided at the start."

    return {"goals": sorted(goals, key=lambda g: g["level"])}


def inventorize_dataset(state: MassiCoreState) -> MassiCoreState:
    work_dir = state["settings"]["runtime_config"]["working_directory"]
    paths = map(get_file_stats, walk_working_dir_for_files(seed_path=work_dir))
    file_overviews: list[FileOverview] = [
        {"location": p, "stats": str(s)} for (p, s) in paths
    ]
    csv_overviews: list[CSVOverview] = [
        {**f, "details": get_csv_details(f["location"])}
        for f in file_overviews
        if f["location"].suffix == ".csv"
    ]
    return {"dataset": {"files": file_overviews, "csv_files": csv_overviews}}


# -- Map
def map_goals(state: MassiCoreState) -> MassiCoreState:
    settings = state["settings"]
    dataset = state["dataset"]
    active_goal_pointer = len(state["resolutions"])
    if active_goal_pointer < len(state["goals"]):
        goal = state["goals"][active_goal_pointer]
        return [
            Send(
                run_metadata_derivation_goal.__name__,
                {"settings": settings, "goal": goal, "dataset": dataset},
            )
        ]
    else:
        return [Send(terminate.__name__, {**state})]


# -- Subgraph invokation
def run_metadata_derivation_goal(
    state: MassiGoalResolutionState,
    dependencies: Dependencies,
) -> MassiCoreState:
    assert dependencies.metadata_resolution_subgraph
    resolution_subgraph: MassiResolutionWorkflowGraph = (
        dependencies.metadata_resolution_subgraph.graph
    )
    resolution: MassiGoalResolutionState = resolution_subgraph.invoke(state)
    logger.debug(resolution)
    return {"resolutions": [resolution]}


def terminate(state: MassiCoreState) -> MassiCoreState:
    # FIXME(implement): should summarise the results and exit
    logger.debug("Reached the end")
    logger.debug(f"{state=}")
    return {}


# Derivation subgraph
# -------------------


# -- Subgraph
def start_metadata_derivation(
    state: MassiGoalResolutionState,
) -> MassiGoalResolutionState:
    prompt_builder = METADATA_AGENT_PROMPT_BUILDER_REGISTRY.get(
        state["goal"]["metadata_goal_key"]
    )
    assert (
        prompt_builder
    ), f"Could not create a prompt builder instance - using unknown metadata goal key: {state["goal"]["metadata_goal_key"]}."

    csv_overview = "\n".join(
        [
            f'==> {c["location"]} <==\n-- head ({c["details"]["head_size"]}/{c["details"]["row_count"]} rows) --\n```csv\n{c["details"]["head"]}\n```\n-- column descriptive statistics ({c["details"]["column_count"]} columns) --\n```csv\n{c["details"]["descriptive_stats"]}\n```'
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
        "xsd_schema": get_xmlschema_validator(
            state["goal"]["schema_source"]
        ).to_string(),
    }
    context_blocks = prompt_builder.get_context_blocks(architect_context)
    architect_prompt = prompt_builder.get_architect_prompt(context_blocks)
    logger.debug(architect_prompt)
    return {
        "context_blocks": prompt_builder.get_context_blocks(architect_context),
        "architect_prompt": architect_prompt,
    }


def build_blueprint_xml(
    state: MassiGoalResolutionState, dependencies: Dependencies | None = None
) -> MassiGoalResolutionState:
    assert dependencies
    architect_agent = dependencies.architect_client
    assert architect_agent

    result = architect_agent.invoke(state["architect_prompt"])
    logger.debug(result)
    return {"architect_xml_blueprint": result}


def make_gap_derivation_plan(
    state: MassiGoalResolutionState, dependencies: Dependencies | None = None
) -> MassiGoalResolutionState:
    assert dependencies
    reviewer_agent = dependencies.reviewer_client
    assert reviewer_agent

    blueprint = state["architect_xml_blueprint"]
    prompt_builder = METADATA_AGENT_PROMPT_BUILDER_REGISTRY.get(
        state["goal"]["metadata_goal_key"]
    )
    reviewer_prompt = prompt_builder.get_reviewer_prompt(
        state["context_blocks"],
        state["architect_prompt"],
        blueprint["content"],
    )
    result: MetadataGapDerivationPlan = reviewer_agent.invoke(reviewer_prompt)
    logger.debug(result)

    return {
        "gap_derivation_plan": result,
        "current_gap_task_pointer": 0,
        "working_copy_xml_blueprint": blueprint,
    }


def verify_gap_derivation_plan(
    state: MassiGoalResolutionState,
) -> MassiGoalResolutionState:
    plan = state["gap_derivation_plan"]
    gaps = plan["gaps"]
    verified_plan: VerifiedMetadataGapDerivationPlan = {
        **plan,
        "gaps": list(map(partial(validate_gap_task, state=state), gaps)),
    }

    return {"verified_gap_derivation_plan": verified_plan}


# *__Conditional__*
def check_is_plan_usable(state: MassiGoalResolutionState) -> str:
    valid_gap_tasks: VerifiedMetadataGapDerivationPlan = take_valid_plan_tasks(state)
    total_steps_count = len(valid_gap_tasks["gaps"])

    if total_steps_count < len(state["verified_gap_derivation_plan"]["gaps"]):
        logger.warning(
            "Some gap task are not valid and are not included for execution."
        )

    current_pointer = state["current_gap_task_pointer"]
    completed = total_steps_count <= current_pointer
    return (
        export_metadata.__name__
        if completed
        else prepare_derivation_instruction.__name__
    )


def prepare_derivation_instruction(
    state: MassiGoalResolutionState, dependencies: Dependencies | None = None
) -> MassiGoalResolutionState:
    assert dependencies
    gap_derivation_manager = dependencies.gap_derivation_manager_client
    assert gap_derivation_manager

    valid_gap_tasks: VerifiedMetadataGapDerivationPlan = take_valid_plan_tasks(state)
    current_gap_task_pointer = state["current_gap_task_pointer"]
    current_gap_task = valid_gap_tasks["gaps"][current_gap_task_pointer]
    logger.debug(current_gap_task)

    rich_instruction: str = gap_derivation_manager.invoke(
        current_gap_task,
        dependencies.execution_mode,
        state["architect_prompt"],
        state["working_copy_xml_blueprint"]["content"],
    )
    logger.debug(rich_instruction)

    return {"current_gap_instruction_prompt": rich_instruction}


def execute_gap_derivation(
    state: MassiGoalResolutionState, dependencies: Dependencies | None = None
) -> MassiGoalResolutionState:
    assert dependencies
    # Select the executor based on the condfigured mode:
    gap_derivation_executor = (
        dependencies.data_explorer_client
        if dependencies.execution_mode == MassiExecutionMode.DATA_INQUIRY
        else dependencies.author_interviewer_client
    )
    assert gap_derivation_executor

    valid_gap_tasks: VerifiedMetadataGapDerivationPlan = take_valid_plan_tasks(state)
    current_task_pointer = state["current_gap_task_pointer"]
    current_gap_task = valid_gap_tasks["gaps"][current_task_pointer]
    current_gap_instruction = state["current_gap_instruction_prompt"]

    result = gap_derivation_executor.invoke(current_gap_instruction, current_gap_task)

    return {"last_gap_derivation_result": result}


def synthesize_metadata(
    state: MassiGoalResolutionState, dependencies: Dependencies | None = None
) -> MassiGoalResolutionState:
    assert dependencies
    metadata_gap_patcher = dependencies.metadata_gap_patcher_client
    assert metadata_gap_patcher

    updated_blueprint = metadata_gap_patcher.invoke(
        state["last_gap_derivation_result"],
        state["working_copy_xml_blueprint"],
    )

    return {
        "working_copy_xml_blueprint": updated_blueprint,
        "current_gap_task_pointer": state["current_gap_task_pointer"] + 1,
    }


def export_metadata(state: MassiGoalResolutionState) -> MassiGoalResolutionState:
    # FIXME(implement): should store the metadata file into the specified target
    logger.debug("Reached the end")
    logger.debug(f"{state=}")
    return {}


# Graph construction
# ------------------


def _build_goal_resolution_graph(
    dependencies: Dependencies,
) -> MassiWorkflow[MassiGoalResolutionState]:
    builder = StateGraph(MassiGoalResolutionState)

    nodes = [
        (start_metadata_derivation, {}),
        (build_blueprint_xml, {"dependencies": dependencies}),
        (make_gap_derivation_plan, {"dependencies": dependencies}),
        (verify_gap_derivation_plan, {}),
        (prepare_derivation_instruction, {"dependencies": dependencies}),
        (execute_gap_derivation, {"dependencies": dependencies}),
        (synthesize_metadata, {"dependencies": dependencies}),
        (export_metadata, {}),
    ]
    for fn, kwargs in nodes:
        node_name = fn.__name__
        node_func = partial(fn, **kwargs) if kwargs else fn
        builder.add_node(node_name, node_func)

    builder.add_edge(START, start_metadata_derivation.__name__)
    builder.add_edge(start_metadata_derivation.__name__, build_blueprint_xml.__name__)
    builder.add_edge(build_blueprint_xml.__name__, make_gap_derivation_plan.__name__)
    builder.add_edge(
        make_gap_derivation_plan.__name__, verify_gap_derivation_plan.__name__
    )
    # * export if completed, otherwise process
    builder.add_conditional_edges(
        verify_gap_derivation_plan.__name__,
        check_is_plan_usable,
        [prepare_derivation_instruction.__name__, export_metadata.__name__],
    )
    builder.add_edge(
        prepare_derivation_instruction.__name__, execute_gap_derivation.__name__
    )
    builder.add_edge(execute_gap_derivation.__name__, synthesize_metadata.__name__)
    # * loop back to verification
    builder.add_edge(synthesize_metadata.__name__, verify_gap_derivation_plan.__name__)
    builder.add_edge(export_metadata.__name__, END)

    return MassiWorkflow(
        graph=builder.compile(checkpointer=None),
        execution_settings=dict(),
    )


def build_graph(dependencies: Dependencies) -> MassiWorkflow[MassiCoreWorkflowGraph]:
    builder = StateGraph(MassiCoreState)

    nodes = [
        (_refine_initalisation, {}),
        (inventorize_dataset, {}),
        (run_metadata_derivation_goal, {"dependencies": dependencies}),
        (terminate, {}),
    ]
    for fn, kwargs in nodes:
        node_name = fn.__name__
        node_func = partial(fn, **kwargs) if kwargs else fn
        builder.add_node(node_name, node_func)

    builder.add_edge(START, _refine_initalisation.__name__)
    builder.add_edge(_refine_initalisation.__name__, inventorize_dataset.__name__)

    builder.add_conditional_edges(
        inventorize_dataset.__name__,
        map_goals,
        [run_metadata_derivation_goal.__name__, terminate.__name__],
    )

    builder.add_edge(terminate.__name__, END)

    # memory = None
    memory = MemorySaver()
    return MassiWorkflow(
        graph=builder.compile(checkpointer=memory),
        execution_settings=dict(),
    )
