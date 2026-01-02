"""
MCP Server Manager

Manages multiple MCP server connections and provides a unified interface
for interacting with all servers.
"""

import asyncio
from typing import Any, Dict, List, Optional
from pathlib import Path

from src.mcp.client import MCPClient
from src.config.models import AppConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MCPServerManager:
    """
    Manages multiple MCP server connections.
    
    This manager handles the lifecycle of multiple MCP servers and provides
    a unified interface for tool calls across all servers.
    """
    
    def __init__(self, config: AppConfig):
        """
        Initialize MCP Server Manager.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.clients: Dict[str, MCPClient] = {}
        self._initialized = False
        
        logger.info("Initialized MCP Server Manager")
    
    async def initialize(self):
        """Initialize all MCP server connections."""
        if self._initialized:
            logger.warning("MCP Server Manager already initialized")
            return
        
        try:
            logger.info("Initializing MCP servers...")
            
            # Initialize Gmail MCP server
            gmail_client = MCPClient(
                "gmail",
                "python",
                ["-m", "mcp_servers.gmail"]
            )
            await gmail_client.connect()
            self.clients["gmail"] = gmail_client
            logger.info("Gmail MCP server initialized")
            
            # Initialize Database MCP server
            db_client = MCPClient(
                "database",
                "python",
                ["-m", "mcp_servers.database"]
            )
            await db_client.connect()
            self.clients["database"] = db_client
            logger.info("Database MCP server initialized")
            
            # Initialize Document MCP server
            doc_client = MCPClient(
                "document",
                "python",
                ["-m", "mcp_servers.document"]
            )
            await doc_client.connect()
            self.clients["document"] = doc_client
            logger.info("Document MCP server initialized")
            
            self._initialized = True
            logger.info(f"All {len(self.clients)} MCP servers initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP servers: {e}")
            await self.shutdown()
            raise
    
    async def shutdown(self):
        """Shutdown all MCP server connections."""
        logger.info("Shutting down MCP servers...")
        
        for name, client in self.clients.items():
            try:
                await client.disconnect()
                logger.info(f"Disconnected from {name} server")
            except Exception as e:
                logger.error(f"Error disconnecting from {name}: {e}")
        
        self.clients.clear()
        self._initialized = False
        logger.info("All MCP servers shut down")
    
    def get_client(self, server_name: str) -> Optional[MCPClient]:
        """
        Get MCP client for a specific server.
        
        Args:
            server_name: Name of the server (gmail, database, document)
            
        Returns:
            MCPClient instance or None if not found
        """
        return self.clients.get(server_name)
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict) -> Any:
        """
        Call a tool on a specific MCP server.
        
        Args:
            server_name: Name of the server
            tool_name: Name of the tool
            arguments: Tool arguments
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If server not found
            RuntimeError: If server not connected
        """
        client = self.get_client(server_name)
        if not client:
            raise ValueError(f"MCP server not found: {server_name}")
        
        if not client.is_connected:
            raise RuntimeError(f"MCP server not connected: {server_name}")
        
        return await client.call_tool(tool_name, arguments)
    
    async def list_all_tools(self) -> Dict[str, List[Dict]]:
        """
        List all available tools from all servers.
        
        Returns:
            Dictionary mapping server names to their tool lists
        """
        all_tools = {}
        
        for name, client in self.clients.items():
            try:
                tools = await client.list_tools()
                all_tools[name] = tools
            except Exception as e:
                logger.error(f"Error listing tools from {name}: {e}")
                all_tools[name] = []
        
        return all_tools
    
    @property
    def is_initialized(self) -> bool:
        """Check if manager is initialized."""
        return self._initialized
    
    @property
    def connected_servers(self) -> List[str]:
        """Get list of connected server names."""
        return [
            name for name, client in self.clients.items()
            if client.is_connected
        ]
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()


async def test_mcp_manager():
    """Test function for MCP Server Manager."""
    from src.config.loader import load_config
    
    config = load_config()
    
    async with MCPServerManager(config) as manager:
        print(f"Connected servers: {manager.connected_servers}")
        
        # List all tools
        all_tools = await manager.list_all_tools()
        for server, tools in all_tools.items():
            print(f"\n{server} tools:")
            for tool in tools:
                print(f"  - {tool['name']}: {tool['description']}")
        
        # Test Gmail tool
        print("\nTesting Gmail fetch_emails tool...")
        result = await manager.call_tool("gmail", "fetch_emails", {
            "query": "is:unread",
            "max_results": 5
        })
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(test_mcp_manager())

# Made with Bob
