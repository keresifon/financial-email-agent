# MCP Integration Plan

## Overview

This document outlines the plan to refactor the Financial Email Agent from a monolithic architecture to a modular MCP (Model Context Protocol) architecture.

## Current State

**Architecture:** Monolithic with direct service integration
- `src/main.py` directly imports and uses all services
- Tight coupling between components
- All operations synchronous
- Working and tested implementation

**Available MCP Servers:**
- `mcp_servers/gmail.py` - Gmail API operations
- `mcp_servers/database.py` - MongoDB operations
- `mcp_servers/document.py` - Document processing

## Target State

**Architecture:** MCP-based modular architecture
- `src/main.py` acts as MCP client
- Communicates with MCP servers via stdio
- Loose coupling between components
- Async operations
- Each server runs independently

## Integration Phases

### Phase 1: MCP Client Setup (Week 1)

**Goal:** Create MCP client infrastructure in main application

**Tasks:**
1. Create `src/mcp/client.py` - MCP client wrapper
2. Add MCP client initialization in `src/main.py`
3. Implement connection management for multiple servers
4. Add error handling and retry logic
5. Create configuration for MCP server endpoints

**Files to Create:**
- `src/mcp/__init__.py`
- `src/mcp/client.py`
- `src/mcp/manager.py` - Manages multiple MCP server connections

**Files to Modify:**
- `src/main.py` - Add MCP client initialization
- `src/config/models.py` - Add MCP configuration models

**Deliverables:**
- Working MCP client that can connect to servers
- Configuration system for MCP servers
- Basic error handling

### Phase 2: Gmail MCP Integration (Week 2)

**Goal:** Replace direct Gmail API calls with MCP server calls

**Current Implementation:**
```python
# src/main.py
from src.email.service import EmailService
email_service = EmailService(config)
emails = email_service.get_financial_emails(days_back=7)
```

**Target Implementation:**
```python
# src/main.py
from src.mcp.client import MCPClient
gmail_client = MCPClient("gmail-server")
result = await gmail_client.call_tool("fetch_emails", {
    "query": "after:2026-01-01 label:Shopping",
    "max_results": 50
})
emails = json.loads(result[0].text)
```

**Tasks:**
1. Update `src/main.py` to use Gmail MCP server
2. Replace `EmailService` calls with MCP tool calls
3. Handle async operations
4. Update attachment downloading to use MCP
5. Test email fetching via MCP

**Files to Modify:**
- `src/main.py` - Replace EmailService with MCP calls
- `mcp_servers/gmail.py` - Ensure all needed tools are available

**Deliverables:**
- Email fetching via MCP working
- Attachment downloading via MCP working
- Email marking (read/unread) via MCP working

### Phase 3: Database MCP Integration (Week 3)

**Goal:** Replace direct MongoDB calls with MCP server calls

**Current Implementation:**
```python
# src/main.py
from src.database.connection import MongoDBConnection
db_connection = MongoDBConnection(config.mongodb)
db = db_connection.get_database()
collection = db["emails"]
collection.insert_one(email_data)
```

**Target Implementation:**
```python
# src/main.py
db_client = MCPClient("database-server")
result = await db_client.call_tool("save_document", {
    "collection": "emails",
    "document": email_data
})
```

**Tasks:**
1. Update `src/main.py` to use Database MCP server
2. Replace all MongoDB operations with MCP tool calls
3. Update queries and searches to use MCP
4. Test data storage and retrieval via MCP

**Files to Modify:**
- `src/main.py` - Replace MongoDBConnection with MCP calls
- `mcp_servers/database.py` - Ensure all needed tools are available

**Deliverables:**
- Document saving via MCP working
- Document retrieval via MCP working
- Search and queries via MCP working

### Phase 4: Document Processing MCP Integration (Week 4)

**Goal:** Replace direct document processing with MCP server calls

**Current Implementation:**
```python
# src/main.py
from src.email.attachment_processor import AttachmentProcessor
processor = AttachmentProcessor(gmail_client)
text = processor.extract_text_from_pdf(file_path)
```

**Target Implementation:**
```python
# src/main.py
doc_client = MCPClient("document-server")
result = await doc_client.call_tool("extract_pdf_text", {
    "file_path": file_path
})
text = json.loads(result[0].text)["text"]
```

**Tasks:**
1. Update attachment processing to use Document MCP server
2. Replace PDF extraction with MCP calls
3. Replace OCR processing with MCP calls
4. Test document processing via MCP

**Files to Modify:**
- `src/main.py` - Replace AttachmentProcessor with MCP calls
- `mcp_servers/document.py` - Ensure all needed tools are available

**Deliverables:**
- PDF text extraction via MCP working
- OCR processing via MCP working
- Document analysis via MCP working

### Phase 5: Async Refactoring (Week 5)

