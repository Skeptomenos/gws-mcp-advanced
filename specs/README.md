# Auth Improvement Specs

This directory contains detailed specifications for fixing authentication issues and improving the architecture of the `gws-mcp-advanced` server.

## Context
The project has resolved P0-P3 code quality issues. The current critical blocker is an authentication flaw where users are constantly prompted to re-authenticate because session mappings are stored in memory and lost on server restart.

## Problem
- **RC-1**: `OAuth21SessionStore` stores session mappings in memory (`_mcp_session_mapping`), losing them on restart.
- **RC-2**: Session ID mismatch prevents finding credentials after restart.
- **RC-3**: Credential lookup is brittle (requires exact email).
- **RC-4**: Token refresh doesn't sync across all storage layers.
- **RC-5**: No auto-recovery for single-user mode.

## Goal
Implement a robust, persistent authentication system that survives server restarts and handles single-user scenarios gracefully.

## Specs
1. **[01_diagnostics_and_testing.md](./01_diagnostics_and_testing.md)**: Infrastructure for debugging and verifying auth flows.
2. **[02_session_persistence_and_recovery.md](./02_session_persistence_and_recovery.md)**: The core fix - persisting session mappings and adding auto-recovery.
3. **[03_architecture_and_consolidation.md](./03_architecture_and_consolidation.md)**: Refactoring the auth module for long-term maintainability (DI, Errors, Consolidation).
