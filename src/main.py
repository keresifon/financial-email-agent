"""
Financial Email Agent - Main Application

This is the main entry point for the Financial Email Agent application.
It orchestrates email processing, classification, and data extraction.
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime, timezone

from src.config.loader import load_config
from src.config.models import AppConfig
from src.database.connection import MongoDBConnection
from src.llm.client import LLMClient
from src.email.service import EmailService
from src.email.attachment_processor import AttachmentProcessor
from src.classifier.service import EmailClassifier
from src.extractors.service import DataExtractor
from src.utils.logger import get_logger, setup_logger

logger = get_logger(__name__)


class FinancialEmailAgent:
    """
    Main application class for the Financial Email Agent.
    
    This class orchestrates the entire email processing pipeline:
    1. Fetch emails from Gmail
    2. Classify emails by type
    3. Extract structured data
    4. Store in MongoDB
    5. Mark emails as processed
    """
    
    def __init__(self, config: AppConfig):
        """
        Initialize the Financial Email Agent.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.use_mcp = config.mcp.enabled
        self.mcp_manager = None
        
        # Initialize services
        logger.info(f"Initializing Financial Email Agent (MCP: {self.use_mcp})")
        
        # Database (only if not using MCP)
        if not self.use_mcp:
            self.db_connection = MongoDBConnection(config.mongodb)
            self.db_connection.connect()
            self.db = self.db_connection.get_database()
        else:
            self.db_connection = None
            self.db = None
        
        # LLM Client
        self.llm_client = LLMClient(config=config.llama)
        
        # Email Service (only if not using MCP)
        if not self.use_mcp:
            self.email_service = EmailService(config)
            self.attachment_processor = AttachmentProcessor(
                gmail_client=self.email_service.gmail_client
            )
        else:
            self.email_service = None
            self.attachment_processor = None
        
        # Classifier
        self.classifier = EmailClassifier(self.llm_client, config)
        
        # Data Extractor
        self.extractor = DataExtractor(self.llm_client, config)
        
        logger.info("Financial Email Agent initialized successfully")
    
    async def initialize_mcp(self):
        """Initialize MCP manager (async)."""
        if self.use_mcp and not self.mcp_manager:
            from src.mcp.manager import MCPServerManager
            self.mcp_manager = MCPServerManager(self.config)
            await self.mcp_manager.initialize()
            logger.info("MCP Manager initialized")
    
    async def shutdown_mcp(self):
        """Shutdown MCP manager."""
        if self.mcp_manager:
            await self.mcp_manager.shutdown()
            logger.info("MCP Manager shut down")
    
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
        query = f"after:{date_from}"
        
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
    
    async def _save_document_mcp(self, collection: str, document: Dict) -> str:
        """
        Save a document to MongoDB via MCP.
        
        Args:
            collection: Collection name
            document: Document to save
            
        Returns:
            Document ID as string
        """
        import json
        
        logger.info(f"Saving document to {collection} via MCP")
        
        result = await self.mcp_manager.call_tool("database", "save_document", {
            "collection": collection,
            "document": document
        })
        
        response = json.loads(result[0].text)
        if response.get("success"):
            document_id = response.get("document_id")
            logger.info(f"Document saved with ID: {document_id}")
            return document_id
        else:
            error = response.get("error", "Unknown error")
            raise Exception(f"Failed to save document: {error}")
    
    async def _get_statistics_mcp(self) -> Dict:
        """
        Get database statistics via MCP.
        
        Returns:
            Statistics dictionary
        """
        import json
        
        logger.info("Getting database statistics via MCP")
        
        result = await self.mcp_manager.call_tool("database", "get_statistics", {})
        
        response = json.loads(result[0].text)
        if response.get("success"):
            stats = response.get("statistics", {})
            
            # Transform to match expected format
            formatted_stats = {
                "total_emails": 0,
                "by_category": {},
                "by_collection": {},
                "recent_activity": []
            }
            
            if "collections" in stats:
                for coll_name, coll_stats in stats["collections"].items():
                    count = coll_stats.get("document_count", 0)
                    formatted_stats["by_collection"][coll_name] = count
                    formatted_stats["total_emails"] += count
            
            return formatted_stats
        else:
            error = response.get("error", "Unknown error")
            logger.error(f"Failed to get statistics: {error}")
            return {"error": error}
    
    async def _process_email_mcp(self, email_data: Dict) -> Dict:
        """
        Process a single email through the complete pipeline using MCP.
        
        Args:
            email_data: Email data dictionary from MCP
            
        Returns:
            Processing result dictionary
        """
        try:
            email_id = email_data.get("id", "unknown")
            subject = email_data.get("subject", "No subject")
            
            logger.info(f"Processing email (MCP): {subject}")
            
            result = {
                "email_id": email_id,
                "subject": subject,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "status": "success",
                "steps": {}
            }
            
            # Email is already parsed from MCP
            result["steps"]["parse"] = {"status": "success"}
            
            # Process attachments via MCP
            processed_attachments = []
            attachment_text = ""
            attachments = email_data.get("attachments", [])
            
            if attachments and len(attachments) > 0:
                logger.info(f"Processing {len(attachments)} attachments via MCP")
                processed_attachments = await self._process_attachments_mcp(email_id, attachments)
                
                # Combine attachment text
                attachment_text = "\n\n".join([
                    f"=== {att['filename']} ===\n{att['text']}"
                    for att in processed_attachments if att.get("text_extracted")
                ])
                
                result["steps"]["process_attachments"] = {
                    "status": "success",
                    "count": len(processed_attachments),
                    "extracted_count": sum(1 for a in processed_attachments if a.get("text_extracted"))
                }
                logger.info(f"Extracted text from {result['steps']['process_attachments']['extracted_count']} attachments")
            
            # Combine email body and attachment text
            combined_text = email_data.get("body", "")
            if attachment_text:
                combined_text += "\n\n=== ATTACHMENTS ===\n\n" + attachment_text
            
            # Classify email
            logger.info("Classifying email")
            classification = self.classifier.classify({
                "subject": email_data.get("subject", ""),
                "from": email_data.get("from", ""),
                "body": combined_text,
                "date": email_data.get("date", ""),
                "attachments": [att.get("filename", "") for att in attachments]
            })
            
            result["classification"] = classification
            result["steps"]["classify"] = {
                "status": "success",
                "category": classification.get("category"),
                "confidence": classification.get("confidence")
            }
            
            # Extract data based on classification
            category = classification.get("category", "other")
            confidence = classification.get("confidence", 0.0)
            
            if confidence >= self.config.classification.min_confidence and category != "other":
                logger.info(f"Extracting data for category: {category}")
                
                doc_type_map = {
                    "invoice": "invoice",
                    "receipt": "receipt",
                    "statement": "statement",
                    "payment_confirmation": "payment_confirmation"
                }
                
                doc_type = doc_type_map.get(category, "invoice")
                
                extracted_data = self.extractor.extract(
                    document_type=doc_type,
                    text=combined_text,
                    metadata={
                        "email_id": email_id,
                        "subject": subject,
                        "from": email_data.get("from", ""),
                        "date": email_data.get("date", ""),
                        "has_attachments": len(attachments) > 0,
                        "attachment_count": len(attachments)
                    }
                )
                
                result["extracted_data"] = extracted_data
                result["steps"]["extract"] = {"status": "success"}
                
                validation = self.extractor.validate_extraction(extracted_data, doc_type)
                result["validation"] = validation
                result["steps"]["validate"] = {
                    "status": "success",
                    "is_valid": validation.get("is_valid"),
                    "completeness": validation.get("completeness_score")
                }
            else:
                logger.info(f"Skipping extraction: confidence {confidence:.2f} below threshold or category is 'other'")
                result["steps"]["extract"] = {
                    "status": "skipped",
                    "reason": "Low confidence or unclassified"
                }
            
            # Store in database via MCP
            logger.info("Storing in database via MCP")
            document = {
                "email_id": email_id,
                "subject": subject,
                "from": email_data.get("from", ""),
                "date": email_data.get("date", ""),
                "classification": classification,
                "extracted_data": result.get("extracted_data"),
                "validation": result.get("validation"),
                "attachments": processed_attachments,
                "has_attachments": len(attachments) > 0,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "status": "processed"
            }
            
            collection_map = {
                "invoice": self.config.mongodb.collections.invoices,
                "receipt": self.config.mongodb.collections.receipts,
                "statement": self.config.mongodb.collections.bank_statements,
                "other": self.config.mongodb.collections.emails
            }
            
            collection_name = collection_map.get(category, self.config.mongodb.collections.emails)
            
            document_id = await self._save_document_mcp(collection_name, document)
            result["database_id"] = document_id
            result["steps"]["store"] = {
                "status": "success",
                "collection": collection_name,
                "document_id": document_id
            }
            
            # Mark email as read via MCP
            logger.info("Marking email as processed via MCP")
            await self.mcp_manager.call_tool("gmail", "mark_as_read", {
                "message_id": email_id
            })
            result["steps"]["mark_processed"] = {"status": "success"}
            
            logger.info(f"Successfully processed email (MCP): {subject}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing email (MCP): {e}")
            return {
                "email_id": email_data.get("id", "unknown"),
                "subject": email_data.get("subject", "No subject"),
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": str(e)
            }
    
    def process_email(self, email_data: Dict) -> Dict:
        """
        Process a single email through the complete pipeline.
        
        Args:
            email_data: Email data dictionary
            
        Returns:
            Processing result dictionary
        """
        try:
            email_id = email_data.get("id", "unknown")
            subject = email_data.get("subject", "No subject")
            
            logger.info(f"Processing email: {subject}")
            
            result = {
                "email_id": email_id,
                "subject": subject,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "status": "success",
                "steps": {}
            }
            
            # Step 1: Parse email
            logger.info("Step 1: Parsing email")
            parsed_email = self.email_service.parse_email(email_data)
            result["steps"]["parse"] = {"status": "success"}
            
            # Step 1.5: Process attachments
            processed_attachments = []
            attachment_text = ""
            attachments = parsed_email.get("attachments", [])
            
            if attachments and len(attachments) > 0:
                logger.info(f"Step 1.5: Processing {len(attachments)} attachments")
                processed_attachments = self.attachment_processor.process_attachments(
                    email_id, attachments
                )
                attachment_text = self.attachment_processor.get_combined_text(processed_attachments)
                
                result["steps"]["process_attachments"] = {
                    "status": "success",
                    "count": len(processed_attachments),
                    "extracted_count": sum(1 for a in processed_attachments if a.get("text_extracted"))
                }
                logger.info(f"Extracted text from {result['steps']['process_attachments']['extracted_count']} attachments")
            
            # Combine email body and attachment text for classification
            combined_text = parsed_email.get("body", "")
            if attachment_text:
                combined_text += "\n\n=== ATTACHMENTS ===\n\n" + attachment_text
            
            # Step 2: Classify email
            logger.info("Step 2: Classifying email")
            classification = self.classifier.classify({
                "subject": parsed_email.get("subject", ""),
                "from": parsed_email.get("from", ""),
                "body": combined_text,  # Now includes attachment text
                "date": parsed_email.get("date", ""),
                "attachments": [att.get("filename", "") for att in attachments]
            })
            
            result["classification"] = classification
            result["steps"]["classify"] = {
                "status": "success",
                "category": classification.get("category"),
                "confidence": classification.get("confidence")
            }
            
            # Step 3: Extract data based on classification
            category = classification.get("category", "other")
            confidence = classification.get("confidence", 0.0)
            
            if confidence >= self.config.classification.min_confidence and category != "other":
                logger.info(f"Step 3: Extracting data for category: {category}")
                
                # Map category to document type
                doc_type_map = {
                    "invoice": "invoice",
                    "receipt": "receipt",
                    "statement": "statement",
                    "payment_confirmation": "payment_confirmation"
                }
                
                doc_type = doc_type_map.get(category, "invoice")
                
                extracted_data = self.extractor.extract(
                    document_type=doc_type,
                    text=combined_text,  # Use combined text including attachments
                    metadata={
                        "email_id": email_id,
                        "subject": subject,
                        "from": parsed_email.get("from", ""),
                        "date": parsed_email.get("date", ""),
                        "has_attachments": len(attachments) > 0,
                        "attachment_count": len(attachments)
                    }
                )
                
                result["extracted_data"] = extracted_data
                result["steps"]["extract"] = {"status": "success"}
                
                # Validate extraction
                validation = self.extractor.validate_extraction(extracted_data, doc_type)
                result["validation"] = validation
                result["steps"]["validate"] = {
                    "status": "success",
                    "is_valid": validation.get("is_valid"),
                    "completeness": validation.get("completeness_score")
                }
            else:
                logger.info(f"Skipping extraction: confidence {confidence:.2f} below threshold or category is 'other'")
                result["steps"]["extract"] = {
                    "status": "skipped",
                    "reason": "Low confidence or unclassified"
                }
            
            # Step 4: Store in database
            logger.info("Step 4: Storing in database")
            
            # Prepare document for storage
            document = {
                "email_id": email_id,
                "subject": subject,
                "from": parsed_email.get("from", ""),
                "date": parsed_email.get("date", ""),
                "classification": classification,
                "extracted_data": result.get("extracted_data"),
                "validation": result.get("validation"),
                "attachments": processed_attachments,  # Include attachment info
                "has_attachments": len(attachments) > 0,
                "processed_at": datetime.now(timezone.utc),
                "status": "processed"
            }
            
            # Store in appropriate collection based on category
            collection_map = {
                "invoice": self.config.mongodb.collections.invoices,
                "receipt": self.config.mongodb.collections.receipts,
                "statement": self.config.mongodb.collections.bank_statements,
                "other": self.config.mongodb.collections.emails
            }
            
            collection_name = collection_map.get(category, self.config.mongodb.collections.emails)
            collection = self.db[collection_name]
            
            insert_result = collection.insert_one(document)
            result["database_id"] = str(insert_result.inserted_id)
            result["steps"]["store"] = {
                "status": "success",
                "collection": collection_name,
                "document_id": str(insert_result.inserted_id)
            }
            
            # Step 4.5: Store extracted financial data in separate collection
            if result.get("extracted_data") and category != "other":
                logger.info("Step 4.5: Storing extracted financial data")
                
                extracted = result.get("extracted_data", {})
                
                # Build clean financial data based on category
                financial_data = {
                    "email_id": email_id,
                    "email_document_id": str(insert_result.inserted_id),
                    "category": category,
                    "from": parsed_email.get("from", ""),
                    "date": parsed_email.get("date", ""),
                    "confidence": confidence,
                    "extracted_at": datetime.now(timezone.utc),
                    "source": "email_with_attachments" if len(attachments) > 0 else "email_body"
                }
                
                # Add category-specific fields
                if category == "invoice":
                    financial_data.update({
                        "invoice_number": extracted.get("invoice_number"),
                        "vendor": extracted.get("vendor") or extracted.get("from"),
                        "amount": extracted.get("amount") or extracted.get("total_amount"),
                        "currency": extracted.get("currency", "USD"),
                        "due_date": extracted.get("due_date"),
                        "issue_date": extracted.get("issue_date") or extracted.get("date")
                    })
                elif category == "receipt":
                    financial_data.update({
                        "merchant": extracted.get("merchant") or extracted.get("vendor"),
                        "amount": extracted.get("amount") or extracted.get("total_amount"),
                        "currency": extracted.get("currency", "USD"),
                        "date": extracted.get("date") or extracted.get("transaction_date"),
                        "items": extracted.get("items", [])
                    })
                elif category == "statement":
                    financial_data.update({
                        "account_number": extracted.get("account_number"),
                        "period": extracted.get("period") or extracted.get("statement_period"),
                        "balance": extracted.get("balance") or extracted.get("closing_balance"),
                        "transactions": extracted.get("transactions", [])
                    })
                elif category == "payment_confirmation":
                    financial_data.update({
                        "amount": extracted.get("amount") or extracted.get("payment_amount"),
                        "currency": extracted.get("currency", "USD"),
                        "date": extracted.get("date") or extracted.get("payment_date"),
                        "recipient": extracted.get("recipient") or extracted.get("payee"),
                        "reference": extracted.get("reference") or extracted.get("transaction_id")
                    })
                
                # Store in financial_data collection
                financial_collection = self.db["financial_data"]
                financial_insert = financial_collection.insert_one(financial_data)
                
                result["financial_data_id"] = str(financial_insert.inserted_id)
                result["steps"]["store_financial_data"] = {
                    "status": "success",
                    "document_id": str(financial_insert.inserted_id)
                }
                logger.info(f"Stored financial data with ID: {financial_insert.inserted_id}")
            
            # Step 5: Mark email as processed
            logger.info("Step 5: Marking email as processed")
            self.email_service.mark_as_read(email_id)
            
            # Move to processed folder
            self.email_service.move_to_folder(email_id, "Processed")
            result["steps"]["mark_processed"] = {"status": "success"}
            
            logger.info(f"Successfully processed email: {subject}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing email: {e}")
            return {
                "email_id": email_data.get("id", "unknown"),
                "subject": email_data.get("subject", "No subject"),
                "processed_at": datetime.utcnow().isoformat(),
                "status": "error",
                "error": str(e)
            }
    
    async def process_batch_mcp(self, max_emails: int = 50) -> Dict:
        """
        Process a batch of emails using MCP.
        
        Args:
            max_emails: Maximum number of emails to process
            
        Returns:
            Batch processing summary
        """
        logger.info(f"Starting batch processing via MCP (max {max_emails} emails)")
        
        summary = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "total_fetched": 0,
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "results": []
        }
        
        try:
            # Initialize MCP
            await self.initialize_mcp()
            
            # Fetch emails via MCP
            logger.info("Fetching financial emails via MCP")
            emails = await self._fetch_emails_mcp(days_back=7)
            
            summary["total_fetched"] = len(emails)
            logger.info(f"Fetched {len(emails)} emails via MCP")
            
            # Process each email
            for i, email in enumerate(emails):
                logger.info(f"Processing email {i+1}/{len(emails)}")
                
                result = await self._process_email_mcp(email)
                summary["results"].append(result)
                summary["total_processed"] += 1
                
                if result.get("status") == "success":
                    summary["successful"] += 1
                elif result.get("status") == "error":
                    summary["failed"] += 1
                else:
                    summary["skipped"] += 1
            
            summary["completed_at"] = datetime.now(timezone.utc).isoformat()
            
            logger.info(
                f"Batch processing complete: {summary['successful']} successful, "
                f"{summary['failed']} failed, {summary['skipped']} skipped"
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error in batch processing (MCP): {e}")
            summary["error"] = str(e)
            summary["completed_at"] = datetime.now(timezone.utc).isoformat()
            return summary
        
        finally:
            # Shutdown MCP
            await self.shutdown_mcp()
    
    def process_batch(self, max_emails: int = 50) -> Dict:
        """
        Process a batch of emails.
        
        Args:
            max_emails: Maximum number of emails to process
            
        Returns:
            Batch processing summary
        """
        logger.info(f"Starting batch processing (max {max_emails} emails)")
        
        summary = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "total_fetched": 0,
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "results": []
        }
        
        try:
            # Fetch emails
            logger.info("Fetching financial emails")
            emails = self.email_service.get_financial_emails(
                days_back=7,
                max_results=max_emails
            )
            
            summary["total_fetched"] = len(emails)
            logger.info(f"Fetched {len(emails)} emails")
            
            # Process each email
            for i, email in enumerate(emails):
                logger.info(f"Processing email {i+1}/{len(emails)}")
                
                result = self.process_email(email)
                summary["results"].append(result)
                summary["total_processed"] += 1
                
                if result.get("status") == "success":
                    summary["successful"] += 1
                elif result.get("status") == "error":
                    summary["failed"] += 1
                else:
                    summary["skipped"] += 1
            
            summary["completed_at"] = datetime.now(timezone.utc).isoformat()
            
            logger.info(
                f"Batch processing complete: {summary['successful']} successful, "
                f"{summary['failed']} failed, {summary['skipped']} skipped"
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            summary["error"] = str(e)
            summary["completed_at"] = datetime.utcnow().isoformat()
            return summary
    
    async def get_statistics_async(self) -> Dict:
        """
        Get processing statistics from the database (async, MCP-aware).
        
        Returns:
            Statistics dictionary
        """
        if self.use_mcp:
            return await self._get_statistics_mcp()
        else:
            return self.get_statistics()
    
    def get_statistics(self) -> Dict:
        """
        Get processing statistics from the database (sync, direct mode).
        
        Returns:
            Statistics dictionary
        """
        try:
            stats = {
                "total_emails": 0,
                "by_category": {},
                "by_collection": {},
                "recent_activity": []
            }
            
            # Count documents in each collection
            collections = [
                self.config.mongodb.collections.emails,
                self.config.mongodb.collections.invoices,
                self.config.mongodb.collections.receipts,
                self.config.mongodb.collections.bank_statements
            ]
            
            for coll_name in collections:
                collection = self.db[coll_name]
                count = collection.count_documents({})
                stats["by_collection"][coll_name] = count
                stats["total_emails"] += count
            
            # Get category distribution
            for coll_name in collections:
                collection = self.db[coll_name]
                pipeline = [
                    {"$group": {
                        "_id": "$classification.category",
                        "count": {"$sum": 1}
                    }}
                ]
                
                for doc in collection.aggregate(pipeline):
                    category = doc["_id"]
                    count = doc["count"]
                    stats["by_category"][category] = stats["by_category"].get(category, 0) + count
            
            # Get recent activity (last 10 processed emails)
            emails_collection = self.db[self.config.mongodb.collections.emails]
            recent = emails_collection.find().sort("processed_at", -1).limit(10)
            
            for email in recent:
                stats["recent_activity"].append({
                    "subject": email.get("subject"),
                    "category": email.get("classification", {}).get("category"),
                    "processed_at": email.get("processed_at", "").isoformat() if isinstance(email.get("processed_at"), datetime) else email.get("processed_at")
                })
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {"error": str(e)}
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up resources")
        if self.db_connection:
            self.db_connection.disconnect()


async def async_main():
    """Async main entry point for MCP mode."""
    try:
        # Load configuration first
        config = load_config()
        
        # Setup logging
        setup_logger(config.logging)
        
        logger.info("=" * 60)
        logger.info("Financial Email Agent Starting (MCP Mode)")
        logger.info("=" * 60)
        
        logger.info(f"Configuration loaded: {config.environment} environment")
        logger.info(f"MCP enabled: {config.mcp.enabled}")
        
        # Initialize agent
        agent = FinancialEmailAgent(config)
        
        # Process emails via MCP
        logger.info("Starting email processing via MCP")
        summary = await agent.process_batch_mcp(max_emails=config.email.monitoring.max_emails_per_check)
        
        # Display summary
        logger.info("=" * 60)
        logger.info("Processing Summary")
        logger.info("=" * 60)
        logger.info(f"Total fetched: {summary['total_fetched']}")
        logger.info(f"Total processed: {summary['total_processed']}")
        logger.info(f"Successful: {summary['successful']}")
        logger.info(f"Failed: {summary['failed']}")
        logger.info(f"Skipped: {summary['skipped']}")
        
        # Get statistics
        stats = await agent.get_statistics_async()
        logger.info("=" * 60)
        logger.info("Database Statistics")
        logger.info("=" * 60)
        logger.info(f"Total emails in database: {stats.get('total_emails', 0)}")
        logger.info(f"By category: {stats.get('by_category', {})}")
        logger.info(f"By collection: {stats.get('by_collection', {})}")
        
        # Cleanup
        agent.cleanup()
        
        logger.info("=" * 60)
        logger.info("Financial Email Agent Completed")
        logger.info("=" * 60)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


def main():
    """Main entry point."""
    return asyncio.run(async_main())


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
