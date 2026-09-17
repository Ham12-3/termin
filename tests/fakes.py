"""Test doubles: a fake OpenAI client and helpers that build real SDK errors."""

from __future__ import annotations

import json
from types import SimpleNamespace

import httpx2

FAKE_KEY = "sk-test-fake-0123456789"

_REQUEST = httpx2.Request("POST", "https://api.openai.com/v1/chat/completions")


def tool_calls(*calls: tuple[str, dict | str], text: str | None = None) -> SimpleNamespace:
    """A scripted assistant message that asks for tools.

    Each call is (tool_name, arguments). Arguments may be a dict or raw JSON text.
    Call ids are "call_1", "call_2", ... in order.
    """
    return SimpleNamespace(
        content=text,
        tool_calls=[
            SimpleNamespace(
                id=f"call_{number}",
                type="function",
                function=SimpleNamespace(
                    name=name,
                    arguments=args if isinstance(args, str) else json.dumps(args),
                ),
            )
            for number, (name, args) in enumerate(calls, start=1)
        ],
    )


class _FakeCompletions:
    def __init__(self, replies: tuple) -> None:
        self._replies = list(replies)
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        reply = self._replies.pop(0)
        if isinstance(reply, BaseException):
            raise reply
        if not isinstance(reply, SimpleNamespace):
            reply = SimpleNamespace(content=reply, tool_calls=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=reply)])


class FakeOpenAIClient:
    """Replays scripted replies in order.

    Each reply is text, None, a `tool_calls(...)` message, or an exception to raise.
    """

    def __init__(self, *replies) -> None:
        self.completions = _FakeCompletions(replies)
        self.chat = SimpleNamespace(completions=self.completions)


def status_error(error_class, status: int):
    """Build an SDK status error whose raw message contains the fake key."""
    response = httpx2.Response(status, request=_REQUEST)
    return error_class(f"raw error mentioning {FAKE_KEY}", response=response, body=None)


def connection_error(error_class):
    return error_class(request=_REQUEST)
