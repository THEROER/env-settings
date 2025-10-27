"""msgspec-based settings loader with .env support."""

from .core import BaseSettings, load_settings

__all__ = ["BaseSettings", "load_settings"]
