"""Thin wrapper around the OpenAI Chat Completions API.

This is the only module that talks to OpenAI. SDK errors are turned into
`LLMError` with a friendly message that never contains the API key.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import openai


class LLMError(Exception):
    """A model call failed. The message is safe to show to users."""


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: str  # raw JSON text, exactly as the model sent it


@dataclass
class AssistantReply:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLM:
    def __init__(self, client: Any, model: str) -> None:
        self._client = client
        self.model = model

    def complete(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
    ) -> AssistantReply:
        request: dict[str, Any] = {"model": self.model, "messages": messages}
        if tools:
            request["tools"] = tools
            request["tool_choice"] = tool_choice
        try:
            response = self._client.chat.completions.create(**request)
        except openai.OpenAIError as err:
            raise LLMError(friendly_error(err, self.model)) from None

        message = response.choices[0].message
        return AssistantReply(text=message.content or "", tool_calls=_function_calls(message))


def create_client(api_key: str) -> openai.OpenAI:
    return openai.OpenAI(api_key=api_key)


def _function_calls(message: Any) -> list[ToolCall]:
    calls = []
    for call in message.tool_calls or []:
        if getattr(call, "type", None) == "function":
            calls.append(ToolCall(call.id, call.function.name, call.function.arguments or ""))
    return calls


def friendly_error(err: openai.OpenAIError, model: str) -> str:
    """Map an OpenAI SDK error to a plain-English message (never the raw error text)."""
    if isinstance(err, openai.AuthenticationError):
        return "OpenAI didn't accept your API key. Check OPENAI_API_KEY in your .env file."
    if isinstance(err, openai.PermissionDeniedError):
        return f"Your OpenAI account doesn't have access to the model '{model}'."
    if isinstance(err, openai.NotFoundError):
        return f"OpenAI couldn't find the model '{model}'. Check OPENAI_MODEL in your .env file."
    if isinstance(err, openai.RateLimitError):
        return (
            "OpenAI is limiting requests right now, or your account is out of credit. "
            "Wait a moment and try again, or check your OpenAI billing."
        )
    if isinstance(err, openai.APIConnectionError):
        return "Couldn't reach OpenAI. Check your internet connection and try again."
    if isinstance(err, openai.BadRequestError):
        return "OpenAI couldn't process that request. Try rephrasing your question."
    if isinstance(err, openai.APIStatusError):
        return f"OpenAI had a problem (error {err.status_code}). Try again in a moment."
    return "Something went wrong talking to OpenAI. Try again in a moment."
