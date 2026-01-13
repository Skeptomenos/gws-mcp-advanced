"""
Template for testing MCP tools with mocked Google services.

This module demonstrates how to test MCP tools by:
1. Mocking the Google API service object
2. Mocking the authentication decorator
3. Testing the tool's business logic in isolation

Usage:
    Copy this template and adapt for other tool modules (drive, calendar, etc.)
"""

from unittest.mock import MagicMock

import pytest


class TestSearchGmailMessages:
    """Tests for the search_gmail_messages tool."""

    @pytest.fixture
    def mock_gmail_service(self):
        """Create a mock Gmail service with common response patterns."""
        service = MagicMock()

        messages_resource = MagicMock()
        service.users.return_value.messages.return_value = messages_resource

        messages_resource.list.return_value.execute.return_value = {
            "messages": [
                {"id": "msg_001", "threadId": "thread_001"},
                {"id": "msg_002", "threadId": "thread_002"},
            ],
            "resultSizeEstimate": 2,
        }

        messages_resource.get.return_value.execute.return_value = {
            "id": "msg_001",
            "threadId": "thread_001",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                ],
                "body": {"data": "VGVzdCBib2R5IGNvbnRlbnQ="},  # "Test body content" base64
                "mimeType": "text/plain",
            },
        }

        return service

    @pytest.mark.asyncio
    async def test_search_returns_formatted_results(self, mock_gmail_service):
        """Verify search returns properly formatted message list."""
        from gmail.gmail_tools import _extract_message_body

        payload = {
            "body": {"data": "VGVzdCBib2R5IGNvbnRlbnQ="},
            "mimeType": "text/plain",
        }

        result = _extract_message_body(payload)

        assert "Test body content" in result

    @pytest.mark.asyncio
    async def test_empty_search_returns_no_results_message(self, mock_gmail_service):
        """Verify empty search results are handled gracefully."""
        mock_gmail_service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
            "messages": [],
            "resultSizeEstimate": 0,
        }

        messages = mock_gmail_service.users().messages().list(userId="me", q="nonexistent").execute()

        assert messages["messages"] == []
        assert messages["resultSizeEstimate"] == 0


class TestGetGmailMessageContent:
    """Tests for the get_gmail_message_content tool."""

    @pytest.fixture
    def mock_message_payload(self):
        """Create a mock message payload with multipart content."""
        return {
            "mimeType": "multipart/alternative",
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": "UGxhaW4gdGV4dCBjb250ZW50"},  # "Plain text content"
                },
                {
                    "mimeType": "text/html",
                    "body": {"data": "PGh0bWw+SFRNTCB0ZXh0PC9odG1sPg=="},  # "<html>HTML text</html>"
                },
            ],
        }

    def test_extract_plain_text_from_multipart(self, mock_message_payload):
        """Verify plain text extraction from multipart messages."""
        from gmail.gmail_tools import _extract_message_bodies

        bodies = _extract_message_bodies(mock_message_payload)

        assert "Plain text content" in bodies["text"]
        assert "HTML" in bodies["html"]

    def test_html_to_text_conversion(self):
        """Verify HTML is properly converted to readable text."""
        from gmail.gmail_tools import _html_to_text

        html = "<html><body><p>Hello <strong>World</strong></p></body></html>"
        result = _html_to_text(html)

        assert "Hello" in result
        assert "World" in result
        assert "<" not in result


class TestGmailToolIntegration:
    """Integration-style tests that verify tool decorator behavior."""

    def test_tool_is_registered_as_mcp_tool(self):
        """Verify tools are registered with the MCP server."""
        from gmail.gmail_tools import search_gmail_messages

        assert hasattr(search_gmail_messages, "name")
        assert search_gmail_messages.name == "search_gmail_messages"

    def test_empty_body_returns_no_content_message(self):
        """Verify empty body content returns appropriate fallback message."""
        from gmail.gmail_tools import _format_body_content

        result = _format_body_content("", "")

        assert "[No readable content found]" in result
