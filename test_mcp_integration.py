"""
Test script for MCP Integration

This script tests the MCP integration in stages:
1. Test MCP server imports
2. Test MCP client connection
3. Test individual MCP servers
4. Test full workflow
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.loader import load_config
from src.mcp.client import MCPClient
from src.mcp.manager import MCPServerManager
from src.utils.logger import setup_logger, get_logger

logger = get_logger(__name__)


async def test_mcp_imports():
    """Test 1: Verify all MCP imports work."""
    print("\n" + "="*60)
    print("TEST 1: MCP Imports")
    print("="*60)
    
    try:
        from src.mcp.client import MCPClient
        from src.mcp.manager import MCPServerManager
        print("[OK] MCP client imports successful")
        
        import mcp_servers.gmail
        print("[OK] Gmail MCP server import successful")
        
        import mcp_servers.document
        print("[OK] Document MCP server import successful")
        
        import mcp_servers.database
        print("[OK] Database MCP server import successful")
        
        return True
    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        return False


async def test_config_loading():
    """Test 2: Verify configuration loads correctly."""
    print("\n" + "="*60)
    print("TEST 2: Configuration Loading")
    print("="*60)
    
    try:
        config = load_config()
        print(f"[OK] Configuration loaded")
        print(f"   - MCP enabled: {config.mcp.enabled}")
        print(f"   - Environment: {config.environment}")
        print(f"   - Database: {config.mongodb.database}")
        print(f"   - LLM model: {config.llama.model}")
        
        if not config.mcp.enabled:
            print("[WARN] WARNING: MCP is not enabled in config!")
            return False
        
        return True
    except Exception as e:
        print(f"[FAIL] Config loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_mcp_manager_init():
    """Test 3: Test MCP Manager initialization."""
    print("\n" + "="*60)
    print("TEST 3: MCP Manager Initialization")
    print("="*60)
    
    try:
        config = load_config()
        manager = MCPServerManager(config)
        print("[OK] MCP Manager created")
        
        print("   Attempting to initialize MCP servers...")
        await manager.initialize()
        print("[OK] MCP Manager initialized")
        
        connected = manager.connected_servers
        print(f"   Connected servers: {connected}")
        
        if len(connected) != 3:
            print(f"[WARN] WARNING: Expected 3 servers, got {len(connected)}")
        
        # List tools from each server
        print("\n   Listing available tools:")
        all_tools = await manager.list_all_tools()
        for server_name, tools in all_tools.items():
            print(f"   - {server_name}: {len(tools)} tools")
            for tool in tools[:3]:  # Show first 3 tools
                print(f"     • {tool['name']}")
        
        await manager.shutdown()
        print("[OK] MCP Manager shut down")
        
        return True
    except Exception as e:
        print(f"[FAIL] MCP Manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_gmail_mcp():
    """Test 4: Test Gmail MCP server specifically."""
    print("\n" + "="*60)
    print("TEST 4: Gmail MCP Server")
    print("="*60)
    
    try:
        config = load_config()
        manager = MCPServerManager(config)
        await manager.initialize()
        
        print("   Testing Gmail MCP tools...")
        
        # Test list tools
        gmail_client = manager.get_client("gmail")
        if gmail_client:
            tools = await gmail_client.list_tools()
            print(f"[OK] Gmail server has {len(tools)} tools")
            for tool in tools:
                print(f"   - {tool['name']}: {tool['description'][:50]}...")
        else:
            print("[FAIL] Gmail client not found")
            return False
        
        await manager.shutdown()
        return True
    except Exception as e:
        print(f"[FAIL] Gmail MCP test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_document_mcp():
    """Test 5: Test Document MCP server."""
    print("\n" + "="*60)
    print("TEST 5: Document MCP Server")
    print("="*60)
    
    try:
        config = load_config()
        manager = MCPServerManager(config)
        await manager.initialize()
        
        print("   Testing Document MCP tools...")
        
        doc_client = manager.get_client("document")
        if doc_client:
            tools = await doc_client.list_tools()
            print(f"[OK] Document server has {len(tools)} tools")
            for tool in tools:
                print(f"   - {tool['name']}: {tool['description'][:50]}...")
        else:
            print("[FAIL] Document client not found")
            return False
        
        await manager.shutdown()
        return True
    except Exception as e:
        print(f"[FAIL] Document MCP test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_database_mcp():
    """Test 6: Test Database MCP server."""
    print("\n" + "="*60)
    print("TEST 6: Database MCP Server")
    print("="*60)
    
    try:
        config = load_config()
        manager = MCPServerManager(config)
        await manager.initialize()
        
        print("   Testing Database MCP tools...")
        
        db_client = manager.get_client("database")
        if db_client:
            tools = await db_client.list_tools()
            print(f"[OK] Database server has {len(tools)} tools")
            for tool in tools:
                print(f"   - {tool['name']}: {tool['description'][:50]}...")
        else:
            print("[FAIL] Database client not found")
            return False
        
        await manager.shutdown()
        return True
    except Exception as e:
        print(f"[FAIL] Database MCP test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("MCP INTEGRATION TEST SUITE")
    print("="*60)
    
    # Setup logging
    config = load_config()
    setup_logger(config.logging)
    
    results = []
    
    # Run tests
    results.append(("Imports", await test_mcp_imports()))
    results.append(("Configuration", await test_config_loading()))
    results.append(("MCP Manager", await test_mcp_manager_init()))
    results.append(("Gmail MCP", await test_gmail_mcp()))
    results.append(("Document MCP", await test_document_mcp()))
    results.append(("Database MCP", await test_database_mcp()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed! MCP integration is working correctly.")
        return 0
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

# Made with Bob
