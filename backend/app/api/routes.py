"""API routes"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional
from datetime import datetime, timedelta
import logging

from app.api.models import (
    TokenResponse, LogQueryRequest, LogQueryResponse,
    LogSearchRequest, AggregationRequest, AggregationResponse,
    LogEvent
)
from app.auth.jwt_handler import create_access_token, verify_password, hash_password
from app.auth.jwt_bearer import jwt_bearer
from app.search.client import get_opensearch_client, search_logs, aggregate_logs
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Mock user database (replace with real database in production)
USERS_DB = {
    settings.default_admin_user: {
        "username": settings.default_admin_user,
        "hashed_password": hash_password(settings.default_admin_password)
    }
}


@router.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login endpoint to get JWT token"""
    user = USERS_DB.get(form_data.username)
    
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    token = create_access_token({"sub": user["username"]})
    
    return TokenResponse(access_token=token)


@router.get("/api/logs", response_model=LogQueryResponse, tags=["Logs"])
async def query_logs(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    timestamp: Optional[datetime] = None,
    window_seconds: int = 60,
    source_file: Optional[str] = None,
    page: int = 1,
    page_size: int = 100,
    token: Optional[str] = Depends(jwt_bearer)
):
    """Query logs by time range or specific timestamp"""
    
    try:
        # Handle timestamp with window
        if timestamp:
            start_time = timestamp - timedelta(seconds=window_seconds/2)
            end_time = timestamp + timedelta(seconds=window_seconds/2)
        
        # Default to last hour if no time specified
        if not start_time or not end_time:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)
        
        client = get_opensearch_client()
        results = search_logs(
            client,
            start_time=start_time,
            end_time=end_time,
            source_file=source_file,
            page=page,
            page_size=page_size
        )
        
        return LogQueryResponse(**results)
        
    except Exception as e:
        logger.error(f"Error querying logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/api/logs/search", response_model=LogQueryResponse, tags=["Logs"])
async def search_logs_endpoint(
    request: LogSearchRequest,
    token: Optional[str] = Depends(jwt_bearer)
):
    """Search logs by query string"""
    
    try:
        client = get_opensearch_client()
        results = search_logs(
            client,
            start_time=request.start_time,
            end_time=request.end_time,
            query=request.query,
            fields=request.fields,
            page=request.page,
            page_size=request.page_size
        )
        
        return LogQueryResponse(**results)
        
    except Exception as e:
        logger.error(f"Error searching logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/api/logs/aggregations", response_model=AggregationResponse, tags=["Logs"])
async def get_aggregations(
    start_time: datetime,
    end_time: datetime,
    interval: str = "1h",
    token: Optional[str] = Depends(jwt_bearer)
):
    """Get aggregations (time series, top tokens, source distribution)"""
    
    try:
        client = get_opensearch_client()
        results = aggregate_logs(
            client,
            start_time=start_time,
            end_time=end_time,
            interval=interval
        )
        
        return AggregationResponse(**results)
        
    except Exception as e:
        logger.error(f"Error getting aggregations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/api/stats", tags=["Stats"])
async def get_stats(token: Optional[str] = Depends(jwt_bearer)):
    """Get overall statistics"""
    
    try:
        client = get_opensearch_client()
        index_name = f"{settings.opensearch_index_prefix}-*"
        
        count = client.count(index=index_name)
        indices = client.cat.indices(index=index_name, format="json")
        
        return {
            "total_events": count["count"],
            "indices": len(indices),
            "index_size": sum(int(idx.get("store.size", "0").replace("kb", "").replace("mb", "").replace("gb", "")) for idx in indices if "store.size" in idx)
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
