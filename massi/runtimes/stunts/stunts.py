import pprint as pp
from dataclasses import dataclass
from datetime import datetime

from langchain_core.language_models import BaseChatModel


@dataclass
class FakeChatInteraction:
    messages: str
    timestamp: datetime


class RelayChatModel(BaseChatModel):
    """Instead of asking an LLM, this class asks an external actor to provide a response manually.
    Relies on the standard `input` function.

    Examples:
        >>> from unittest.mock import patch
        >>> mock_relay_response = "Anything you want it to be, buddy."
        >>> with patch('builtins.input', return_value=mock_relay_response):
        ...     relay = RelayChatModel()
        ...     relay.invoke(["What is the weather in your current location?"]) # doctest: +ELLIPSIS
        <MagicMock name='input' id='...'>
        'Anything you want it to be, buddy.'
    """

    __type = "relay"

    def __init__(self):
        self.__interaction_history = []

    def _generate(self, *args, **kwargs):
        pass

    def _llm_type(self, *args, **kwargs):
        return self.__type

    def with_structured_output(self, *args, **kwargs):
        return self

    def invoke(self, messages, *args, **kwargs):
        self.__interaction_history.append(FakeChatInteraction(messages, datetime.now()))
        pp.pprint(input, indent=2)
        response = input("Please provide a response to this input: ")
        return response
