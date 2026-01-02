# Changelog

## [Unreleased] - 2026-01-02

### Added
- **Attachment Processing**: Full support for extracting text from PDF and image attachments
  - New `AttachmentProcessor` class in `src/email/attachment_processor.py`
  - Supports PDF (PyPDF2) and image files (Tesseract OCR)
  - Automatic temp file cleanup
  - Combined text from attachments with email body for better classification

- **Shopping Label Filter**: Email processing now limited to emails with "Shopping" label
  - Updated `get_financial_emails()` to use `label:Shopping` query
  - Eliminates promotional/marketing noise
  - Focuses on actual purchase-related financial documents

- **Clean Financial Data Storage**: Separate collection for extracted financial data
  - Category-specific fields only (no full email content)
  - Easier querying and reporting
  - Fields mapped per category:
    - Invoice: invoice_number, vendor, amount, currency, due_date, issue_date
    - Receipt: merchant, amount, currency, date, items
    - Statement: account_number, period, balance, transactions
    - Payment: amount, currency, date, recipient, reference

### Changed
- **Improved Classification Prompt**: Better handling of non-financial emails
  - Added explicit rules for distinguishing financial vs marketing emails
  - Updated category descriptions for clarity
  - Added "other" category for non-financial content
  - Better examples in prompt

- **Fixed Deprecation Warnings**: Replaced `datetime.utcnow()` with `datetime.now(timezone.utc)`
  - Updated all datetime calls throughout `src/main.py`
  - Added `timezone` import

- **Removed Debug Logging**: Cleaned up verbose attachment detection logging
  - Removed line that logged all attachment filenames
  - Kept essential processing logs only

### Architecture Notes

**Current Implementation:** Monolithic architecture with direct service integration
- Main application (`src/main.py`) directly imports and uses services
- All components tightly integrated for simplicity and performance

**MCP Servers Available (Not Yet Integrated):**
- `mcp_servers/gmail.py` - Gmail API operations
- `mcp_servers/database.py` - MongoDB operations
- `mcp_servers/document.py` - Document processing
- Future enhancement: Full MCP integration for modular architecture

### Technical Details

**Files Modified:**
- `src/main.py`: Added attachment processing, fixed datetime deprecations, removed debug logs
- `src/email/service.py`: Updated query to filter by Shopping label
- `src/classifier/service.py`: Improved classification prompt and category descriptions
- `src/email/attachment_processor.py`: New file for attachment processing
- `README.md`: Updated architecture section to clarify current implementation

**Dependencies:**
- PyPDF2: For PDF text extraction
- Pillow: For image handling
- pytesseract: For OCR text extraction from images

**Configuration:**
- Requires Tesseract OCR installed on system
- Temp directory for attachment processing: `./temp_attachments/`

### Usage

1. **Label Shopping Emails**: Apply "Shopping" label in Gmail to purchase-related emails
2. **Run Agent**: `python -m src.main`
3. **Attachments**: Automatically processed when present in emails
4. **Query Data**: Use `financial_data` collection for clean, structured financial data

### Breaking Changes
None - All changes are backward compatible

### Migration Notes
- Existing emails will not be reprocessed
- New "Shopping" label filter means only labeled emails will be processed going forward
- Consider labeling historical shopping emails if you want them processed