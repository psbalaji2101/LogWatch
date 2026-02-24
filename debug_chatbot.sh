#!/bin/bash

echo "=== Checking Log Timestamps ==="
curl -s -k -u admin:admin 'https://localhost:9200/logs-*/_search?pretty' \
  -H 'Content-Type: application/json' \
  -d '{
    "size": 0,
    "aggs": {
      "min": {"min": {"field": "timestamp"}},
      "max": {"max": {"field": "timestamp"}}
    }
  }' | grep value_as_string

echo -e "\n=== Testing Chatbot Query ==="
curl -s -X POST http://localhost:8000/api/chat/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "natural_language_query": "Analyze logs from last 5 hour"
  }' | jq '{
    keywords,
    time_window_minutes,
    time_range: .summary.time_range,
    total_logs: .summary.total_logs
  }'

echo -e "\n=== Backend Logs ==="
docker compose logs backend --tail=20 | grep -E "Parsing|Parsed|Final request|Analyzing logs"
