"""Show agent activity in the terminal."""

from __future__ import annotations

from rich.console import Console
from rich.text import Text


def status_message(tool_name: str, arguments: dict) -> str:
    """A short, friendly line describing what a tool is doing."""
    if tool_name == "get_vitamin_info":
        return f"Looking up {arguments.get('name') or 'that nutrient'}..."
    return "Checking my notes..."


class ConsoleEvents:
    """Prints a status line each time the agent uses a tool."""

    def __init__(self, console: Console) -> None:
        self.console = console

    def on_tool_start(self, name: str, arguments: dict) -> None:
        self.console.print(Text(status_message(name, arguments), style="dim italic"))

    def on_tool_end(self, name: str, result: dict) -> None:
        pass
