"""Tests for env-settings."""

from __future__ import annotations

from pathlib import Path

import msgspec
import pytest

from env_settings import BaseSettings, load_composed_settings, load_settings


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


def test_loads_json_list_values() -> None:
    settings = ExampleSettings.load(
        env={"TAGS": '["landing.live_stats","monitoring.live_status"]'}
    )
    assert settings.tags == ["landing.live_stats", "monitoring.live_status"]


def test_loads_delimited_list_values() -> None:
    settings = ExampleSettings.load(env={"TAGS": "alpha; beta\n gamma"})
    assert settings.tags == ["alpha", "beta", "gamma"]


def test_loads_key_value_dict_values() -> None:
    class MetadataSettings(BaseSettings):
        metadata: dict[str, int] = msgspec.field(default_factory=dict)

    settings = MetadataSettings.load(env={"METADATA": "first=1, second:2; third=3"})

    assert settings.metadata == {"first": 1, "second": 2, "third": 3}


def test_loads_complex_json_values() -> None:
    class PolicySettings(BaseSettings):
        rules: list[dict[str, str | int | list[str]]] = msgspec.field(
            default_factory=list
        )

    settings = PolicySettings.load(
        env={
            "RULES": (
                '[{"id":"policy.example","score":95,'
                '"evidence_urls":["https://example.com"]}]'
            )
        }
    )

    assert settings.rules == [
        {
            "id": "policy.example",
            "score": 95,
            "evidence_urls": ["https://example.com"],
        }
    ]


def test_loads_delimited_list_of_dict_values() -> None:
    class RuleSettings(BaseSettings):
        rules: list[dict[str, int]] = msgspec.field(default_factory=list)

    settings = RuleSettings.load(
        env={"RULES": "id=1,score=95; id=2,score=90\nid=3,score=85"}
    )

    assert settings.rules == [
        {"id": 1, "score": 95},
        {"id": 2, "score": 90},
        {"id": 3, "score": 85},
    ]


def test_invalid_bool_raises_validation_error() -> None:
    with pytest.raises(msgspec.ValidationError, match="invalid value for DEBUG"):
        ExampleSettings.load(env={"DEBUG": "treu"})


def test_loads_file_backed_value(tmp_path: Path) -> None:
    class SecretSettings(BaseSettings):
        token: str = ""
        token_file: str | None = None

    secret_file = tmp_path / "token"
    secret_file.write_text("secret-token\n")

    settings = SecretSettings.load(env={"TOKEN_FILE": str(secret_file)})

    assert settings.token == "secret-token"
    assert settings.token_file == str(secret_file)


def test_load_settings_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOST", "helper.example")

    settings = load_settings(ExampleSettings)
    assert settings.host == "helper.example"


def test_invalid_cls_raises() -> None:
    class Other:
        pass

    with pytest.raises(TypeError):
        load_settings(Other)  # type: ignore[type-var]


def test_load_composed_settings_preserves_nested_defaults() -> None:
    class Defaults(BaseSettings):
        debug: bool = False
        service_name: str = "composed-service"

    class UpstreamSettings(BaseSettings):
        target: str = ""
        timeout_seconds: float = 5.0

    class AppSettings(msgspec.Struct, kw_only=True):
        debug: bool = False
        service_name: str = "app"
        upstream: UpstreamSettings = msgspec.field(
            default_factory=lambda: UpstreamSettings(target="default:5000")
        )

    settings = load_composed_settings(
        AppSettings,
        env={"DEBUG": "true", "UPSTREAM_TIMEOUT_SECONDS": "2.5"},
        defaults_cls=Defaults,
        prefixes={"upstream": "UPSTREAM_"},
    )

    assert settings.debug is True
    assert settings.service_name == "composed-service"
    assert settings.upstream.target == "default:5000"
    assert settings.upstream.timeout_seconds == pytest.approx(2.5)
