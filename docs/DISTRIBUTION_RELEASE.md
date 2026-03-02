# Distribution and Release Guide

## Metadata
- Last Updated (UTC): 2026-03-02T13:53:12Z
- Primary Distribution: `uvx` from PyPI
- Python Package: `google-workspace-mcp-advanced`

## Primary Channels (uvx-first)
1. Stable: latest PyPI release
2. Pinned: explicit version (`==x.y.z`)

## Prerequisite: Install uv
`uvx` is provided by `uv`, so users must install `uv` first.

```bash
# macOS (Homebrew)
brew install uv

# Linux/macOS (official installer)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify
uv --version
```

## Consumer Install Paths (Recommended)
```bash
# Stable
uvx google-workspace-mcp-advanced --transport stdio

# Deterministic pinned
uvx google-workspace-mcp-advanced==1.0.0 --transport stdio
```

## Release Order
1. Publish Python package to PyPI.
2. Validate stable (`uvx package`) and pinned (`uvx package==x.y.z`) paths.

## GitHub Workflows
1. `.github/workflows/release-pypi.yml`

## Trusted Publishing Requirements
1. Configure PyPI trusted publisher for this repository/project.
2. Keep workflow permissions:
   - `id-token: write`
   - `contents: read`

## Rollback Playbook (uvx-first)
If a release is bad, pin consumers to the last known-good version:

```bash
uvx google-workspace-mcp-advanced==<good_version> --transport stdio
```

## Pre-Release Validation Checklist (Primary Lane)
1. `uv run python scripts/check_distribution_scope.py`
2. `uv run pytest -q tests/unit/core/test_distribution_checks.py`
3. `uvx google-workspace-mcp-advanced==1.0.0 --help`
