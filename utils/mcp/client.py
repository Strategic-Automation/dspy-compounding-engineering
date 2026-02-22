import asyncio
import inspect
import sys
import threading
from typing import Any, Callable, Dict, List, Optional

import dspy
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from config import settings
from utils.io.logger import logger


class MCPManager:
    """
    Manages connections to MCP servers via stdio and provides synchronous
    wrappers around the tools so they can be consumed by DSPy agents.
    
    Since DSPy expects synchronous tools, we run an asyncio event loop
    in a background thread to handle the async MCP client operations.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MCPManager, cls).__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self._servers: Dict[str, dict] = {}
        self._tools: Dict[str, dspy.Tool] = {}
        
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _run_sync(self, coro):
        """Runs an async coroutine synchronously on the background event loop."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    async def _connect_to_server(self, name: str, command: list[str]):
        """Async method to initialize a stdio client connection to a server."""
        try:
            # We must hold references to the context managers to keep them alive
            server_params = StdioServerParameters(
                command=command[0],
                args=command[1:]
            )
            
            # Since fastmcp stdio runs over stdin/stdout, we must be careful with logging
            # But here we are the client.
            stdio_ctx = stdio_client(server_params)
            read, write = await stdio_ctx.__aenter__()
            
            session = ClientSession(read, write)
            await session.__aenter__()
            await session.initialize()
            
            # Discover tools
            response = await session.list_tools()
            
            self._servers[name] = {
                "session": session,
                "stdio_ctx": stdio_ctx,
                "tools": response.tools
            }
            logger.debug(f"Successfully connected to MCP Server: {name} ({len(response.tools)} tools)")
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server '{name}': {e}")
            raise

    def connect_all(self):
        """Discovers and connects to all configured MCP servers."""
        for name, command in settings.mcp_servers.items():
            if name not in self._servers:
                self._run_sync(self._connect_to_server(name, command))

    def get_tool(self, tool_name: str) -> Optional[dspy.Tool]:
        """
        Retrieves a DSPy Tool wrapper for a given MCP tool name across all servers.
        Returns None if tool is not found.
        """
        if tool_name in self._tools:
            return self._tools[tool_name]
        
        for server_name, server_data in self._servers.items():
            for mcp_tool in server_data["tools"]:
                if mcp_tool.name == tool_name:
                    wrapper = self._create_sync_tool_wrapper(server_name, mcp_tool)
                    self._tools[tool_name] = wrapper
                    return wrapper
        return None

    def get_all_tools(self) -> List[dspy.Tool]:
        """Returns all discovered tools wrapped as DSPy tools."""
        all_tools = []
        for server_name, server_data in self._servers.items():
            for mcp_tool in server_data["tools"]:
                tool = self.get_tool(mcp_tool.name)
                if tool:
                    all_tools.append(tool)
        return all_tools

    def _create_sync_tool_wrapper(self, server_name: str, mcp_tool: Any) -> dspy.Tool:
        """
        Creates a synchronous Python function that correctly maps arguments
        and calls the MCP tool over the background event loop, then wraps it in dspy.Tool.
        """
        # Dynamic function generation using exec to preserve signature, 
        # or simplified *args, **kwargs approach with docstring.
        # DSPy relies heavily on signatures for prompt generation.
        
        def wrapper(*args, **kwargs):
            # For simplicity, we assume named arguments are used or we can map them.
            # In a robust implementation, we would inspect the mcp_tool schema 
            # and map *args to **kwargs cleanly. FastMCP/MCP tools take named arguments.
            
            # Convert args to kwargs if needed (simplified assumption: caller uses kwargs)
            if args:
                logger.warning(f"MCP tool {mcp_tool.name} was called with positional arguments. This might fail if the names don't match the schema.")
            
            async def _call():
                session: ClientSession = self._servers[server_name]["session"]
                result = await session.call_tool(mcp_tool.name, arguments=kwargs)
                # MCP results are lists of content objects (TextContent, ImageContent)
                # For DSPy, we concatenate text outputs.
                texts = [c.text for c in result.content if hasattr(c, "text")]
                return "\n".join(texts)

            try:
                return self._run_sync(_call())
            except Exception as e:
                return f"Error executing tool {mcp_tool.name}: {str(e)}"

        # Set metadata for DSPy to read
        wrapper.__name__ = mcp_tool.name
        wrapper.__doc__ = mcp_tool.description or "No description provided."
        
        return dspy.Tool(wrapper)

    def close(self):
        """Closes all connections."""
        async def _close():
            for name, data in self._servers.items():
                try:
                    await data["session"].__aexit__(None, None, None)
                    await data["stdio_ctx"].__aexit__(None, None, None)
                except Exception as e:
                    logger.debug(f"Error closing MCP server {name}: {e}")
        
        self._run_sync(_close())
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=2.0)
