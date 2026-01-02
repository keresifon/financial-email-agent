"""
MCP Client

Provides a client interface for communicating with MCP servers via stdio.
"""

import asyncio
import json
import subprocess
from typing import Any, Dict, List, Optional
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.utils.logger import get_logger

logger = get_logger(__name__)


class MCPClient:
    """
    Client for communicating with an MCP server.
    
    This client manages the connection to a single MCP server and provides
    methods for calling tools and managing the connection lifecycle.
    """
    
    def __init__(self, server_name: str, command: str, args: Optional[List[str]] = None):
        """
        Initialize MCP client.
        
        Args:
            server_name: Name of the MCP server (e.g., "gmail", "database")
            command: Command to start the server (e.g., "python")
            args: Arguments for the command (e.g., ["-m", "mcp_servers.gmail"])
        """
        self.server_name = server_name
        self.command = command
        self.args = args or []
        self.session: Optional[ClientSession] = None
        self.read_stream = None
        self.write_stream = None
        self._connected = False
        
        logger.info(f"Initialized MCP client for server: {server_name}")
    
    async def connect(self) -> bool:
        """
        Connect to the MCP server.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to MCP server: {self.server_name}")
            
            # Create server parameters
            server_params = StdioServerParameters(
                command=self.command,
                args=self.args,
                env=None
            )
            
            # Connect to server using context manager
            stdio_transport = stdio_client(server_params)
            self.read_stream, self.write_stream = await stdio_transport.__aenter__()
            
            # Initialize session
            self.session = ClientSession(self.read_stream, self.write_stream)
            
            # Initialize the session
            await self.session.initialize()
            
            self._connected = True
            logger.info(f"Successfully connected to MCP server: {self.server_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {self.server_name}: {e}")
            self._connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self.session:
            try:
                # ClientSession doesn't have close(), just cleanup
                self.session = None
                self._connected = False
                logger.info(f"Disconnected from MCP server: {self.server_name}")
            except Exception as e:
                logger.error(f"Error disconnecting from {self.server_name}: {e}")
                self.session = None
                self._connected = False
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Tool execution result
            
        Raises:
            RuntimeError: If not connected to server
            Exception: If tool execution fails
        """
        if not self._connected or not self.session:
            raise RuntimeError(f"Not connected to MCP server: {self.server_name}")
        
        try:
            logger.debug(f"Calling tool '{tool_name}' on {self.server_name} with args: {arguments}")
            
            # Call the tool
            result = await self.session.call_tool(tool_name, arguments)
            
            logger.debug(f"Tool '{tool_name}' executed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error calling tool '{tool_name}' on {self.server_name}: {e}")
            raise
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools on the MCP server.
        
        Returns:
            List of tool definitions
        """
        if not self._connected or not self.session:
            raise RuntimeError(f"Not connected to MCP server: {self.server_name}")
        
        try:
            tools = await self.session.list_tools()
            logger.info(f"Listed {len(tools.tools)} tools from {self.server_name}")
            return [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                }
                for tool in tools.tools
            ]
        except Exception as e:
            logger.error(f"Error listing tools from {self.server_name}: {e}")
            raise
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected to server."""
        return self._connected
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


async def test_mcp_client():
    """Test function for MCP client."""
    # Test Gmail MCP server
    async with MCPClient(
        "gmail",
        "python",
        ["-m", "mcp_servers.gmail"]
    ) as client:
        # List available tools
        tools = await client.list_tools()
        print(f"Available tools: {[t['name'] for t in tools]}")
        
        # Test fetch_emails tool
        result = await client.call_tool("fetch_emails", {
            "query": "is:unread",
            "max_results": 5
        })
        print(f"Fetch emails result: {result}")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_mcp_client())

# Made with Bob
