from typing import ClassVar, TypedDict

from langchain.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from massi_simple.config import MassiDefaults, ModelConfig

# Prompt templating
# -----------------


def format_prefix(prefix: str) -> str:
    return (prefix + "__") if prefix else ""


def to_prompt(data: dict[str, str], prefix: str | None = None) -> str:
    return "\n".join(
        f"<{format_prefix(prefix)}{k}>\n{v.strip()}\n</{format_prefix(prefix)}{k}>"
        for k, v in data.items()
        if v
    )


class AgentPromptPreambleBits(TypedDict, total=False):
    role: str
    input_specification: str
    information_grounding_rule: str
    output_format: str


class BaseAgentPromptBuilder:
    PROMPT_KEY_PREFIX: ClassVar[str] = format_prefix(MassiDefaults.PROMPT_KEY_PREFIX)
    preamble: ClassVar[AgentPromptPreambleBits] = {"role": "You are an Agent."}

    def _unknowns(self) -> str:
        return "please-specify-unknowns-in-subclasses"

    def _task(self) -> str:
        return "please-specify-task-in-subclasses"

    def system_prompt_with_input(self, inputs: dict[str, str]) -> str:
        """Generate the full system prompt for the Architect agent role.

        Examples:
            >>> builder = BaseAgentPromptBuilder()
            >>> print(builder.system_prompt_with_input({"foo": "some-bar"}))
            <massi_prompt_role>
            You are an Agent.
            </massi_prompt_role>
            <massi_prompt__unknown_handling_rule>
            please-specify-unknowns-in-subclasses
            </massi_prompt__unknown_handling_rule>
            <massi_prompt__task_specification>
            please-specify-task-in-subclasses
            </massi_prompt__task_specification>
            <massi_prompt__inputs>
            <massi_prompt__foo>
            some-bar
            </massi_prompt__foo>
            </massi_prompt__inputs>
        """
        return (
            # preamble, see the `AgentPromptPreambleBits`
            to_prompt(self.preamble, prefix=self.PROMPT_KEY_PREFIX).strip()
            # uproach to unknowns
            + f"""
<{self.PROMPT_KEY_PREFIX}unknown_handling_rule>
{self._unknowns()}
</{self.PROMPT_KEY_PREFIX}unknown_handling_rule>"""
            # task specification
            + f"""
<{self.PROMPT_KEY_PREFIX}task_specification>
{self._task()}
</{self.PROMPT_KEY_PREFIX}task_specification>"""
            # input specification
            + f"""
<{self.PROMPT_KEY_PREFIX}inputs>
{to_prompt(inputs, prefix=self.PROMPT_KEY_PREFIX)}
</{self.PROMPT_KEY_PREFIX}inputs>"""
        ).strip()


# LLM Clients
# -----------


def make_llm(model: ModelConfig) -> BaseChatModel:
    match model.provider:
        case "ollama":
            return ChatOllama(**model)
        case "openai":
            return ChatOpenAI(**model)
        case "uva":
            return ChatOpenAI(**model)
