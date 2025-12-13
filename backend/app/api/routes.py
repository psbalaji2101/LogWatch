"""API routes"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional
from datetime import datetime, timedelta
import logging

from pydantic import BaseModel

from app.api.models import (
    TokenResponse, LogQueryRequest, LogQueryResponse,
    LogSearchRequest, AggregationRequest, AggregationResponse,
    LogEvent
)
from app.auth.jwt_handler import create_access_token, verify_password, hash_password
from app.auth.jwt_bearer import jwt_bearer
from app.search.client import get_opensearch_client, search_logs, aggregate_logs
from app.config import settings
from datetime import datetime, timezone, timedelta
from dateutil import parser as dtparser

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

IST = timezone(timedelta(hours=5, minutes=30))

@router.get("/api/logs", response_model=LogQueryResponse, tags=["Logs"])
def query_logs(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    timestamp: Optional[str] = None,
    window_seconds: int = 3600,
    source_file: Optional[str] = None,
    page: int = 1,
    page_size: int = 100,
    token: Optional[str] = Depends(jwt_bearer)
):
    """
    Query logs by time range or specific timestamp (default: last hour)
    """
    from dateutil import parser as dtparser
    try:
        # Convert times to datetime if given as strings
        if timestamp:
            tstamp = dtparser.parse(timestamp)
            start_time = tstamp - timedelta(seconds=window_seconds / 2)
            end_time = tstamp + timedelta(seconds=window_seconds / 2)
        elif start_time and end_time:
            start_time = dtparser.parse(start_time)
            end_time = dtparser.parse(end_time)
        else:
            end_time = datetime.now()
            start_time = end_time - timedelta(seconds=window_seconds)

        client = get_opensearch_client()
        results = search_logs(
            client,
            start_time=start_time_dt,
            end_time=end_time_dt,
            source_file=source_file,
            page=page,
            page_size=page_size
        )

        log_models = [LogEvent(**log) for log in results["logs"]]
        return LogQueryResponse(
            total=results["total"],
            page=page,
            page_size=page_size,
            logs=log_models
        )
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
    start_time: str,
    end_time: str,
    interval: str = "1h",
    token: Optional[str] = Depends(jwt_bearer)
):
    """Get aggregations (time series, top tokens, source distribution)"""
    from dateutil import parser as dtparser
    try:
        start_dt = dtparser.parse(start_time)
        end_dt = dtparser.parse(end_time)
        client = get_opensearch_client()
        results = aggregate_logs(
            client,
            start_time=start_dt,
            end_time=end_dt,
            interval=interval
        )
        
        # Handle missing keys - provide defaults
        return AggregationResponse(
            time_series=results.get("time_series", []),
            top_tokens=results.get("top_tokens", []),
            sources=results.get("sources", [])
        )
    except Exception as e:
        logger.error(f"Error getting aggregations: {e}")
        # Return empty aggregations instead of error
        return AggregationResponse(
            time_series=[],
            top_tokens=[],
            sources=[]
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

class LogSearchRequest(BaseModel):
    """Log search request model"""
    start_time: str
    end_time: str
    query: Optional[str] = None
    page: int = 1
    page_size: int = 50
    fields: Optional[list[str]] = None