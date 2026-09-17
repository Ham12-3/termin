"""The terminal app: read a question, run the agent, print the answer."""

from __future__ import annotations

import sys
from collections.abc import Callable

from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text

from vitaagent.agent.history import History
from vitaagent.agent.llm import LLM, LLMError, create_client
from vitaagent.agent.loop import Agent
from vitaagent.agent.prompts import build_system_prompt
from vitaagent.config import ConfigError, load_settings
from vitaagent.tools.registry import default_registry
from vitaagent.ui.render import ConsoleEvents

PROMPT = "[bold green]You:[/] "
EXIT_COMMANDS = {"/exit", "/quit"}


def main() -> int:
    _use_utf8_streams()
    console = Console()
    try:
        settings = load_settings()
    except ConfigError as err:
        console.print(Text(str(err), style="red"))
        return 1

    agent = Agent(
        llm=LLM(create_client(settings.openai_api_key), settings.openai_model),
        registry=default_registry(),
        history=History(build_system_prompt()),
        events=ConsoleEvents(console),
    )
    return run_repl(console, agent, read_line=lambda: console.input(PROMPT))


def run_repl(console: Console, agent: Agent, read_line: Callable[[], str]) -> int:
    console.print(Text("VitaAgent", style="bold cyan"), "- ask me about vitamins, minerals and healthy eating.")
    console.print("General information only, not medical advice. Type /exit to quit.\n")

    while True:
        try:
            user_text = read_line().strip()
            if not user_text:
                continue
            if user_text.lower() in EXIT_COMMANDS:
                break
            if user_text.startswith("/"):
                console.print(Text("Unknown command. Type /exit to quit.", style="yellow"))
                continue
            answer(console, agent, user_text)
        except (EOFError, KeyboardInterrupt):
            break

    console.print("\nGoodbye! Look after yourself.")
    return 0


def answer(console: Console, agent: Agent, user_text: str) -> None:
    """Run one question through the agent and print the reply or a friendly error."""
    try:
        with console.status("Thinking..."):
            reply = agent.run_turn(user_text)
    except LLMError as err:
        console.print(Text(str(err), style="red"))
        return

    console.print(Markdown(reply))
    console.print()


def _use_utf8_streams() -> None:
    """Avoid UnicodeEncodeError on Windows when output is piped (answers contain µ, ≥, emoji)."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
