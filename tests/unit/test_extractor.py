"""
Unit tests for Data Extractor Service
"""

import pytest
from unittest.mock import Mock
from decimal import Decimal

from src.extractors.service import DataExtractor
from src.config.models import AppConfig


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    return Mock()


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return Mock(spec=AppConfig)


@pytest.fixture
def extractor(mock_llm_client, mock_config):
    """Create an extractor instance with mocked dependencies."""
    return DataExtractor(mock_llm_client, mock_config)


class TestDataExtractor:
    """Test cases for DataExtractor."""
    
    def test_initialization(self, extractor, mock_llm_client, mock_config):
        """Test extractor initialization."""
        assert extractor.llm_client == mock_llm_client
        assert extractor.config == mock_config
    
    def test_build_extraction_prompt_invoice(self, extractor):
        """Test invoice extraction prompt building."""
        text = "Invoice #12345 from Acme Corp. Total: $1,250.00"
        prompt = extractor._build_extraction_prompt("invoice", text)
        
        assert "invoice" in prompt.lower()
        assert "invoice_number" in prompt
        assert "vendor_name" in prompt
        assert "total_amount" in prompt
        assert text in prompt
    
    def test_build_extraction_prompt_receipt(self, extractor):
        """Test receipt extraction prompt building."""
        text = "Receipt from Store. Total: $50.00"
        prompt = extractor._build_extraction_prompt("receipt", text)
        
        assert "receipt" in prompt.lower()
        assert "merchant_name" in prompt
        assert "transaction_date" in prompt
        assert text in prompt
    
    def test_extract_invoice_success(self, extractor, mock_llm_client):
        """Test successful invoice data extraction."""
        mock_llm_client.generate.return_value = '''
        {
            "invoice_number": "INV-2024-001",
            "vendor_name": "Acme Corp",
            "vendor_email": "billing@acme.com",
            "invoice_date": "2024-01-15",
            "due_date": "2024-02-15",
            "total_amount": 1250.00,
            "currency": "USD",
            "tax_amount": 125.00,
            "subtotal": 1125.00,
            "line_items": [
                {"description": "Service A", "amount": 500.00},
                {"description": "Service B", "amount": 625.00}
            ]
        }
        '''
        
        text = "Invoice #INV-2024-001..."
        result = extractor.extract("invoice", text)
        
        assert result["invoice_number"] == "INV-2024-001"
        assert result["vendor_name"] == "Acme Corp"
        assert result["total_amount"] == 1250.00
        assert result["document_type"] == "invoice"
        assert "extracted_at" in result
        assert len(result["line_items"]) == 2
    
    def test_extract_with_markdown_json(self, extractor, mock_llm_client):
        """Test extraction with markdown-wrapped JSON."""
        mock_llm_client.generate.return_value = '''```json
        {
            "merchant_name": "Coffee Shop",
            "transaction_date": "2024-01-15",
            "total_amount": 15.50,
            "currency": "USD",
            "payment_method": "credit card"
        }
        ```'''
        
        result = extractor.extract("receipt", "Receipt text...")
        
        assert result["merchant_name"] == "Coffee Shop"
        assert result["total_amount"] == 15.50
    
    def test_extract_invalid_json(self, extractor, mock_llm_client):
        """Test handling of invalid JSON response."""
        mock_llm_client.generate.return_value = "Not valid JSON"
        
        result = extractor.extract("invoice", "Invoice text...")
        
        assert "error" in result
        assert result["document_type"] == "invoice"
    
    def test_extract_with_metadata(self, extractor, mock_llm_client):
        """Test extraction with metadata."""
        mock_llm_client.generate.return_value = '''
        {
            "invoice_number": "123",
            "vendor_name": "Test",
            "total_amount": 100.00
        }
        '''
        
        metadata = {"email_id": "abc123", "subject": "Invoice"}
        result = extractor.extract("invoice", "Text", metadata)
        
        assert result["metadata"] == metadata
    
    def test_normalize_amounts_string_currency(self, extractor):
        """Test amount normalization from currency strings."""
        data = {
            "total_amount": "$1,250.50",
            "tax_amount": "€125.00",
            "subtotal": "1125.50"
        }
        
        extractor._normalize_amounts(data)
        
        assert isinstance(data["total_amount"], float)
        assert data["total_amount"] == 1250.50
        assert isinstance(data["subtotal"], float)
    
    def test_normalize_amounts_line_items(self, extractor):
        """Test amount normalization in line items."""
        data = {
            "line_items": [
                {"description": "Item 1", "amount": "$500.00"},
                {"description": "Item 2", "amount": 625.00}
            ]
        }
        
        extractor._normalize_amounts(data)
        
        assert data["line_items"][0]["amount"] == 500.00
        assert data["line_items"][1]["amount"] == 625.00
    
    def test_normalize_amounts_transactions(self, extractor):
        """Test amount normalization in transactions."""
        data = {
            "transactions": [
                {"date": "2024-01-15", "amount": "$100.00"},
                {"date": "2024-01-16", "amount": "-50.00"}
            ]
        }
        
        extractor._normalize_amounts(data)
        
        assert data["transactions"][0]["amount"] == 100.00
        assert data["transactions"][1]["amount"] == -50.00
    
    def test_batch_extract(self, extractor, mock_llm_client):
        """Test batch extraction."""
        mock_llm_client.generate.return_value = '''
        {
            "invoice_number": "123",
            "vendor_name": "Test",
            "total_amount": 100.00
        }
        '''
        
        documents = [
            {"type": "invoice", "text": "Invoice 1"},
            {"type": "receipt", "text": "Receipt 1"}
        ]
        
        results = extractor.batch_extract(documents)
        
        assert len(results) == 2
        assert all("document_type" in r for r in results)
    
    def test_validate_extraction_complete(self, extractor):
        """Test validation of complete extraction."""
        extracted_data = {
            "invoice_number": "INV-001",
            "vendor_name": "Acme Corp",
            "total_amount": 1000.00,
            "invoice_date": "2024-01-15"
        }
        
        validation = extractor.validate_extraction(extracted_data, "invoice")
        
        assert validation["is_valid"] is True
        assert validation["completeness_score"] == 1.0
        assert len(validation["missing_fields"]) == 0
    
    def test_validate_extraction_incomplete(self, extractor):
        """Test validation of incomplete extraction."""
        extracted_data = {
            "invoice_number": "INV-001",
            "total_amount": 1000.00
        }
        
        validation = extractor.validate_extraction(extracted_data, "invoice")
        
        assert validation["is_valid"] is False
        assert validation["completeness_score"] == 0.5
        assert "vendor_name" in validation["missing_fields"]
        assert "invoice_date" in validation["missing_fields"]
    
    def test_validate_extraction_with_error(self, extractor):
        """Test validation when extraction has error."""
        extracted_data = {
            "error": "Extraction failed",
            "invoice_number": "INV-001"
        }
        
        validation = extractor.validate_extraction(extracted_data, "invoice")
        
        assert validation["is_valid"] is False
        assert any("error" in issue.lower() for issue in validation["issues"])
    
    def test_validate_extraction_negative_amount(self, extractor):
        """Test validation detects negative amounts."""
        extracted_data = {
            "invoice_number": "INV-001",
            "vendor_name": "Test",
            "total_amount": -100.00,
            "invoice_date": "2024-01-15"
        }
        
        validation = extractor.validate_extraction(extracted_data, "invoice")
        
        assert any("negative" in issue.lower() for issue in validation["issues"])
    
    def test_validate_extraction_receipt(self, extractor):
        """Test validation for receipt document type."""
        extracted_data = {
            "merchant_name": "Store",
            "transaction_date": "2024-01-15",
            "total_amount": 50.00
        }
        
        validation = extractor.validate_extraction(extracted_data, "receipt")
        
        assert validation["is_valid"] is True
        assert validation["completeness_score"] == 1.0
    
    def test_extract_exception_handling(self, extractor, mock_llm_client):
        """Test exception handling during extraction."""
        mock_llm_client.generate.side_effect = Exception("API Error")
        
        result = extractor.extract("invoice", "Text")
        
        assert "error" in result
        assert result["document_type"] == "invoice"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob
