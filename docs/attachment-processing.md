# Attachment Processing Feature

## Overview

The Financial Email Agent now includes full attachment processing capabilities. The system can download, extract text from, and analyze email attachments to improve classification accuracy and data extraction.

## Supported File Types

### Documents
- **PDF** (.pdf) - Extracted using PyPDF2
- **Images** (.png, .jpg, .jpeg, .tiff, .tif) - Extracted using Tesseract OCR

### Coming Soon
- Excel files (.xlsx, .xls)
- Word documents (.docx, .doc)
- CSV files (.csv)

## How It Works

### 1. Email Processing Pipeline

```
Email Received
    ↓
Step 1: Parse Email (headers, body, attachment metadata)
    ↓
Step 1.5: Process Attachments
    - Download each attachment
    - Extract text from supported file types
    - Combine all extracted text
    ↓
Step 2: Classify Email (using body + attachment text)
    ↓
Step 3: Extract Financial Data (from combined text)
    ↓
Step 4: Store in Database
    - Email metadata → category-specific collection
    - Extracted financial data → financial_data collection
    ↓
Step 5: Mark as Processed
```

### 2. Attachment Processing Details

For each attachment:
1. **Download**: Attachment is downloaded to temporary directory
2. **Text Extraction**: 
   - PDFs: Text extracted page by page
   - Images: OCR performed using Tesseract
3. **Cleanup**: Temporary files deleted after processing
4. **Storage**: Attachment metadata and extraction status stored in database

### 3. Database Schema

#### Email Collections (invoices, receipts, bank_statements, emails)
```json
{
  "email_id": "19b8061b99795b35",
  "subject": "Invoice #12345",
  "from": "vendor@example.com",
  "date": "2026-01-02",
  "classification": {
    "category": "invoice",
    "confidence": 0.95
  },
  "extracted_data": { ... },
  "attachments": [
    {
      "filename": "invoice_12345.pdf",
      "mime_type": "application/pdf",
      "size": 45678,
      "text_extracted": true,
      "text_length": 1234,
      "error": null
    }
  ],
  "has_attachments": true,
  "processed_at": "2026-01-02T20:30:00Z"
}
```

#### Financial Data Collection (financial_data)
```json
{
  "email_id": "19b8061b99795b35",
  "email_document_id": "507f1f77bcf86cd799439011",
  "category": "invoice",
  "subject": "Invoice #12345",
  "from": "vendor@example.com",
  "date": "2026-01-02",
  "extracted_data": {
    "invoice_number": "INV-12345",
    "amount": 1234.56,
    "currency": "USD",
    "due_date": "2026-02-01",
    "vendor": "Acme Corp"
  },
  "validation": {
    "is_valid": true,
    "completeness_score": 0.9
  },
  "confidence": 0.95,
  "has_attachments": true,
  "source": "email_with_attachments",
  "extracted_at": "2026-01-02T20:30:00Z"
}
```

## Benefits

### 1. Improved Classification Accuracy
- LLM can analyze actual document content, not just filenames
- Better detection of invoice numbers, amounts, dates
- More accurate category assignment

### 2. Complete Data Extraction
- Extract data from PDF invoices, receipts, statements
- Process scanned documents via OCR
- Capture information not in email body

### 3. Separate Financial Data Storage
- Clean, structured financial data in dedicated collection
- Easy querying and reporting
- Links back to original email for audit trail

### 4. Audit Trail
- Track which attachments were processed
- Record extraction success/failure
- Maintain source information (email vs attachment)

## Usage Examples

### Example 1: Invoice Email with PDF Attachment

**Email:**
- Subject: "Invoice for December Services"
- Body: "Please see attached invoice"
- Attachment: invoice_dec_2025.pdf

**Processing:**
1. PDF downloaded and text extracted
2. Combined text used for classification → "invoice" (confidence: 0.95)
3. Data extracted: invoice number, amount, due date, vendor
4. Stored in:
   - `invoices` collection (full email + attachment info)
   - `financial_data` collection (extracted structured data)

### Example 2: Receipt Email with Image Attachment

**Email:**
- Subject: "Receipt from Store"
- Body: "Thank you for your purchase"
- Attachment: receipt_20260102.jpg

**Processing:**
1. Image processed with OCR
2. Text extracted from receipt image
3. Classified as "receipt" (confidence: 0.88)
4. Data extracted: merchant, amount, date, items
5. Stored in both collections

## Configuration

### Temporary Directory
By default, attachments are downloaded to system temp directory. Configure in code:

```python
attachment_processor = AttachmentProcessor(
    gmail_client=gmail_client,
    temp_dir="/path/to/temp"  # Optional
)
```

### Supported File Types
Add new file types by extending `AttachmentProcessor.SUPPORTED_TYPES`:

```python
SUPPORTED_TYPES = {
    'pdf': extract_text_from_pdf,
    'png': extract_text_from_image,
    'xlsx': extract_text_from_excel,  # Add new types
}
```

## Querying Financial Data

### Get All Invoices with Extracted Data
```python
financial_data = db.financial_data.find({
    "category": "invoice",
    "validation.is_valid": True
})
```

### Get High-Confidence Extractions
```python
high_confidence = db.financial_data.find({
    "confidence": {"$gte": 0.9},
    "has_attachments": True
})
```

### Get Extractions from Specific Sender
```python
vendor_data = db.financial_data.find({
    "from": {"$regex": "vendor@example.com"},
    "category": "invoice"
})
```

### Monthly Financial Summary
```python
from datetime import datetime

monthly_total = db.financial_data.aggregate([
    {
        "$match": {
            "category": "invoice",
            "date": {
                "$gte": "2026-01-01",
                "$lt": "2026-02-01"
            }
        }
    },
    {
        "$group": {
            "_id": None,
            "total": {"$sum": "$extracted_data.amount"},
            "count": {"$sum": 1}
        }
    }
])
```

## Troubleshooting

### PDF Extraction Fails
- Ensure PyPDF2 is installed: `pip install PyPDF2`
- Some PDFs may be image-based (scanned) - use OCR instead
- Check PDF is not password-protected

### OCR Not Working
- Install Tesseract OCR: https://github.com/tesseract-ocr/tesseract
- Ensure tesseract is in system PATH
- Install pytesseract: `pip install pytesseract`

### Attachments Not Downloaded
- Check Gmail API permissions include attachment access
- Verify attachment_id is present in email metadata
- Check network connectivity

### Temporary Files Not Cleaned Up
- Check file permissions on temp directory
- Verify cleanup is called in finally block
- Manual cleanup: delete `email_*` folders in temp directory

## Performance Considerations

### Processing Time
- PDF extraction: ~1-2 seconds per page
- OCR: ~3-5 seconds per image
- Large attachments may take longer

### Storage
- Extracted text stored in database
- Original attachments not stored (download from Gmail if needed)
- Consider text length limits for very large documents

### Rate Limits
- Gmail API has rate limits for attachment downloads
- Implement exponential backoff for failures
- Process in batches if handling many emails

## Future Enhancements

1. **Excel/CSV Processing**: Extract tabular data from spreadsheets
2. **Word Document Support**: Process .docx files
3. **Multi-language OCR**: Support for non-English documents
4. **Attachment Caching**: Cache extracted text to avoid re-processing
5. **Parallel Processing**: Process multiple attachments concurrently
6. **Smart Extraction**: Use document structure to improve extraction
7. **Attachment Storage**: Option to store original files in cloud storage

## Made with Bob