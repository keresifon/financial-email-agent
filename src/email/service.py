"""
Email Service

This service handles email operations using Gmail API.
"""

import json
import base64
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from src.config.models import AppConfig
from src.utils.logger import get_logger
from src.email.gmail_client import GmailClient

logger = get_logger(__name__)


class EmailService:
    """
    Service for email operations using Gmail MCP server.
    
    This service provides a high-level interface for:
    - Fetching emails
    - Parsing email content
    - Downloading attachments
    - Marking emails as processed
    """
    
    def __init__(self, config: AppConfig):
        """
        Initialize the email service.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.email_config = config.email
        
        # Initialize Gmail client
        try:
            self.gmail_client = GmailClient()
            logger.info("Gmail client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gmail client: {e}")
            raise
    
    def fetch_unread_emails(self, max_results: int = 50, query: Optional[str] = None) -> List[Dict]:
        """
        Fetch unread emails from Gmail.
        
        Args:
            max_results: Maximum number of emails to fetch
            query: Optional Gmail search query
            
        Returns:
            List of email dictionaries
        """
        try:
            logger.info(f"Fetching up to {max_results} unread emails")
            
            # Build query
            if query is None:
                query = "is:unread"
            elif "is:unread" not in query:
                query = f"is:unread {query}"
            
            # In a real implementation, this would call the Gmail MCP server
            # For now, we'll return a placeholder structure
            logger.info(f"Query: {query}")
            
            # TODO: Integrate with Gmail MCP server via MCP client
            # emails = mcp_client.call_tool("fetch_emails", {
            #     "query": query,
            #     "max_results": max_results
            # })
            
            emails = []
            logger.info(f"Fetched {len(emails)} emails")
            
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []
    
    def parse_email(self, email_data: Dict) -> Dict:
        """
        Parse email data into a structured format.
        
        Args:
            email_data: Raw email data from Gmail API
            
        Returns:
            Parsed email dictionary
        """
        try:
            parsed = {
                "id": email_data.get("id"),
                "thread_id": email_data.get("threadId"),
                "subject": "",
                "from": "",
                "to": [],
                "cc": [],
                "date": None,
                "body": "",
                "body_html": "",
                "attachments": [],
                "labels": email_data.get("labelIds", []),
                "snippet": email_data.get("snippet", ""),
            }
            
            # Parse headers
            headers = email_data.get("payload", {}).get("headers", [])
            for header in headers:
                name = header.get("name", "").lower()
                value = header.get("value", "")
                
                if name == "subject":
                    parsed["subject"] = value
                elif name == "from":
                    parsed["from"] = value
                elif name == "to":
                    parsed["to"] = [addr.strip() for addr in value.split(",")]
                elif name == "cc":
                    parsed["cc"] = [addr.strip() for addr in value.split(",")]
                elif name == "date":
                    parsed["date"] = value
            
            # Parse body
            payload = email_data.get("payload", {})
            parsed["body"] = self._extract_body(payload, "text/plain")
            parsed["body_html"] = self._extract_body(payload, "text/html")
            
            # Parse attachments
            parsed["attachments"] = self._extract_attachments(payload)
            
            logger.debug(f"Parsed email: {parsed['subject']}")
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error parsing email: {e}")
            return {
                "id": email_data.get("id"),
                "error": str(e),
                "raw_data": email_data
            }
    
    def _extract_body(self, payload: Dict, mime_type: str) -> str:
        """
        Extract email body of specific MIME type.
        
        Args:
            payload: Email payload
            mime_type: MIME type to extract (text/plain or text/html)
            
        Returns:
            Email body text
        """
        try:
            # Check if this part matches the MIME type
            if payload.get("mimeType") == mime_type:
                body_data = payload.get("body", {}).get("data", "")
                if body_data:
                    return base64.urlsafe_b64decode(body_data).decode("utf-8")
            
            # Check parts recursively
            parts = payload.get("parts", [])
            for part in parts:
                if part.get("mimeType") == mime_type:
                    body_data = part.get("body", {}).get("data", "")
                    if body_data:
                        return base64.urlsafe_b64decode(body_data).decode("utf-8")
                
                # Recursive check for nested parts
                if "parts" in part:
                    result = self._extract_body(part, mime_type)
                    if result:
                        return result
            
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting body: {e}")
            return ""
    
    def _extract_attachments(self, payload: Dict) -> List[Dict]:
        """
        Extract attachment information from email payload.
        
        Args:
            payload: Email payload
            
        Returns:
            List of attachment dictionaries
        """
        attachments = []
        
        try:
            parts = payload.get("parts", [])
            
            for part in parts:
                filename = part.get("filename")
                if filename:
                    attachment = {
                        "filename": filename,
                        "mime_type": part.get("mimeType"),
                        "size": part.get("body", {}).get("size", 0),
                        "attachment_id": part.get("body", {}).get("attachmentId"),
                    }
                    attachments.append(attachment)
                
                # Check nested parts
                if "parts" in part:
                    nested_attachments = self._extract_attachments(part)
                    attachments.extend(nested_attachments)
            
        except Exception as e:
            logger.error(f"Error extracting attachments: {e}")
        
        return attachments
    
    def download_attachment(self, email_id: str, attachment_id: str, save_path: str) -> bool:
        """
        Download an email attachment.
        
        Args:
            email_id: Email ID
            attachment_id: Attachment ID
            save_path: Path to save the attachment
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Downloading attachment {attachment_id} from email {email_id}")
            
            # Download using Gmail client
            attachment_data = self.gmail_client.get_attachment(email_id, attachment_id)
            
            if attachment_data:
                # Ensure directory exists
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                
                # Save attachment
                with open(save_path, "wb") as f:
                    f.write(attachment_data)
                
                logger.info(f"Saved attachment to {save_path}")
                return True
            else:
                logger.error("No attachment data received")
                return False
            
        except Exception as e:
            logger.error(f"Error downloading attachment: {e}")
            return False
    
    def mark_as_read(self, email_id: str) -> bool:
        """
        Mark an email as read.
        
        Args:
            email_id: Email ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return self.gmail_client.mark_as_read(email_id)
            
        except Exception as e:
            logger.error(f"Error marking email as read: {e}")
            return False
    
    def move_to_folder(self, email_id: str, folder_name: str) -> bool:
        """
        Move an email to a folder (label in Gmail).
        
        Args:
            email_id: Email ID
            folder_name: Folder/label name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return self.gmail_client.add_label(email_id, folder_name)
            
        except Exception as e:
            logger.error(f"Error moving email to folder: {e}")
            return False
    
    def search_emails(self, query: str, max_results: int = 100) -> List[Dict]:
        """
        Search emails using Gmail query syntax.
        
        Args:
            query: Gmail search query
            max_results: Maximum number of results
            
        Returns:
            List of matching emails
        """
        try:
            logger.info(f"Searching emails with query: {query}")
            
            # Use Gmail client to search
            raw_emails = self.gmail_client.search_emails(query, max_results)
            
            # Parse each email
            parsed_emails = []
            for raw_email in raw_emails:
                parsed = self.parse_email(raw_email)
                parsed_emails.append(parsed)
            
            logger.info(f"Found {len(parsed_emails)} matching emails")
            
            return parsed_emails
            
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []
    
    def get_emails_by_date_range(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        max_results: int = 100
    ) -> List[Dict]:
        """
        Get emails within a date range.
        
        Args:
            start_date: Start date
            end_date: End date (defaults to now)
            max_results: Maximum number of results
            
        Returns:
            List of emails
        """
        if end_date is None:
            end_date = datetime.now()
        
        # Build Gmail query for date range
        start_str = start_date.strftime("%Y/%m/%d")
        end_str = end_date.strftime("%Y/%m/%d")
        
        query = f"after:{start_str} before:{end_str}"
        
        return self.search_emails(query, max_results)
    
    def get_financial_emails(self, days_back: int = 7, max_results: int = 100) -> List[Dict]:
        """
        Get emails that likely contain financial information.
        Only fetches emails with the 'Shopping' label.
        
        Args:
            days_back: Number of days to look back
            max_results: Maximum number of results
            
        Returns:
            List of financial emails with Shopping label
        """
        start_date = datetime.now() - timedelta(days=days_back)
        start_str = start_date.strftime("%Y/%m/%d")
        
        # Only fetch emails with Shopping label
        query = f"after:{start_str} label:Shopping"
        
        return self.search_emails(query, max_results)

# Made with Bob
