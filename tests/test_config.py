from pathlib import Path

import pytest
from dotenv import dotenv_values

from fakes import FAKE_KEY
from vitaagent.config import PLACEHOLDERS, PROJECT_ROOT, ConfigError, Settings, load_settings


def write_env(tmp_path: Path, text: str) -> Path:
    path = tmp_path / ".env"
    path.write_text(text, encoding="utf-8")
    return path


def test_loads_values_from_env_file(tmp_path):
    env = write_env(tmp_path, f"OPENAI_API_KEY={FAKE_KEY}\nOPENAI_MODEL=test-model\n")
    settings = load_settings(env)
    assert settings.openai_api_key == FAKE_KEY
    assert settings.openai_model == "test-model"


def test_env_file_wins_over_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "from-environment")
    env = write_env(tmp_path, f"OPENAI_API_KEY={FAKE_KEY}\nOPENAI_MODEL=from-file\n")
    assert load_settings(env).openai_model == "from-file"


def test_falls_back_to_environment_variables(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_KEY)
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    settings = load_settings(tmp_path / ".env")
    assert settings.openai_model == "test-model"


def test_missing_env_file_points_to_example(tmp_path):
    with pytest.raises(ConfigError, match=r"Copy \.env\.example to \.env"):
        load_settings(tmp_path / ".env")


def test_only_the_missing_setting_is_named(tmp_path):
    env = write_env(tmp_path, f"OPENAI_API_KEY={FAKE_KEY}\n")
    with pytest.raises(ConfigError) as info:
        load_settings(env)
    message = str(info.value)
    assert "OPENAI_MODEL" in message
    assert "OPENAI_API_KEY" not in message
    assert FAKE_KEY not in message


def test_placeholder_values_count_as_missing(tmp_path):
    env = write_env(tmp_path, "OPENAI_API_KEY=sk-your-key-here\nOPENAI_MODEL=your-model-name\n")
    with pytest.raises(ConfigError, match="OPENAI_API_KEY and OPENAI_MODEL"):
        load_settings(env)


def test_surrounding_whitespace_is_ignored(tmp_path):
    env = write_env(tmp_path, f'OPENAI_API_KEY=" {FAKE_KEY} "\nOPENAI_MODEL=test-model\n')
    assert load_settings(env).openai_api_key == FAKE_KEY


def test_api_key_is_hidden_from_repr():
    settings = Settings(openai_api_key=FAKE_KEY, openai_model="test-model")
    assert FAKE_KEY not in repr(settings)
    assert "test-model" in repr(settings)


def test_env_example_only_has_placeholders():
    values = dotenv_values(PROJECT_ROOT / ".env.example")
    assert {"OPENAI_API_KEY", "OPENAI_MODEL"} <= set(values)
    assert all(value in PLACEHOLDERS for value in values.values())


def test_env_file_is_gitignored():
    lines = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in lines
