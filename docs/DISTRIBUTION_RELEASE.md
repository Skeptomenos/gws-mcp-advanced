# Distribution and Release Guide

## Metadata
- Last Updated (UTC): 2026-03-01T21:00:38Z
- npm Package: `@skeptomenos/gws-mcp-advanced`
- Python Package: `gws-mcp-advanced`

## Channels
1. Stable: `latest`
2. Prerelease: `next`
3. Pinned: explicit version (`@x.y.z`)

## Consumer Install Paths
```bash
# Stable
npx -y @skeptomenos/gws-mcp-advanced --transport stdio

# Prerelease
npx -y @skeptomenos/gws-mcp-advanced@next --transport stdio

# Deterministic pinned
npx -y @skeptomenos/gws-mcp-advanced@1.0.0 --transport stdio
```

## Release Order (Required)
1. Publish Python package to PyPI first.
2. Publish npm package second, only after matching PyPI version exists.

This ordering is enforced by:
1. `scripts/check_release_version_match.py` (Python/npm version coupling).
2. `scripts/check_pypi_version_available.py` (npm publish blocked until PyPI has matching version).

## GitHub Workflows
1. PyPI publish workflow: `.github/workflows/release-pypi.yml`
2. npm publish workflow: `.github/workflows/release-npm.yml`

### Trusted Publishing Requirements
1. Configure PyPI trusted publisher for this repository and target project.
2. Configure npm trusted publisher for this repository and package scope.
3. Keep workflow permissions:
   - `id-token: write`
   - `contents: read`

## Provenance
1. npm publishes use provenance:
   - `npm publish --access public --provenance`
2. Preserve workflow OIDC permissions in release workflows to keep provenance active.

## Rollback Playbook
If the latest npm release is bad:

1. Identify previous good version:
```bash
npm view @skeptomenos/gws-mcp-advanced versions --json
```

2. Repoint `latest` dist-tag to known-good:
```bash
npm dist-tag add @skeptomenos/gws-mcp-advanced@<good_version> latest
```

3. Optionally remove bad `latest` tag association:
```bash
npm dist-tag rm @skeptomenos/gws-mcp-advanced latest
npm dist-tag add @skeptomenos/gws-mcp-advanced@<good_version> latest
```

4. Keep pinned consumer fallback:
```bash
npx -y @skeptomenos/gws-mcp-advanced@<good_version> --transport stdio
```

## Pre-Release Validation Checklist
1. `uv run python scripts/check_distribution_scope.py`
2. `uv run python scripts/check_release_version_match.py`
3. `uv run pytest -q tests/unit/core/test_npm_launcher.py tests/unit/core/test_distribution_checks.py`
4. `node --check bin/gws-mcp-advanced.cjs`
5. `npm pack --dry-run`
