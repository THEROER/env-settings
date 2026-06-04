# env-settings

A tiny settings loader inspired by `pydantic_settings`, but implemented with [`msgspec`](https://github.com/jcrist/msgspec). It allows loading structured configuration from environment variables and optional `.env` files without depending on Pydantic.

## Features

- Define settings as `msgspec.Struct` classes
- Load values from the current environment, optional `.env` files, and defaults
- Automatic type coercion for scalar values and common collection formats
- Optional prefixes and case-insensitive matching
- File-backed secret fallback via `*_FILE` variables
- Declarative loading for top-level settings composed from prefixed blocks

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

List values can be written as CSV, semicolon/newline-delimited text, or JSON:

```env
APP_ALLOWED_ORIGINS=https://example.com,https://api.example.com
APP_ALLOWED_LOCALES=en;uk;fr
APP_ALLOWED_TOPICS=["landing.live_stats","monitoring.live_status"]
```

Dict values can be written as JSON or delimited key-value pairs:

```env
APP_LIMITS={"checkout":20,"login":60}
APP_LIMITS=checkout=20,login:60;refresh=120
```

`list[dict[...]]` values can be written as JSON or as records separated by
semicolon/newline. Within each record, comma separates key-value pairs:

```env
APP_RULES=[{"id":"policy.example","score":95,"evidence_urls":["https://example.com"]}]
APP_RULES=id=1,score=95;id=2,score=90
```

Prefer JSON when values are deeply nested or may contain delimiters.

Boolean values are parsed strictly. Accepted values are `1/0`, `true/false`,
`yes/no`, `on/off`, and `y/n`.

## File-backed values

If `TOKEN` is empty or unset, `TOKEN_FILE` can point to a file containing the
value:

```python
class SecretSettings(BaseSettings):
    token: str = ""
    token_file: str | None = None

settings = SecretSettings.load()
```

```env
TOKEN_FILE=/run/secrets/api_token
```

The `token_file` field is optional. `TOKEN_FILE` also works when only `token`
is defined.

## Composed settings

Services with a top-level `msgspec.Struct` can load nested settings blocks
declaratively:

```python
from env_settings import BaseSettings, ServiceDefaultsBase, load_composed_settings
import msgspec

class DatabaseSettings(BaseSettings):
    host: str = "localhost"
    port: int = 5432

class ServiceDefaults(ServiceDefaultsBase):
    service_name: str = "example-service"

class Settings(msgspec.Struct, kw_only=True):
    debug: bool = False
    service_name: str = "example-service"
    database: DatabaseSettings = msgspec.field(default_factory=DatabaseSettings)

settings = load_composed_settings(
    Settings,
    env_file=".env",
    defaults_cls=ServiceDefaults,
    prefixes={"database": "POSTGRES_"},
)
```

Default factories on nested fields are preserved and then overridden by matching
environment values.

## Installation

```bash
uv add git+https://github.com/THEROER/env-settings
```

## Development

```bash
uv sync --dev
uv run pytest
```
