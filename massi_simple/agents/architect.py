from typing import ClassVar

from langchain.messages import AIMessage, SystemMessage

from massi_simple.config import MassiConfig
from massi_simple.dto import (
    ArchitectOutputs,
    Node,
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


class _BaseArchitectPromptBuilder(BaseAgentPromptBuilder):
    """A shared superclass prompt builder for Architect agent roles.

    Examples:
        >>> builder = _BaseArchitectPromptBuilder()
        >>> print(builder.system_prompt_with_input({"dataset_overview": "some-data", "metadata_schema": "some-schema"}))
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
        please-specify-task-in-subclasses
        </massi_prompt__task_specification>
        <massi_prompt__inputs>
        <massi_prompt_dataset_overview>
        some-data
        </massi_prompt_dataset_overview>
        <massi_prompt_metadata_schema>
        some-schema
        </massi_prompt_metadata_schema>
        </massi_prompt__inputs>
    """

    # FIXME(implement): populate the prompt bits
    preamble: ClassVar[AgentPromptPreambleBits] = {
        "role": "n/a",
        "input_spec": "n/a",
        "information_grounding_rule": "n/a",
        "output_format": "n/a",
    }


class SuperArchitectPrompt(_BaseArchitectPromptBuilder):
    # FIXME(implement): populate the prompt bits
    def _uknowns(self) -> str:
        return NotImplementedError("todo")

    def _task(self) -> str:
        return NotImplementedError("todo")


class StandardArchitectPrompt(_BaseArchitectPromptBuilder):
    # FIXME(implement): populate the prompt bits
    def _uknowns(self) -> str:
        return NotImplementedError("todo")

    def _task(self) -> str:
        return NotImplementedError("todo")


# Architect Agents
# ----------------


def _architect(
    config: MassiConfig,
    prompt_builder: _BaseArchitectPromptBuilder,
) -> Node:
    """Creates an Architect Agent as a node for the workflow graph.

    Args:
        config (MassiConfig): the high-level massi configurations.
        prompt_builder (_BaseArchitectPromptBuilder): specific Architect prompt builder to use.

    Returns:
        Node: the Agent wrapped as a workflow node.
    """
    llm = make_llm(model=config["agent_models"]["architect"])

    def node(state: WorkflowState) -> WorkflowState:
        inputs = state["architect_inputs"]
        system_prompt = prompt_builder.system_prompt_with_input(inputs)
        llm_client = llm.with_structured_output(ArchitectOutputs)
        response: AIMessage = llm_client.invoke([SystemMessage(system_prompt)])
        assert validate_dict(ArchitectOutputs, response.content)
        result: WorkflowState = {
            "architect_outputs": response.content,
            "messages": response,
        }
        return result

    return node


def super_architect(config: MassiConfig) -> Node:
    base_node = _architect(config, SuperArchitectPrompt())

    def node(state: WorkflowState) -> WorkflowState:
        metadata_template = base_node(state)["architect_outputs"]["metadata_template"]
        return {"workflow_outputs": {"metadata_instance": metadata_template}}

    return node


def standard_architect(config: MassiConfig) -> Node:
    return _architect(config, StandardArchitectPrompt())
