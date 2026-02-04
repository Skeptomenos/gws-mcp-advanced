# Workflow & Ops Standards (2026)

> **Mandate:** Clean History, Reproducible Builds.

## 1. Git Discipline
- **Branches:** `feat/xyz`, `fix/abc`. Short-lived (<24h).
- **Commits:** Conventional Commits required.
  - `feat: ...`, `fix: ...`, `refactor: ...`, `docs: ...`, `test: ...`
- **Atomic PRs:** One feature per PR. No "while I'm here" changes.

## 2. Configuration
- **Secrets:** NEVER in git. Use `.env`.
- **Validation:** Crash app on startup if `ENV` is missing/invalid (use Zod/Pydantic).
- **Defaults:** `.env.example` must contain all keys with dummy values.

## 3. Docker Strategy
- **Determinism:** Always copy `lock` files (`pnpm-lock.yaml`) first. Use `pnpm install --frozen-lockfile`.
- **Multi-Stage:**
  1.  `builder`: Install full deps, compile.
  2.  `runner`: Alpine/Distroless image. Copy ONLY binary/dist.
- **User:** Run as non-root `USER node` / `USER app`.

## 4. CI/CD Triggers
- Run **Testing & Linting** on every Push.
- Block Merge if CI fails.

## 5. Command Timeout Policy
- **5-Minute Limit:** If any command runs longer than 5 minutes, stop it immediately.
- **Capture Context:** Save logs, partial output, and current state before stopping.
- **Report & Ask:** Inform the user with context before retrying or changing approach.
- **Never Retry Blindly:** Do not re-run the same hanging command without user approval.

## 6. Multi-Agent Concurrency
Assume you are NOT the only agent working on this codebase.

- **Refresh Before Editing:** Always check `git status` / `git diff` before modifying files.
- **Read-Only Git:** Never run destructive git commands (`reset`, `revert`, `force push`). Only read commands (`status`, `diff`, `log`, `show`).
- **Don't Assume Ownership:** If code you wrote is missing or changed, another agent or user likely modified it. Do not "fix" it without asking.
- **Atomic Commits:** Complete your task fully before committing. Partial commits create confusion for other agents.

## 7. Adding Dependencies
Before adding ANY new dependency:
1. **Search:** Find 2-3 well-maintained alternatives.
2. **Evaluate:** Check GitHub stars, last commit date, open issues.
3. **Confirm:** Present options to user with pros/cons before adding.
4. **Document:** Add brief comment in package file explaining choice if non-obvious.
