"""Tests for DuckDuckGo search tool."""

from unittest.mock import MagicMock, patch

import pytest


@patch("utils.search.ddg_search.DDGS")
def test_search_web_success(mock_ddgs_class):
    """Test successful search with results."""
    # Setup mock
    mock_ddgs = MagicMock()
    mock_ddgs_class.return_value = mock_ddgs
    mock_ddgs.text.return_value = [
        {
            "title": "Python Best Practices 2024",
            "href": "https://example.com/python-best-practices",
            "body": "Learn the latest Python best practices for 2024...",
        },
        {
            "title": "Python Style Guide",
            "href": "https://pep8.org",
            "body": "Official Python style guide PEP 8...",
        },
    ]

    # Import and test
    from utils.search import search_web

    results = search_web("python best practices")

    # Assertions
    assert len(results) == 2
    assert results[0]["title"] == "Python Best Practices 2024"
    assert results[0]["url"] == "https://example.com/python-best-practices"
    assert results[0]["source"] == "DuckDuckGo"
    assert results[1]["title"] == "Python Style Guide"

    # Verify DDGS was called correctly
    mock_ddgs_class.assert_called_once_with(timeout=10)
    mock_ddgs.text.assert_called_once_with("python best practices", max_results=5)


@patch("utils.search.ddg_search.DDGS")
def test_search_web_empty_results(mock_ddgs_class):
    """Test search with no results."""
    mock_ddgs = MagicMock()
    mock_ddgs_class.return_value = mock_ddgs
    mock_ddgs.text.return_value = []

    from utils.search import search_web

    results = search_web("xyzabc123nonexistent")

    assert results == []


@patch("utils.search.ddg_search.DDGS")
def test_search_web_with_max_results(mock_ddgs_class):
    """Test search with custom max_results parameter."""
    mock_ddgs = MagicMock()
    mock_ddgs_class.return_value = mock_ddgs
    mock_ddgs.text.return_value = [
        {"title": f"Result {i}", "href": f"https://example.com/{i}", "body": f"Body {i}"}
        for i in range(3)
    ]

    from utils.search import search_web

    results = search_web("test query", max_results=3)

    assert len(results) == 3
    mock_ddgs.text.assert_called_once_with("test query", max_results=3)


@patch("utils.search.ddg_search.DDGS")
def test_search_web_handles_errors(mock_ddgs_class):
    """Test that errors are handled gracefully."""
    mock_ddgs = MagicMock()
    mock_ddgs_class.return_value = mock_ddgs
    mock_ddgs.text.side_effect = Exception("Network error")

    from utils.search import search_web

    results = search_web("test query")

    # Should return error result instead of crashing
    assert len(results) == 1
    assert results[0]["title"] == "Search Error"
    assert "Network error" in results[0]["source"]


@patch("utils.search.ddg_search.DDGS")
def test_search_web_missing_fields(mock_ddgs_class):
    """Test handling of results with missing fields."""
    mock_ddgs = MagicMock()
    mock_ddgs_class.return_value = mock_ddgs
    mock_ddgs.text.return_value = [
        {"title": "Only Title"},  # Missing href and body
        {"href": "https://example.com"},  # Missing title and body
    ]

    from utils.search import search_web

    results = search_web("test")

    assert len(results) == 2
    assert results[0]["title"] == "Only Title"
    assert results[0]["url"] == ""
    assert results[0]["source"] == "DuckDuckGo"
    assert results[1]["title"] == ""
    assert results[1]["url"] == "https://example.com"
