# """OpenSearch client and operations"""

# from opensearchpy import OpenSearch, AsyncOpenSearch
# from opensearchpy.helpers import async_bulk
# from typing import List, Dict, Any, Optional
# from datetime import datetime
# import logging

# from app.config import settings

# logger = logging.getLogger(__name__)

# _client: Optional[AsyncOpenSearch] = None


# def get_opensearch_client() -> AsyncOpenSearch:
#     """Get or create OpenSearch client"""
#     global _client
    
#     if _client is None:
#         _client = OpenSearch(
#             hosts=[{
#                 'host': settings.opensearch_host,
#                 'port': settings.opensearch_port
#             }],
#             http_auth=(settings.opensearch_user, settings.opensearch_password),
#             use_ssl=True,
#             verify_certs=settings.opensearch_verify_certs,
#             ssl_show_warn=False,
#             timeout=30
#         )
#         logger.info("OpenSearch client created")
    
#     return _client


# async def bulk_index_logs(client: AsyncOpenSearch, logs: List[Dict[str, Any]]) -> Dict:
#     """Bulk index logs to OpenSearch"""
    
#     if not logs:
#         return {"success": 0, "errors": 0}
    
#     # Prepare bulk actions
#     actions = []
#     for log in logs:
#         # Determine index name (daily rotation)
#         date_str = log['timestamp'][:10] if isinstance(log['timestamp'], str) else log['timestamp'].strftime('%Y-%m-%d')
#         index_name = f"{settings.opensearch_index_prefix}-{date_str}"
        
#         action = {
#             "_index": index_name,
#             "_source": log
#         }
#         actions.append(action)
    
#     # Bulk index
#     try:
#         success, errors = await async_bulk(
#             client,
#             actions,
#             chunk_size=settings.batch_size,
#             raise_on_error=False
#         )
        
#         logger.info(f"Bulk indexed {success} logs, {len(errors)} errors")
#         return {"success": success, "errors": len(errors)}
        
#     except Exception as e:
#         logger.error(f"Bulk index error: {e}")
#         raise


# async def search_logs(
#     client: AsyncOpenSearch,
#     start_time: datetime,
#     end_time: datetime,
#     query: Optional[str] = None,
#     source_file: Optional[str] = None,
#     fields: Optional[List[str]] = None,
#     page: int = 1,
#     page_size: int = 100
# ) -> Dict:
#     """Search logs with filters"""
    
#     index_name = f"{settings.opensearch_index_prefix}-*"
    
#     # Build query
#     must_clauses = [
#         {
#             "range": {
#                 "timestamp": {
#                     "gte": start_time.isoformat(),
#                     "lte": end_time.isoformat()
#                 }
#             }
#         }
#     ]
    
#     if source_file:
#         must_clauses.append({"term": {"source_file.keyword": source_file}})
    
#     if query:
#         must_clauses.append({
#             "multi_match": {
#                 "query": query,
#                 "fields": ["raw_line", "tokens", "fields.*"]
#             }
#         })
    
#     body = {
#         "query": {
#             "bool": {
#                 "must": must_clauses
#             }
#         },
#         "sort": [{"timestamp": "desc"}],
#         "from": (page - 1) * page_size,
#         "size": page_size
#     }
    
#     try:
#         response = await client.search(index=index_name, body=body)
        
#         logs = []
#         for hit in response['hits']['hits']:
#             log = hit['_source']
#             logs.append(log)
        
#         return {
#             "total": response['hits']['total']['value'],
#             "page": page,
#             "page_size": page_size,
#             "logs": logs
#         }
        
#     except Exception as e:
#         logger.error(f"Search error: {e}")
#         raise


# async def aggregate_logs(
#     client: AsyncOpenSearch,
#     start_time: datetime,
#     end_time: datetime,
#     interval: str = "1h"
# ) -> Dict:
#     """Get aggregations for logs"""
    
#     index_name = f"{settings.opensearch_index_prefix}-*"
    
#     body = {
#         "query": {
#             "range": {
#                 "timestamp": {
#                     "gte": start_time.isoformat(),
#                     "lte": end_time.isoformat()
#                 }
#             }
#         },
#         "size": 0,
#         "aggs": {
#             "time_series": {
#                 "date_histogram": {
#                     "field": "timestamp",
#                     "fixed_interval": interval
#                 }
#             },
#             "top_tokens": {
#                 "terms": {
#                     "field": "tokens.keyword",
#                     "size": 10
#                 }
#             },
#             "sources": {
#                 "terms": {
#                     "field": "source_file.keyword",
#                     "size": 20
#                 }
#             }
#         }
#     }
    
#     try:
#         response = await client.search(index=index_name, body=body)
        
