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
    Parse natural language query to extract keywords, time, and file filters
    """
    
    query_lower = query.lower()
    
    # Extract time window
    time_window = 30
    time_patterns = [
        (r'(\d+)\s*day', 1440),           # X days → convert to minutes
        (r'(\d+)\s*days', 1440),
        (r'(\d+)\s*week', 10080),         # X weeks → 7*1440 minutes
        (r'(\d+)\s*weeks', 10080),
        (r'(\d+)\s*hour', 60),            # X hours
        (r'(\d+)\s*hours', 60),
        (r'(\d+)\s*h\b', 60),
        (r'(\d+)\s*min', 1),
        (r'(\d+)\s*minutes', 1),
        # Also handle "past 30 days", "last 7 days" etc.
        (r'past\s+(\d+)\s*day', 1440),
        (r'last\s+(\d+)\s*day', 1440),
        (r'past\s+(\d+)\s*week', 10080),
        (r'last\s+(\d+)\s*week', 10080),
    ]
    
    for pattern, multiplier in time_patterns:
        match = re.search(pattern, query_lower)
        if match:
            amount = int(match.group(1))
            time_window = amount * multiplier
            break
    time_window = min(time_window, 1440)  # Cap at 1440 minutes (1 day)
    
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
    
    # Extract source file (NEW)
    source_file = None
    
    # Pattern 1: "file format1_date_only.log"
    file_match = re.search(r'file\s+(\S+\.log)', query_lower)
    if file_match:
        source_file = file_match.group(1)
    
    # Pattern 2: "from format1_date_only.log"
    if not source_file:
        file_match = re.search(r'from\s+(\S+\.log)', query_lower)
        if file_match:
            source_file = file_match.group(1)
    
    # Pattern 3: "in format1_date_only.log"
    if not source_file:
        file_match = re.search(r'in\s+(\S+\.log)', query_lower)
        if file_match:
            source_file = file_match.group(1)
    
    # Pattern 4: Just the filename itself
    if not source_file:
        file_match = re.search(r'(format\d+_\w+\.log)', query_lower)
        if file_match:
            source_file = file_match.group(1)
    
    # Make sure to prepend the path
    if source_file and not source_file.startswith('/'):
        source_file = f"/logs_in/{source_file}"
    
    return {
        "keywords": keywords,
        "time_window_minutes": time_window,
        "source_file": source_file  # NEW
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
            
            # Override with parsed values (if not already set)
            if not request.keywords:
                request.keywords = parsed.get('keywords')
            if request.time_window_minutes == 30:  # Default value
                request.time_window_minutes = parsed.get('time_window_minutes', 30)
            if not request.source_file:
                request.source_file = parsed.get('source_file')
        
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
