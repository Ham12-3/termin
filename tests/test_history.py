import json

from vitaagent.agent.history import History
from vitaagent.agent.llm import ToolCall


def contents(history: History) -> list:
    return [message["content"] for message in history.messages()[1:]]


def add_tool_turn(history: History, question: str, answer: str) -> None:
    history.add_user(question)
    history.add_assistant("", [ToolCall("call_1", "get_vitamin_info", '{"name": "iron"}')])
    history.add_tool_result("call_1", '{"name": "Iron"}')
    history.add_assistant(answer)


def test_system_prompt_is_always_first():
    history = History("be kind")
    history.add_user("hi")
    history.add_assistant("hello")
    assert history.messages() == [
        {"role": "system", "content": "be kind"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]


def test_tool_calls_and_results_use_openai_message_format():
    history = History("be kind")
    add_tool_turn(history, "iron?", "Iron carries oxygen.")
    assert history.messages()[2] == {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "get_vitamin_info", "arguments": '{"name": "iron"}'},
            }
        ],
    }
    assert history.messages()[3] == {"role": "tool", "tool_call_id": "call_1", "content": '{"name": "Iron"}'}


def test_length_excludes_system_prompt():
    history = History("be kind")
    assert len(history) == 0
    history.add_user("hi")
    assert len(history) == 1


def test_discard_last_turn_removes_everything_from_the_last_user_message():
    history = History("be kind")
    history.add_user("first")
    history.add_assistant("reply")
    history.add_user("second")
    history.add_assistant("", [ToolCall("call_1", "get_vitamin_info", "{}")])
    history.discard_last_turn()
    assert contents(history) == ["first", "reply"]


def test_discard_on_empty_history_does_nothing():
    history = History("be kind")
    history.discard_last_turn()
    assert len(history) == 0


def size_of_one_tool_turn() -> int:
    sample = History("be kind")
    add_tool_turn(sample, "question 1", "x" * 100)
    return sum(len(json.dumps(m, ensure_ascii=False)) for m in sample.messages()[1:])


def test_trim_drops_oldest_whole_turns_first():
    history = History("be kind", max_chars=size_of_one_tool_turn() * 2 + 10)
    for number in range(1, 6):
        add_tool_turn(history, f"question {number}", "x" * 100)
    history.trim()

    messages = history.messages()[1:]
    assert messages[0] == {"role": "user", "content": "question 4"}
    assert [m["content"] for m in messages if m["role"] == "user"] == ["question 4", "question 5"]


def test_trim_never_leaves_a_tool_result_without_its_call():
    history = History("be kind", max_chars=300)
    for number in range(1, 8):
        add_tool_turn(history, f"question {number}", "y" * 50)
    history.trim()

    seen_call_ids = set()
    for message in history.messages()[1:]:
        for call in message.get("tool_calls", []):
            seen_call_ids.add(call["id"])
        if message["role"] == "tool":
            assert message["tool_call_id"] in seen_call_ids
    assert history.messages()[1]["role"] == "user"


def test_trim_always_keeps_the_latest_turn():
    history = History("be kind", max_chars=10)
    history.add_user("old question")
    history.add_assistant("old answer")
    history.add_user("a very long current question " * 10)
    history.trim()
    assert contents(history) == ["a very long current question " * 10]


def test_trim_does_nothing_under_budget():
    history = History("be kind")
    add_tool_turn(history, "question", "answer")
    history.trim()
    assert len(history) == 4


def test_clear_keeps_system_prompt():
    history = History("be kind")
    history.add_user("hi")
    history.clear()
    assert history.messages() == [{"role": "system", "content": "be kind"}]
