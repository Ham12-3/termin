from types import SimpleNamespace

import openai
import pytest

from fakes import FAKE_KEY, FakeOpenAIClient, connection_error, status_error, tool_calls
from vitaagent.agent.llm import LLM, LLMError, ToolCall

TOOLS = [{"type": "function", "function": {"name": "get_vitamin_info", "parameters": {}}}]


def test_sends_model_and_messages_and_returns_text():
    client = FakeOpenAIClient("Hello!")
    messages = [{"role": "user", "content": "hi"}]
    reply = LLM(client, "test-model").complete(messages)
    assert reply.text == "Hello!"
    assert reply.tool_calls == []
    assert client.completions.calls == [{"model": "test-model", "messages": messages}]


def test_missing_content_becomes_empty_text():
    assert LLM(FakeOpenAIClient(None), "test-model").complete([]).text == ""


def test_sends_tools_and_tool_choice():
    client = FakeOpenAIClient("Hi")
    LLM(client, "test-model").complete([], tools=TOOLS, tool_choice="none")
    call = client.completions.calls[0]
    assert call["tools"] == TOOLS
    assert call["tool_choice"] == "none"


def test_returns_tool_calls():
    client = FakeOpenAIClient(tool_calls(("get_vitamin_info", {"name": "iron"}), ("get_vitamin_info", "{}")))
    reply = LLM(client, "test-model").complete([], tools=TOOLS)
    assert reply.text == ""
    assert reply.tool_calls == [
        ToolCall("call_1", "get_vitamin_info", '{"name": "iron"}'),
        ToolCall("call_2", "get_vitamin_info", "{}"),
    ]


def test_ignores_non_function_tool_calls():
    message = tool_calls(("get_vitamin_info", {}))
    message.tool_calls.append(SimpleNamespace(id="call_x", type="custom", custom=None))
    reply = LLM(FakeOpenAIClient(message), "test-model").complete([], tools=TOOLS)
    assert [call.id for call in reply.tool_calls] == ["call_1"]


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (status_error(openai.AuthenticationError, 401), "OPENAI_API_KEY"),
        (status_error(openai.PermissionDeniedError, 403), "access to the model 'test-model'"),
        (status_error(openai.NotFoundError, 404), "OPENAI_MODEL"),
        (status_error(openai.RateLimitError, 429), "out of credit"),
        (status_error(openai.BadRequestError, 400), "rephrasing"),
        (status_error(openai.InternalServerError, 500), "error 500"),
        (connection_error(openai.APIConnectionError), "internet connection"),
        (connection_error(openai.APITimeoutError), "internet connection"),
    ],
)
def test_sdk_errors_become_friendly_messages(error, expected):
    with pytest.raises(LLMError) as info:
        LLM(FakeOpenAIClient(error), "test-model").complete([])
    assert expected in str(info.value)
    assert FAKE_KEY not in str(info.value)
    assert info.value.__cause__ is None
