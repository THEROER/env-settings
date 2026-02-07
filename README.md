# env-settings

A tiny settings loader inspired by `pydantic_settings`, but implemented with [`msgspec`](https://github.com/jcrist/msgspec). It allows loading structured configuration from environment variables and optional `.env` files without depending on Pydantic.

## Features

- Define settings as `msgspec.Struct` classes
- Load values from the current environment, optional `.env` files, and defaults
- Automatic type coercion performed by `msgspec`
- Optional prefixes and case-insensitive matching

## Usage

```python
from typing import Optional
import msgspec

from env_settings import BaseSettings

class AppSettings(BaseSettings):
    debug: bool = False
    database_url: str
    api_key: Optional[str] = None

settings = AppSettings.load(env_file=".env", prefix="APP_")
print(settings.database_url)
```

`.env` values override defaults, while real environment variables take precedence over the file.

## Installation

```bash
poetry add git+https://github.com/THEROER/env-settings
```

## Development

```bash
poetry install
poetry run pytest
```
