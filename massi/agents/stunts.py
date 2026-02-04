import pprint as pp
from dataclasses import dataclass
from datetime import datetime

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel


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
        ...     with patch('builtins.print'):
        ...         relay = RelayChatModel()
        ...         relay.invoke(["What is the weather in your current location?"])
        'Anything you want it to be, buddy.'

        >>> class AnswerModel(BaseModel):
        ...     answer: str
        >>> mock_answer = f'{{"answer": "{mock_relay_response}"}}'
        >>> with patch('builtins.input', return_value=mock_answer):
        ...     with patch('builtins.print'):
        ...         relay = RelayChatModel()
        ...         relay.with_structured_output(AnswerModel).invoke(["What is the weather in your current location?"])
        AnswerModel(answer='Anything you want it to be, buddy.')
        >>> len(relay._interaction_history)
        2
    """

    __type = "relay"

    def __init__(self):
        self._interaction_history = []
        self._postprocess_result = lambda x: x

    def _generate(self, *args, **kwargs):
        pass

    def _llm_type(self, *args, **kwargs):
        return self.__type

    def with_structured_output(self, schema: BaseModel, *, include_raw=False, **kwargs):
        self._postprocess_result = schema.model_validate_json
        return self

    def invoke(self, messages, *args, **kwargs):
        self._interaction_history.append(FakeChatInteraction(messages, datetime.now()))

        print(pp.pformat(messages, indent=2))
        response = self._postprocess_result(
            input("\n----\nPlease provide an appropriate response to this input: ")
        )

        self._interaction_history.append(FakeChatInteraction(response, datetime.now()))
        self._postprocess_result = lambda x: x
        return response
