"""OpenSearch index mappings"""

from backend.app.config import settings


def get_index_template():
    """Get OpenSearch index template for log events"""
    
    return {
        "index_patterns": [f"{settings.opensearch_index_prefix}-*"],
        "template": {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "refresh_interval": "5s",
                "codec": "best_compression"
            },
            "mappings": {
                "properties": {
                    "timestamp": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
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
                        "analyzer": "standard"
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
                    "fields": {
                        "type": "object",
                        "enabled": True
                    },
                    "ingest_id": {
                        "type": "keyword"
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
        print(f"Created index template: {template_name}")
        return True
    except Exception as e:
        print(f"Error creating template: {e}")
        return False
