"""msgspec-based settings loader with .env support."""

from .core import (
    BaseSettings,
    ServiceDefaultsBase,
    load_composed_settings,
    load_settings,
)

__all__ = [
    "BaseSettings",
    "ServiceDefaultsBase",
    "load_composed_settings",
    "load_settings",
]
