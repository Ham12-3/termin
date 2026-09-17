"""Collects tool schemas and runs tools by name.

Each tool module defines a `SCHEMA` (OpenAI function format) next to its
function. `ToolRegistry.run` never raises: every problem comes back as an
{"error": ...} result so the model can recover.
"""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable, Iterable

from vitaagent.tools import vitamins

ToolFunction = Callable[..., dict]


class ToolRegistry:
    def __init__(self, tools: Iterable[tuple[dict, ToolFunction]]) -> None:
        self._tools = {schema["function"]["name"]: (schema, function) for schema, function in tools}

    def schemas(self) -> list[dict]:
        return [schema for schema, _ in self._tools.values()]

    def run(self, name: str, arguments: str) -> dict:
        if name not in self._tools:
            return {"error": f"There is no tool called '{name}'.", "available_tools": sorted(self._tools)}

        args = parse_arguments(arguments)
        if args is None:
            return {"error": f"The arguments for '{name}' were not a valid JSON object."}

        _, function = self._tools[name]
        try:
            inspect.signature(function).bind(**args)
        except TypeError as err:
            return {"error": f"Wrong arguments for '{name}': {err}."}

        try:
            return function(**args)
        except Exception as err:  # a tool bug must not crash the app
            return {"error": f"The tool '{name}' failed unexpectedly ({type(err).__name__})."}


def parse_arguments(arguments: str) -> dict | None:
    """Parse the model's JSON arguments. Returns None unless it is a JSON object."""
    try:
        value = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def default_registry() -> ToolRegistry:
    return ToolRegistry([(vitamins.SCHEMA, vitamins.get_vitamin_info)])
