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
    def get_system_prompt(self, context_block: str) -> str: ...

    @abstractmethod
    def invoke(self, prompt: str) -> MetadataBlueprint: ...

    def get_context_prompt_block(self, context: ArchitectContextProps) -> str:
        """A standard way to format the context block."""
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


# Agent Instances
# ---------------

# Darwin Core
# :::::::::::


class DarwinCoreArchitect(MetadataArchitect):
    def __init__(self, llm_client: BaseChatModel):
        self._client = llm_client

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


# Ecological Metadata Language
# ::::::::::::::::::::::::::::


class EMLArchitect(MetadataArchitect):
    def __init__(self, llm_client: BaseChatModel):
        self._client = llm_client

    def get_system_prompt(self, context_block: str) -> str:
        return f"""
## **PROMPT FOR TEAM MEMBER AGENT: EML (Ecological Metadata Language) ARCHITECT**

### **Role**

You are a Senior Metadata Engineer specializing in EML 2.2.0. Your goal is to generate an `eml.xml` blueprint that captures the **high-level research context** and **methodological provenance** that sits outside the scope of Darwin Core (DwC) data mapping.

### **Contextual Building Blocks**

{context_block}

### **Task: Research Context & Provenance Mapping**

Focus on the following EML-specific modules which provide the essential "narrative" of the data:

1.  **Methods Module:** Document sampling protocols, quality control, and step-by-step procedures.
2.  **Project Module:** Map the institutional context, including funding, study area descriptions, and project personnel roles.
3.  **Maintenance Module:** Describe the frequency of updates and the current status of the dataset.
4.  **AdditionalMetadata Module:** Use this for custom extensions or information that doesn't fit standard schemas but is present in the context.

**Modular Schema Integration Clause:**
Search for specialized sub-packages (e.g., `eml-methods`, `eml-project`, `eml-access`). If the context hints at complex methodological details (e.g., sensor specs, lab protocols), generate a structured block with gaps even if the XSD provided is a high-level summary.

### **Technical Logic & Mapping Rules**

1. **Complementary Logic:** Do not spend effort on detailed column mapping (this is handled by the DwC Architect). Focus on the **Dataset-level** descriptive and administrative metadata.
2. **Gap Syntax:** Use `{XMLBlueprintGapPattern.get_gap_pattern()}` for all placeholders.
3. **Disambiguation:** Use **STRING** for prose, **DATE** for milestones, and **URI** for persistent identifiers.

### **Expected Output Format (Research Context Focus)**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<eml:eml 
    packageId="uuid-placeholder" 
    system="knb" 
    xmlns:eml="[https://eml.ecoinformatics.org/eml-2.2.0](https://eml.ecoinformatics.org/eml-2.2.0)"
    xmlns:xsi="[http://www.w3.org/2001/XMLSchema-instance](http://www.w3.org/2001/XMLSchema-instance)">
    
  <dataset>
    <title>{XMLBlueprintGapPattern.get_gap_pattern(gap_id="GAP_001", gap_type="STRING", gap_description="DATASET_TITLE")}</title>
    
    <creator>
      <individualName>
        <surName>{XMLBlueprintGapPattern.get_gap_pattern(gap_id="GAP_002", gap_type="STRING", gap_description="PI_SURNAME")}</surName>
      </individualName>
      <userId directory="[https://orcid.org](https://orcid.org)">{XMLBlueprintGapPattern.get_gap_pattern(gap_id="GAP_003", gap_type="URI", gap_description="ORCID")}</userId>
    </creator>

    <methods>
      <methodStep>
        <description>
          <para>{XMLBlueprintGapPattern.get_gap_pattern(gap_id="GAP_004", gap_type="STRING", gap_description="SAMPLING_PROTOCOL_NARRATIVE")}</para>
        </description>
        <instrumentation>{XMLBlueprintGapPattern.get_gap_pattern(gap_id="GAP_005", gap_type="STRING", gap_description="SENSOR_OR_EQUIPMENT_SPECS")}</instrumentation>
      </methodStep>
      <qualityControl>
        <description>
          <para>{XMLBlueprintGapPattern.get_gap_pattern(gap_id="GAP_006", gap_type="STRING", gap_description="QA_QC_PROCEDURES")}</para>
        </description>
      </qualityControl>
    </methods>

    <project>
      <title>{XMLBlueprintGapPattern.get_gap_pattern(gap_id="GAP_007", gap_type="STRING", gap_description="PARENT_PROJECT_TITLE")}</title>
      <personnel>
        <individualName><surName>...</surName></individualName>
        <role>Principal Investigator</role>
      </personnel>
      <funding>
        <para>{XMLBlueprintGapPattern.get_gap_pattern(gap_id="GAP_008", gap_type="STRING", gap_description="GRANT_AGENCY_AND_ID")}</para>
      </funding>
      <studyAreaDescription>
        <descriptor name="habitat_type" citableClassificationSystem="false">
          <descriptorValue>{XMLBlueprintGapPattern.get_gap_pattern(gap_id="GAP_009", gap_type="STRING", gap_description="HABITAT_CLASSIFICATION")}</descriptorValue>
        </descriptor>
      </studyAreaDescription>
    </project>

    <maintenance>
      <description><para>Dataset status: {XMLBlueprintGapPattern.get_gap_pattern(gap_id="GAP_010", gap_type="STRING", gap_description="MAINTENANCE_STATUS")}</para></description>
      <maintenanceUpdateFrequency>{XMLBlueprintGapPattern.get_gap_pattern(gap_id="GAP_011", gap_type="STRING", gap_description="UPDATE_FREQ")}</maintenanceUpdateFrequency>
    </maintenance>

    </dataset>

  <additionalMetadata>
    <metadata>
      {XMLBlueprintGapPattern.get_gap_pattern(gap_id="GAP_012", gap_type="STRING", gap_description="CUSTOM_METADATA_EXTENSIONS")}
    </metadata>
  </additionalMetadata>
</eml:eml>
```
""".strip()

    def invoke(self, prompt: str) -> MetadataBlueprint:
        # Utilizing structured output to ensure we get back our MetadataBlueprint TypedDict
        return self._client.with_structured_output(MetadataBlueprint).invoke(
            [HumanMessage(content=prompt)]
        )
