"""Tests for centralized tool integration."""

from unittest.mock import patch, MagicMock
import dspy
from utils.agent.tools import get_research_tools, get_internet_search_tool


def _get_tool_name(tool):
    """Helper to get tool name across different dspy versions."""
    if hasattr(tool, "name"):
        return tool.name
    if hasattr(tool, "tool_name"):
        return tool.tool_name
    if hasattr(tool, "func"):
        return tool.func.__name__
    return str(tool)


def _get_tool_desc(tool):
    """Helper to get tool description across different dspy versions."""
    for attr in ["desc", "description", "docstring"]:
        if hasattr(tool, attr):
            return getattr(tool, attr)
    if hasattr(tool, "func"):
        return tool.func.__doc__
    return ""


def test_internet_search_tool_creation():
    """Test that the internet search tool is created correctly."""
    tool = get_internet_search_tool()
    
    assert isinstance(tool, dspy.Tool)
    assert _get_tool_name(tool) == "internet_search"
    assert "Search the internet" in _get_tool_desc(tool)


def test_research_tools_bundle_includes_search():
    """Test that the research tools bundle includes the internet search tool."""
    tools = get_research_tools()
    
    tool_names = [_get_tool_name(t) for t in tools]
    assert "internet_search" in tool_names
    assert "fetch_documentation" in tool_names


def test_internet_search_tool_execution():
    """Test the execution of the internet search tool (with mocks)."""
    tool = get_internet_search_tool()
    
    mock_results = [
        {"title": "Test Title", "url": "https://test.com", "source": "DuckDuckGo"}
    ]
    
    with patch("utils.search.search_web", return_value=mock_results):
        result = tool.func("test query")
        
        assert "Test Title" in result
        assert "https://test.com" in result
        assert "DuckDuckGo" in result


def test_internet_search_tool_empty_results():
    """Test the execution of the internet search tool with no results."""
    tool = get_internet_search_tool()
    
    with patch("utils.search.search_web", return_value=[]):
        result = tool.func("test query")
        assert "No search results found" in result
