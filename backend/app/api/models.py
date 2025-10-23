"""API request/response models"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class LoginRequest(BaseModel):
    """Login request model"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str = "bearer"


class LogEvent(BaseModel):
    """Log event model"""
    timestamp: datetime
    source_file: str
    line_number: int
    raw_line: str
    tokens: List[str] = []
    fields: Dict[str, Any] = {}
    ingest_id: Optional[str] = None


class LogQueryRequest(BaseModel):
    """Log query request"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    timestamp: Optional[datetime] = None
    window_seconds: int = 60
    query: Optional[str] = None
    source_file: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=1000)


class LogSearchRequest(BaseModel):
    """Log search request"""
    query: str
    start_time: datetime
    end_time: datetime
    fields: Optional[List[str]] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=100, ge=1, le=1000)


class LogQueryResponse(BaseModel):
    """Log query response"""
    total: int
    page: int
    page_size: int
    logs: List[LogEvent]


class AggregationRequest(BaseModel):
    """Aggregation request"""
    start_time: datetime
    end_time: datetime
    interval: str = "1h"  # 1m, 5m, 1h, 1d


class AggregationResponse(BaseModel):
    """Aggregation response"""
    time_series: List[Dict[str, Any]]
    top_tokens: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
