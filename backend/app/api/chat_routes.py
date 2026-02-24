"""Chat API routes"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import re

from app.ai.analyzer import get_analyzer
from app.auth.jwt_bearer import jwt_bearer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])


# Request/Response models
class AnalyzeRequest(BaseModel):
    """Log analysis request"""
    timestamp: Optional[datetime] = None
    keywords: Optional[str] = None
    time_window_minutes: int = Field(default=30, ge=1, le=1440)
    chat_history: Optional[List[Dict[str, str]]] = None
    natural_language_query: Optional[str] = None  # NEW
    source_file: Optional[str] = None  # NEW


class AnalyzeResponse(BaseModel):
    """Log analysis response"""
    analysis: str
    summary: Dict[str, Any]
    suggested_queries: List[str]
    chart_data: Optional[Dict[str, Any]]
    timestamp: str
    keywords: Optional[str] = None
    time_window_minutes: int = Field(default=30, ge=1, le=10080)
    chat_history: Optional[List[Dict[str, str]]] = None
    natural_language_query: Optional[str] = None
    source_file: Optional[str] = None


class FeedbackRequest(BaseModel):
    """User feedback on AI response"""
    message_id: str
    rating: int = Field(ge=-1, le=1)  # -1: thumbs down, 1: thumbs up
    comment: Optional[str] = None


def parse_natural_language_query(query: str) -> dict:
    """
    Parse natural language query to extract keywords, time, and file filters.
    Supports phrases like:
      - "last 5 hours"
      - "past 30 minutes"
      - "analyze logs from the past week"
      - "in format1_2025-11-02.log"
    """
    query_lower = query.lower()
    
    # Default time window (in minutes)
    time_window = 30

    # Expanded regex patterns
    time_patterns = [
        (r'\b(\d+)\s*minute(s)?\b', 1),
        (r'\b(\d+)\s*min\b', 1),
        (r'\b(\d+)\s*hour(s)?\b', 60),
        (r'\b(\d+)\s*h\b', 60),
        (r'\b(\d+)\s*day(s)?\b', 1440),
        (r'\b(\d+)\s*week(s)?\b', 10080),
        (r'\blast\s+(\d+)\s*minute(s)?\b', 1),
        (r'\blast\s+(\d+)\s*hour(s)?\b', 60),
        (r'\blast\s+(\d+)\s*day(s)?\b', 1440),
        (r'\blast\s+(\d+)\s*week(s)?\b', 10080),
        (r'\bpast\s+(\d+)\s*minute(s)?\b', 1),
        (r'\bpast\s+(\d+)\s*hour(s)?\b', 60),
        (r'\bpast\s+(\d+)\s*day(s)?\b', 1440),
        (r'\bpast\s+(\d+)\s*week(s)?\b', 10080),
        # Handle singular forms: "last hour", "past day", etc.
        (r'\blast\s+hour\b', 60),
        (r'\blast\s+day\b', 1440),
        (r'\blast\s+week\b', 10080),
        (r'\bpast\s+hour\b', 60),
        (r'\bpast\s+day\b', 1440),
        (r'\bpast\s+week\b', 10080),
    ]

    for pattern, multiplier in time_patterns:
        match = re.search(pattern, query_lower)
        if match:
            amount = int(match.group(1)) if match.groups()[0] else 1
            time_window = amount * multiplier
            logger.info(f"✅ [NL Parse] Matched pattern: {pattern} → {amount} × {multiplier} = {time_window} minutes")
            break
    else:
        logger.info(f"ℹ️ [NL Parse] No time pattern matched, using default: {time_window} minutes")

    # (Optional) remove cap if you want more than 1 day
    # time_window = min(time_window, 1440)

    # Extract keywords
    keywords = None
    keyword_mapping = {
        'error': 'ERROR',
        'errors': 'ERROR',
        'warning': 'WARNING',
        'warnings': 'WARNING',
        'warn': 'WARN',
        'database': 'database',
        'db': 'database',
        'payment': 'payment',
        'timeout': 'timeout',
        'memory': 'memory',
        'fail': 'fail',
        'failure': 'fail',
        'crash': 'crash',
        'down': 'down',
    }

    for word, keyword in keyword_mapping.items():
        if word in query_lower:
            keywords = keyword
            break

    # Extract file reference (if mentioned)
    source_file = None
    for pattern in [
        r'file\s+(\S+\.log)',
        r'from\s+(\S+\.log)',
        r'in\s+(\S+\.log)',
        r'(format\d+_\w+\.log)',
    ]:
        match = re.search(pattern, query_lower)
        if match:
            source_file = match.group(1)
            break

    if source_file and not source_file.startswith('/'):
        source_file = f"/logs_in/{source_file}"

    logger.info(f"✅ [NL Parse] Query received: {query_lower}")
    logger.info(f"✅ [NL Parse] Parsed -> time_window: {time_window}, keywords: {keywords}, source_file: {source_file}")

    return {
        "keywords": keywords,
        "time_window_minutes": time_window,
        "source_file": source_file
    }


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_logs(
    request: AnalyzeRequest,
    token: Optional[str] = Depends(jwt_bearer)
):
    try:
        # Parse natural language query if provided
        if request.natural_language_query:
            parsed = parse_natural_language_query(request.natural_language_query)
            logger.info(f"Parsed NL query: {parsed}")
            logger.info(f"Original request before override: {request}")
            
            # Override with parsed values from natural language
            # Always override when NL query is present
            if not request.keywords:
                request.keywords = parsed.get('keywords')
            # Always use parsed time window from natural language query
            request.time_window_minutes = parsed.get('time_window_minutes', request.time_window_minutes)
            if not request.source_file:
                request.source_file = parsed.get('source_file')
        
            logger.info(f"Modified request after override: {request}")
            
        analyzer = get_analyzer()
        result = analyzer.analyze(
            timestamp=request.timestamp,
            keywords=request.keywords,
            time_window_minutes=request.time_window_minutes,
            chat_history=request.chat_history,
            source_file=request.source_file
        )
        
        return AnalyzeResponse(**result)
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    token: Optional[str] = Depends(jwt_bearer)
):
    """
    Submit feedback on AI analysis
    
    - **message_id**: ID of the message
    - **rating**: -1 (thumbs down) or 1 (thumbs up)
    - **comment**: Optional comment
    """
    
    try:
        # Store feedback (in production, save to database)
        logger.info(f"Feedback received: {request.rating} for message {request.message_id}")
        
        # TODO: Store in database for model improvement
        
        return {
            "status": "success",
            "message": "Feedback recorded"
        }
        
    except Exception as e:
        logger.error(f"Feedback submission failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
