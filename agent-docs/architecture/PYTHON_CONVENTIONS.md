# Python Conventions

## Formatting

- **Line length**: 120 characters (configured in pyproject.toml)
- **Quotes**: Always use double quotes for strings
- **Target**: Python 3.10+ (use `|` for unions, `match` statements where appropriate)

## Imports

Group imports in this order, separated by blank lines:

1. Standard library
2. Third-party packages
3. Local modules

```python
import asyncio
import logging
from typing import Optional, List

from googleapiclient.errors import HttpError

from auth.service_decorator import require_google_service
from core.server import server
```

## Naming Conventions

| Type                | Style                                                  |
| ------------------- | ------------------------------------------------------ |
| Functions/variables | `snake_case`                                           |
| Classes             | `PascalCase`                                           |
| Constants           | `UPPER_SNAKE_CASE`                                     |
| Loggers             | `logger = logging.getLogger(__name__)` at module level |

## Type Hints

Always use explicit type hints for function signatures and complex variables.
Avoid `Any` unless absolutely necessary for dynamic Google API responses.

```python
# Good
async def search_files(query: str, max_results: int = 10) -> list[dict]:
    ...

# Avoid
async def search_files(query, max_results=10):
    ...
```

## Error Handling

1. Use custom error types from `core/errors.py` for domain-specific failures
2. Use `@handle_http_errors` decorator for standard Google API error mapping
3. Never use empty `except:` blocks
4. Log errors with `logger.error(..., exc_info=True)` when appropriate

```python
# Good
try:
    result = await asyncio.to_thread(api_call)
except HttpError as e:
    logger.error("API call failed", exc_info=True)
    raise GoogleAPIError(f"Failed to fetch: {e}") from e

# Bad - swallows all errors
try:
    result = api_call()
except:
    pass
```
