import json

import openai
import pytest

from fakes import FakeOpenAIClient, status_error, tool_calls
from vitaagent.agent.history import History
from vitaagent.agent.llm import LLM, LLMError
from vitaagent.agent.loop import MAX_STEPS, STEP_LIMIT_ANSWER, Agent
from vitaagent.tools.registry import ToolRegistry

LOOKUP_SCHEMA = {
    "type": "function",
    "function": {"name": "lookup", "parameters": {"type": "object"}},
}


def lookup(name: str) -> dict:
    return {"name": name, "found": True}


class RecordingEvents:
    def __init__(self) -> None:
        self.events: list[tuple] = []

    def on_tool_start(self, name, arguments):
        self.events.append(("start", name, arguments))

    def on_tool_end(self, name, result):
        self.events.append(("end", name, result))


def make_agent(*replies):
    client = FakeOpenAIClient(*replies)
    events = RecordingEvents()
    agent = Agent(
        llm=LLM(client, "test-model"),
        registry=ToolRegistry([(LOOKUP_SCHEMA, lookup)]),
        history=History("system prompt"),
        events=events,
    )
    return agent, client, events


def tool_messages(agent: Agent) -> list[dict]:
    return [m for m in agent.history.messages() if m["role"] == "tool"]


def test_plain_answer_uses_one_step_with_tools_offered():
    agent, client, events = make_agent("Iron carries oxygen.")
    assert agent.run_turn("What does iron do?") == "Iron carries oxygen."
    assert len(client.completions.calls) == 1
    assert client.completions.calls[0]["tools"] == [LOOKUP_SCHEMA]
    assert client.completions.calls[0]["tool_choice"] == "auto"
    assert events.events == []


def test_tool_result_is_sent_back_before_the_answer():
    agent, client, events = make_agent(tool_calls(("lookup", {"name": "iron"})), "Here you go.")
    assert agent.run_turn("iron?") == "Here you go."

    second_call = client.completions.calls[1]["messages"]
    assert [m["role"] for m in second_call] == ["system", "user", "assistant", "tool"]
    assert second_call[3]["tool_call_id"] == "call_1"
    assert json.loads(second_call[3]["content"]) == {"name": "iron", "found": True}
    assert events.events == [
        ("start", "lookup", {"name": "iron"}),
        ("end", "lookup", {"name": "iron", "found": True}),
    ]


def test_several_tool_calls_in_one_reply_all_run_in_order():
    agent, _, _ = make_agent(
        tool_calls(("lookup", {"name": "iron"}), ("lookup", {"name": "zinc"})), "Done."
    )
    agent.run_turn("iron and zinc?")
    results = tool_messages(agent)
    assert [m["tool_call_id"] for m in results] == ["call_1", "call_2"]
    assert [json.loads(m["content"])["name"] for m in results] == ["iron", "zinc"]


def test_unknown_tool_error_goes_back_to_the_model():
    agent, _, events = make_agent(tool_calls(("make_coffee", {})), "Sorry, I can't do that.")
    assert agent.run_turn("coffee?") == "Sorry, I can't do that."
    assert "no tool called 'make_coffee'" in json.loads(tool_messages(agent)[0]["content"])["error"]
    assert events.events[0] == ("start", "make_coffee", {})


def test_invalid_json_arguments_go_back_to_the_model_as_an_error():
    agent, _, events = make_agent(tool_calls(("lookup", '{"name": ')), "Let me try again.")
    assert agent.run_turn("iron?") == "Let me try again."
    assert "not a valid JSON object" in json.loads(tool_messages(agent)[0]["content"])["error"]
    assert events.events[0] == ("start", "lookup", {})


def test_step_limit_forces_an_answer_on_the_last_step():
    replies = [tool_calls(("lookup", {"name": "iron"}))] * (MAX_STEPS - 1) + ["Final answer."]
    agent, client, _ = make_agent(*replies)
    assert agent.run_turn("loop forever") == "Final answer."
    assert len(client.completions.calls) == MAX_STEPS
    assert [c["tool_choice"] for c in client.completions.calls] == ["auto"] * (MAX_STEPS - 1) + ["none"]


def test_tool_calls_on_the_last_step_are_ignored():
    replies = [tool_calls(("lookup", {"name": "iron"}))] * MAX_STEPS
    agent, client, _ = make_agent(*replies)
    assert agent.run_turn("loop forever") == STEP_LIMIT_ANSWER
    assert len(client.completions.calls) == MAX_STEPS
    last = agent.history.messages()[-1]
    assert last == {"role": "assistant", "content": STEP_LIMIT_ANSWER}


def test_history_keeps_earlier_turns():
    agent, client, _ = make_agent("First.", "Second.")
    agent.run_turn("one")
    agent.run_turn("two")
    sent = [m["content"] for m in client.completions.calls[1]["messages"]]
    assert sent == ["system prompt", "one", "First.", "two"]


def test_failed_turn_is_removed_from_history():
    agent, _, _ = make_agent(
        "First.",
        tool_calls(("lookup", {"name": "iron"})),
        status_error(openai.RateLimitError, 429),
    )
    agent.run_turn("one")
    with pytest.raises(LLMError):
        agent.run_turn("two")
    assert [m["content"] for m in agent.history.messages()] == ["system prompt", "one", "First."]


def test_ctrl_c_mid_turn_also_removes_the_turn():
    agent, _, _ = make_agent(tool_calls(("lookup", {"name": "iron"})), KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        agent.run_turn("one")
    assert len(agent.history) == 0


def test_history_is_trimmed_before_each_model_call():
    agent, client, _ = make_agent("a" * 200, "b" * 200, "Third.")
    agent.history.max_chars = 400  # room for one earlier turn (~270 chars) plus the new question
    agent.run_turn("one")
    agent.run_turn("two")
    agent.run_turn("three")
    sent = [m["content"] for m in client.completions.calls[2]["messages"]]
    assert sent == ["system prompt", "two", "b" * 200, "three"]
