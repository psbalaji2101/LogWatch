# backend/app/ai/aggregator.py
'''Aggregation-first analyzer orchestration service'''

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import asyncio
from dataclasses import dataclass

from app.search.client import get_opensearch_client
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AggregationBucket:
    '''Represents a time bucket with aggregated metrics'''
    timestamp: datetime
    total_count: int
    error_count: int
    warning_count: int
    top_services: List[tuple]  # [(service, count), ...]
    top_messages: List[tuple]  # [(message, count), ...]
    top_errors: List[tuple]  # [(error, count), ...]
    

class AggregationOrchestrator:
    '''Orchestrates log analysis by aggregating first'''
    
    def __init__(self):
        self.client = get_opensearch_client()
        self.index_pattern = f"{settings.opensearch_index_prefix}-*"
        self.bucket_size_minutes = 5  # 5-minute buckets
    
    async def orchestrate_analysis(
        self,
        start_time: datetime,
        end_time: datetime,
        keywords: Optional[str] = None,
        source_file: Optional[str] = None,
        top_k: int = 10
    ) -> Dict[str, Any]:
        '''
        Orchestrate analysis through aggregation stages.
        
        Returns structured aggregations for prioritization:
        {
            "time_buckets": [AggregationBucket...],
            "top_services": [(service, count), ...],
            "top_errors": [(error, count), ...],
            "error_rate": 0.15,
            "priority_queries": ["query1", "query2", ...],
            "estimated_chunks": int,
            "recommended_sampling": float
        }
        '''
        
        logger.info(f"Starting aggregation orchestration: {start_time} to {end_time}")
        
        try:
            # Stage 1: Time-bucket aggregations
            time_buckets = await self._aggregate_by_time(
                start_time, end_time, keywords, source_file
            )
            
            # Stage 2: Service-level breakdown
            top_services = await self._get_top_services(
                start_time, end_time, keywords, source_file, top_k
            )
            
            # Stage 3: Error analysis
            top_errors = await self._get_top_errors(
                start_time, end_time, keywords, source_file, top_k
            )
            
            # Stage 4: Error rate & severity
            stats = await self._get_severity_stats(
                start_time, end_time, keywords, source_file
            )
            
            # Stage 5: Generate priority queries for chunk workers
            priority_queries = self._generate_priority_queries(
                top_services, top_errors, keywords
            )
            
            # Stage 6: Estimate chunking strategy
            total_logs = sum(b.total_count for b in time_buckets)
            num_chunks = max(1, total_logs // settings.batch_size)
            recommended_sampling = min(1.0, settings.batch_size * 1.5 / total_logs)
            
            result = {
                "time_buckets": [
                    {
                        "timestamp": b.timestamp.isoformat(),
                        "total_count": b.total_count,
                        "error_count": b.error_count,
                        "warning_count": b.warning_count,
                        "error_rate": b.error_count / max(b.total_count, 1),
                        "top_services": b.top_services[:5],
                        "top_messages": [(msg, cnt) for msg, cnt in b.top_messages[:3]],
                    }
                    for b in time_buckets
                ],
                "top_services": top_services,
                "top_errors": top_errors,
                "error_rate": stats["error_rate"],
                "warning_rate": stats["warning_rate"],
                "total_logs": total_logs,
                "priority_queries": priority_queries,
                "estimated_chunks": num_chunks,
                "recommended_sampling": recommended_sampling,
                "analysis_scope": {
                    "time_range": f"{start_time.isoformat()} to {end_time.isoformat()}",
                    "keywords": keywords,
                    "source_file": source_file
                }
            }
            
            logger.info(f"Aggregation complete: {total_logs} logs, {len(top_services)} services, error_rate={stats['error_rate']:.2%}")
            
            return result
            
        except Exception as e:
            logger.error(f"Aggregation orchestration failed: {e}", exc_info=True)
            raise
    
    async def _aggregate_by_time(
        self,
        start_time: datetime,
        end_time: datetime,
        keywords: Optional[str],
        source_file: Optional[str]
    ) -> List[AggregationBucket]:
        '''Get time-bucketed aggregations (5-min buckets)'''
        
        query_body = {
            "size": 0,
            "query": self._build_filter_query(start_time, end_time, keywords, source_file),
            "aggs": {
                "time_buckets": {
                    "date_histogram": {
                        "field": "timestamp",
                        "fixed_interval": f"{self.bucket_size_minutes}m",
                        "min_doc_count": 0
                    },
                    "aggs": {
                        "error_count": {
                            "filter": {"term": {"fields.level": "ERROR"}}
                        },
                        "warning_count": {
                            "filter": {"term": {"fields.level": "WARNING"}}
                        },
                        "top_services": {
                            "terms": {"field": "fields.service.keyword", "size": 5}
                        },
                        "top_messages": {
                            "terms": {"field": "raw_line.keyword", "size": 3}
                        }
                    }
                }
            }
        }
        
        response = self.client.search(index=self.index_pattern, body=query_body)
        
        buckets = []
        for bucket in response["aggregations"]["time_buckets"]["buckets"]:
            timestamp = datetime.fromisoformat(bucket["key_as_string"].replace("Z", "+00:00"))
            
            top_services = [(s["key"], s["doc_count"]) for s in bucket["top_services"]["buckets"]]
            top_messages = [(m["key"], m["doc_count"]) for m in bucket["top_messages"]["buckets"]]
            
            buckets.append(AggregationBucket(
                timestamp=timestamp,
                total_count=bucket["doc_count"],
                error_count=bucket["error_count"]["doc_count"],
                warning_count=bucket["warning_count"]["doc_count"],
                top_services=top_services,
                top_messages=top_messages,
                top_errors=[]
            ))
        
        return buckets
    
    async def _get_top_services(
        self,
        start_time: datetime,
        end_time: datetime,
        keywords: Optional[str],
        source_file: Optional[str],
        top_k: int
    ) -> List[tuple]:
        '''Get top services by log volume'''
        
        query_body = {
            "size": 0,
            "query": self._build_filter_query(start_time, end_time, keywords, source_file),
            "aggs": {
                "services": {
                    "terms": {"field": "fields.service.keyword", "size": top_k}
                }
            }
        }
        
        response = self.client.search(index=self.index_pattern, body=query_body)
        return [(bucket["key"], bucket["doc_count"]) for bucket in response["aggregations"]["services"]["buckets"]]
    
    async def _get_top_errors(
        self,
        start_time: datetime,
        end_time: datetime,
        keywords: Optional[str],
        source_file: Optional[str],
        top_k: int
    ) -> List[tuple]:
        '''Get top error messages by frequency'''
        
        query_body = {
            "size": 0,
            "query": {
                "bool": {
                    "must": [
                        self._build_filter_query(start_time, end_time, keywords, source_file),
                        {"term": {"fields.level": "ERROR"}}
                    ]
                }
            },
            "aggs": {
                "errors": {"terms": {"field": "raw_line.keyword", "size": top_k}}
            }
        }
        
        try:
            response = self.client.search(index=self.index_pattern, body=query_body)
            return [(bucket["key"][:100], bucket["doc_count"]) for bucket in response["aggregations"]["errors"]["buckets"]]
        except Exception as e:
            logger.warning(f"Error aggregation failed: {e}")
            return []
    
    async def _get_severity_stats(
        self,
        start_time: datetime,
        end_time: datetime,
        keywords: Optional[str],
        source_file: Optional[str]
    ) -> Dict[str, float]:
        '''Get severity breakdown stats'''
        
        query_body = {
            "size": 0,
            "query": self._build_filter_query(start_time, end_time, keywords, source_file),
            "aggs": {
                "by_level": {"terms": {"field": "fields.level.keyword", "size": 10}}
            }
        }
        
        response = self.client.search(index=self.index_pattern, body=query_body)
        total = response["hits"]["total"]["value"]
        
        stats = {"error_rate": 0.0, "warning_rate": 0.0, "info_rate": 0.0}
        
        for bucket in response["aggregations"]["by_level"]["buckets"]:
            level = bucket["key"].upper()
            count = bucket["doc_count"]
            rate = count / max(total, 1)
            
            if level == "ERROR":
                stats["error_rate"] = rate
            elif level in ["WARNING", "WARN"]:
                stats["warning_rate"] = rate
            elif level == "INFO":
                stats["info_rate"] = rate
        
        return stats
    
    def _build_filter_query(
        self,
        start_time: datetime,
        end_time: datetime,
        keywords: Optional[str],
        source_file: Optional[str]
    ) -> Dict[str, Any]:
        '''Build OpenSearch query with filters'''
        
        must_clauses = [
            {
                "range": {
                    "timestamp": {
                        "gte": start_time.isoformat(),
                        "lte": end_time.isoformat()
                    }
                }
            }
        ]
        
        if keywords:
            must_clauses.append({
                "multi_match": {
                    "query": keywords,
                    "fields": ["raw_line", "fields.message", "tokens"]
                }
            })
        
        if source_file:
            must_clauses.append({
                "term": {"source_file.keyword": source_file}
            })
        
        return {"bool": {"must": must_clauses}} if len(must_clauses) > 1 else must_clauses[0]
    
    def _generate_priority_queries(
        self,
        top_services: List[tuple],
        top_errors: List[tuple],
        keywords: Optional[str]
    ) -> List[str]:
        '''Generate OpenSearch queries for chunk workers to fetch high-priority logs'''
        
        queries = []
        
        if top_services:
            top_service = top_services[0][0]
            queries.append(f'fields.service:"{top_service}" AND fields.level:ERROR')
        
        if top_errors:
            top_error = top_errors[0][0][:50]
            queries.append(f'raw_line:"{top_error}"')
        
        if keywords:
            queries.append(f'(raw_line:{keywords} OR tokens:{keywords}) AND fields.level:(ERROR OR WARNING)')
        
        if len(top_services) > 1:
            services = " OR ".join([f'"{s[0]}"' for s in top_services[:3]])
            queries.append(f'fields.service:({services})')
        
        return queries[:5]


_orchestrator = None

def get_orchestrator() -> AggregationOrchestrator:
    '''Get or create orchestrator instance'''
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AggregationOrchestrator()
    return _orchestrator
