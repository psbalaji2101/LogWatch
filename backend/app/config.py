"""Application configuration"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # OpenSearch
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_user: str = "admin"
    opensearch_password: str = "admin"
    opensearch_index_prefix: str = "logs"
    opensearch_scheme: str = "https"
    opensearch_verify_certs: bool = False
    
    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    jwt_secret: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    
    # Ingestion
    logs_directory: str = "/logs_in"
    checkpoint_db: str = "/data/checkpoints.db"
    batch_size: int = 1000
    max_workers: int = 4
    poll_interval_seconds: int = 1
    
    # Security
    require_auth: bool = False
    default_admin_user: str = "admin"
    default_admin_password: str = "admin123"
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        extra = "ignore"  # <-- allow extra keys like vite_api_url
        env_file = ".env"
        case_sensitive = False


settings = Settings()
