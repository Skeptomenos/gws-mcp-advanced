"""Unit tests for Search scope policy (API-key auth, no OAuth cse scope)."""

from auth.scopes import BASE_SCOPES, TOOL_SCOPES_MAP, get_scopes_for_tools

CSE_SCOPE = "https://www.googleapis.com/auth/cse"


def test_search_tool_group_is_not_mapped_to_oauth_scopes():
    assert "search" not in TOOL_SCOPES_MAP


def test_search_enabled_does_not_add_cse_scope_to_requested_scopes():
    scopes = set(get_scopes_for_tools(["search"]))
    assert CSE_SCOPE not in scopes
    assert scopes == set(BASE_SCOPES)


def test_full_scope_aggregation_excludes_cse_scope():
    scopes = set(get_scopes_for_tools())
    assert CSE_SCOPE not in scopes
