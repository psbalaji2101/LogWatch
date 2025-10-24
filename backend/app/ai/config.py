"""AI service configuration"""

from pydantic_settings import BaseSettings
from typing import Optional


class AISettings(BaseSettings):
    """AI service settings"""
    
    # Provider config (groq, openai, ollama, etc.)
    ai_provider: str = "groq"
    
    # Groq
    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.1-70b-versatile"
    
    # OpenAI (for future extensibility)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    
    # Ollama (for future extensibility)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    
    # Generation params
    ai_temperature: float = 0.3
    ai_max_tokens: int = 2000
    
    # Analysis config
    max_logs_per_analysis: int = 200
    context_window_minutes: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False


ai_settings = AISettings()

