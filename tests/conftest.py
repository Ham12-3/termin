"""Shared fixtures. Tests never call the real OpenAI API."""

from __future__ import annotations

import io

import pytest
from rich.console import Console


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Stop real environment variables leaking into tests."""
    for name in ("OPENAI_API_KEY", "OPENAI_MODEL"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def console() -> Console:
    """A plain-text Rich console that writes to memory. Read it with `console.file.getvalue()`."""
    return Console(file=io.StringIO(), width=100, color_system=None)
