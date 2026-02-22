import pytest
import os
from unittest.mock import patch, MagicMock
from utils.mcp.client import MCPManager

# We can mock out the actual StdioServerParameters and FastMCP to avoid spawning processes during tests,
# or we can do a light integration test if we have the servers locally. Since we just wrote
# them, an integration test is very useful.

@pytest.fixture
def manager():
    manager = MCPManager()
    yield manager
    # Clean up the singleton instance for other tests if necessary
    manager.close()
    MCPManager._instance = None


@pytest.mark.asyncio
def test_mcp_manager_singleton():
    m1 = MCPManager()
    m2 = MCPManager()
    assert m1 is m2
    m1.close()
    MCPManager._instance = None


def test_mcp_client_connects_and_wraps_tools(manager):
    """
    Integration test:
    Connects to the local file_server and search_server and retrieves tools.
    """
    # Just configure one simple server to avoid heavy loads
    with patch("utils.mcp.client.settings") as mock_settings:
        mock_settings.mcp_servers = {
            "test_file": ["python", "-m", "mcp_servers.file_server"]
        }
        
        manager.connect_all()
        
        # Check if the tools are loaded
        tools = manager.get_all_tools()
        assert len(tools) > 0
        
        # Verify it has standard dspy.Tool properties
        tool = manager.get_tool("read_file")
        assert tool is not None
        assert tool.name == "read_file"
        assert callable(tool)
        
        # Try a quick call (we expect it to execute the fastmcp via stdio)
        # Assuming the root directory has a pyproject.toml
        result = tool(file_path="pyproject.toml", start_line=1, end_line=3)
        assert "[project]" in result or "version =" in result or "name =" in result


def test_mcp_compounding_server_connects(manager):
    """
    Integration test: Connects to the compounding server and verifies the tools are exported.
    """
    with patch("utils.mcp.client.settings") as mock_settings:
        mock_settings.mcp_servers = {
            "compounding": ["python", "-m", "mcp_servers.compounding_server"]
        }
        
        manager.connect_all()
        
        tools = manager.get_all_tools()
        # Should have at least the 5 we exposed
        assert len(tools) >= 5
        
        tool_names = [t.name for t in tools]
        assert "compounding_review" in tool_names
        assert "compounding_work" in tool_names
        assert "compounding_plan" in tool_names

