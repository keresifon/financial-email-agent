"""
Utility helper functions for the Financial Email Agent.

This module provides common utility functions used throughout the application.
"""

import re
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from decimal import Decimal, InvalidOperation


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a filename by removing invalid characters.

    Args:
        filename: Original filename
        max_length: Maximum filename length

    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip('. ')
    
    # Truncate if too long
    if len(sanitized) > max_length:
        name, ext = Path(sanitized).stem, Path(sanitized).suffix
        max_name_length = max_length - len(ext)
        sanitized = name[:max_name_length] + ext
    
    return sanitized or 'unnamed'


def generate_hash(data: Union[str, bytes], algorithm: str = 'sha256') -> str:
    """
    Generate a hash for the given data.

    Args:
        data: Data to hash (string or bytes)
        algorithm: Hash algorithm (md5, sha1, sha256, sha512)

    Returns:
        Hexadecimal hash string
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    hash_func = hashlib.new(algorithm)
    hash_func.update(data)
    return hash_func.hexdigest()


def parse_currency(value: str) -> Optional[Decimal]:
    """
    Parse a currency string to Decimal.

    Args:
        value: Currency string (e.g., "$1,234.56", "€1.234,56")

    Returns:
        Decimal value or None if parsing fails
    """
    if not value:
        return None
    
    # Remove currency symbols and whitespace
    cleaned = re.sub(r'[^\d.,\-+]', '', value)
    
    # Handle different decimal separators
    # If there are multiple commas or dots, assume the last one is decimal
    if ',' in cleaned and '.' in cleaned:
        # Determine which is the decimal separator
        last_comma = cleaned.rfind(',')
        last_dot = cleaned.rfind('.')
        
        if last_comma > last_dot:
            # Comma is decimal separator (European format)
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            # Dot is decimal separator (US format)
            cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        # Only commas - could be thousands or decimal
        comma_count = cleaned.count(',')
        if comma_count == 1 and len(cleaned.split(',')[1]) <= 2:
            # Likely decimal separator
            cleaned = cleaned.replace(',', '.')
        else:
            # Likely thousands separator
            cleaned = cleaned.replace(',', '')
    
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def extract_email_address(text: str) -> Optional[str]:
    """
    Extract email address from text.

    Args:
        text: Text containing email address

    Returns:
        Email address or None if not found
    """
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(pattern, text)
    return match.group(0) if match else None


def extract_phone_number(text: str) -> Optional[str]:
    """
    Extract phone number from text.

    Args:
        text: Text containing phone number

    Returns:
        Phone number or None if not found
    """
    # Pattern for various phone formats
    patterns = [
        r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # +1-234-567-8900
        r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # (234) 567-8900
        r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',  # 234-567-8900
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    
    return None


def extract_date(text: str) -> Optional[datetime]:
    """
    Extract date from text using common formats.

    Args:
        text: Text containing date

    Returns:
        datetime object or None if not found
    """
    # Common date patterns
    patterns = [
        (r'\d{4}-\d{2}-\d{2}', '%Y-%m-%d'),  # 2024-01-15
        (r'\d{2}/\d{2}/\d{4}', '%m/%d/%Y'),  # 01/15/2024
        (r'\d{2}-\d{2}-\d{4}', '%m-%d-%Y'),  # 01-15-2024
        (r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}', '%d %B %Y'),
    ]
    
    for pattern, date_format in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return datetime.strptime(match.group(0), date_format)
            except ValueError:
                continue
    
    return None


def mask_sensitive_data(text: str, mask_char: str = '*') -> str:
    """
    Mask sensitive data in text (emails, phone numbers, credit cards).

    Args:
        text: Text to mask
        mask_char: Character to use for masking

    Returns:
        Masked text
    """
    # Mask email addresses
    text = re.sub(
        r'\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b',
        lambda m: f"{m.group(1)[:2]}{mask_char * 3}@{m.group(2)}",
        text
    )
    
    # Mask phone numbers
    text = re.sub(
        r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',
        lambda m: f"{mask_char * 3}-{mask_char * 3}-{m.group(0)[-4:]}",
        text
    )
    
    # Mask credit card numbers
    text = re.sub(
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        lambda m: f"{mask_char * 4}-{mask_char * 4}-{mask_char * 4}-{m.group(0)[-4:]}",
        text
    )
    
    return text


def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.

    Args:
        dict1: First dictionary
        dict2: Second dictionary (takes precedence)

    Returns:
        Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Safely parse JSON string.

    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails

    Returns:
        Parsed JSON or default value
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, default: str = '{}') -> str:
    """
    Safely serialize object to JSON string.

    Args:
        obj: Object to serialize
        default: Default value if serialization fails

    Returns:
        JSON string or default value
    """
    try:
        return json.dumps(obj, default=str, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return default


def get_file_extension(filename: str) -> str:
    """
    Get file extension from filename.

    Args:
        filename: Filename or path

    Returns:
        File extension (lowercase, without dot)
    """
    return Path(filename).suffix.lower().lstrip('.')


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure directory exists, create if it doesn't.

    Args:
        path: Directory path

    Returns:
        Path object
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_timestamp(tz: Optional[timezone] = None) -> str:
    """
    Get current timestamp in ISO format.

    Args:
        tz: Timezone (defaults to UTC)

    Returns:
        ISO format timestamp string
    """
    if tz is None:
        tz = timezone.utc
    return datetime.now(tz).isoformat()


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split a list into chunks of specified size.

    Args:
        lst: List to chunk
        chunk_size: Size of each chunk

    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """
    Flatten a nested dictionary.

    Args:
        d: Dictionary to flatten
        parent_key: Parent key prefix
        sep: Separator for nested keys

    Returns:
        Flattened dictionary
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

