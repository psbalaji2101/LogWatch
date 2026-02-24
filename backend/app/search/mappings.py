# backend/app/search/mappings.py
"""OpenSearch index mappings with aggregation-first support"""

from app.config import settings


def get_index_template():
    """Get OpenSearch index template for log events with optimized aggregation fields"""
    
    return {
        "index_patterns": [f"{settings.opensearch_index_prefix}-*"],
        "template": {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "refresh_interval": "5s",
                "codec": "best_compression",
                # Enable query cache for faster aggregations
                "index.queries.cache.enabled": True,
                "index.store.stats_refresh_interval": "30s"
            },
            "mappings": {
                # Dynamic templates to prevent date auto-detection in fields.*
                "dynamic_templates": [
                    {
                        "fields_as_text": {
                            "path_match": "fields.*",
                            "mapping": {
                                "type": "text",
                                "fields": {
                                    "keyword": {
                                        "type": "keyword",
                                        "ignore_above": 256
                                    }
                                }
                            }
                        }
                    },
                    {
                        "strings_as_keywords": {
                            "match_mapping_type": "string",
                            "match": "*_id",
                            "mapping": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    }
                ],
                "properties": {
                    # === CORE FIELDS ===
                    "@timestamp": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    # Legacy field kept for backward compatibility
                    "timestamp": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "raw_timestamp": {
                        "type": "keyword",
                        "ignore_above": 512
                    },
                    "ingested_at": {
                        "type": "date"
                    },
                    "timestamp_confidence": {
                        "type": "float"
                    },
                    "timestamp_source": {
                        "type": "keyword",
                        "ignore_above": 256
                    },
                    "timestamp_origin": {
                        "type": "keyword",
                        "ignore_above": 256
                    },
                    "timestamp_assumed_year": {
                        "type": "integer"
                    },
                    "timestamp_timezone_assumed": {
                        "type": "keyword",
                        "ignore_above": 64
                    },
                    "timestamp_format": {
                        "type": "keyword",
                        "ignore_above": 256
                    },
                    "timestamp_parse_error": {
                        "type": "keyword",
                        "ignore_above": 512
                    },
                    "source_file": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    },
                    "line_number": {
                        "type": "integer"
                    },
                    "raw_line": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 512
                            }
                        }
                    },
                    "tokens": {
                        "type": "text",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    },
                    "ingest_id": {
                        "type": "keyword"
                    },
                    
                    # === AGGREGATION FIELDS ===
                    # Nested object for structured log data
                    "fields": {
                        "type": "object",
                        "enabled": True,
                        "dynamic": "true",
                        "properties": {
                            # Log level - heavily used in aggregations
                            "level": {
                                "type": "keyword",
                                "ignore_above": 256
                            },
                            # Service name - for service-level breakdown
                            "service": {
                                "type": "keyword",
                                "ignore_above": 256
                            },
                            # Error/warning message
                            "message": {
                                "type": "text",
                                "fields": {
                                    "keyword": {
                                        "type": "keyword",
                                        "ignore_above": 512
                                    }
                                }
                            },
                            # HTTP status code
                            "status_code": {
                                "type": "keyword"
                            },
                            # Exception/error type
                            "error_type": {
                                "type": "keyword",
                                "ignore_above": 256
                            },
                            # Request endpoint/path
                            "endpoint": {
                                "type": "keyword",
                                "ignore_above": 256
                            },
                            # Request duration (for performance analysis)
                            "duration_ms": {
                                "type": "integer"
                            },
                            # User/trace ID for correlation
                            "trace_id": {
                                "type": "keyword",
                                "ignore_above": 256
                            },
                            "user_id": {
                                "type": "keyword",
                                "ignore_above": 256
                            },
                            # Host/environment
                            "host": {
                                "type": "keyword",
                                "ignore_above": 256
                            },
                            "environment": {
                                "type": "keyword",
                                "ignore_above": 256
                            },
                            # Generic string field for custom data
                            "additional": {
                                "type": "text",
                                "fields": {
                                    "keyword": {
                                        "type": "keyword",
                                        "ignore_above": 256
                                    }
                                }
                            }
                        }
                    },
                    
                    # === CHUNKING & SUMMARIZATION FIELDS (for Option B) ===
                    "chunk_id": {
                        "type": "keyword",
                        "ignore_above": 256
                    },
                    "chunk_index": {
                        "type": "integer"
                    },
                    "summary_cached": {
                        "type": "boolean"
                    }
                }
            }
        }
    }


def create_index_template(client):
    """Create index template in OpenSearch"""
    
    template_name = f"{settings.opensearch_index_prefix}-template"
    template = get_index_template()
    
    try:
        client.indices.put_index_template(
            name=template_name,
            body=template
        )
        print(f"✅ Created index template: {template_name}")
        return True
    except Exception as e:
        print(f"❌ Error creating template: {e}")
        return False


def get_summaries_index_template():
    """Get OpenSearch index template for log summaries (chunk results)"""
    
    return {
        "index_patterns": [f"{settings.opensearch_index_prefix}-summaries-*"],
        "template": {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "refresh_interval": "10s",
                "codec": "best_compression"
            },
            "mappings": {
                "properties": {
                    # Summary metadata
                    "chunk_id": {
                        "type": "keyword"
                    },
                    "timestamp": {
                        "type": "date"
                    },
                    "total_logs": {
                        "type": "integer"
                    },
                    "error_count": {
                        "type": "integer"
                    },
                    "warning_count": {
                        "type": "integer"
                    },
                    
                    # Summary text (main content)
                    "summary_text": {
                        "type": "text"
                    },
                    
                    # Vector embedding for semantic search (RAG)
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 384,  # For sentence-transformers models
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
                    
                    # Key patterns extracted from logs
                    "key_patterns": {
                        "type": "keyword"
                    },
                    
                    # Top errors in chunk (nested for queries)
                    "top_errors": {
                        "type": "nested",
                        "properties": {
                            "error": {
                                "type": "text",
                                "fields": {
                                    "keyword": {
                                        "type": "keyword",
                                        "ignore_above": 512
                                    }
                                }
                            },
                            "count": {
                                "type": "integer"
                            }
                        }
                    },
                    
                    # Top services in chunk
                    "top_services": {
                        "type": "nested",
                        "properties": {
                            "service": {
                                "type": "keyword"
                            },
                            "count": {
                                "type": "integer"
                            }
                        }
                    },
                    
                    # Sample lines from chunk
                    "sample_lines": {
                        "type": "text"
                    },
                    
                    # Suggested queries for drill-down
                    "suggested_queries": {
                        "type": "keyword"
                    },
                    
                    # Ingestion timestamp
                    "ingest_timestamp": {
                        "type": "date"
                    }
                }
            }
        }
    }


def create_summaries_index_template(client):
    """Create summaries index template in OpenSearch"""
    
    template_name = f"{settings.opensearch_index_prefix}-summaries-template"
    template = get_summaries_index_template()
    
    try:
        client.indices.put_index_template(
            name=template_name,
            body=template
        )
        print(f"✅ Created summaries index template: {template_name}")
        return True
    except Exception as e:
        print(f"❌ Error creating summaries template: {e}")
        return False
