"""
Attachment Processor

Handles downloading and processing email attachments.
"""

import os
import tempfile
from typing import Dict, List, Optional
from pathlib import Path

from src.utils.logger import get_logger
from src.utils.helpers import (
    extract_text_from_pdf,
    extract_text_from_image,
    sanitize_filename,
    get_file_extension,
    ensure_directory
)

logger = get_logger(__name__)


class AttachmentProcessor:
    """
    Process email attachments and extract text content.
    """
    
    # Supported file types for text extraction
    SUPPORTED_TYPES = {
        'pdf': extract_text_from_pdf,
        'png': extract_text_from_image,
        'jpg': extract_text_from_image,
        'jpeg': extract_text_from_image,
        'tiff': extract_text_from_image,
        'tif': extract_text_from_image,
    }
    
    def __init__(self, gmail_client, temp_dir: Optional[str] = None):
        """
        Initialize attachment processor.
        
        Args:
            gmail_client: Gmail client for downloading attachments
            temp_dir: Temporary directory for downloads (uses system temp if None)
        """
        self.gmail_client = gmail_client
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.session_dir = None
    
    def create_session_dir(self, email_id: str) -> Path:
        """
        Create a temporary directory for this email's attachments.
        
        Args:
            email_id: Email ID
            
        Returns:
            Path to session directory
        """
        session_path = Path(self.temp_dir) / f"email_{email_id}"
        ensure_directory(session_path)
        self.session_dir = session_path
        logger.debug(f"Created session directory: {session_path}")
        return session_path
    
    def cleanup_session_dir(self):
        """Clean up temporary session directory."""
        if self.session_dir and self.session_dir.exists():
            try:
                import shutil
                shutil.rmtree(self.session_dir)
                logger.debug(f"Cleaned up session directory: {self.session_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup session directory: {e}")
            finally:
                self.session_dir = None
    
    def download_attachment(
        self,
        email_id: str,
        attachment_id: str,
        filename: str
    ) -> Optional[Path]:
        """
        Download an attachment to temporary directory.
        
        Args:
            email_id: Email ID
            attachment_id: Attachment ID
            filename: Attachment filename
            
        Returns:
            Path to downloaded file or None if failed
        """
        try:
            # Ensure session directory exists
            if not self.session_dir:
                self.create_session_dir(email_id)
            
            # Sanitize filename
            safe_filename = sanitize_filename(filename)
            file_path = self.session_dir / safe_filename
            
            logger.info(f"Downloading attachment: {filename}")
            
            # Download using Gmail client
            attachment_data = self.gmail_client.get_attachment(email_id, attachment_id)
            
            if attachment_data:
                with open(file_path, 'wb') as f:
                    f.write(attachment_data)
                logger.info(f"Downloaded to: {file_path}")
                return file_path
            else:
                logger.error(f"No data received for attachment: {filename}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading attachment {filename}: {e}")
            return None
    
    def extract_text_from_attachment(self, file_path: Path) -> Optional[str]:
        """
        Extract text from an attachment file.
        
        Args:
            file_path: Path to attachment file
            
        Returns:
            Extracted text or None if extraction failed
        """
        try:
            extension = get_file_extension(file_path.name)
            
            if extension not in self.SUPPORTED_TYPES:
                logger.debug(f"Unsupported file type: {extension}")
                return None
            
            logger.info(f"Extracting text from {file_path.name} ({extension})")
            
            # Get appropriate extraction function
            extract_func = self.SUPPORTED_TYPES[extension]
            
            # Extract text
            text = extract_func(str(file_path))
            
            if text:
                logger.info(f"Extracted {len(text)} characters from {file_path.name}")
                return text
            else:
                logger.warning(f"No text extracted from {file_path.name}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting text from {file_path.name}: {e}")
            return None
    
    def process_attachments(
        self,
        email_id: str,
        attachments: List[Dict]
    ) -> List[Dict]:
        """
        Process all attachments for an email.
        
        Args:
            email_id: Email ID
            attachments: List of attachment metadata dicts
            
        Returns:
            List of processed attachment dicts with extracted text
        """
        processed = []
        
        try:
            # Create session directory
            self.create_session_dir(email_id)
            
            for attachment in attachments:
                filename = attachment.get('filename', 'unknown')
                attachment_id = attachment.get('attachment_id')
                
                if not attachment_id:
                    logger.warning(f"No attachment ID for {filename}")
                    continue
                
                result = {
                    'filename': filename,
                    'mime_type': attachment.get('mime_type'),
                    'size': attachment.get('size', 0),
                    'attachment_id': attachment_id,
                    'text_extracted': False,
                    'text': None,
                    'error': None
                }
                
                # Check if file type is supported
                extension = get_file_extension(filename)
                if extension not in self.SUPPORTED_TYPES:
                    result['error'] = f"Unsupported file type: {extension}"
                    processed.append(result)
                    continue
                
                # Download attachment
                file_path = self.download_attachment(email_id, attachment_id, filename)
                
                if not file_path:
                    result['error'] = "Download failed"
                    processed.append(result)
                    continue
                
                # Extract text
                text = self.extract_text_from_attachment(file_path)
                
                if text:
                    result['text_extracted'] = True
                    result['text'] = text
                    result['text_length'] = len(text)
                else:
                    result['error'] = "Text extraction failed"
                
                processed.append(result)
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing attachments: {e}")
            return processed
        
        finally:
            # Cleanup temporary files
            self.cleanup_session_dir()
    
    def get_combined_text(self, processed_attachments: List[Dict]) -> str:
        """
        Combine text from all processed attachments.
        
        Args:
            processed_attachments: List of processed attachment dicts
            
        Returns:
            Combined text from all attachments
        """
        texts = []
        
        for attachment in processed_attachments:
            if attachment.get('text_extracted') and attachment.get('text'):
                filename = attachment.get('filename', 'unknown')
                text = attachment.get('text', '')
                texts.append(f"=== {filename} ===\n{text}\n")
        
        return '\n\n'.join(texts)


# Made with Bob