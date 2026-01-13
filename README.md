# GWS MCP Advanced

Advanced Model Context Protocol (MCP) server for Google Workspace integration.

This project is an advanced fork of [taylorwilsdon/google_workspace_mcp](https://github.com/taylorwilsdon/google_workspace_mcp), merged with advanced file synchronization features from the `drive-synapsis` MCP. It provides AI assistants with comprehensive access to Gmail, Google Drive, Calendar, Docs, Sheets, Chat, Forms, Slides, Tasks, and Search with bidirectional sync capabilities.

## Features

- **10 Google Services**: Gmail, Drive, Calendar, Docs, Sheets, Chat, Forms, Slides, Tasks, Search
- **50+ Tools**: Comprehensive API coverage for each service
- **Advanced Sync Tools**: Bidirectional file synchronization between local files and Google Drive (based on `drive-synapsis`)
- **Search Aliases**: Quick reference to search results using A-Z aliases
- **OAuth 2.0/2.1**: Secure authentication with modern session management
- **Async Architecture**: Non-blocking operations for high performance

## Quick Start

### Prerequisites

- Python 3.11+
- uv (recommended) or pip

### Installation

```bash
# Clone the repository
cd gws-mcp-advanced

# Install with uv
uv pip install -e .

# Or with pip
pip install -e .
```

### Running the Server

```bash
# STDIO mode (default, for MCP clients)
python main.py

# HTTP mode (for web-based clients)
python main.py --transport streamable-http

# Single-user mode (bypasses session mapping)
python main.py --single-user

# Load specific services only
python main.py --tools gmail drive calendar
```

### MCP Client Configuration

Add to your MCP client configuration (e.g., Claude Desktop, OpenCode):

```json
{
  "mcpServers": {
    "gws-mcp-advanced": {
      "command": "python",
      "args": ["/path/to/gws-mcp-advanced/main.py"],
      "env": {
        "USER_GOOGLE_EMAIL": "your.email@gmail.com"
      }
    }
  }
}
```

## Authentication

This server uses OAuth 2.0/2.1 credentials. On first use:

1. The server will provide an OAuth URL
2. Open the URL in your browser
3. Sign in with your Google account
4. Grant the requested permissions
5. Credentials are stored in `~/.config/gws-mcp-advanced/credentials/`

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `USER_GOOGLE_EMAIL` | Your Google email | Required |
| `MCP_SINGLE_USER_MODE` | Bypass session mapping | `false` |
| `WORKSPACE_MCP_PORT` | HTTP server port | `9876` |
| `WORKSPACE_MCP_CONFIG_DIR` | Directory for credentials | `~/.config/gws-mcp-advanced` |


## Available Tools

### Gmail
- `search_gmail_messages` - Search emails
- `get_gmail_message_content` - Read email content
- `send_gmail_message` - Send emails
- `draft_gmail_message` - Create drafts
- And more...

### Google Drive
- `search_google_drive` - Search files (results cached with A-Z aliases)
- `read_google_drive_file` - Read file content
- `create_google_doc` - Create documents
- `upload_file` - Upload files
- **Sync Tools**:
  - `link_local_file` - Link local file to Drive
  - `update_google_doc` - Upload local to Drive (dry-run default)
  - `download_google_doc` - Download Drive to local (dry-run default)
  - `upload_folder` - Recursive folder upload
  - `mirror_drive_folder` - Recursive folder download
  - `download_doc_tabs` - Multi-tab document sync

### Google Calendar
- `get_events` - List calendar events
- `create_event` - Create events
- `modify_event` - Update events
- `delete_event` - Delete events

### Google Docs
- `get_document_outline` - Get document structure
- `read_document_section` - Read specific sections
- `append_to_google_doc` - Append content
- `replace_doc_text` - Find and replace

### Google Sheets
- `read_sheet_range` - Read cell ranges
- `update_sheet_cell` - Update cells
- `create_sheet` - Create spreadsheets
- `append_to_sheet` - Append rows

### Google Chat
- `list_spaces` - List chat spaces
- `get_messages` - Read messages
- `send_message` - Send messages

### Google Forms
- `get_form` - Get form details
- `list_form_responses` - List responses
- `create_form` - Create forms

### Google Slides
- `get_presentation` - Get presentation details
- `create_presentation` - Create presentations
- `batch_update_presentation` - Update slides

### Google Tasks
- `list_tasks` - List tasks
- `create_task` - Create tasks
- `update_task` - Update tasks

### Google Search
- `search_custom` - Programmable Search Engine

## Search Aliases

When you search Google Drive, results are automatically cached with aliases:

```
Search results:
[A] Project Plan - Google Doc
[B] Budget 2024 - Google Sheet
[C] Team Photo - Image
```

Use aliases in subsequent commands:
```
read_google_drive_file(file_id="A")  # Reads "Project Plan"
```

## Sync Tools

The sync tools enable bidirectional synchronization between local files and Google Drive:

### Linking Files
```python
link_local_file(local_path="docs/notes.md", file_id="A")
```

### Uploading Changes (Safe by Default)
```python
# Dry run - shows diff without making changes
update_google_doc(local_path="docs/notes.md")

# Apply changes
update_google_doc(local_path="docs/notes.md", dry_run=False)
```

### Downloading Changes (Safe by Default)
```python
# Dry run - shows diff without making changes
download_google_doc(local_path="docs/notes.md")

# Apply changes
download_google_doc(local_path="docs/notes.md", dry_run=False)
```

## Development

### Project Structure

```
google-workspace-mcp/
├── auth/                 # OAuth and authentication
│   ├── google_auth.py    # Core auth logic
│   ├── google_oauth_config.py  # Embedded credentials
│   └── service_decorator.py # @require_google_service
├── core/                 # Shared utilities
│   ├── errors.py         # Custom error types
│   ├── managers.py       # SearchManager, SyncManager
│   └── server.py         # FastMCP server instance
├── gdrive/               # Google Drive tools
│   ├── drive_tools.py    # Core Drive tools
│   └── sync_tools.py     # Sync tools
├── gmail/                # Gmail tools
├── gcalendar/            # Calendar tools
├── gdocs/                # Docs tools
├── gsheets/              # Sheets tools
├── gchat/                # Chat tools
├── gforms/               # Forms tools
├── gslides/              # Slides tools
├── gtasks/               # Tasks tools
├── gsearch/              # Search tools
├── main.py               # CLI entry point
├── fastmcp_server.py     # FastMCP Cloud entry point
└── pyproject.toml        # Package configuration
```

### Running Tests

```bash
pytest tests/
```

## License

MIT License.
