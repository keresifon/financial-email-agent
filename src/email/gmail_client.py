"""
Gmail API Client

This module handles Gmail API authentication and operations.
"""

import os
import pickle
import base64
from typing import Dict, List, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]


class GmailClient:
    """
    Gmail API client for email operations.
    """
    
    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token.pickle"):
        """
        Initialize Gmail client.
        
        Args:
            credentials_path: Path to OAuth2 credentials file
            token_path: Path to save/load token
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API."""
        creds = None
        
        # Load token if it exists
        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
                logger.info("Loaded existing Gmail credentials")
            except Exception as e:
                logger.warning(f"Could not load token: {e}")
        
        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("Refreshing Gmail credentials")
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Could not refresh credentials: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_path}\n"
                        "Please download OAuth2 credentials from Google Cloud Console"
                    )
                
                logger.info("Starting OAuth2 flow - browser will open for authentication")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("Authentication successful")
            
            # Save credentials
            try:
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)
                logger.info("Saved Gmail credentials")
            except Exception as e:
                logger.warning(f"Could not save token: {e}")
        
        # Build service
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail API service initialized")
        except Exception as e:
            logger.error(f"Failed to build Gmail service: {e}")
            raise
    
    def search_emails(self, query: str, max_results: int = 100) -> List[Dict]:
        """
        Search emails using Gmail query syntax.
        
        Args:
            query: Gmail search query
            max_results: Maximum number of results
            
        Returns:
            List of email dictionaries
        """
        try:
            logger.info(f"Searching emails: {query}")
            
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} messages")
            
            # Fetch full message details
            emails = []
            for msg in messages:
                try:
                    email_data = self.service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    emails.append(email_data)
                except HttpError as e:
                    logger.error(f"Error fetching message {msg['id']}: {e}")
            
            logger.info(f"Retrieved {len(emails)} full email details")
            return emails
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []
    
    def get_attachment(self, email_id: str, attachment_id: str) -> Optional[bytes]:
        """
        Download an email attachment.
        
        Args:
            email_id: Email ID
            attachment_id: Attachment ID
            
        Returns:
            Attachment data as bytes, or None if error
        """
        try:
            logger.info(f"Downloading attachment {attachment_id} from email {email_id}")
            
            attachment = self.service.users().messages().attachments().get(
                userId='me',
                messageId=email_id,
                id=attachment_id
            ).execute()
            
            data = attachment.get('data')
            if data:
                file_data = base64.urlsafe_b64decode(data)
                logger.info(f"Downloaded {len(file_data)} bytes")
                return file_data
            
            return None
            
        except HttpError as e:
            logger.error(f"Gmail API error downloading attachment: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading attachment: {e}")
            return None
    
    def mark_as_read(self, email_id: str) -> bool:
        """
        Mark an email as read.
        
        Args:
            email_id: Email ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Marking email {email_id} as read")
            
            self.service.users().messages().modify(
                userId='me',
                id=email_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            
            logger.info(f"Email {email_id} marked as read")
            return True
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error marking email as read: {e}")
            return False
    
    def add_label(self, email_id: str, label_name: str) -> bool:
        """
        Add a label to an email.
        
        Args:
            email_id: Email ID
            label_name: Label name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get or create label
            label_id = self._get_or_create_label(label_name)
            if not label_id:
                return False
            
            logger.info(f"Adding label '{label_name}' to email {email_id}")
            
            self.service.users().messages().modify(
                userId='me',
                id=email_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            
            logger.info(f"Label added successfully")
            return True
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error adding label: {e}")
            return False
    
    def _get_or_create_label(self, label_name: str) -> Optional[str]:
        """
        Get label ID or create if it doesn't exist.
        
        Args:
            label_name: Label name
            
        Returns:
            Label ID or None if error
        """
        try:
            # List existing labels
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            # Check if label exists
            for label in labels:
                if label['name'] == label_name:
                    return label['id']
            
            # Create new label
            logger.info(f"Creating new label: {label_name}")
            label_object = {
                'name': label_name,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }
            
            created_label = self.service.users().labels().create(
                userId='me',
                body=label_object
            ).execute()
            
            return created_label['id']
            
        except HttpError as e:
            logger.error(f"Gmail API error managing labels: {e}")
            return None
        except Exception as e:
            logger.error(f"Error managing labels: {e}")
            return None


# Made with Bob