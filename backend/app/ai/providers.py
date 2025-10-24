"""AI provider abstraction layer"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    @abstractmethod
    def generate(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate completion from messages"""
        pass


class GroqProvider(AIProvider):
    """Groq AI provider"""
    
    def __init__(self, api_key: str, model: str = "llama-3.1-70b-versatile"):
        from groq import Groq
        self.client = Groq(api_key=api_key)
        self.model = model
        logger.info(f"Initialized Groq provider with model: {model}")
    
    def generate(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate completion using Groq"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get('temperature', 0.3),
                max_tokens=kwargs.get('max_tokens', 2000),
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise


class OllamaProvider(AIProvider):
    """Ollama local provider (for future use)"""
    
    def __init__(self, base_url: str, model: str):
        import requests
        self.base_url = base_url
        self.model = model
        self.session = requests.Session()
        logger.info(f"Initialized Ollama provider: {base_url}/{model}")
    
    def generate(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate completion using Ollama"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get('temperature', 0.3),
                        "num_predict": kwargs.get('max_tokens', 2000)
                    }
                }
            )
            response.raise_for_status()
            return response.json()['message']['content']
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise


def get_ai_provider(provider_name: str, **kwargs) -> AIProvider:
    """Factory to get AI provider"""
    
    if provider_name == "groq":
        return GroqProvider(
            api_key=kwargs.get('api_key'),
            model=kwargs.get('model', 'llama-3.1-70b-versatile')
        )
    elif provider_name == "ollama":
        return OllamaProvider(
            base_url=kwargs.get('base_url', 'http://localhost:11434'),
            model=kwargs.get('model', 'llama3.2:3b')
        )
    else:
        raise ValueError(f"Unknown AI provider: {provider_name}")
