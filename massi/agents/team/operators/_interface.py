from typing import Literal, TypedDict

from langchain.chat_models import BaseChatModel


class OperatorProps(TypedDict):
    llm_client: BaseChatModel | None = None
    recursion_limit: int = 15
    turn_limit: int = 7


class OperatorRequest(TypedDict):
    plaintext_files: list[str]
    """Path to all non-tabular source files"""
    tabular_files: list[str]
    """Path to all tabular source files"""
    instruction: str
    """The specific task from the parent graph"""


class OperatorResponse(TypedDict):
    success: bool
    status: Literal["rejected", "completed"]
    outcome: str
    result_value: str | None
    """
    The final value that should be entered in the upstream metadata record. 
    None if the outcome is not successful.
    """
