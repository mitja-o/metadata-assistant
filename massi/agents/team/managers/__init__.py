from abc import ABC, abstractmethod

from langchain.chat_models import BaseChatModel
from langchain.messages import HumanMessage, SystemMessage

from massi.agents.team._dto import MetadataGapTask, XMLBlueprintGapPattern

# Agent Protocol
# --------------


class GapDerivationManager(ABC):
    @abstractmethod
    def get_system_prompt(self) -> str: ...

    @abstractmethod
    def get_instruction_prompt(
        self,
        task: MetadataGapTask,
        architect_prompt: str,
        xml_blueprint: str,
    ) -> str: ...

    @abstractmethod
    def invoke(self, derivation_request: str) -> str:
        """A manager's task is to describe the derivation instruction to the derivation operator.
        It generates a structured prompt in order to guide the operators' derivation process.
        It uses the context provided to formulate the request most clearly.

        Args:
            derivation_request (str): the description of a task to derive a clear instruction for

        Returns:
            str: a structured prompt describing the derivation instruction to the operator
        """
        ...


# Agent Instances
# ---------------


class NaiveGapDerivationManager(GapDerivationManager):
    def get_system_prompt(self):
        return "n/a"

    def get_instruction_prompt(self, task: MetadataGapTask, *_args):
        return task["gap_derivation_request"]

    def invoke(self, derivation_request: str) -> str:
        return derivation_request


class DataGapDerivationManager(GapDerivationManager):
    def __init__(self, llm_client: BaseChatModel):
        self._client = llm_client

    def get_system_prompt(self) -> str:
        return f"""
### ROLE
You are the _massi_ Derivation Manager. Your job is to translate high-level metadata "Gaps" into precise technical instructions for a Data Explorer Agent.

### CONTEXT ASSETS
1. **Architect Prompt**: The original user intent/requirement.
2. **XML Blueprint**: The target structure containing placeholders like {XMLBlueprintGapPattern.get_gap_pattern()}.
3. **Gap Task**: The specific placeholder you are currently responsible for filling.

### OBJECTIVE
Generate a "Derivation Instruction". This instruction must tell the Data Explorer:
- Exactly which files to look at (from the provided scope).
- What technical logic to apply (e.g., "Find the 0-based index of column X", "Identify the Darwin Core URI for header Y").
- How to handle ambiguity (e.g., "If no exact match is found, suggest the most likely standard term").

### INSTRUCTION GUIDELINES
- Be direct and imperative (e.g., "Analyze schema of file X and return...").
- Reference the `gap_type` (INDEX, URI, or STRING) so the explorer knows the expected format.
- Do not provide code; provide a logical plan the explorer can execute via SQL.
""".strip()

    def get_instruction_prompt(
        self, task: MetadataGapTask, architect_prompt: str, xml_blueprint: str
    ) -> str:
        return f"""
Based on the following context, write a clear, step-by-step instruction for a Data Explorer agent to resolve this gap:

### CURRENT TASK
- **Gap ID**: {task['gap_id']}
- **Gap Type**: {task['gap_type']}
- **Description**: {task['gap_description']}
- **Relevant Files**: {", ".join(task['gap_scope_files'])}
- **Initial Request**: {task['gap_derivation_request']}

### GLOBAL BLUEPRINT CONTEXT
**Original Architect Goal**:
{architect_prompt}

**Target XML Structure (Excerpt)**:
{xml_blueprint}
""".strip()

    def invoke(self, derivation_request: str) -> str:
        """
        Uses an LLM to synthesize the high-level task and technical blueprints
        into a concrete instruction for the Data Explorer operator.
        """
        manager_system_prompt = self.get_system_prompt()
        response = self._client.invoke(
            [
                SystemMessage(content=manager_system_prompt),
                HumanMessage(content=derivation_request),
            ]
        )
        return response.content
