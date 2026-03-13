from abc import ABC, abstractmethod
from dataclasses import dataclass

from langchain_core.language_models import BaseChatModel


@dataclass
class Config:
    """Configuration of the agent's workflow.

    Examples:
        >>> Config(**{"model_url": "http://host.docker.internal:11434", "model_name": "granite4:3b"})
        Config(model_name='granite4:3b', model_url='http://host.docker.internal:11434', api_key=None)
        >>> Config(**dict(model_url="http://127.0.0.1:11434", model_name="phi4-mini:3.8b"))
        Config(model_name='phi4-mini:3.8b', model_url='http://127.0.0.1:11434', api_key=None)
    """

    model_name: str
    model_url: str | None = None
    api_key: str | None = None


class PromptClient(ABC):
    @abstractmethod
    def prompt_user(
        self, queries: list[str] = [], prelude: list[str] = []
    ) -> list[str]: ...


@dataclass
class Dependencies:
    llm_client: BaseChatModel | None = None
    prompt_client: PromptClient | None = None
    working_directory: str = "."
