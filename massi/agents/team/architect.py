from abc import ABC, abstractmethod
from typing import TypedDict

from langchain.chat_models import BaseChatModel
from langchain.messages import HumanMessage

from massi.agents.team._dto import MetadataBlueprint, XMLBlueprintGapPattern

# Local DTOs
# ----------


class ArchitectContextProps(TypedDict):
    xsd_schema: str
    file_overview: str
    csv_overview: str


# Agent Protocol
# --------------


class MetadataArchitect(ABC):
    @abstractmethod
    def get_context_prompt_block(self, context: ArchitectContextProps) -> str: ...

    @abstractmethod
    def get_system_prompt(self, context_block: str) -> str: ...

    @abstractmethod
    def invoke(self, prompt: str) -> MetadataBlueprint: ...


# Agent Instances
# ---------------


class DarwinCoreArchitect(MetadataArchitect):
    def __init__(self, llm_client: BaseChatModel):
        self._client = llm_client

    def get_context_prompt_block(self, context: ArchitectContextProps) -> str:
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

    def get_system_prompt(self, context_block: str) -> str:
        return f"""
## **PROMPT FOR TEAM MEMBER AGENT: Darwin Core Archive (DwC-A) XML ARCHITECT**

### **Role**

You are a precision XML Developer specializing in Darwin Core Archive (DwC-A) structures. Your task is to generate a `meta.xml` file that accurately reflects a **Star Schema** organization derived from a set of provided CSV files and an XSD metadata schema.

### **Contextual Building Blocks**

{context_block}

### **Task: Star Schema Identification**

Before generating the XML, you must analyze the relationship between the provided CSV files to establish the Star Schema:

* **Identify the Core:** Locate the primary entity file (the "Core") which contains the base records (e.g., Events or Taxa) that other files reference.
* **Identify Extensions:** Locate subordinate files (the "Extensions") that provide many-to-one supplemental data to the Core records.
* **Identify the Linkage:** Determine the specific column (the foreign key) used to join Extension records back to the Core's unique identifier.

### **Technical Logic & Mapping Rules**

Generate the XML following the `<archive>` structure. Where metadata is missing or ambiguous, you must insert placeholders using the syntax: `{XMLBlueprintGapPattern.get_gap_pattern()}`.

**1. Disambiguation of Gap TYPEs:**

{XMLBlueprintGapPattern.get_gap_type_description()}

**2. Strict Mapping Rules:**

{XMLBlueprintGapPattern.get_mapping_rules()}

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
<archive xmlns="http://rs.tdwg.org/dwc/text/" metadata="{XMLBlueprintGapPattern.get_gap_pattern(gap_id="GAP_001", gap_type="URI", gap_description="METADATA_LOCATION")}">
  <core rowType="[CORE_URI]" fieldsTerminatedBy="," fieldsEnclosedBy="&quot;" ignoreHeaderLines="1">
    <files>
      <location>[CORE_FILENAME]</location>
    </files>
    <id index="[PRIMARY_KEY_INDEX]" />
    <field index="1" term="http://rs.tdwg.org/dwc/terms/exampleTerm"/>
    <field index="{XMLBlueprintGapPattern.get_gap_pattern(gap_id="GAP_002", gap_type="INDEX", gap_description="UNCERTAIN_COL")}" term="{XMLBlueprintGapPattern.get_gap_pattern(gap_id="GAP_003", gap_type="URI", gap_description="UNMAPPED_HEADER")}"/>
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

    def invoke(self, prompt: str) -> MetadataBlueprint:
        return self._client.with_structured_output(MetadataBlueprint).invoke(
            [HumanMessage(content=prompt)]
        )
