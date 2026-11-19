from collections.abc import Callable
from pathlib import Path
from typing import TypedDict

from langgraph.graph import MessagesState
from pydantic import TypeAdapter

# Shared Utilities
# ----------------


def validate_dict(dict_type: type, item: dict) -> bool:
    TypeAdapter(dict_type).validate_python(item)
    return True


# Global Data Transfer Objects
# ----------------------------


class MetadataSchema:
    name: str
    """The official name of this metadata schema: e.g. `'Ecological Metadata Language'`.
    See: <https://eml.ecoinformatics.org/>"""
    abbreviation: str
    """The official abbreviation of the name: e.g. `'EML'`.
    See: <https://eml.ecoinformatics.org/>"""
    summary: str
    """Brief summary of what this schema is for: e.g. `'The Ecological Metadata Language (EML) defines a comprehensive vocabulary and a readable XML markup syntax for documenting research data.'`. 
    See: <https://eml.ecoinformatics.org/>"""
    specification: str
    """The string-formatted schema specification: e.g. `'<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" ...>...</xs:schema>'`
    See: <https://eml.ecoinformatics.org/>"""
    specification_format: str
    """What is the format the schema is specified in: e.g. `'XSD'`, `'JsonSchema'`, etc.
    See: <https://eml.ecoinformatics.org/>"""


# Agent Data Transfer Objects
# ---------------------------

# Architect
# ~~~~~~~~~


class ArchitectInputs(TypedDict):
    dataset_overview: str
    metadata_schema: str


class ArchitectOutputs(TypedDict):
    metadata_template: str
    """Metadata template for the given dataset and metadata schema."""


# Populator
# ~~~~~~~~~


class PopulatorOutputs(TypedDict):
    metadata_instance: str
    """A full metadata instance populated from the metadata template."""


# Workflow Graph State
# --------------------


class WorkflowInputs(TypedDict):
    dataset_path: Path
    """The path to the dataset files."""
    metadata_schema: MetadataSchema
    """The metadata schema description."""


class WorkflowOutputs(TypedDict):
    metadata_instance: str
    """A full metadata instance populated from the metadata template."""


class WorkflowState(MessagesState, total=False):
    # full workflow
    # -------------
    workflow_inputs: WorkflowInputs
    workflow_outputs: WorkflowOutputs
    # nested agents
    # -------------
    architect_inputs: ArchitectInputs
    architect_outputs: ArchitectOutputs
    populator_outputs: PopulatorOutputs


type Node = Callable[[WorkflowState], WorkflowState]