**Goal:** Convert main application to fully async

**Tasks:**
1. Convert `FinancialEmailAgent` class to async
2. Update all methods to use `async/await`
3. Implement concurrent processing where beneficial
4. Add async error handling
5. Update scheduler to work with async operations

**Files to Modify:**
- `src/main.py` - Convert to async
- All service files that interact with MCP

**Deliverables:**
- Fully async main application
- Concurrent email processing
- Improved performance

### Phase 6: Testing & Validation (Week 6)

**Goal:** Ensure MCP implementation works correctly

**Tasks:**
1. Create integration tests for MCP architecture
2. Test each MCP server independently
3. Test end-to-end workflow
4. Performance testing and optimization
5. Error handling validation

**Files to Create:**
- `tests/integration/test_mcp_gmail.py`
- `tests/integration/test_mcp_database.py`
- `tests/integration/test_mcp_document.py`
- `tests/integration/test_mcp_workflow.py`

**Deliverables:**
- Comprehensive test suite
- Performance benchmarks
- Error handling validation

### Phase 7: Documentation & Deployment (Week 7)

**Goal:** Document MCP architecture and update deployment

**Tasks:**
1. Update README.md with MCP architecture
2. Create MCP deployment guide
3. Update SETUP_INSTRUCTIONS.md for MCP
4. Create MCP troubleshooting guide
5. Update CHANGELOG.md

**Files to Modify:**
- `README.md`
- `DEPLOYMENT.md`
- `SETUP_INSTRUCTIONS.md`
- `CHANGELOG.md`
- `docs/mcp-architecture.md`

**Deliverables:**
- Complete MCP documentation
- Deployment guide for MCP architecture
- Updated setup instructions

## Technical Considerations

### MCP Server Management

**Option 1: Manual Server Start**
```bash
# Terminal 1
python -m mcp_servers.gmail

# Terminal 2
python -m mcp_servers.database

# Terminal 3
python -m mcp_servers.document

# Terminal 4
python src/main.py
```

**Option 2: Process Manager (Recommended)**
```python
# src/mcp/manager.py
class MCPServerManager:
    def start_servers(self):
        """Start all MCP servers as subprocesses"""
        self.gmail_process = subprocess.Popen([...])
        self.db_process = subprocess.Popen([...])
        self.doc_process = subprocess.Popen([...])
```

### Configuration

Add to `config/config.yaml`:
```yaml
mcp:
  servers:
    gmail:
      command: "python -m mcp_servers.gmail"
      stdio: true
    database:
      command: "python -m mcp_servers.database"
      stdio: true
    document:
      command: "python -m mcp_servers.document"
      stdio: true
```

### Error Handling

- Implement retry logic for MCP tool calls
- Handle server disconnections gracefully
- Add health checks for MCP servers
- Implement fallback to direct calls if MCP fails

### Performance

- Use connection pooling for MCP clients
- Implement caching where appropriate
- Process emails concurrently using asyncio
- Monitor and optimize MCP communication overhead

## Migration Strategy

### Gradual Migration (Recommended)

1. Keep monolithic code intact
2. Add MCP integration alongside existing code
3. Use feature flag to switch between implementations
4. Test MCP thoroughly before removing monolithic code
5. Remove monolithic code once MCP is stable

### Feature Flag Example

```python
# src/config/models.py
class AppConfig:
    use_mcp: bool = False  # Feature flag

# src/main.py
if config.use_mcp:
    # Use MCP implementation
    emails = await mcp_client.fetch_emails()
else:
    # Use monolithic implementation
    emails = email_service.get_financial_emails()
```

## Rollback Plan

If MCP integration causes issues:

1. Switch feature flag: `use_mcp = False`
2. Revert to main branch: `git checkout main`
3. Keep MCP branch for future work
4. Document issues encountered
5. Plan fixes before next attempt

## Success Criteria

- [ ] All MCP servers running independently
- [ ] Main application communicates via MCP
- [ ] All tests passing
- [ ] Performance equal or better than monolithic
- [ ] Error handling robust
- [ ] Documentation complete
- [ ] Deployment guide updated

## Timeline

- **Week 1:** MCP Client Setup
- **Week 2:** Gmail MCP Integration
- **Week 3:** Database MCP Integration
- **Week 4:** Document Processing MCP Integration
- **Week 5:** Async Refactoring
- **Week 6:** Testing & Validation
- **Week 7:** Documentation & Deployment

**Total Duration:** 7 weeks

## Next Steps

1. Review this plan
2. Set up development environment for MCP work
3. Start Phase 1: MCP Client Setup
4. Create feature branch: `feature/mcp-integration` ✅ (Done)
5. Begin implementation

---

**Status:** Planning Complete - Ready for Implementation
**Branch:** feature/mcp-integration
**Last Updated:** 2026-01-02