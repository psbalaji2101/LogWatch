# backend/app/ai/summarizer.py
'''Chunk-based log summarization worker'''

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import json
from dataclasses import dataclass

from app.search.client import get_opensearch_client
from app.ai.providers import get_ai_provider
from app.ai.config import ai_settings
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LogChunk:
    '''Represents a chunk of logs for summarization'''
    chunk_id: str
    start_time: datetime
    end_time: datetime
    total_logs: int
    logs: List[Dict[str, Any]]
    query_filter: Optional[str] = None


@dataclass
class ChunkSummary:
    '''Summary of a log chunk'''
    chunk_id: str
    timestamp: datetime
    total_logs: int
    error_count: int
    warning_count: int
    summary_text: str
    top_errors: List[tuple]
    top_services: List[tuple]
    sample_lines: List[str]
    key_patterns: List[str]
    suggested_queries: List[str]
    embedding: Optional[List[float]] = None


class ChunkSummarizer:
    '''Summarizes log chunks using LLM or extractive methods'''
    
    def __init__(self, use_small_model: bool = True):
        '''Initialize summarizer
        
        Args:
            use_small_model: If True, use cheaper model; else use default
        '''
        self.client = get_opensearch_client()
        self.index_pattern = f"{settings.opensearch_index_prefix}-*"
        self.summary_index = f"{settings.opensearch_index_prefix}-summaries"
        self.use_small_model = use_small_model
        
        # Get provider-specific settings
        provider_name = ai_settings.ai_provider
        
        if provider_name == "modelbroker":
            self.ai_provider = get_ai_provider(
                provider_name,
                api_key=ai_settings.modelbroker_api_key,
                model=ai_settings.modelbroker_model,
                base_url=ai_settings.modelbroker_base_url
            )
        elif provider_name == "groq":
            self.ai_provider = get_ai_provider(
                provider_name,
                api_key=ai_settings.groq_api_key,
                model=ai_settings.groq_model
            )
        elif provider_name == "ollama":
            self.ai_provider = get_ai_provider(
                provider_name,
                base_url=ai_settings.ollama_base_url,
                model=ai_settings.ollama_model
            )
        else:
            raise ValueError(f"Unsupported AI provider: {provider_name}")
        
        self._ensure_summary_index()
    
    def _ensure_summary_index(self):
        '''Create summaries index with vector field for embeddings'''
        
        index_exists = self.client.indices.exists(index=self.summary_index)
        
        if not index_exists:
            mapping = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "index": {"codec": "best_compression"}
                },
                "mappings": {
                    "properties": {
                        "chunk_id": {"type": "keyword"},
                        "timestamp": {"type": "date"},
                        "total_logs": {"type": "integer"},
                        "error_count": {"type": "integer"},
                        "warning_count": {"type": "integer"},
                        "summary_text": {"type": "text"},
                        "top_errors": {"type": "nested"},
                        "top_services": {"type": "nested"},
                        "sample_lines": {"type": "text"},
                        "key_patterns": {"type": "keyword"},
                        "suggested_queries": {"type": "keyword"},
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": 384,
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimil",
                                "engine": "lucene",
                                "parameters": {
                                    "ef_construction": 128,
                                    "m": 24
                                }
                            }
                        },
                        "ingest_timestamp": {"type": "date"}
                    }
                }
            }
            
            self.client.indices.create(index=self.summary_index, body=mapping)
            logger.info(f"Created summaries index: {self.summary_index}")
    
    async def summarize_chunk(self, chunk: LogChunk) -> ChunkSummary:
        '''Summarize a single log chunk'''
        
        logger.info(f"Summarizing chunk {chunk.chunk_id}: {len(chunk.logs)} logs")
        
        try:
            error_count = sum(1 for log in chunk.logs 
                            if log.get("fields", {}).get("level") == "ERROR")
            warning_count = sum(1 for log in chunk.logs 
                              if log.get("fields", {}).get("level") in ["WARNING", "WARN"])
            
            top_errors = self._extract_top_errors(chunk.logs, top_k=5)
            top_services = self._extract_top_services(chunk.logs, top_k=5)
            sample_lines = self._get_sample_lines(chunk.logs, count=3)
            key_patterns = self._extract_patterns(chunk.logs)
            
            summary_text = await self._generate_summary(
                chunk.logs, top_errors, top_services, key_patterns
            )
            
            suggested_queries = self._generate_suggested_queries(
                top_errors, top_services, chunk.query_filter
            )
            
            embedding = await self._generate_embedding(summary_text)
            
            summary = ChunkSummary(
                chunk_id=chunk.chunk_id,
                timestamp=datetime.utcnow(),
                total_logs=len(chunk.logs),
                error_count=error_count,
                warning_count=warning_count,
                summary_text=summary_text,
                top_errors=top_errors,
                top_services=top_services,
                sample_lines=sample_lines,
                key_patterns=key_patterns,
                suggested_queries=suggested_queries,
                embedding=embedding
            )
            
            await self._store_summary(summary)
            
            logger.info(f"Summarized chunk {chunk.chunk_id}: {error_count} errors, {warning_count} warnings")
            
            return summary
            
        except Exception as e:
            logger.error(f"Chunk summarization failed: {e}", exc_info=True)
            raise
    
    def _extract_top_errors(self, logs: List[Dict], top_k: int = 5) -> List[tuple]:
        '''Extract top error messages'''
        
        error_counts = {}
        for log in logs:
            if log.get("fields", {}).get("level") == "ERROR":
                msg = log.get("raw_line", "")[:100]
                error_counts[msg] = error_counts.get(msg, 0) + 1
        
        return sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:top_k]
    
    def _extract_top_services(self, logs: List[Dict], top_k: int = 5) -> List[tuple]:
        '''Extract top services by frequency'''
        
        service_counts = {}
        for log in logs:
            service = log.get("fields", {}).get("service", "unknown")
            service_counts[service] = service_counts.get(service, 0) + 1
        
        return sorted(service_counts.items(), key=lambda x: x[1], reverse=True)[:top_k]
    
    def _get_sample_lines(self, logs: List[Dict], count: int = 3) -> List[str]:
        '''Get representative sample lines'''
        
        seen_types = set()
        samples = []
        
        for log in logs:
            level = log.get("fields", {}).get("level", "INFO")
            service = log.get("fields", {}).get("service", "unknown")
            key = f"{level}:{service}"
            
            if key not in seen_types and len(samples) < count:
                samples.append(log.get("raw_line", ""))
                seen_types.add(key)
        
        return samples
    
    def _extract_patterns(self, logs: List[Dict]) -> List[str]:
        '''Extract key patterns from logs'''
        
        patterns = set()
        
        for log in logs:
            level = log.get("fields", {}).get("level", "").upper()
            service = log.get("fields", {}).get("service", "")
            
            if level == "ERROR":
                patterns.add(f"ERROR in {service}")
            elif level == "WARNING":
                patterns.add(f"WARNING from {service}")
        
        return list(patterns)
    
    async def _generate_summary(
        self,
        logs: List[Dict],
        top_errors: List[tuple],
        top_services: List[tuple],
        patterns: List[str]
    ) -> str:
        '''Generate summary using LLM or extractive method'''
        
        summary = f"Chunk with {len(logs)} logs. " \
                  f"Error rate: {len([l for l in logs if l.get('fields', {}).get('level') == 'ERROR']) / max(len(logs), 1):.1%}. " \
                  f"Top issues: {', '.join([e for e, _ in top_errors[:2]])}. " \
                  f"Services: {', '.join([s for s, _ in top_services[:2]])}"
        
        return summary
    
    def _generate_suggested_queries(
        self,
        top_errors: List[tuple],
        top_services: List[tuple],
        chunk_filter: Optional[str]
    ) -> List[str]:
        '''Generate OpenSearch queries for drill-down'''
        
        queries = []
        
        if top_errors:
            queries.append(f'raw_line:"{top_errors[0][0]}"')
        
        if top_services:
            service = top_services[0][0]
            queries.append(f'fields.service:"{service}" AND fields.level:ERROR')
        
        if chunk_filter:
            queries.append(chunk_filter)
        
        return queries[:3]
    
    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        '''Generate embedding for summary text (placeholder)'''
        return None
    
    async def _store_summary(self, summary: ChunkSummary):
        '''Store summary in OpenSearch'''
        
        doc = {
            "chunk_id": summary.chunk_id,
            "timestamp": datetime.utcnow().isoformat(),
            "total_logs": summary.total_logs,
            "error_count": summary.error_count,
            "warning_count": summary.warning_count,
            "summary_text": summary.summary_text,
            "top_errors": [{"error": e, "count": c} for e, c in summary.top_errors],
            "top_services": [{"service": s, "count": c} for s, c in summary.top_services],
            "sample_lines": summary.sample_lines,
            "key_patterns": summary.key_patterns,
            "suggested_queries": summary.suggested_queries,
            "embedding": summary.embedding,
            "ingest_timestamp": datetime.utcnow().isoformat()
        }
        
        doc_id = f"{summary.chunk_id}-{int(datetime.utcnow().timestamp())}"
        self.client.index(index=self.summary_index, id=doc_id, body=doc)
        
        logger.info(f"Stored summary: {doc_id}")


_summarizer = None

def get_summarizer() -> ChunkSummarizer:
    '''Get or create summarizer instance'''
    global _summarizer
    if _summarizer is None:
        _summarizer = ChunkSummarizer(use_small_model=True)
    return _summarizer