#         return {
#             "time_series": [
#                 {"timestamp": bucket['key_as_string'], "count": bucket['doc_count']}
#                 for bucket in response['aggregations']['time_series']['buckets']
#             ],
#             "top_tokens": [
#                 {"token": bucket['key'], "count": bucket['doc_count']}
#                 for bucket in response['aggregations']['top_tokens']['buckets']
#             ],
#             "sources": [
#                 {"source": bucket['key'], "count": bucket['doc_count']}
#                 for bucket in response['aggregations']['sources']['buckets']
#             ]
#         }
        
#     except Exception as e:
#         logger.error(f"Aggregation error: {e}")
#         raise


# ----- ChatGPT Augmented Code Below -----

"""OpenSearch client and operations"""

from opensearchpy import OpenSearch, helpers
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from app.config import settings

logger = logging.getLogger(__name__)

_client: Optional[OpenSearch] = None

def get_opensearch_client() -> OpenSearch:
    """Get or create synchronous OpenSearch client"""
    global _client
    if _client is None:
        _client = OpenSearch(
            hosts=[{
                'host': settings.opensearch_host,
                'port': settings.opensearch_port
            }],
            http_auth=(settings.opensearch_user, settings.opensearch_password),
            use_ssl=True,
            verify_certs=settings.opensearch_verify_certs,
            ssl_show_warn=False,
            timeout=30
        )
        logger.info("OpenSearch client created")
    return _client


def bulk_index_logs(client: OpenSearch, logs: List[Dict[str, Any]]) -> Dict:
    """Bulk index logs to OpenSearch"""
    if not logs:
        return {"success": 0, "errors": 0}

    actions = []
    for log in logs:
        date_str = log['timestamp'][:10] if isinstance(log['timestamp'], str) else log['timestamp'].strftime('%Y-%m-%d')
        index_name = f"{settings.opensearch_index_prefix}-{date_str}"
        actions.append({"_index": index_name, "_source": log})

    try:
        success, errors = helpers.bulk(client, actions, chunk_size=settings.batch_size, raise_on_error=False)
        logger.info(f"Bulk indexed {success} logs, {len(errors) if errors else 0} errors")
        return {"success": success, "errors": len(errors) if errors else 0}
    except Exception as e:
        logger.error(f"Bulk index error: {e}")
        raise


def search_logs(
    client: OpenSearch,
    start_time: datetime,
    end_time: datetime,
    query: Optional[str] = None,
    source_file: Optional[str] = None,
    fields: Optional[List[str]] = None,
    page: int = 1,
    page_size: int = 100
) -> Dict:
    """Search logs with filters"""
    index_name = f"{settings.opensearch_index_prefix}-*"

    must_clauses = [
        {"range": {"timestamp": {"gte": start_time.isoformat(), "lte": end_time.isoformat()}}}
    ]
    if source_file:
        must_clauses.append({"term": {"source_file.keyword": source_file}})
    if query:
        must_clauses.append({"multi_match": {"query": query, "fields": ["raw_line", "tokens", "fields.*"]}})

    body = {
        "query": {"bool": {"must": must_clauses}},
        "sort": [{"timestamp": "desc"}],
        "from": (page - 1) * page_size,
        "size": page_size
    }

    try:
        response = client.search(index=index_name, body=body)
        logs = [hit['_source'] for hit in response['hits']['hits']]
        return {"total": response['hits']['total']['value'], "page": page, "page_size": page_size, "logs": logs}
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise


def aggregate_logs(client: OpenSearch, start_time: datetime, end_time: datetime, interval: str = "1h") -> Dict:
    """Get aggregations for logs"""
    index_name = f"{settings.opensearch_index_prefix}-*"

    body = {
        "query": {"range": {"timestamp": {"gte": start_time.isoformat(), "lte": end_time.isoformat()}}},
        "size": 0,
        "aggs": {
            "time_series": {"date_histogram": {"field": "timestamp", "fixed_interval": interval}},
            "top_tokens": {"terms": {"field": "tokens.keyword", "size": 10}},
            "sources": {"terms": {"field": "source_file.keyword", "size": 20}}
        }
    }

    try:
        response = client.search(index=index_name, body=body)
        return {
            "time_series": [{"timestamp": b['key_as_string'], "count": b['doc_count']} for b in response['aggregations']['time_series']['buckets']],
            "top_tokens": [{"token": b['key'], "count": b['doc_count']} for b in response['aggregations']['top_tokens']['buckets']],
            "sources": [{"source": b['key'], "count": b['doc_count']} for b in response['aggregations']['sources']['buckets']]
        }
    except Exception as e:
        logger.error(f"Aggregation error: {e}")
        raise