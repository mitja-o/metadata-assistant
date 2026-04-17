from abc import ABC, abstractmethod

from langchain.chat_models import BaseChatModel
from langchain.messages import HumanMessage

from massi.agents.team._dto import MetadataGapDerivationPlan, XMLBlueprintGapPattern

# Agent Protocol
# --------------


class MetadataBlueprintPlanner(ABC):
    @abstractmethod
    def get_system_prompt(
        self, context_blocks: str, architect_prompt: str, xml_blueprint: str
    ) -> str: ...

    @abstractmethod
    def invoke(self, prompt: str) -> MetadataGapDerivationPlan: ...


# Agent Instances
# ---------------


class DarwinCorePlanner(MetadataBlueprintPlanner):
    def __init__(self, llm_client: BaseChatModel):
        self._client = llm_client

    def get_system_prompt(
        self, context_blocks: str, architect_prompt: str, xml_blueprint: str
    ) -> str:
        return f"""
## System Prompt: XML Blueprint Derivation Planner

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
    "gap_replacement_pattern": "The exact full string to be replaced (e.g., '{XMLBlueprintGapPattern.get_gap_pattern(gap_id="GAP_001", gap_type="URI", gap_description="METADATA_LOCATION")}')",
    "gap_scope_files": ["list_of_relevant_filenames.csv"],
    "gap_derivation_request": "Detailed prompt for the execution agent. Include: 1. Goal 2. Column logic 3. Transformation rules (if any) 4. Fallback/Default value strategy."
  }}
]}}
```

### Constraints & Quality Gates

* **No Hallucinations:** Only include gaps explicitly marked in the Blueprint.
* **Atomicity:** Each `gap_derivation_request` must be a self-contained prompt. Do not refer to "the previous message" or "other gaps."
* **Grounding:** The `gap_scope_files` must be given and can not be empty. Specify the files that are most relevant based on the context and the blueprint structure. ALWAYS use the exact file paths specified in the Data Context section.
* **Precision:** The `gap_replacement_pattern` must be an **exact string match** to allow for programmatic `string.replace()` operations later.
* **Summary:** The `gap_description` must be concise and summarise the context in which the gap is found.

### Data Context

{context_blocks}

---

## Review and Planning Execution

**Please process the following input:**

**[ORIGINAL CONTEXT]**
{architect_prompt}

**[XML BLUEPRINT]**
{xml_blueprint}
"""

    def invoke(self, prompt: str) -> MetadataGapDerivationPlan:
        return self._client.with_structured_output(MetadataGapDerivationPlan).invoke(
            [HumanMessage(content=prompt)]
        )
