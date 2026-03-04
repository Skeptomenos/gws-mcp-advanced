from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

ALLOWED_USER_DOCS = {
    "docs/INDEX.md",
    "docs/COMPARISON.md",
    "docs/DISTRIBUTION_RELEASE.md",
    "docs/RELEASE_NOTES.md",
}

ALLOWED_SETUP_PREFIXES = (
    "docs/setup/",
    "docs/usage/",
    "docs/troubleshooting/",
)

ALLOWED_LEGACY_STUBS = {
    "docs/STATUS.md",
    "docs/DRY_RUN_MATRIX.md",
    "docs/OPENCODE_MCP_MANUAL_TESTING.md",
    "docs/DISTRIBUTION_TEST_PHASE.md",
}


def is_allowed(path: str) -> bool:
    if path in ALLOWED_USER_DOCS:
        return True
    if path in ALLOWED_LEGACY_STUBS:
        return True
    return path.startswith(ALLOWED_SETUP_PREFIXES)


def validate_stub(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    return text.startswith("# Legacy Redirect:") and "This file moved to:" in text


def main() -> int:
    violations: list[str] = []

    for md in sorted(DOCS.rglob("*.md")):
        rel = md.relative_to(ROOT).as_posix()
        if not is_allowed(rel):
            violations.append(f"{rel}: contributor/internal docs must be in agent-docs/, not docs/.")
            continue

        if rel in ALLOWED_LEGACY_STUBS and not validate_stub(md):
            violations.append(f"{rel}: legacy stub must use the redirect template.")

    if violations:
        print("docs separation check failed:")
        for v in violations:
            print(f"- {v}")
        return 1

    print("docs separation check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
