"""Core settings loading utilities."""

from __future__ import annotations

import os
from pathlib import Path
import types
import typing
from typing import Any, Mapping, TypeVar
from typing import get_args, get_origin, get_type_hints

import msgspec

_T = TypeVar("_T", bound="BaseSettings")

_SENTINEL = object()

UNION_TYPES: set[Any] = {typing.Union}
if hasattr(types, "UnionType"):
    UNION_TYPES.add(types.UnionType)


def _parse_bool(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "on"}


def _coerce_value(expected_type: Any, raw: Any) -> Any:  # noqa: ANN401
    origin = get_origin(expected_type)
    if origin is None:
        if not isinstance(raw, str):
            return raw
        if expected_type is str:
            return raw
        if expected_type is int:
            return int(raw)
        if expected_type is float:
            return float(raw)
        if expected_type is bool:
            return _parse_bool(raw)
        return raw

    if origin is list:
        item_type = get_args(expected_type)[0]
        if isinstance(raw, str):
            items = [item.strip() for item in raw.split(",") if item.strip()]
            return [_coerce_value(item_type, item) for item in items]
        if isinstance(raw, list):
            return [_coerce_value(item_type, item) for item in raw]
        return raw

    if origin in UNION_TYPES:
        args = get_args(expected_type)
        if type(None) in args:
            if isinstance(raw, str) and raw == "":
                return None
            non_none = next(arg for arg in args if arg is not type(None))
            return _coerce_value(non_none, raw)

    return raw


def _parse_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        data[key] = value
    return data


class BaseSettings(msgspec.Struct, kw_only=True, omit_defaults=True):
    """Base class for settings definitions."""

    @classmethod
    def _collect_env(
        cls,
        *,
        env: Mapping[str, str] | None,
        env_file: str | os.PathLike[str] | None,
        prefix: str | None,
        case_sensitive: bool,
        defaults: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}

        fields = {name if case_sensitive else name.upper(): name for name in cls.__struct_fields__}
        prefix_cmp = prefix if case_sensitive else (prefix.upper() if prefix else None)

        def resolve_field(key: str, *, allow_prefix: bool) -> str | None:
            key_cmp = key if case_sensitive else key.upper()
            if allow_prefix and prefix_cmp:
                if not key_cmp.startswith(prefix_cmp):
                    return None
                key_cmp = key_cmp[len(prefix_cmp) :]
            return fields.get(key_cmp) or (fields.get(key) if allow_prefix is False else None)

        if defaults:
            for key, value in defaults.items():
                field = fields.get(key if case_sensitive else key.upper()) or resolve_field(key, allow_prefix=False)
                if field:
                    result[field] = value

        if env_file:
            env_path = Path(env_file)
            file_values = _parse_env_file(env_path)
            for key, value in file_values.items():
                field = resolve_field(key, allow_prefix=True)
                if field:
                    result[field] = value

        source = env or os.environ
        for key, value in source.items():
            field = resolve_field(key, allow_prefix=True)
            if field:
                result[field] = value

        return result

    @classmethod
    def load(
        cls: type[_T],
        *,
        env: Mapping[str, str] | None = None,
        env_file: str | os.PathLike[str] | None = None,
        prefix: str | None = None,
        case_sensitive: bool = False,
        defaults: Mapping[str, Any] | None = None,
    ) -> _T:
        """Create settings instance from environment data."""

        raw = cls._collect_env(
            env=env,
            env_file=env_file,
            prefix=prefix,
            case_sensitive=case_sensitive,
            defaults=defaults,
        )
        if raw:
            type_hints = get_type_hints(cls, include_extras=True)
            for name, hinted_type in type_hints.items():
                if name not in raw:
                    continue
                raw[name] = _coerce_value(hinted_type, raw[name])
        return msgspec.convert(raw, cls)


class ServiceDefaultsBase(BaseSettings):
    """Common top-level service defaults used across microservices."""

    debug: bool = False
    sqlalchemy_echo: bool = False
    service_name: str = "service"
    public_base_url: str = "https://leavelocal.com"
    cors_allow_origins: list[str] = msgspec.field(default_factory=list)
    cors_allow_origins_debug: list[str] = msgspec.field(default_factory=list)
    snowflake_worker_id: int = 0
    snowflake_datacenter_id: int = 0


def load_settings(
    cls: type[_T],
    *,
    env: Mapping[str, str] | None = None,
    env_file: str | os.PathLike[str] | None = None,
    prefix: str | None = None,
    case_sensitive: bool = False,
    defaults: Mapping[str, Any] | None = None,
) -> _T:
    """Convenience helper to instantiate settings."""

    if not issubclass(cls, BaseSettings):
        msg = "cls must derive from BaseSettings"
        raise TypeError(msg)
    return cls.load(
        env=env,
        env_file=env_file,
        prefix=prefix,
        case_sensitive=case_sensitive,
        defaults=defaults,
    )
