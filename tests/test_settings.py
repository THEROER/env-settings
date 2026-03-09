"""Tests for env-settings."""

from __future__ import annotations

from pathlib import Path

import msgspec
import pytest

from env_settings import BaseSettings, load_settings


class ExampleSettings(BaseSettings):
    debug: bool = False
    host: str = "localhost"
    port: int = 8000
    timeout: float = 5.5
    tags: list[str] = msgspec.field(default_factory=list)


def test_load_from_defaults_only() -> None:
    settings = ExampleSettings.load(defaults={"PORT": "9000", "DEBUG": "true"})
    assert settings.port == 9000
    assert settings.debug is True


def test_load_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_HOST", "example.com")
    monkeypatch.setenv("APP_PORT", "8100")

    settings = ExampleSettings.load(prefix="APP_")
    assert settings.host == "example.com"
    assert settings.port == 8100


def test_load_from_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("HOST=envfile.example\nDEBUG=true\n")

    settings = ExampleSettings.load(env_file=env_file)
    assert settings.host == "envfile.example"
    assert settings.debug is True


def test_env_precedence_over_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("PORT=9000\n")
    monkeypatch.setenv("PORT", "9100")

    settings = ExampleSettings.load(env_file=env_file)
    assert settings.port == 9100


def test_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("app_timeout", "12.34")

    settings = ExampleSettings.load(prefix="APP_")
    assert settings.timeout == pytest.approx(12.34)


def test_load_settings_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOST", "helper.example")

    settings = load_settings(ExampleSettings)
    assert settings.host == "helper.example"


def test_invalid_cls_raises() -> None:
    class Other:
        pass

    with pytest.raises(TypeError):
        load_settings(Other)  # type: ignore[type-var]
