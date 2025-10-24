"""Chat API routes"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

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


class AnalyzeResponse(BaseModel):
    """Log analysis response"""
    analysis: str
    summary: Dict[str, Any]
    suggested_queries: List[str]
    chart_data: Optional[Dict[str, Any]]
    timestamp: str


class FeedbackRequest(BaseModel):
    """User feedback on AI response"""
    message_id: str
    rating: int = Field(ge=-1, le=1)  # -1: thumbs down, 1: thumbs up
    comment: Optional[str] = None


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_logs(
    request: AnalyzeRequest,
    token: Optional[str] = Depends(jwt_bearer)
):
    """
    Analyze logs using AI
    
    - **timestamp**: Reference timestamp (default: now)
    - **keywords**: Filter keywords
    - **time_window_minutes**: Time range (1-1440 minutes)
    - **chat_history**: Previous conversation context
    """
    
    try:
        analyzer = get_analyzer()
        
        result = analyzer.analyze(
            timestamp=request.timestamp,
            keywords=request.keywords,
            time_window_minutes=request.time_window_minutes,
            chat_history=request.chat_history
        )
        
        return AnalyzeResponse(**result)
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


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
