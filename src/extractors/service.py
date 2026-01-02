"""
Data Extractor Service

This service uses LLM to extract structured financial data from emails and documents.
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal

from src.llm.client import LLMClient
from src.config.models import AppConfig
from src.utils.logger import get_logger
from src.utils.helpers import parse_currency

logger = get_logger(__name__)


class DataExtractor:
    """
    Extractor for financial data from emails and documents using LLM.
    
    Extracts:
    - Invoice data: invoice number, amount, due date, vendor
    - Receipt data: merchant, amount, date, items
    - Statement data: account number, period, transactions
    - Payment data: amount, date, reference number
    """
    
    def __init__(self, llm_client: LLMClient, config: AppConfig):
        """
        Initialize the data extractor.
        
        Args:
            llm_client: LLM client for extraction
            config: Application configuration
        """
        self.llm_client = llm_client
        self.config = config
    
    def _build_extraction_prompt(self, document_type: str, text: str) -> str:
        """
        Build the extraction prompt for the LLM.
        
        Args:
            document_type: Type of document (invoice, receipt, statement, etc.)
            text: Document text to extract from
            
        Returns:
            Extraction prompt
        """
        prompts = {
            "invoice": """Extract the following information from this invoice:

Required fields:
- invoice_number: Invoice or bill number
- vendor_name: Name of the vendor/supplier
- vendor_email: Vendor email address (if available)
- invoice_date: Date of invoice
- due_date: Payment due date
- total_amount: Total amount due
- currency: Currency code (USD, EUR, etc.)
- line_items: List of items/services with description and amount

Optional fields:
- tax_amount: Tax amount
- subtotal: Subtotal before tax
- payment_terms: Payment terms (e.g., "Net 30")
- purchase_order: PO number if available

Document text:
{text}

Respond with a JSON object containing the extracted data. Use null for missing fields.
Example:
{{
    "invoice_number": "INV-2024-001",
    "vendor_name": "Acme Corp",
    "vendor_email": "billing@acme.com",
    "invoice_date": "2024-01-15",
    "due_date": "2024-02-15",
    "total_amount": 1250.00,
    "currency": "USD",
    "tax_amount": 125.00,
    "subtotal": 1125.00,
    "payment_terms": "Net 30",
    "line_items": [
        {{"description": "Service A", "amount": 500.00}},
        {{"description": "Service B", "amount": 625.00}}
    ]
}}""",
            
            "receipt": """Extract the following information from this receipt:

Required fields:
- merchant_name: Name of the merchant/store
- transaction_date: Date of purchase
- total_amount: Total amount paid
- currency: Currency code
- payment_method: Payment method (credit card, cash, etc.)

Optional fields:
- transaction_id: Transaction or receipt number
- items: List of purchased items with description and price
- tax_amount: Tax amount
- subtotal: Subtotal before tax
- merchant_address: Store address
- merchant_phone: Store phone number

Document text:
{text}

Respond with a JSON object containing the extracted data. Use null for missing fields.""",
            
            "statement": """Extract the following information from this bank/credit card statement:

Required fields:
- account_number: Account number (last 4 digits only for security)
- statement_period_start: Statement period start date
- statement_period_end: Statement period end date
- opening_balance: Opening balance
- closing_balance: Closing balance
- currency: Currency code

Optional fields:
- account_holder: Account holder name
- institution_name: Bank/financial institution name
- transactions: List of transactions with date, description, and amount
- total_credits: Total credits/deposits
- total_debits: Total debits/withdrawals

Document text:
{text}

Respond with a JSON object containing the extracted data. Use null for missing fields.""",
            
            "payment_confirmation": """Extract the following information from this payment confirmation:

Required fields:
- payment_amount: Amount paid
- payment_date: Date of payment
- currency: Currency code
- recipient: Payment recipient name

Optional fields:
- confirmation_number: Confirmation or reference number
- payment_method: Payment method used
- transaction_id: Transaction ID
- invoice_number: Related invoice number
- account_number: Account number (last 4 digits)

Document text:
{text}

