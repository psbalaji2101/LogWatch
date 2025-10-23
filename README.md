
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
python scripts/generate_logs.py --output ./logs_in --count 10000

Ingest Logs to the Application
python -m app.cli.ingest --file ./logs_in/sample_logs.json

setup OpenSearch
python scripts/setup_opensearch.py

start watcher
docker compose exec backend python -m app.cli.watch --directory /logs_in

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