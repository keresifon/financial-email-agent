"""
Integration tests for complete email processing workflow
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.main import FinancialEmailAgent
from src.config.loader import load_config


@pytest.fixture
def mock_db_connection():
    """Mock MongoDB connection."""
    with patch('src.main.MongoDBConnection') as mock:
        connection = Mock()
        db = Mock()
        
        # Mock collections
        collection = Mock()
        collection.insert_one.return_value = Mock(inserted_id="test_id_123")
        collection.count_documents.return_value = 10
        collection.find.return_value = Mock()
        collection.aggregate.return_value = []
        
        db.__getitem__ = Mock(return_value=collection)
        db.list_collection_names.return_value = ["emails", "invoices"]
        
        connection.get_database.return_value = db
        connection.connect.return_value = None
        connection.disconnect.return_value = None
        
        mock.return_value = connection
        yield mock


@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""
    with patch('src.main.LLMClient') as mock:
        client = Mock()
        
        # Mock classification response
        client.generate.return_value = '''
        {
            "category": "invoice",
            "confidence": 0.95,
            "reasoning": "Email contains invoice number and payment terms",
            "keywords": ["invoice", "payment", "due date"]
        }
        '''
        
        mock.return_value = client
        yield mock


@pytest.fixture
def mock_email_service():
    """Mock Email Service."""
    with patch('src.main.EmailService') as mock:
        service = Mock()
        
        # Mock email data
        service.get_financial_emails.return_value = [
            {
                "id": "email_123",
                "threadId": "thread_123",
                "subject": "Invoice #12345",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Invoice #12345"},
                        {"name": "From", "value": "vendor@example.com"},
                        {"name": "Date", "value": "Mon, 15 Jan 2024 10:00:00 +0000"}
                    ],
                    "body": {"data": "SW52b2ljZSBkZXRhaWxz"}  # Base64 encoded
                }
            }
        ]
        
        service.parse_email.return_value = {
            "id": "email_123",
            "subject": "Invoice #12345",
            "from": "vendor@example.com",
            "body": "Invoice for services rendered. Amount: $1,250.00",
            "date": "2024-01-15",
            "attachments": []
        }
        
        service.mark_as_read.return_value = True
        service.move_to_folder.return_value = True
        
        mock.return_value = service
        yield mock


class TestWorkflowIntegration:
    """Integration tests for complete workflow."""
    
    def test_agent_initialization(self, mock_db_connection, mock_llm_client, mock_email_service):
        """Test agent initialization with all dependencies."""
        config = load_config()
        agent = FinancialEmailAgent(config)
        
        assert agent.config == config
        assert agent.db_connection is not None
        assert agent.llm_client is not None
        assert agent.email_service is not None
        assert agent.classifier is not None
        assert agent.extractor is not None
    
    def test_process_single_email(self, mock_db_connection, mock_llm_client, mock_email_service):
        """Test processing a single email through complete pipeline."""
        config = load_config()
        agent = FinancialEmailAgent(config)
        
        # Mock extractor response
        with patch.object(agent.extractor, 'extract') as mock_extract:
            mock_extract.return_value = {
                "invoice_number": "INV-12345",
                "vendor_name": "Acme Corp",
                "total_amount": 1250.00,
                "currency": "USD",
                "invoice_date": "2024-01-15"
            }
            
            with patch.object(agent.extractor, 'validate_extraction') as mock_validate:
                mock_validate.return_value = {
                    "is_valid": True,
                    "completeness_score": 1.0,
                    "issues": [],
                    "missing_fields": []
                }
                
                email_data = {
                    "id": "email_123",
                    "subject": "Invoice #12345",
                    "payload": {
                        "headers": [
                            {"name": "Subject", "value": "Invoice #12345"},
                            {"name": "From", "value": "vendor@example.com"}
                        ]
                    }
                }
                
                result = agent.process_email(email_data)
                
                assert result["status"] == "success"
                assert result["email_id"] == "email_123"
                assert "classification" in result
                assert result["classification"]["category"] == "invoice"
                assert "extracted_data" in result
                assert "database_id" in result
                assert result["steps"]["parse"]["status"] == "success"
                assert result["steps"]["classify"]["status"] == "success"
                assert result["steps"]["extract"]["status"] == "success"
                assert result["steps"]["store"]["status"] == "success"
    
    def test_process_email_low_confidence(self, mock_db_connection, mock_llm_client, mock_email_service):
        """Test processing email with low confidence classification."""
        config = load_config()
        agent = FinancialEmailAgent(config)
        
        # Mock low confidence classification
        with patch.object(agent.classifier, 'classify') as mock_classify:
            mock_classify.return_value = {
                "category": "other",
                "confidence": 0.5,
                "reasoning": "Unclear document type",
                "keywords": [],
                "needs_review": True
            }
            
            email_data = {
                "id": "email_456",
                "subject": "Question",
                "payload": {"headers": []}
            }
            
            result = agent.process_email(email_data)
            
            assert result["status"] == "success"
            assert result["steps"]["extract"]["status"] == "skipped"
            assert "Low confidence" in result["steps"]["extract"]["reason"]
    
    def test_process_batch(self, mock_db_connection, mock_llm_client, mock_email_service):
        """Test batch processing of multiple emails."""
        config = load_config()
        agent = FinancialEmailAgent(config)
        
        with patch.object(agent, 'process_email') as mock_process:
            mock_process.return_value = {
                "status": "success",
                "email_id": "test_123"
            }
            
            summary = agent.process_batch(max_emails=10)
            
            assert "total_fetched" in summary
            assert "total_processed" in summary
            assert "successful" in summary
            assert "failed" in summary
            assert "started_at" in summary
            assert "completed_at" in summary
    
    def test_process_email_with_error(self, mock_db_connection, mock_llm_client, mock_email_service):
        """Test error handling during email processing."""
        config = load_config()
        agent = FinancialEmailAgent(config)
        
        # Mock classifier to raise exception
        with patch.object(agent.classifier, 'classify') as mock_classify:
            mock_classify.side_effect = Exception("Classification error")
            
            email_data = {
                "id": "email_error",
                "subject": "Test",
                "payload": {"headers": []}
            }
            
            result = agent.process_email(email_data)
            
            assert result["status"] == "error"
            assert "error" in result
    
    def test_get_statistics(self, mock_db_connection, mock_llm_client, mock_email_service):
        """Test getting database statistics."""
        config = load_config()
        agent = FinancialEmailAgent(config)
        
        stats = agent.get_statistics()
        
        assert "total_emails" in stats
        assert "by_category" in stats
        assert "by_collection" in stats
        assert "recent_activity" in stats
    
    def test_cleanup(self, mock_db_connection, mock_llm_client, mock_email_service):
        """Test resource cleanup."""
        config = load_config()
        agent = FinancialEmailAgent(config)
        
        agent.cleanup()
        
        agent.db_connection.disconnect.assert_called_once()


class TestEndToEndScenarios:
    """End-to-end scenario tests."""
    
    def test_invoice_processing_scenario(self, mock_db_connection, mock_llm_client, mock_email_service):
        """Test complete invoice processing scenario."""
        config = load_config()
        agent = FinancialEmailAgent(config)
        
        # Setup mocks for invoice scenario
        with patch.object(agent.classifier, 'classify') as mock_classify:
            mock_classify.return_value = {
                "category": "invoice",
                "confidence": 0.95,
                "reasoning": "Contains invoice number and payment terms",
                "keywords": ["invoice", "payment", "due"],
                "needs_review": False
            }
            
            with patch.object(agent.extractor, 'extract') as mock_extract:
                mock_extract.return_value = {
                    "invoice_number": "INV-2024-001",
                    "vendor_name": "Acme Corp",
                    "vendor_email": "billing@acme.com",
                    "invoice_date": "2024-01-15",
                    "due_date": "2024-02-15",
                    "total_amount": 1250.00,
                    "currency": "USD",
                    "line_items": [
                        {"description": "Service A", "amount": 500.00},
                        {"description": "Service B", "amount": 750.00}
                    ]
                }
                
                with patch.object(agent.extractor, 'validate_extraction') as mock_validate:
                    mock_validate.return_value = {
                        "is_valid": True,
                        "completeness_score": 1.0,
                        "issues": [],
                        "missing_fields": []
                    }
                    
                    email_data = {
                        "id": "invoice_email",
                        "subject": "Invoice INV-2024-001",
                        "payload": {
                            "headers": [
                                {"name": "Subject", "value": "Invoice INV-2024-001"},
                                {"name": "From", "value": "billing@acme.com"}
                            ]
                        }
                    }
                    
                    result = agent.process_email(email_data)
                    
                    # Verify complete workflow
                    assert result["status"] == "success"
                    assert result["classification"]["category"] == "invoice"
                    assert result["classification"]["confidence"] == 0.95
                    assert result["extracted_data"]["invoice_number"] == "INV-2024-001"
                    assert result["extracted_data"]["total_amount"] == 1250.00
                    assert result["validation"]["is_valid"] is True
                    assert all(step["status"] in ["success", "skipped"] for step in result["steps"].values())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob
