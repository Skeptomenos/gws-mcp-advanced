# Comparison: gws-mcp-advanced vs. taylorwilsdon/google_workspace_mcp

This document highlights the key differences between the `gws-mcp-advanced` fork and the upstream `taylorwilsdon/google_workspace_mcp` repository.

While the upstream repository is a robust, feature-complete implementation, this advanced fork integrates the **Drive Synapsis engine** and architectural improvements designed for high-performance agent workflows.

| Feature | Upstream (`taylorwilsdon`) | Advanced Fork (`gws-mcp-advanced`) |
| :--- | :--- | :--- |
| **Core Services** | 10 Services (Gmail, Drive, etc.) | **Same 10 Services** (Full parity) |
| **File Synchronization** | Basic (Create/Read/Download) | **Bidirectional Sync Engine** (Drive Synapsis) |
| **Code Architecture** | Monolithic tool files | **Modular** domain-specific packages (Refactored v0.9.1) |
| **Search Experience** | Standard file lists | **Smart Aliasing** (Returns `[A] File.pdf` for context efficiency) |
| **Tool Count** | ~90 tools | **100+ tools** (Adds sync & aliasing tools) |
| **Authentication** | OAuth 2.0/2.1, Disk/Redis | **Enhanced Persistence**: Atomic writes, auto-recovery, diagnostics |

## Key Enhancements

### 1. Drive Synapsis Integration (The "Killer Feature")
The upstream repo treats Drive as a remote storage to access. This fork treats Drive as a **synchronized filesystem**.

- **Bidirectional Sync**: Edit a local markdown file, and it updates the linked Google Doc automatically.
- **Recursive Mirroring**: Download entire Drive folders to local disk with `mirror_drive_folder`.
- **Hybrid Split-Sync**: Download a Google Doc as a folder containing the full text *plus* individual tabs as separate files.
- **Local Linking**: Link any local file to a Drive ID for persistent sync (`link_local_file`).

### 2. Architectural Refactor (v0.9.1)
We completely restructured the codebase to support scalable development.

- **Upstream**: Tools are grouped in large files (e.g., `gmail_tools.py` ~1600 lines).
- **Advanced**: Tools are split by domain (e.g., `gmail/messages.py`, `gmail/threads.py`, `gdrive/permissions.py`).
- **Benefit**: Easier for teams to contribute without merge conflicts; cleaner separation of concerns.

### 3. LLM Interaction Optimizations
- **Search Aliases**: When searching, we cache results and assign short aliases (A, B, C).
    - *Upstream*: "Read file 1234567890abcdef..." (High token cost, error-prone)
    - *Advanced*: "Read file [A]" (Low token cost, reliable)
- **Formatted Outputs**: Tools return markdown-optimized responses designed specifically for Claude/Gemini consumption.

### 4. Enterprise Hardening
- **Atomic Auth Storage**: Prevents `credentials.json` corruption if the server crashes during a write.
- **Self-Healing Sessions**: Automatically recovers authentication state from disk if memory mapping is lost on restart.
- **Auth Diagnostics**: Built-in debugging tools (`AUTH_DIAGNOSTICS=1`) to trace permission issues.

---
*Analysis based on v0.9.1 of gws-mcp-advanced*
