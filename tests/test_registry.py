from vitaagent.tools.registry import ToolRegistry, default_registry, parse_arguments


def schema(name: str) -> dict:
    return {"type": "function", "function": {"name": name, "parameters": {"type": "object"}}}


def double(number: int) -> dict:
    return {"result": number * 2}


def broken() -> dict:
    raise ValueError("secret internal detail")


REGISTRY = ToolRegistry([(schema("double"), double), (schema("broken"), broken)])


def test_runs_a_tool_with_json_arguments():
    assert REGISTRY.run("double", '{"number": 21}') == {"result": 42}


def test_lists_schemas():
    assert [s["function"]["name"] for s in REGISTRY.schemas()] == ["double", "broken"]


def test_unknown_tool_returns_error_with_available_tools():
    result = REGISTRY.run("triple", "{}")
    assert "no tool called 'triple'" in result["error"]
    assert result["available_tools"] == ["broken", "double"]


def test_invalid_json_returns_error():
    assert "not a valid JSON object" in REGISTRY.run("double", '{"number": ')["error"]


def test_non_object_json_returns_error():
    assert "not a valid JSON object" in REGISTRY.run("double", "[1, 2]")["error"]


def test_wrong_argument_names_return_error():
    assert "Wrong arguments for 'double'" in REGISTRY.run("double", '{"amount": 2}')["error"]


def test_missing_arguments_return_error():
    assert "Wrong arguments for 'double'" in REGISTRY.run("double", "")["error"]


def test_tool_exception_returns_error_without_details():
    result = REGISTRY.run("broken", "{}")
    assert result == {"error": "The tool 'broken' failed unexpectedly (ValueError)."}


def test_parse_arguments():
    assert parse_arguments('{"a": 1}') == {"a": 1}
    assert parse_arguments("") == {}
    assert parse_arguments("nope") is None
    assert parse_arguments('"text"') is None


def test_default_registry_has_the_vitamin_tool():
    names = [s["function"]["name"] for s in default_registry().schemas()]
    assert names == ["get_vitamin_info"]
