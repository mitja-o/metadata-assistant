from typing import ClassVar

from langchain.messages import AIMessage, SystemMessage

from massi_simple.config import MassiConfig
from massi_simple.dto import (
    Node,
    PopulatorOutputs,
    WorkflowState,
    validate_dict,
)
from massi_simple.llms import (
    AgentPromptPreambleBits,
    BaseAgentPromptBuilder,
    make_llm,
)

# Prompt Builders
# ---------------


class PopulatorPromptBuilder(BaseAgentPromptBuilder):
    """A prompt builder for Architect agent roles.

    Examples:
        >>> builder = PopulatorPromptBuilder()
        >>> print(builder.system_prompt_with_input({"metadata_template": "some-template"}))
        <massi_prompt_role>
        n/a
        </massi_prompt_role>
        <massi_prompt_input_spec>
        n/a
        </massi_prompt_input_spec>
        <massi_prompt_information_grounding_rule>
        n/a
        </massi_prompt_information_grounding_rule>
        <massi_prompt_output_format>
        n/a
        </massi_prompt_output_format>
        <massi_prompt__unknown_handling_rule>
        please-specify-unknowns-in-subclasses
        </massi_prompt__unknown_handling_rule>
        <massi_prompt__task_specification>
        todo
        </massi_prompt__task_specification>
        <massi_prompt__inputs>
        <massi_prompt_metadata_template>
        some-template
        </massi_prompt_metadata_template>
        </massi_prompt__inputs>
    """

    # FIXME(implement): populate the prompt bits
    preamble: ClassVar[AgentPromptPreambleBits] = {
        "role": "n/a",
        "input_spec": "n/a",
        "information_grounding_rule": "n/a",
        "output_format": "n/a",
    }

    # FIXME(implement): populate the prompt bits
    def _uknowns(self) -> str:
        return NotImplementedError("todo")

    def _task(self) -> str:
        return NotImplementedError("todo")


# Architect Agents
# ----------------


def populator(config: MassiConfig) -> Node:
    """Creates a Populator Agent as a node for the workflow graph.
    It retrieves the result of an architect and populates all empty gaps to produce a metadata instance.

    Args:
        config (MassiConfig): the high-level massi configurations.

    Returns:
        Node: the Agent wrapped as a workflow node.
    """
    prompt_builder = PopulatorPromptBuilder()
    llm = make_llm(model=config["agent_models"]["populator"])

    def node(state: WorkflowState) -> WorkflowState:
        inputs = state["architect_outputs"]
        system_prompt = prompt_builder.system_prompt_with_input(inputs)
        llm_client = llm.with_structured_output(PopulatorOutputs)
        response: AIMessage = llm_client.invoke([SystemMessage(system_prompt)])
        assert validate_dict(PopulatorOutputs, response.content)
        result: WorkflowState = {
            "populator_outputs": response.content,
            "messages": response,
        }
        return result

    return node
