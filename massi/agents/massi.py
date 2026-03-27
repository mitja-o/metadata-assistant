from dataclasses import dataclass

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

import massi.agents.scenarios.basemetadata as uc1_base_metadata
import massi.agents.scenarios.resource_properties as uc3_resources
import massi.agents.scenarios.resources as uc2_resources
from massi.agents.interfaces import Config, Dependencies, PromptClient

# Chat Model Instances
# ====================


def create_ollama_llm(config: Config) -> ChatOllama:
    assert config.model_url, "Model URL needs to be specified for Ollama models"
    return ChatOllama(
        base_url=config.model_url,
        model=config.model_name,
        # format="json"  # forces structured JSON output
    )


def create_openai_llm(config: Config) -> ChatOpenAI:
    assert config.api_key, "API key needs to be specified for OpenAI models"
    return ChatOpenAI(model=config.model_name, api_key=config.api_key)


# I/O Instances
# =============


class StandardIOPromptClient(PromptClient):
    def prompt_user(self, queries=[], prelude=[]):
        for context_msg in prelude:
            print(context_msg)
        return [input(query) for query in queries]


# Workflow Factory
# ================


@dataclass
class MassiScenarioFactory:
    config: Config
    """The user-provided configuration for building the MASSI agents

    Returns:
        _type_: _description_
    """

    def default_dependencies(self) -> Dependencies:
        """Instantiate default dependencies for the scenario-workflows

        Args:
            config (Config): user provided configurations to create external dependencies

        Returns:
            Dependencies: a fully instantiated set of dependencies

        Examples:
            >>> from unittest.mock import patch
            >>> with patch('massi.agents.massi.StandardIOPromptClient', return_value="mock_prompt_client") as MockPromptClient:
            ...     with patch('massi.agents.massi.create_ollama_llm', return_value="mock_ollama") as MockOllama:
            ...         config = Config(**{"model_url": "http://host.docker.internal:11434", "model_name": "granite4:3b"})
            ...         factory = MassiScenarioFactory(config)
            ...         factory.default_dependencies()
            Dependencies(llm_client='mock_ollama', prompt_client='mock_prompt_client', working_directory='.')
        """
        return Dependencies(
            llm_client=create_ollama_llm(self.config),
            prompt_client=StandardIOPromptClient(),
        )

    # UC1: Base Metadata
    # ==================

    def base_metadata_graph(self, dependencies: Dependencies | None = None):
        return uc1_base_metadata.build_graph(
            dependencies if dependencies else self.default_dependencies()
        )

    # UC2: Resource Groupings
    # =======================

    def resource_grouping_graph(self, dependencies: Dependencies | None = None):
        return uc2_resources.build_graph(
            dependencies if dependencies else self.default_dependencies()
        )

    # UC3: Resource Properties
    # ========================

    def resource_properties_graph(self, dependencies: Dependencies | None = None):
        return uc3_resources.build_graph(
            dependencies if dependencies else self.default_dependencies()
        )
