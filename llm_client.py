"""
Centralized LLM client for interacting with OpenRouter API.

This module provides a reusable interface for all LLM interactions,
making it easy to switch models and manage API communication.
"""

import os
import logging
from typing import Optional
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMClient:
    """
    Unified client for OpenRouter API interactions.
    
    Handles:
    - API authentication
    - Model configuration
    - Request/response management
    - Error handling
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ):
        """
        Initialize LLM client.
        
        Args:
            model: Model identifier (defaults to env var or gpt-3.5-turbo)
            temperature: Creativity level (0-1), defaults to 0.7
            max_tokens: Max response length, defaults to 1000
        """
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY not found in environment variables. "
                "Please set it in .env file or environment."
            )
        
        self.base_url = os.getenv(
            "OPENROUTER_BASE_URL",
            "https://openrouter.io/api/v1"
        )
        
        # Allow override via parameter, fall back to env, then use default
        self.model = model or os.getenv("LLM_MODEL", "openai/gpt-3.5-turbo")
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        logger.info(f"LLM Client initialized with model: {self.model}")
    
    def chat_completion(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Send a chat completion request to OpenRouter.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system instruction
            
        Returns:
            Response text from the model
            
        Raises:
            requests.RequestException: If API call fails
        """
        # Prepare system message if provided
        request_messages = messages.copy()
        if system_prompt:
            request_messages.insert(0, {
                "role": "system",
                "content": system_prompt
            })
        
        payload = {
            "model": self.model,
            "messages": request_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/yourusername/ai-patient-simulation",
            "X-Title": "AI Patient Simulation",
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
    
    def set_model(self, model: str) -> None:
        """
        Switch to a different model.
        
        Args:
            model: Model identifier (e.g., 'openai/gpt-4-turbo-preview')
        """
        self.model = model
        logger.info(f"Model switched to: {self.model}")
    
    def set_temperature(self, temperature: float) -> None:
        """Set creativity level (0-1)."""
        if not 0 <= temperature <= 1:
            raise ValueError("Temperature must be between 0 and 1")
        self.temperature = temperature
    
    def set_max_tokens(self, max_tokens: int) -> None:
        """Set maximum response tokens."""
        if max_tokens < 1:
            raise ValueError("Max tokens must be at least 1")
        self.max_tokens = max_tokens


# Global client instance
_client = None


def get_llm_client(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> LLMClient:
    """
    Get or create the global LLM client.
    
    Useful for consistent client usage across modules.
    
    Args:
        model: Override model selection
        temperature: Override temperature
        max_tokens: Override max tokens
        
    Returns:
        LLMClient instance
    """
    global _client
    
    if _client is None:
        _client = LLMClient(model=model, temperature=temperature or 0.7, max_tokens=max_tokens or 1000)
    else:
        if model:
            _client.set_model(model)
        if temperature is not None:
            _client.set_temperature(temperature)
        if max_tokens is not None:
            _client.set_max_tokens(max_tokens)
    
    return _client
