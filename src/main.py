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
        
        # Initialize services
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
    
    def get_statistics(self) -> Dict:
        """
        Get processing statistics from the database.
        
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


def main():
    """Main entry point."""
    try:
        # Load configuration first
        config = load_config()
        
        # Setup logging
        setup_logger(config.logging)
        
        logger.info("=" * 60)
        logger.info("Financial Email Agent Starting")
        logger.info("=" * 60)
        
        logger.info(f"Configuration loaded: {config.environment} environment")
        
        # Initialize agent
        agent = FinancialEmailAgent(config)
        
        # Process emails
        logger.info("Starting email processing")
        summary = agent.process_batch(max_emails=config.email.monitoring.max_emails_per_check)
        
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
        stats = agent.get_statistics()
        logger.info("=" * 60)
        logger.info("Database Statistics")
        logger.info("=" * 60)
        logger.info(f"Total emails in database: {stats.get('total_emails', 0)}")
        logger.info(f"By category: {stats.get('by_category', {})}")
        
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


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
