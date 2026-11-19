from typing import Literal, TypedDict

# Specific Configs
# ----------------

type ModelProvider = Literal["ollama", "openai", "uva"]


class ModelConfig(TypedDict):
    provider: ModelProvider
    model: str
    base_url: str | None = None
    api_key: str | None = None


class AgentModels(TypedDict):
    architect: ModelConfig
    planner: ModelConfig
    instructor: ModelConfig
    operator: ModelConfig
    populator: ModelConfig


class AuthorProxyModels(TypedDict):
    generator: ModelConfig
    embedding: ModelConfig


# Global Configs
# --------------


class MassiRuntimeConfig(TypedDict):
    data_overview_csv_head_size: int = 5


class MassiConfig(TypedDict):
    runtime_config: MassiRuntimeConfig
    agent_models: AgentModels
    author_proxy_models: AuthorProxyModels


class MassiDefaults:
    PROMPT_KEY_PREFIX: str = "massi_prompt"
