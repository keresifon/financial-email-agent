"""
Email Classifier Service

This service uses LLM to classify financial emails into predefined categories
with confidence scoring.
"""

import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from src.llm.client import LLMClient
from src.config.models import AppConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EmailClassifier:
    """
    Classifier for financial emails using LLM.
    
    Categories:
    - invoice: Invoices and bills
    - receipt: Purchase receipts
    - statement: Bank/credit card statements
    - tax_document: Tax-related documents
    - contract: Contracts and agreements
    - payment_confirmation: Payment confirmations
    - other: Other financial documents
    """
    
    CATEGORIES = [
        "invoice",
        "receipt",
        "statement",
        "tax_document",
        "contract",
        "payment_confirmation",
        "other"
    ]
    
    CATEGORY_DESCRIPTIONS = {
        "invoice": "Invoices, bills, or payment requests from vendors/suppliers",
        "receipt": "Purchase receipts or order confirmations",
        "statement": "Bank statements, credit card statements, or account summaries",
        "tax_document": "Tax forms, W-2s, 1099s, or tax-related documents",
        "contract": "Contracts, agreements, or legal documents with financial obligations",
        "payment_confirmation": "Payment confirmations or transaction receipts (e.g., Interac e-Transfer, PayPal)",
        "other": "Non-financial emails (marketing, promotions, newsletters, news, general information)"
    }
    
    def __init__(self, llm_client: LLMClient, config: AppConfig):
        """
        Initialize the email classifier.
        
        Args:
            llm_client: LLM client for classification
            config: Application configuration
        """
        self.llm_client = llm_client
        self.config = config
        self.min_confidence = config.classification.min_confidence
        
    def _build_classification_prompt(self, email_data: Dict) -> str:
        """
        Build the classification prompt for the LLM.
        
        Args:
            email_data: Email data including subject, body, sender, etc.
            
        Returns:
            Classification prompt
        """
        categories_list = "\n".join([
            f"- {cat}: {self.CATEGORY_DESCRIPTIONS[cat]}"
            for cat in self.CATEGORIES
        ])
        
        prompt = f"""You are a financial document classifier. Analyze the following email and classify it into one of these categories:

{categories_list}

IMPORTANT CLASSIFICATION RULES:
1. Only classify as financial categories (invoice, receipt, statement, tax_document, contract, payment_confirmation) if the email contains ACTUAL financial transactions, documents, or obligations
2. Marketing emails, promotions, newsletters, and general information should be classified as "other"
3. "contract" should only be used for actual legal agreements with financial obligations, NOT for promotional offers or general terms
4. "payment_confirmation" is for COMPLETED payments (e.g., "Your payment was received", "Transfer deposited"), NOT for payment requests or scheduled payments

Email Information:
- Subject: {email_data.get('subject', 'N/A')}
- From: {email_data.get('from', 'N/A')}
- Date: {email_data.get('date', 'N/A')}
- Attachments: {', '.join(email_data.get('attachments', [])) if email_data.get('attachments') else 'None'}
- Content (including extracted attachment text): {email_data.get('body', '')[:1000]}

Respond with a JSON object containing:
1. "category": The most appropriate category from the list above
2. "confidence": A confidence score between 0.0 and 1.0
3. "reasoning": Brief explanation for the classification
4. "keywords": List of key terms that influenced the decision

Example responses:
{{
    "category": "invoice",
    "confidence": 0.95,
    "reasoning": "Email contains invoice number, payment terms, and amount due",
    "keywords": ["invoice", "payment due", "amount", "due date"]
}}

{{
    "category": "other",
    "confidence": 0.90,
    "reasoning": "Marketing email promoting products with no actual transaction",
    "keywords": ["sale", "offer", "discount", "shop now"]
}}

Respond only with the JSON object, no additional text."""
        
        return prompt
    
    def classify(self, email_data: Dict) -> Dict:
        """
        Classify an email into a financial category.
        
        Args:
            email_data: Dictionary containing email information
                - subject: Email subject
                - from: Sender email
                - body: Email body text
                - date: Email date
                - attachments: List of attachment names (optional)
                
        Returns:
            Classification result with category, confidence, and metadata
        """
        try:
            logger.info(f"Classifying email: {email_data.get('subject', 'No subject')}")
            
            # Build prompt
            prompt = self._build_classification_prompt(email_data)
            
            # Get LLM response
            response = self.llm_client.generate(
                prompt=prompt,
                temperature=0.1,  # Low temperature for consistent classification
                max_tokens=500
            )
            
            # Parse JSON response
            try:
                # Extract JSON from response (handle markdown code blocks)
                response_text = response.strip()
                if response_text.startswith("```json"):
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif response_text.startswith("```"):
                    response_text = response_text.split("```")[1].split("```")[0].strip()
                
                result = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.debug(f"Raw response: {response}")
                # Fallback to "other" category
                result = {
                    "category": "other",
                    "confidence": 0.5,
                    "reasoning": "Failed to parse classification response",
                    "keywords": []
                }
            
            # Validate category
            category = result.get("category", "other")
            if category not in self.CATEGORIES:
                logger.warning(f"Invalid category '{category}', defaulting to 'other'")
                category = "other"
                result["category"] = category
            
            # Validate confidence
            confidence = float(result.get("confidence", 0.5))
            if not 0.0 <= confidence <= 1.0:
                logger.warning(f"Invalid confidence {confidence}, clamping to [0, 1]")
                confidence = max(0.0, min(1.0, confidence))
                result["confidence"] = confidence
            
            # Add metadata
            result["classified_at"] = datetime.utcnow().isoformat()
            result["email_subject"] = email_data.get("subject", "")
            result["email_from"] = email_data.get("from", "")
            
            # Check if confidence meets minimum threshold
            if confidence < self.min_confidence:
                logger.warning(
                    f"Classification confidence {confidence:.2f} below threshold "
                    f"{self.min_confidence:.2f}"
                )
                result["needs_review"] = True
            else:
                result["needs_review"] = False
            
            logger.info(
                f"Classified as '{category}' with confidence {confidence:.2f}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error classifying email: {e}")
            return {
                "category": "other",
                "confidence": 0.0,
                "reasoning": f"Classification error: {str(e)}",
                "keywords": [],
                "classified_at": datetime.utcnow().isoformat(),
                "email_subject": email_data.get("subject", ""),
                "email_from": email_data.get("from", ""),
                "needs_review": True,
                "error": str(e)
            }
    
    def batch_classify(self, emails: List[Dict]) -> List[Dict]:
        """
        Classify multiple emails in batch.
        
        Args:
            emails: List of email data dictionaries
            
        Returns:
            List of classification results
        """
        results = []
        
        for i, email in enumerate(emails):
            logger.info(f"Classifying email {i+1}/{len(emails)}")
            result = self.classify(email)
            results.append(result)
        
        return results
    
    def get_category_stats(self, classifications: List[Dict]) -> Dict:
        """
        Get statistics about classifications.
        
        Args:
            classifications: List of classification results
            
        Returns:
            Statistics dictionary
        """
        stats = {
            "total": len(classifications),
            "by_category": {},
            "avg_confidence": 0.0,
            "needs_review": 0,
            "high_confidence": 0,  # >= 0.9
            "medium_confidence": 0,  # 0.7 - 0.9
            "low_confidence": 0,  # < 0.7
        }
        
        if not classifications:
            return stats
        
        # Count by category
        for cat in self.CATEGORIES:
            stats["by_category"][cat] = 0
        
        total_confidence = 0.0
        
        for result in classifications:
            category = result.get("category", "other")
            confidence = result.get("confidence", 0.0)
            
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
            total_confidence += confidence
            
            if result.get("needs_review", False):
                stats["needs_review"] += 1
            
            if confidence >= 0.9:
                stats["high_confidence"] += 1
            elif confidence >= 0.7:
                stats["medium_confidence"] += 1
            else:
                stats["low_confidence"] += 1
        
        stats["avg_confidence"] = total_confidence / len(classifications)
        
        return stats

# Made with Bob
