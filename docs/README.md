
***

## File Contents

### **README.md**

```markdown
# LogWatch - Log Ingestion & Search System

A simple, minimal, user-friendly, scalable system that watches a folder of log files, parses each log line into structured fields, stores parsed events in OpenSearch, and provides a responsive UI dashboard to view, graph, and query logs.

## Features

- **File Watcher**: Monitors a directory for new or appended log files using `watchdog`
- **Heterogeneous Log Support**: Handles JSON, CSV, Apache/Nginx, and custom text formats
- **OpenSearch Backend**: Scalable search and analytics storage
- **FastAPI Backend**: High-performance async APIs and ingestion workers
- **React Dashboard**: Minimal, responsive UI with time-series charts
- **JWT Authentication**: Secure API endpoints with token-based auth
- **Production Ready**: Docker Compose for dev, Kubernetes manifests for production
- **Comprehensive Tests**: pytest for backend, Playwright for frontend

## Prerequisites (macOS)

Install required dependencies using Homebrew:

Install Docker Desktop (includes Docker Compose)
brew install --cask docker

Install Python 3.11+
brew install python@3.11

Install Node.js 20+
brew install node@20

Install Make
brew install make

start the project
cd LogIngestion
make dev /
docker compose up -f 

Create log file
python scripts/generate_logs.py --output ./logs_in --count 100
python scripts/generate_realistic_logs.py --output ./logs_in

Ingest Logs to the Application
python -m app.cli.ingest --file ./logs_in/sample_logs.json
docker compose exec backend python -m app.cli.ingest --directory /logs_in

setup OpenSearch
python scripts/setup_opensearch.py

Fix OpenSearch shard limit (auto-configured on startup, or run manually if needed)
python scripts/fix_opensearch_shards.py --stats
# Or inside Docker:
docker compose exec backend python scripts/fix_opensearch_shards.py --stats
# Or directly via curl:
curl -k -u admin:admin -X PUT 'https://localhost:9200/_cluster/settings' \
  -H 'Content-Type: application/json' \
  -d '{"persistent":{"cluster.max_shards_per_node":"5000"}}'

start watcher
docker compose exec backend python -m app.cli.watch --directory /logs_in

cleanup OpenSearch DB data
docker volume rm logingestion_opensearch-data1
docker compose exec backend python scripts/setup_opensearch.py

curl -X DELETE -k -u admin:admin 'https://localhost:9200/logs-*'


-------------------------------------------------------------------------
backend
-------------------------------------------------------------------------
start virtual env for python 

python3.11 -m venv venv
source venv/bin/activate

Install requried packages for Backend 
pip install -r requirements.txt

-------------------------------------------------------------------------
frontend
-------------------------------------------------------------------------
Install depedencies for frontend
npm install

Run dev server 
npm run dev

-------------------------------------------------------------------------
Calls made
-------------------------------------------------------------------------

Get logs from last hour
curl -X GET "http://localhost:8000/api/logs?start_time=2025-10-20T14:00:00Z&end_time=2025-10-20T15:00:00Z"

curl -X GET "http://localhost:8000/api/logs?timestamp=2025-10-20T14:30:00Z&window_seconds=60"

curl -X POST http://localhost:8000/api/logs/search -H "Content-Type: application/json" -d ' { "query": "error", "start_time": "2025-10-20T00:00:00Z", "end_time": "2025-10-20T23:59:59Z" }'

curl -k -u admin:admin 'https://localhost:9200/logs-*/_count?pretty'

curl -X POST http://localhost:8000/api/chat/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": "ERROR",
    "time_window_minutes": 60
  }' | jq '.summary'


-------------------------------------------------------------------------
debug Calls made
-------------------------------------------------------------------------

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
EOF