Respond with a JSON object containing the extracted data. Use null for missing fields."""
        }
        
        template = prompts.get(document_type, prompts["invoice"])
        return template.format(text=text[:4000])  # Limit text length
    
    def extract(self, document_type: str, text: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Extract structured data from document text.
        
        Args:
            document_type: Type of document (invoice, receipt, statement, payment_confirmation)
            text: Document text to extract from
            metadata: Optional metadata about the document
            
        Returns:
            Extracted data dictionary
        """
        try:
            logger.info(f"Extracting data from {document_type}")
            
            # Build prompt
            prompt = self._build_extraction_prompt(document_type, text)
            
            # Get LLM response
            response = self.llm_client.generate(
                prompt=prompt,
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=2000
            )
            
            # Parse JSON response
            try:
                # Extract JSON from response (handle markdown code blocks)
                response_text = response.strip()
                if response_text.startswith("```json"):
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif response_text.startswith("```"):
                    response_text = response_text.split("```")[1].split("```")[0].strip()
                
                extracted_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.debug(f"Raw response: {response}")
                extracted_data = {
                    "error": "Failed to parse extraction response",
                    "raw_response": response[:500]
                }
            
            # Add metadata
            extracted_data["document_type"] = document_type
            extracted_data["extracted_at"] = datetime.utcnow().isoformat()
            extracted_data["extraction_method"] = "llm"
            
            if metadata:
                extracted_data["metadata"] = metadata
            
            # Validate and normalize amounts
            self._normalize_amounts(extracted_data)
            
            logger.info(f"Successfully extracted data from {document_type}")
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error extracting data from {document_type}: {e}")
            return {
                "document_type": document_type,
                "extracted_at": datetime.utcnow().isoformat(),
                "extraction_method": "llm",
                "error": str(e),
                "metadata": metadata
            }
    
    def _normalize_amounts(self, data: Dict) -> None:
        """
        Normalize currency amounts in extracted data.
        
        Args:
            data: Extracted data dictionary (modified in place)
        """
        amount_fields = [
            "total_amount", "tax_amount", "subtotal", "payment_amount",
            "opening_balance", "closing_balance", "total_credits", "total_debits"
        ]
        
        for field in amount_fields:
            if field in data and data[field] is not None:
                try:
                    # Convert to float if it's a string
                    if isinstance(data[field], str):
                        # Try to parse as currency
                        parsed = parse_currency(data[field])
                        if parsed:
                            data[field] = float(parsed)
                        else:
                            data[field] = float(data[field])
                    elif isinstance(data[field], (int, float, Decimal)):
                        data[field] = float(data[field])
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to normalize amount field '{field}': {e}")
        
        # Normalize line items
        if "line_items" in data and isinstance(data["line_items"], list):
            for item in data["line_items"]:
                if isinstance(item, dict) and "amount" in item:
                    try:
                        if isinstance(item["amount"], str):
                            parsed = parse_currency(item["amount"])
                            item["amount"] = float(parsed) if parsed else 0.0
                        else:
                            item["amount"] = float(item["amount"])
                    except (ValueError, TypeError):
                        item["amount"] = 0.0
        
        # Normalize transactions
        if "transactions" in data and isinstance(data["transactions"], list):
            for txn in data["transactions"]:
                if isinstance(txn, dict) and "amount" in txn:
                    try:
                        if isinstance(txn["amount"], str):
                            parsed = parse_currency(txn["amount"])
                            txn["amount"] = float(parsed) if parsed else 0.0
                        else:
                            txn["amount"] = float(txn["amount"])
                    except (ValueError, TypeError):
                        txn["amount"] = 0.0
    
    def batch_extract(self, documents: List[Dict]) -> List[Dict]:
        """
        Extract data from multiple documents in batch.
        
        Args:
            documents: List of document dictionaries with 'type' and 'text' keys
            
        Returns:
            List of extraction results
        """
        results = []
        
        for i, doc in enumerate(documents):
            logger.info(f"Extracting document {i+1}/{len(documents)}")
            
            doc_type = doc.get("type", "invoice")
            text = doc.get("text", "")
            metadata = doc.get("metadata")
            
            result = self.extract(doc_type, text, metadata)
            results.append(result)
        
        return results
    
    def validate_extraction(self, extracted_data: Dict, document_type: str) -> Dict:
        """
        Validate extracted data for completeness and accuracy.
        
        Args:
            extracted_data: Extracted data dictionary
            document_type: Type of document
            
        Returns:
            Validation result with issues and completeness score
        """
        validation = {
            "is_valid": True,
            "completeness_score": 0.0,
            "issues": [],
            "missing_fields": [],
            "validated_at": datetime.utcnow().isoformat()
        }
        
        # Define required fields by document type
        required_fields = {
            "invoice": ["invoice_number", "vendor_name", "total_amount", "invoice_date"],
            "receipt": ["merchant_name", "transaction_date", "total_amount"],
            "statement": ["account_number", "statement_period_start", "statement_period_end"],
            "payment_confirmation": ["payment_amount", "payment_date", "recipient"]
        }
        
        required = required_fields.get(document_type, [])
        
        # Check for required fields
        present_fields = 0
        for field in required:
            if field in extracted_data and extracted_data[field] is not None:
                present_fields += 1
            else:
                validation["missing_fields"].append(field)
                validation["issues"].append(f"Missing required field: {field}")
        
        # Calculate completeness score
        if required:
            validation["completeness_score"] = present_fields / len(required)
        
        # Check for errors in extraction
        if "error" in extracted_data:
            validation["is_valid"] = False
            validation["issues"].append(f"Extraction error: {extracted_data['error']}")
        
        # Validate amounts are positive
        amount_fields = ["total_amount", "payment_amount", "tax_amount"]
        for field in amount_fields:
            if field in extracted_data and extracted_data[field] is not None:
                try:
                    amount = float(extracted_data[field])
                    if amount < 0:
                        validation["issues"].append(f"Negative amount in field: {field}")
                except (ValueError, TypeError):
                    validation["issues"].append(f"Invalid amount format in field: {field}")
        
        # Set overall validity
        if validation["completeness_score"] < 0.5:
            validation["is_valid"] = False
        
        return validation

# Made with Bob
