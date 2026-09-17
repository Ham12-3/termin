"""Conversation history for one session.

The system prompt is kept separately and always sent first. A "turn" is a user
message plus everything after it up to the next user message. Trimming removes
whole turns, so an assistant tool call is never separated from its results.
"""

from __future__ import annotations

import json

from vitaagent.agent.llm import ToolCall

MAX_HISTORY_CHARS = 40_000  # roughly 10k tokens, not counting the system prompt


class History:
    def __init__(self, system_prompt: str, max_chars: int = MAX_HISTORY_CHARS) -> None:
        self.system_prompt = system_prompt
        self.max_chars = max_chars
        self._messages: list[dict] = []

    def __len__(self) -> int:
        return len(self._messages)

    def add_user(self, text: str) -> None:
        self._messages.append({"role": "user", "content": text})

    def add_assistant(self, text: str, tool_calls: list[ToolCall] | None = None) -> None:
        message: dict = {"role": "assistant", "content": text}
        if tool_calls:
            message["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.arguments},
                }
                for call in tool_calls
            ]
        self._messages.append(message)

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        self._messages.append({"role": "tool", "tool_call_id": tool_call_id, "content": content})

    def messages(self) -> list[dict]:
        """The full list to send to the model: system prompt first."""
        return [{"role": "system", "content": self.system_prompt}, *self._messages]

    def discard_last_turn(self) -> None:
        """Remove the latest turn, e.g. when it failed part way through."""
        starts = self._turn_starts()
        if starts:
            del self._messages[starts[-1] :]

    def trim(self) -> None:
        """Drop the oldest whole turns until under budget. The latest turn is always kept."""
        while self._size() > self.max_chars:
            starts = self._turn_starts()
            if len(starts) < 2:
                return
            del self._messages[: starts[1]]

    def clear(self) -> None:
        self._messages.clear()

    def _turn_starts(self) -> list[int]:
        return [i for i, message in enumerate(self._messages) if message["role"] == "user"]

    def _size(self) -> int:
        return sum(len(json.dumps(message, ensure_ascii=False)) for message in self._messages)
