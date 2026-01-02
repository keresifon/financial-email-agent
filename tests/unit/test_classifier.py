"""
Unit tests for Email Classifier Service
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.classifier.service import EmailClassifier
from src.config.models import AppConfig, ClassificationConfig, LlamaConfig


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = Mock()
    return client


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = Mock(spec=AppConfig)
    config.classification = ClassificationConfig(min_confidence=0.7)
    return config


@pytest.fixture
def classifier(mock_llm_client, mock_config):
    """Create a classifier instance with mocked dependencies."""
    return EmailClassifier(mock_llm_client, mock_config)


class TestEmailClassifier:
    """Test cases for EmailClassifier."""
    
    def test_initialization(self, classifier, mock_llm_client, mock_config):
        """Test classifier initialization."""
        assert classifier.llm_client == mock_llm_client
        assert classifier.config == mock_config
        assert classifier.min_confidence == 0.7
    
    def test_categories_defined(self, classifier):
        """Test that all categories are defined."""
        expected_categories = [
            "invoice",
            "receipt",
            "statement",
            "tax_document",
            "contract",
            "payment_confirmation",
            "other"
        ]
        assert classifier.CATEGORIES == expected_categories
        assert len(classifier.CATEGORY_DESCRIPTIONS) == len(expected_categories)
    
    def test_build_classification_prompt(self, classifier):
        """Test prompt building."""
        email_data = {
            "subject": "Invoice #12345",
            "from": "vendor@example.com",
            "body": "Please find attached invoice for services rendered.",
            "date": "2024-01-15"
        }
        
        prompt = classifier._build_classification_prompt(email_data)
        
        assert "Invoice #12345" in prompt
        assert "vendor@example.com" in prompt
        assert "invoice" in prompt.lower()
        assert "JSON" in prompt
    
    def test_classify_invoice_success(self, classifier, mock_llm_client):
        """Test successful invoice classification."""
        # Mock LLM response
        mock_llm_client.generate.return_value = '''
        {
            "category": "invoice",
            "confidence": 0.95,
            "reasoning": "Email contains invoice number and payment terms",
            "keywords": ["invoice", "payment", "due date"]
        }
        '''
        
        email_data = {
            "subject": "Invoice #12345",
            "from": "vendor@example.com",
            "body": "Invoice for services",
            "date": "2024-01-15"
        }
        
        result = classifier.classify(email_data)
        
        assert result["category"] == "invoice"
        assert result["confidence"] == 0.95
        assert result["needs_review"] is False
        assert "classified_at" in result
        assert result["email_subject"] == "Invoice #12345"
    
    def test_classify_low_confidence(self, classifier, mock_llm_client):
        """Test classification with low confidence."""
        mock_llm_client.generate.return_value = '''
        {
            "category": "other",
            "confidence": 0.5,
            "reasoning": "Unclear document type",
            "keywords": []
        }
        '''
        
        email_data = {
            "subject": "Question",
            "from": "someone@example.com",
            "body": "Just checking in",
            "date": "2024-01-15"
        }
        
        result = classifier.classify(email_data)
        
        assert result["category"] == "other"
        assert result["confidence"] == 0.5
        assert result["needs_review"] is True
    
    def test_classify_invalid_json_response(self, classifier, mock_llm_client):
        """Test handling of invalid JSON response."""
        mock_llm_client.generate.return_value = "This is not valid JSON"
        
        email_data = {
            "subject": "Test",
            "from": "test@example.com",
            "body": "Test body",
            "date": "2024-01-15"
        }
        
        result = classifier.classify(email_data)
        
        assert result["category"] == "other"
        assert result["confidence"] == 0.5
        assert "Failed to parse" in result["reasoning"]
    
    def test_classify_with_markdown_json(self, classifier, mock_llm_client):
        """Test parsing JSON wrapped in markdown code blocks."""
        mock_llm_client.generate.return_value = '''```json
        {
            "category": "receipt",
            "confidence": 0.88,
            "reasoning": "Purchase receipt",
            "keywords": ["receipt", "purchase"]
        }
        ```'''
        
        email_data = {
            "subject": "Receipt",
            "from": "store@example.com",
            "body": "Thank you for your purchase",
            "date": "2024-01-15"
        }
        
        result = classifier.classify(email_data)
        
        assert result["category"] == "receipt"
        assert result["confidence"] == 0.88
    
    def test_classify_invalid_category(self, classifier, mock_llm_client):
        """Test handling of invalid category."""
        mock_llm_client.generate.return_value = '''
        {
            "category": "invalid_category",
            "confidence": 0.9,
            "reasoning": "Test",
            "keywords": []
        }
        '''
        
        email_data = {
            "subject": "Test",
            "from": "test@example.com",
            "body": "Test",
            "date": "2024-01-15"
        }
        
        result = classifier.classify(email_data)
        
        assert result["category"] == "other"
    
    def test_classify_exception_handling(self, classifier, mock_llm_client):
        """Test exception handling during classification."""
        mock_llm_client.generate.side_effect = Exception("API Error")
        
        email_data = {
            "subject": "Test",
            "from": "test@example.com",
            "body": "Test",
            "date": "2024-01-15"
        }
        
        result = classifier.classify(email_data)
        
        assert result["category"] == "other"
        assert result["confidence"] == 0.0
        assert result["needs_review"] is True
        assert "error" in result
    
    def test_batch_classify(self, classifier, mock_llm_client):
        """Test batch classification."""
        mock_llm_client.generate.return_value = '''
        {
            "category": "invoice",
            "confidence": 0.9,
            "reasoning": "Test",
            "keywords": []
        }
        '''
        
        emails = [
            {"subject": "Invoice 1", "from": "a@example.com", "body": "Test", "date": "2024-01-15"},
            {"subject": "Invoice 2", "from": "b@example.com", "body": "Test", "date": "2024-01-16"},
        ]
        
        results = classifier.batch_classify(emails)
        
        assert len(results) == 2
        assert all(r["category"] == "invoice" for r in results)
    
    def test_get_category_stats(self, classifier):
        """Test category statistics calculation."""
        classifications = [
            {"category": "invoice", "confidence": 0.95, "needs_review": False},
            {"category": "invoice", "confidence": 0.85, "needs_review": False},
            {"category": "receipt", "confidence": 0.75, "needs_review": False},
            {"category": "other", "confidence": 0.6, "needs_review": True},
        ]
        
        stats = classifier.get_category_stats(classifications)
        
        assert stats["total"] == 4
        assert stats["by_category"]["invoice"] == 2
        assert stats["by_category"]["receipt"] == 1
        assert stats["by_category"]["other"] == 1
        assert stats["needs_review"] == 1
        assert stats["high_confidence"] == 1  # >= 0.9
        assert stats["medium_confidence"] == 2  # 0.7-0.9
        assert stats["low_confidence"] == 1  # < 0.7
        assert 0.7 < stats["avg_confidence"] < 0.8
    
    def test_get_category_stats_empty(self, classifier):
        """Test category statistics with empty list."""
        stats = classifier.get_category_stats([])
        
        assert stats["total"] == 0
        assert stats["avg_confidence"] == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob
