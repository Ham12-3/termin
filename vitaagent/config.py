"""Load VitaAgent settings from the .env file.

Values in .env win over environment variables of the same name. Secret values
are never included in reprs or error messages.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"
DATA_DIR = PROJECT_ROOT / "data"

# Placeholder values shipped in .env.example. Treated as "not set".
PLACEHOLDERS = {"sk-your-key-here", "your-model-name"}


class ConfigError(Exception):
    """A required setting is missing. The message is safe to show to users."""


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = field(repr=False)
    openai_model: str


def load_settings(env_file: Path = DEFAULT_ENV_FILE) -> Settings:
    """Read settings from `env_file`, falling back to environment variables."""
    file_values = dotenv_values(env_file) if env_file.is_file() else {}

    def read(name: str) -> str:
        value = (file_values.get(name) or os.environ.get(name) or "").strip()
        return "" if value in PLACEHOLDERS else value

    missing = [name for name in ("OPENAI_API_KEY", "OPENAI_MODEL") if not read(name)]
    if missing:
        raise ConfigError(_missing_message(missing, env_file))

    return Settings(openai_api_key=read("OPENAI_API_KEY"), openai_model=read("OPENAI_MODEL"))


def _missing_message(missing: list[str], env_file: Path) -> str:
    names = " and ".join(missing)
    verb = "is" if len(missing) == 1 else "are"
    if not env_file.is_file():
        return (
            f"No .env file found, so {names} {verb} not set.\n"
            "Copy .env.example to .env and add your own values."
        )
    return f"{names} {verb} missing from your .env file (or still set to the placeholder)."
