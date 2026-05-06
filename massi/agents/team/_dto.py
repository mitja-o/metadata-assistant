"""Definitions of data transfer objects shared between the massi agents."""

from enum import IntEnum, StrEnum
from pathlib import Path
from typing import Literal, TypedDict

# Data Transfer Objects
# ---------------------


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


type SupportedMetadataGoals = Literal["darwin_core", "eml"]
type MassiExecutionMode = Literal["data-focus", "author-focus"]


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
    schema_source: str
    description: str | None
    metadata_goal_key: SupportedMetadataGoals
    ground_truth_metadata_file: str | None
    """An optional ground truth metadata instance.  
    IMPORTANT: If provided, it should be used as a basis for the metadata template.
    """


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
    tabular_files: list[str]
    plaintext_files: list[str]


class VerifiedMetadataGapTask(MetadataGapTask):
    valid: bool
    validation: GapTaskValidation
    gap_scope_tabular_files: list[str]
    gap_scope_plaintext_files: list[str]


class VerifiedMetadataGapDerivationPlan(TypedDict):
    gaps: list[VerifiedMetadataGapTask]


class MetadataGapDerivationResult(TypedDict):
    content: str


class MetadataGapTaskOutcome(TypedDict):
    task: MetadataGapTask
    result: MetadataGapDerivationResult


class FileOverview(TypedDict):
    location: str
    stats: str


class CSVDetails(TypedDict):
    raw_head: str
    dataframe_head: str
    descriptive_stats: str
    column_count: int
    row_count: int
    head_size: int


class CSVOverview(FileOverview):
    details: CSVDetails


class DatasetFileCollection(TypedDict):
    files: list[FileOverview]
    csv_files: list[CSVOverview]


class XMLBlueprintGapPattern:
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
