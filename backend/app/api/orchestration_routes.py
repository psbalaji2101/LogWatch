# backend/app/api/orchestration_routes.py
'''API routes for aggregation-first analysis and chunk summarization'''

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import uuid

from app.ai.aggregator import get_orchestrator
from app.ai.summarizer import get_summarizer, LogChunk
from app.search.client import get_opensearch_client, search_logs
from app.auth.jwt_bearer import jwt_bearer
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orchestration", tags=["Orchestration"])


# Request/Response Models
class AggregationRequest(BaseModel):
    '''Request for aggregation analysis'''
    start_time: datetime
    end_time: datetime
    keywords: Optional[str] = None
    source_file: Optional[str] = None
    top_k: int = Field(default=10, ge=1, le=50)


class ChunkSummarizationRequest(BaseModel):
    '''Request to summarize a log chunk'''
    query_filter: str
    start_time: datetime
    end_time: datetime
    chunk_id: Optional[str] = None


class RetrieveSummariesRequest(BaseModel):
    '''Request to retrieve relevant summaries (RAG)'''
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


@router.post("/analyze-aggregated")
async def analyze_with_aggregation(
    request: AggregationRequest,
    token: Optional[str] = Depends(jwt_bearer)
):
    '''
    Analyze logs using aggregation-first approach.
    
    Returns high-value metrics and recommended queries for chunking.
    '''
    
    try:
        logger.info(f"Aggregation analysis request: {request.start_time} to {request.end_time}")
        
        orchestrator = get_orchestrator()
        result = await orchestrator.orchestrate_analysis(
            start_time=request.start_time,
            end_time=request.end_time,
            keywords=request.keywords,
            source_file=request.source_file,
            top_k=request.top_k
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Aggregation analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/summarize-chunk")
async def summarize_chunk(
    request: ChunkSummarizationRequest,
    token: Optional[str] = Depends(jwt_bearer)
):
    '''
    Summarize a log chunk.
    
    This is typically called by chunk worker processes, but exposed via API
    for testing and manual chunk analysis.
    '''
    
    try:
        logger.info(f"Chunk summarization request: {request.query_filter}")
        
        client = get_opensearch_client()
        results = search_logs(
            client,
            start_time=request.start_time,
            end_time=request.end_time,
            query=request.query_filter,
            page_size=1000
        )
        
        chunk_id = request.chunk_id or str(uuid.uuid4())
        chunk = LogChunk(
            chunk_id=chunk_id,
            start_time=request.start_time,
            end_time=request.end_time,
            total_logs=len(results["logs"]),
            logs=results["logs"],
            query_filter=request.query_filter
        )
        
        summarizer = get_summarizer()
        summary = await summarizer.summarize_chunk(chunk)
        
        return {
            "chunk_id": summary.chunk_id,
            "timestamp": summary.timestamp.isoformat(),
            "total_logs": summary.total_logs,
            "error_count": summary.error_count,
            "warning_count": summary.warning_count,
            "summary_text": summary.summary_text,
            "top_errors": summary.top_errors,
            "top_services": summary.top_services,
            "sample_lines": summary.sample_lines,
            "key_patterns": summary.key_patterns,
            "suggested_queries": summary.suggested_queries
        }
        
    except Exception as e:
        logger.error(f"Chunk summarization failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/retrieve-summaries")
async def retrieve_summaries(
    request: RetrieveSummariesRequest,
    token: Optional[str] = Depends(jwt_bearer)
):
    '''
    Retrieve relevant summaries for a query (RAG retrieval).
    
    Uses vector similarity search on chunk summaries.
    '''
    
    try:
        logger.info(f"Summary retrieval request: {request.query}")
        
        client = get_opensearch_client()
        index = f"{settings.opensearch_index_prefix}-summaries"
        
        query_body = {
            "size": request.top_k,
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": request.query,
                                "fields": ["summary_text", "key_patterns", "top_errors.error"]
                            }
                        }
                    ]
                }
            },
            "_source": [
                "chunk_id", "timestamp", "summary_text", "error_count", 
                "warning_count", "top_errors", "top_services", "suggested_queries"
            ]
        }
        
        if request.start_time and request.end_time:
            query_body["query"]["bool"]["filter"] = [
                {
                    "range": {
                        "timestamp": {
                            "gte": request.start_time.isoformat(),
                            "lte": request.end_time.isoformat()
                        }
                    }
                }
            ]
        
        response = client.search(index=index, body=query_body)
        
        summaries = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            summaries.append({
                "chunk_id": source.get("chunk_id"),
                "timestamp": source.get("timestamp"),
                "summary": source.get("summary_text"),
                "error_count": source.get("error_count", 0),
                "warning_count": source.get("warning_count", 0),
                "top_errors": source.get("top_errors", []),
                "top_services": source.get("top_services", []),
                "suggested_queries": source.get("suggested_queries", [])
            })
        
        return {
            "status": "success",
            "query": request.query,
            "count": len(summaries),
            "summaries": summaries
        }
        
    except Exception as e:
        logger.error(f"Summary retrieval failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/chunk-status/{chunk_id}")
async def get_chunk_status(
    chunk_id: str,
    token: Optional[str] = Depends(jwt_bearer)
):
    '''Get summarization status of a chunk'''
    
    try:
        client = get_opensearch_client()
        index = f"{settings.opensearch_index_prefix}-summaries"
        
        response = client.search(
            index=index,
            body={"query": {"term": {"chunk_id": chunk_id}}}
        )
        
        if response["hits"]["total"]["value"] == 0:
            return {"status": "not_found", "chunk_id": chunk_id}
        
        summary = response["hits"]["hits"][0]["_source"]
        
        return {
            "status": "completed",
            "chunk_id": chunk_id,
            "timestamp": summary.get("timestamp"),
            "total_logs": summary.get("total_logs"),
            "error_count": summary.get("error_count"),
            "summary": summary.get("summary_text")
        }
        
    except Exception as e:
        logger.error(f"Chunk status lookup failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
