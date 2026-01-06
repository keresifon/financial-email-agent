"""
Simple MCP Server Test

Test if we can run an MCP server directly without subprocess.
"""

import asyncio
import sys

# Test 1: Can we import the Gmail server?
print("Test 1: Importing Gmail MCP server...")
try:
    import mcp_servers.gmail as gmail_server
    print("[OK] Gmail server imported")
except Exception as e:
    print(f"[FAIL] Import failed: {e}")
    sys.exit(1)

# Test 2: Can we access the server app?
print("\nTest 2: Accessing server app...")
try:
    app = gmail_server.app
    print(f"[OK] Server app accessed: {app}")
except Exception as e:
    print(f"[FAIL] App access failed: {e}")
    sys.exit(1)

# Test 3: Can we list tools?
print("\nTest 3: Listing tools...")
async def test_list_tools():
    try:
        # Get the list_tools handler
        tools = await gmail_server.list_tools()
        print(f"[OK] Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description[:50]}...")
        return True
    except Exception as e:
        print(f"[FAIL] List tools failed: {e}")
        import traceback
        traceback.print_exc()
        return False

# Run the async test
result = asyncio.run(test_list_tools())

if result:
    print("\n[SUCCESS] Gmail MCP server is functional!")
    print("\nThe issue is likely with subprocess spawning in MCPClient.")
    print("Recommendation: Check MCPClient.connect() method for stdio communication issues.")
else:
    print("\n[FAIL] Gmail MCP server has issues")

sys.exit(0 if result else 1)

# Made with Bob
