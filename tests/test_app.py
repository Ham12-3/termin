import openai

from fakes import FAKE_KEY, FakeOpenAIClient, status_error, tool_calls
from vitaagent import app
from vitaagent.agent.history import History
from vitaagent.agent.llm import LLM
from vitaagent.agent.loop import Agent
from vitaagent.config import ConfigError
from vitaagent.tools.registry import ToolRegistry
from vitaagent.ui.render import ConsoleEvents

LOOKUP_SCHEMA = {
    "type": "function",
    "function": {"name": "get_vitamin_info", "parameters": {"type": "object"}},
}


def scripted_input(*lines):
    """Return a read_line function that plays `lines`, then behaves like Ctrl+D."""
    remaining = list(lines)

    def read_line() -> str:
        if not remaining:
            raise EOFError
        return remaining.pop(0)

    return read_line


def run(console, client, *lines):
    agent = Agent(
        llm=LLM(client, "test-model"),
        registry=ToolRegistry([(LOOKUP_SCHEMA, lambda name: {"name": name})]),
        history=History("system prompt"),
        events=ConsoleEvents(console),
    )
    code = app.run_repl(console, agent, scripted_input(*lines))
    return code, agent.history, console.file.getvalue()


def test_answers_a_question(console):
    client = FakeOpenAIClient("Vitamin D helps keep bones healthy.")
    code, history, output = run(console, client, "Why is vitamin D important?", "/exit")
    assert code == 0
    assert "Vitamin D helps keep bones healthy." in output
    assert "not medical advice" in output
    assert [m["content"] for m in history.messages()[1:]] == [
        "Why is vitamin D important?",
        "Vitamin D helps keep bones healthy.",
    ]


def test_shows_a_status_line_when_a_tool_runs(console):
    client = FakeOpenAIClient(tool_calls(("get_vitamin_info", {"name": "vitamin D"})), "Done.")
    _, _, output = run(console, client, "Why is vitamin D important?", "/exit")
    assert "Looking up vitamin D..." in output
    assert output.index("Looking up vitamin D...") < output.index("Done.")


def test_end_of_input_exits_cleanly(console):
    code, _, output = run(console, FakeOpenAIClient())
    assert code == 0
    assert "Goodbye" in output


def test_blank_lines_and_unknown_commands_do_not_call_the_model(console):
    client = FakeOpenAIClient()
    _, _, output = run(console, client, "", "   ", "/nope", "/EXIT")
    assert "Unknown command" in output
    assert client.completions.calls == []


def test_api_error_is_friendly_and_removed_from_history(console):
    client = FakeOpenAIClient(status_error(openai.AuthenticationError, 401), "It worked.")
    _, history, output = run(console, client, "first", "second", "/exit")
    assert "didn't accept your API key" in output
    assert FAKE_KEY not in output
    assert "Traceback" not in output
    assert [m["content"] for m in history.messages()[1:]] == ["second", "It worked."]


def test_ctrl_c_while_waiting_exits_cleanly(console):
    code, _, output = run(console, FakeOpenAIClient(KeyboardInterrupt()), "question")
    assert code == 0
    assert "Goodbye" in output


def test_main_shows_config_problem_and_exits_with_error(console, monkeypatch):
    def missing_settings():
        raise ConfigError("OPENAI_API_KEY is missing from your .env file.")

    monkeypatch.setattr(app, "_use_utf8_streams", lambda: None)
    monkeypatch.setattr(app, "Console", lambda: console)
    monkeypatch.setattr(app, "load_settings", missing_settings)
    assert app.main() == 1
    assert "OPENAI_API_KEY is missing" in console.file.getvalue()
