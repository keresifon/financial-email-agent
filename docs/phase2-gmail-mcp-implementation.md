# Phase 2: Gmail MCP Integration - Implementation Guide

## Overview

This document provides detailed implementation steps for Phase 2 of the MCP integration, which focuses on replacing direct Gmail API calls with MCP server communication.

## Current Status

### ✅ Completed
- Phase 1: MCP Client Infrastructure
- MCP configuration models added to `src/config/models.py`
- Feature flag (`mcp.enabled`) ready for gradual migration

### ⏳ In Progress
- Phase 2: Gmail MCP Integration

## Implementation Steps

### Step 1: Update Main Application to Support MCP

#### 1.1 Modify `src/main.py` - Add MCP Manager

**Location:** `src/main.py` lines 39-73

**Current Code:**
```python
def __init__(self, config: AppConfig):
    self.config = config
    logger.info("Initializing Financial Email Agent")
    
    # Database
    self.db_connection = MongoDBConnection(config.mongodb)
    self.db_connection.connect()
    self.db = self.db_connection.get_database()
    
    # LLM Client
    self.llm_client = LLMClient(config=config.llama)
    
    # Email Service
    self.email_service = EmailService(config)
    
    # Attachment Processor
    self.attachment_processor = AttachmentProcessor(
        gmail_client=self.email_service.gmail_client
    )
    
    # Classifier
    self.classifier = EmailClassifier(self.llm_client, config)
    
    # Data Extractor
    self.extractor = DataExtractor(self.llm_client, config)
    
    logger.info("Financial Email Agent initialized successfully")
```

**Target Code:**
```python
def __init__(self, config: AppConfig):
    self.config = config
    self.use_mcp = config.mcp.enabled
    self.mcp_manager = None
    
    logger.info(f"Initializing Financial Email Agent (MCP: {self.use_mcp})")
    
    # Database
    self.db_connection = MongoDBConnection(config.mongodb)
    self.db_connection.connect()
    self.db = self.db_connection.get_database()
    
    # LLM Client
    self.llm_client = LLMClient(config=config.llama)
    
    # Email Service (only if not using MCP)
    if not self.use_mcp:
        self.email_service = EmailService(config)
        self.attachment_processor = AttachmentProcessor(
            gmail_client=self.email_service.gmail_client
        )
    
    # Classifier
    self.classifier = EmailClassifier(self.llm_client, config)
    
    # Data Extractor
    self.extractor = DataExtractor(self.llm_client, config)
    
    logger.info("Financial Email Agent initialized successfully")

async def initialize_mcp(self):
    """Initialize MCP manager (async)."""
    if self.use_mcp:
        from src.mcp.manager import MCPServerManager
        self.mcp_manager = MCPServerManager(self.config)
        await self.mcp_manager.initialize()
        logger.info("MCP Manager initialized")

async def shutdown_mcp(self):
    """Shutdown MCP manager."""
    if self.mcp_manager:
        await self.mcp_manager.shutdown()
        logger.info("MCP Manager shut down")
```

#### 1.2 Convert `run()` Method to Async

**Location:** `src/main.py` - main run method

**Current:**
```python
def run(self, days_back: int = 7):
    """Run the email processing pipeline."""
    # ... synchronous code
```

**Target:**
```python
async def run(self, days_back: int = 7):
    """Run the email processing pipeline."""
    try:
        # Initialize MCP if enabled
        if self.use_mcp:
            await self.initialize_mcp()
        
        # Fetch emails
        if self.use_mcp:
            emails = await self._fetch_emails_mcp(days_back)
        else:
            emails = self._fetch_emails_direct(days_back)
        
        # Process emails
        for email in emails:
            if self.use_mcp:
                await self._process_email_mcp(email)
            else:
                self._process_email_direct(email)
    
    finally:
        # Cleanup
        if self.use_mcp:
            await self.shutdown_mcp()
```

### Step 2: Implement MCP Email Fetching

#### 2.1 Create `_fetch_emails_mcp()` Method

```python
async def _fetch_emails_mcp(self, days_back: int = 7) -> List[Dict]:
    """
    Fetch emails using MCP Gmail server.
    
    Args:
        days_back: Number of days to look back
        
    Returns:
        List of email dictionaries
    """
    from datetime import datetime, timedelta
    import json
    
    # Calculate date
    date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")
    
    # Build query
    query = f"after:{date_from} label:Shopping"
    
    logger.info(f"Fetching emails via MCP with query: {query}")
    
    # Call MCP tool
    result = await self.mcp_manager.call_tool("gmail", "fetch_emails", {
        "query": query,
        "max_results": self.config.email.monitoring.max_emails_per_check,
        "include_body": True
    })
    
    # Parse result
    emails = json.loads(result[0].text)
    logger.info(f"Fetched {len(emails)} emails via MCP")
    
    return emails
```

#### 2.2 Keep Direct Method for Fallback

```python
def _fetch_emails_direct(self, days_back: int = 7) -> List[Dict]:
    """
    Fetch emails using direct EmailService (fallback).
    
    Args:
        days_back: Number of days to look back
        
    Returns:
        List of email dictionaries
    """
    logger.info(f"Fetching emails directly (non-MCP)")
    emails = self.email_service.get_financial_emails(days_back=days_back)
    logger.info(f"Fetched {len(emails)} emails directly")
    return emails
```

