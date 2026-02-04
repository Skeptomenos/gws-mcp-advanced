# Testing Guide

## Quick Commands

```bash
# Run all tests (fastest)
uv run pytest

# Run with coverage (matches CI)
uv run pytest tests/ --cov=.

# Run single test file
uv run pytest tests/test_oauth_state_persistence.py

# Run single test function (recommended for debugging)
uv run pytest tests/test_oauth_state_persistence.py::TestOAuthStatePersistence::test_store_oauth_state_persists_to_disk

# Verbose output
uv run pytest -vs
```

## Test Organization

Tests are organized in the `tests/` directory:

```
tests/
├── fixtures/       # Shared test fixtures
├── integration/    # Integration tests
├── unit/           # Unit tests
└── test_*.py       # Top-level test files
```

## Writing Tests

- Use `pytest-asyncio` for async test functions (configured with `asyncio_mode = "auto"`)
- Test files must match pattern `test_*.py`
- Test classes must match pattern `Test*`
- Test functions must match pattern `test_*`

```python
import pytest

class TestMyFeature:
    async def test_async_operation(self):
        result = await my_async_function()
        assert result is not None

    def test_sync_operation(self):
        result = my_sync_function()
        assert result == expected_value
```

## Type Checking

Pyright is run in CI but is currently permissive (continue-on-error):

```bash
# Install pyright (not in dev-dependencies)
pip install pyright

# Run type verification
pyright --verifytypes gws-mcp-advanced
```

## CI Pipeline

The CI pipeline runs these checks in order:

1. `uv run ruff check .` - Linting
2. `uv run ruff format --check .` - Format verification
3. `uv run pytest tests/ --cov=.` - Tests with coverage
