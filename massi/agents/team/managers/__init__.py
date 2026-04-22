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


# Data-centric
# ::::::::::::


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


# Author-centric
# ::::::::::::::


class AuthorGapDerivationManager(GapDerivationManager):
    def __init__(self, llm_client: BaseChatModel):
        self._client = llm_client

    def get_system_prompt(self) -> str:
        return f"""
### ROLE
You are the _massi_ Interview Architect. Your job is to translate high-level metadata "Gaps" into precise, empathetic, and context-aware interview instructions for an Interviewer Agent.

### CONTEXT ASSETS
1. **Architect Prompt**: The high-level metadata goals (e.g., EML vs DwC).
2. **XML Blueprint**: The target structure containing placeholders like {XMLBlueprintGapPattern.get_gap_pattern()}.
3. **Gap Task**: The specific missing piece of information.

### OBJECTIVE
Generate an "Interview Instruction". This instruction must guide the Interviewer Agent to:
- **Frame the Question**: How to ask the author for the missing data without using overly technical jargon.
- **Provide Context**: Explain *why* this information is needed for the metadata record (e.g., "to ensure your funding is properly cited").
- **Grounded References**: Mention specific files from the `gap_scope_files` to help the author identify the context (e.g., "In your file 'methods_v1.pdf', the sampling section is a bit brief...").
- **Constraint Enforcement**: Remind the interviewer of the required format (e.g., "We need this as a valid ISO 8601 date").

### INSTRUCTION GUIDELINES
- Be conversational yet professional.
- Focus on "Author-Centric" elicitation (e.g., "Ask the author to clarify the roles of the personnel listed in...").
- Do not ask the agent to search data; ask it to conduct a dialogue.
""".strip()

    def get_instruction_prompt(
        self, task: MetadataGapTask, architect_prompt: str, xml_blueprint: str
    ) -> str:
        # We leverage the fact that EML/DwC metadata often comes from the author's head
        return f"""
Based on the following context, formulate a strategic interview guide for the agent to use when speaking with the dataset author:

### CURRENT GAP TO FILL
- **Gap ID**: {task['gap_id']}
- **Field Description**: {task['gap_description']}
- **Required Format (Type)**: {task['gap_type']}
- **Related Files for Reference**: {", ".join(task['gap_scope_files'])}
- **Planner's Initial Request**: {task['gap_derivation_request']}

### GLOBAL CONTEXT
**Metadata Goal**:
{architect_prompt}

**Blueprint Fragment**:
{xml_blueprint}

### YOUR TASK
Generate a prompt for the Interviewer Agent. The prompt should include:
1. A suggested opening question for the author.
2. A list of specific details or "probes" to ask if the first answer is too vague.
3. Instructions on how to map the author's verbal answer back to the required {task['gap_type']} format.
""".strip()

    def invoke(self, derivation_request: str) -> str:
        """
        Synthesizes the metadata requirements into a dialogue strategy
        for the Interviewer Operator.
        """
        system_prompt = self.get_system_prompt()
        response = self._client.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=derivation_request),
            ]
        )
        return response.content
