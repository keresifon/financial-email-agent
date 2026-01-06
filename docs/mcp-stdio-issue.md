# MCP stdio_client Transport Issue

## Summary

The MCP SDK's `stdio_client` transport has a critical bug that prevents it from working on both Windows and Linux platforms. This issue blocks the MCP integration feature branch from being merged.

## Issue Details

### Error
```
RuntimeError: Attempted to exit cancel scope in a different task than it was entered in
```

### Root Cause
The MCP SDK's stdio transport (`mcp.client.stdio.stdio_client`) has an asyncio task management bug where cancel scopes are entered and exited in different tasks, causing the runtime error.

### Platforms Affected
- ✗ Windows 10/11
- ✗ Linux (Ubuntu 22.04 via WSL)

Both platforms exhibit the same hanging behavior and error when interrupted.

## Testing Performed

### Test 1: Direct Server Import (✓ WORKS)
```python
# test_simple_mcp.py - Direct import test
from mcp_servers.gmail import GmailMCPServer
server = GmailMCPServer()
tools = server.list_tools()  # ✓ Works perfectly
```

**Result**: All MCP servers work correctly when imported directly.

### Test 2: stdio_client Transport (✗ FAILS)
```python
# test_mcp_integration.py - Subprocess transport test
async with stdio_client(command, args) as (read, write):
    async with ClientSession(read, write) as session:
        # Hangs here, never completes
```

**Result**: Connection hangs indefinitely on both Windows and Linux.

## Implementation Status

### Completed Work (feature/mcp-integration branch)
1. ✅ MCP Client Infrastructure (`src/mcp/client.py`, `src/mcp/manager.py`)
2. ✅ Three MCP Servers (gmail, document, database)
3. ✅ Async workflow in `src/main.py`
4. ✅ Configuration system with `mcp.enabled` flag
5. ✅ All MCP-based methods implemented
6. ✅ Test scripts created

### Blocked
- Cannot use subprocess-based MCP transport due to SDK bug
- Feature branch cannot be merged until issue is resolved

## Current Solution

The **main branch** already has working direct server access without MCP transport. Since the MCP stdio transport is broken, we should:

1. **Keep main branch as-is** - Direct service calls work perfectly
2. **Park feature/mcp-integration branch** - Wait for MCP SDK fix
3. **Monitor MCP SDK** - Check for updates that fix the stdio transport issue

## Alternative Approaches (Future)

If MCP SDK is fixed, we can:

### Option 1: Direct In-Process Access
Import MCP servers directly without subprocess spawning:
```python
from mcp_servers.gmail import GmailMCPServer
server = GmailMCPServer()
result = await server.call_tool("fetch_emails", {...})
```

**Pros**: Works now, no transport issues
**Cons**: Defeats purpose of MCP (process isolation)

### Option 2: HTTP Transport
Use HTTP instead of stdio for MCP communication:
```python
# Requires MCP servers to expose HTTP endpoints
async with http_client("http://localhost:8001") as client:
    result = await client.call_tool(...)
```

**Pros**: More reliable than stdio
**Cons**: Requires server HTTP implementation

### Option 3: Wait for SDK Fix
Monitor MCP SDK repository for stdio transport fixes.

## Recommendation

**Park the MCP integration work** and continue using the working direct service implementation in main branch. The MCP architecture is sound, but the SDK transport layer is not production-ready.

## References

- Feature Branch: `feature/mcp-integration`
- Last Commit: `a74b14b` - "Add MCP integration test scripts for Linux/WSL testing"
- Test Files: `test_mcp_integration.py`, `test_simple_mcp.py`
- MCP SDK: https://github.com/modelcontextprotocol/python-sdk

## Date
2026-01-06