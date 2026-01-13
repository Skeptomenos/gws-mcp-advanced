# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it privately. **Do not disclose it as a public issue.**

### How to Report

Please email `security@example.com` with a detailed description of the issue. You should receive a response within 48 hours.

## Security Features

This MCP server implements several security measures to protect user data and system integrity:

### 1. Authentication & Authorization
- **OAuth 2.0/2.1**: Uses standard Google OAuth flows.
- **Token Storage**: Tokens are stored securely using encryption (if configured with a backend like Valkey) or in a local credential store with restricted permissions.
- **Granular Scopes**: The application requests scopes based on enabled tools.
  - *Note*: By default, enabling a module (e.g., "gmail") enables all associated scopes (read/write) for that module to support full bidirectional sync capabilities. Users should be aware that the server has broad access to the enabled services.

### 2. Input Validation
- **Pydantic Models**: All tool inputs are validated using Pydantic models to ensure strict typing and structure.
- **Path Traversal Protection**: File operations (like `file://` URL handling) include checks to ensure paths are valid and accessible.

### 3. Sandboxing (Docker)
- **Containerization**: We provide a `Dockerfile` to run the server in an isolated container.
- **Non-root User**: The container runs as a non-privileged user (`mcpuser`) to limit the impact of any potential RCE vulnerability.
- **Minimal Base Image**: Uses `python:3.10-slim` to reduce the attack surface.

### 4. Transport Security
- **Stdio Mode**: By default, the server runs over stdio, which is secure when running locally or via SSH.
- **SSE Mode**: Supports Server-Sent Events over HTTP. When using this mode, ensure you are running behind a secure proxy (like Nginx) that handles TLS termination and authentication if exposed to a network.

## Recommendations for Deployers

1.  **Use Docker**: Always run the MCP server in a Docker container to isolate it from the host system.
2.  **Environment Variables**: Inject credentials (Client ID, Client Secret) via environment variables, not files.
3.  **Network Isolation**: If running in a cloud environment, restrict egress traffic to only necessary Google API endpoints (`*.googleapis.com`).
4.  **Least Privilege**: Only map volumes that are absolutely necessary. Avoid mounting sensitive host directories.

## Vulnerability Management

We follow a standard vulnerability management process:
1.  **Triage**: We assess the impact and severity of the reported issue.
2.  **Fix**: We develop a patch to address the vulnerability.
3.  **Release**: We release a new version of the package.
4.  **Disclose**: We publish a security advisory detailing the issue and the fix.
