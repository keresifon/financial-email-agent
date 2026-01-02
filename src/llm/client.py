"""
LLM client wrapper for Ollama/Llama integration.

This module provides a client for interacting with Ollama API
to use Llama models for text generation and analysis.
"""

import json
from typing import Optional, Dict, Any, List
import httpx
from datetime import datetime

from ..config.models import LlamaConfig
from ..utils.logger import get_logger
from ..utils.retry import retry

logger = get_logger(__name__)


class LLMClient:
    """Client for interacting with Ollama API."""

    def __init__(self, config: LlamaConfig):
        """
        Initialize LLM client.

        Args:
            config: Llama configuration
        """
        self.config = config
        self.base_url = config.api_url
        self.model = config.model
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """
        Get or create HTTP client.

        Returns:
            HTTP client instance
        """
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.config.timeout_seconds,
                follow_redirects=True,
            )
        return self._client

    def close(self):
        """Close HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    @retry(max_attempts=3, delay=2.0, exceptions=(httpx.HTTPError, httpx.TimeoutException))
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> str:
        """
        Generate text using Llama model.

        Args:
            prompt: User prompt
            system: System prompt (optional)
            temperature: Sampling temperature (optional, uses config default)
            max_tokens: Maximum tokens (optional, uses config default)
            stream: Whether to stream response

        Returns:
            Generated text

        Raises:
            httpx.HTTPError: If API request fails
        """
        client = self._get_client()
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
            }
        }
        
        if system:
            payload["system"] = system
        
        logger.debug(f"Sending request to Ollama API: {self.base_url}/api/generate")
        start_time = datetime.now()
        
        try:
            response = client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.debug(f"Ollama API response received in {duration:.2f}s")
            
            result = response.json()
            return result.get("response", "")
            
        except httpx.HTTPError as e:
            logger.error(f"Ollama API request failed: {e}")
            raise

    @retry(max_attempts=3, delay=2.0, exceptions=(httpx.HTTPError, httpx.TimeoutException))
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Chat with Llama model using conversation history.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (optional)
            max_tokens: Maximum tokens (optional)

        Returns:
            Generated response

        Raises:
            httpx.HTTPError: If API request fails
        """
        client = self._get_client()
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
            }
        }
        
        logger.debug(f"Sending chat request to Ollama API")
        start_time = datetime.now()
        
        try:
            response = client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.debug(f"Ollama chat response received in {duration:.2f}s")
            
            result = response.json()
            return result.get("message", {}).get("content", "")
            
        except httpx.HTTPError as e:
            logger.error(f"Ollama chat request failed: {e}")
            raise

    def extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from LLM response.

        Args:
            text: Response text that may contain JSON

        Returns:
            Parsed JSON dict or None if not found
        """
        # Try to find JSON in the response
        try:
            # First, try to parse the entire response as JSON
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON between code blocks
        import re
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        # Try to find JSON without code blocks
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        logger.warning("Could not extract JSON from LLM response")
        return None

    def health_check(self) -> bool:
        """
        Check if Ollama API is accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            client = self._get_client()
            response = client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            
            # Check if our model is available (case-insensitive)
            data = response.json()
            models = [m.get("name") for m in data.get("models", [])]
            models_lower = [m.lower() for m in models]
            
            if self.model.lower() in models_lower:
                logger.info(f"Ollama API is healthy, model {self.model} is available")
                return True
            else:
                logger.warning(f"Model {self.model} not found in Ollama. Available models: {models}")
                return False
                
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    def list_models(self) -> List[str]:
        """
        List available models in Ollama.

        Returns:
            List of model names
        """
        try:
            client = self._get_client()
            response = client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            
            data = response.json()
            models = [m.get("name") for m in data.get("models", [])]
            return models
            
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class PromptTemplate:
    """Template for constructing prompts."""

    def __init__(self, template: str, **default_values):
        """
        Initialize prompt template.

        Args:
            template: Template string with {placeholders}
            **default_values: Default values for placeholders
        """
        self.template = template
        self.default_values = default_values

    def format(self, **kwargs) -> str:
        """
        Format template with provided values.

        Args:
            **kwargs: Values to fill in template

        Returns:
            Formatted prompt string
        """
        # Merge default values with provided values
        values = {**self.default_values, **kwargs}
        return self.template.format(**values)


# Common prompt templates
CLASSIFICATION_TEMPLATE = PromptTemplate(
    """Analyze the following email and classify it into one of these categories:
- invoice
- receipt
- bank_statement
- expense_report
- other

Email Subject: {subject}
Email Body: {body}

Respond with ONLY the category name, nothing else."""
)

EXTRACTION_TEMPLATE = PromptTemplate(
    """Extract structured information from the following {document_type}.

{content}

Extract the following fields and respond with a JSON object:
{fields}

Respond with ONLY valid JSON, no additional text."""
)

SUMMARY_TEMPLATE = PromptTemplate(
    """Summarize the following email in 2-3 sentences:

Subject: {subject}
Body: {body}

Summary:"""
)

# Made with Bob