### Step 3: Implement MCP Attachment Processing

#### 3.1 Create `_process_attachments_mcp()` Method

```python
async def _process_attachments_mcp(self, email_id: str, attachments: List[Dict]) -> List[Dict]:
    """
    Process attachments using MCP servers.
    
    Args:
        email_id: Email ID
        attachments: List of attachment metadata
        
    Returns:
        List of processed attachments with extracted text
    """
    import json
    import tempfile
    from pathlib import Path
    
    processed = []
    
    for attachment in attachments:
        try:
            attachment_id = attachment.get("attachmentId")
            filename = attachment.get("filename", "unknown")
            mime_type = attachment.get("mimeType", "")
            
            logger.info(f"Processing attachment: {filename}")
            
            # Download attachment via MCP
            with tempfile.TemporaryDirectory() as temp_dir:
                result = await self.mcp_manager.call_tool("gmail", "get_attachment", {
                    "message_id": email_id,
                    "attachment_id": attachment_id,
                    "save_path": temp_dir
                })
                
                download_info = json.loads(result[0].text)
                file_path = download_info["file_path"]
                
                # Extract text based on type
                text = ""
                if mime_type == "application/pdf":
                    # Extract PDF text via MCP
                    result = await self.mcp_manager.call_tool("document", "extract_pdf_text", {
                        "file_path": file_path
                    })
                    extract_info = json.loads(result[0].text)
                    text = extract_info.get("text", "")
                
                elif mime_type.startswith("image/"):
                    # Extract image text via OCR using MCP
                    result = await self.mcp_manager.call_tool("document", "extract_image_text", {
                        "file_path": file_path,
                        "language": "eng"
                    })
                    extract_info = json.loads(result[0].text)
                    text = extract_info.get("text", "")
                
                processed.append({
                    "filename": filename,
                    "mime_type": mime_type,
                    "text": text,
                    "text_extracted": len(text) > 0
                })
                
                logger.info(f"Extracted {len(text)} characters from {filename}")
        
        except Exception as e:
            logger.error(f"Error processing attachment {filename}: {e}")
            processed.append({
                "filename": filename,
                "mime_type": mime_type,
                "text": "",
                "text_extracted": False,
                "error": str(e)
            })
    
    return processed
```

### Step 4: Update Main Entry Point

#### 4.1 Modify `main()` Function

**Location:** Bottom of `src/main.py`

**Current:**
```python
def main():
    """Main entry point."""
    setup_logger()
    logger.info("Starting Financial Email Agent")
    
    try:
        config = load_config()
        agent = FinancialEmailAgent(config)
        agent.run(days_back=7)
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**Target:**
```python
async def async_main():
    """Async main entry point."""
    setup_logger()
    logger.info("Starting Financial Email Agent")
    
    try:
        config = load_config()
        agent = FinancialEmailAgent(config)
        await agent.run(days_back=7)
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

def main():
    """Main entry point."""
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
```

### Step 5: Testing

#### 5.1 Test with MCP Disabled (Default)

```bash
# Ensure mcp.enabled = false in config
python src/main.py
```

Should work exactly as before (monolithic).

#### 5.2 Test with MCP Enabled

```yaml
# config/config.yaml
mcp:
  enabled: true
```

```bash
python src/main.py
```

Should use MCP servers for Gmail operations.

#### 5.3 Test MCP Servers Independently

```bash
# Terminal 1: Start Gmail MCP server
python -m mcp_servers.gmail

# Terminal 2: Test client
python -c "
import asyncio
from src.mcp.client import MCPClient

async def test():
    async with MCPClient('gmail', 'python', ['-m', 'mcp_servers.gmail']) as client:
        tools = await client.list_tools()
        print(f'Tools: {[t[\"name\"] for t in tools]}')

asyncio.run(test())
"
```

## Implementation Checklist

- [ ] Add MCP configuration to `src/config/models.py` ✅
- [ ] Update `FinancialEmailAgent.__init__()` with MCP support
- [ ] Add `initialize_mcp()` and `shutdown_mcp()` methods
- [ ] Convert `run()` method to async
- [ ] Implement `_fetch_emails_mcp()` method
- [ ] Implement `_process_attachments_mcp()` method
- [ ] Keep direct methods as fallback
- [ ] Update main entry point to use `asyncio.run()`
- [ ] Test with MCP disabled (regression test)
- [ ] Test with MCP enabled
- [ ] Test individual MCP servers
- [ ] Update documentation
- [ ] Commit Phase 2 changes

## Estimated Time

- Implementation: 4-6 hours
- Testing: 2-3 hours
- Documentation: 1 hour
- **Total: 7-10 hours (1 week as per plan)**

## Next Phase

After Phase 2 is complete and tested:
- **Phase 3**: Database MCP Integration
- Replace `MongoDBConnection` with MCP database server calls
- Similar pattern to Gmail integration

## Notes

- Feature flag allows gradual rollout
- Fallback to direct methods if MCP fails
- All MCP operations are async
- Proper error handling throughout
- Logging at each step for debugging

---

**Status:** Phase 2 - In Progress
**Last Updated:** 2026-01-02