# Made with Bob



def extract_text_from_pdf(file_path: str, pages: Optional[List[int]] = None) -> str:
    """
    Extract text from PDF file.

    Args:
        file_path: Path to PDF file
        pages: Specific pages to extract (None for all pages)

    Returns:
        Extracted text
    """
    try:
        import PyPDF2
        
        text = []
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            
            pages_to_extract = pages if pages else range(total_pages)
            
            for page_num in pages_to_extract:
                if 0 <= page_num < total_pages:
                    page = pdf_reader.pages[page_num]
                    text.append(page.extract_text())
        
        return '\n\n'.join(text)
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {e}")


def extract_text_from_image(file_path: str, language: str = 'eng') -> str:
    """
    Extract text from image using OCR (Tesseract).

    Args:
        file_path: Path to image file
        language: OCR language code (default: 'eng')

    Returns:
        Extracted text
    """
    try:
        import pytesseract
        from PIL import Image
        
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image, lang=language)
        return text.strip()
    except Exception as e:
        raise Exception(f"Failed to extract text from image: {e}")


def parse_excel_file(file_path: str, sheet_name: Optional[str] = None, max_rows: int = 1000) -> List[Dict[str, Any]]:
    """
    Parse Excel or CSV file.

    Args:
        file_path: Path to Excel/CSV file
        sheet_name: Sheet name for Excel files (None for first sheet)
        max_rows: Maximum number of rows to return

    Returns:
        List of dictionaries representing rows
    """
    try:
        import pandas as pd
        
        file_ext = get_file_extension(file_path)
        
        if file_ext == 'csv':
            df = pd.read_csv(file_path, nrows=max_rows)
        elif file_ext in ['xlsx', 'xls']:
            df = pd.read_excel(file_path, sheet_name=sheet_name or 0, nrows=max_rows)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        # Convert to list of dictionaries
        return df.to_dict('records')
    except Exception as e:
        raise Exception(f"Failed to parse Excel file: {e}")


def extract_text_from_docx(file_path: str) -> str:
    """
    Extract text from Word document (.docx).

    Args:
        file_path: Path to DOCX file

    Returns:
        Extracted text
    """
    try:
        from docx import Document
        
        doc = Document(file_path)
        text = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text.append(paragraph.text)
        
        return '\n\n'.join(text)
    except Exception as e:
        raise Exception(f"Failed to extract text from DOCX: {e}")


def get_file_metadata(file_path: str) -> Dict[str, Any]:
    """
    Get file metadata (size, timestamps, etc.).

    Args:
        file_path: Path to file

    Returns:
        Dictionary with file metadata
    """
    try:
        import os
        from datetime import datetime
        
        stat = os.stat(file_path)
        
        return {
            'size': stat.st_size,
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'accessed': datetime.fromtimestamp(stat.st_atime).isoformat(),
        }
    except Exception as e:
        raise Exception(f"Failed to get file metadata: {e}")
