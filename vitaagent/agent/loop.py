"""The agent loop: call the model, run the tools it asks for, repeat until it answers.

The loop knows nothing about the terminal. It reports tool activity through
`AgentEvents`, which the UI implements.
"""

from __future__ import annotations

import json
from typing import Protocol

from vitaagent.agent.history import History
from vitaagent.agent.llm import LLM, AssistantReply, ToolCall
from vitaagent.tools.registry import ToolRegistry, parse_arguments

MAX_STEPS = 10  # model calls per question
STEP_LIMIT_ANSWER = (
    "Sorry, I couldn't finish working that out. Could you ask again in a simpler way, "
    "or split it into smaller questions?"
)


class AgentEvents(Protocol):
    def on_tool_start(self, name: str, arguments: dict) -> None: ...

    def on_tool_end(self, name: str, result: dict) -> None: ...


class NoEvents:
    def on_tool_start(self, name: str, arguments: dict) -> None:
        pass

    def on_tool_end(self, name: str, result: dict) -> None:
        pass


class Agent:
    def __init__(
        self,
        llm: LLM,
        registry: ToolRegistry,
        history: History,
        events: AgentEvents | None = None,
    ) -> None:
        self.llm = llm
        self.registry = registry
        self.history = history
        self.events = events or NoEvents()

    def run_turn(self, user_text: str) -> str:
        """Answer one user message. If anything fails, the turn is removed from history."""
        self.history.add_user(user_text)
        try:
            return self._run_steps()
        except BaseException:
            self.history.discard_last_turn()
            raise

    def _run_steps(self) -> str:
        for step in range(1, MAX_STEPS + 1):
            last_step = step == MAX_STEPS
            self.history.trim()
            reply = self.llm.complete(
                self.history.messages(),
                tools=self.registry.schemas(),
                tool_choice="none" if last_step else "auto",
            )
            if last_step and reply.tool_calls:
                # Tools were switched off, so any calls here are ignored.
                reply = AssistantReply(text=reply.text or STEP_LIMIT_ANSWER)

            self.history.add_assistant(reply.text, reply.tool_calls)
            if not reply.tool_calls:
                return reply.text
            for call in reply.tool_calls:
                self._run_tool(call)

        raise AssertionError("unreachable: the last step always returns")

    def _run_tool(self, call: ToolCall) -> None:
        self.events.on_tool_start(call.name, parse_arguments(call.arguments) or {})
        result = self.registry.run(call.name, call.arguments)
        self.events.on_tool_end(call.name, result)
        self.history.add_tool_result(call.id, json.dumps(result, ensure_ascii=False))
