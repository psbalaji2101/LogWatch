# LogWatch System Architecture

**Version**: 1.0  
**Date**: October 25, 2025  
**Author**: Balaji PS

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Principles](#architecture-principles)
3. [Component Architecture](#component-architecture)
4. [Data Flow](#data-flow)
5. [Database Schema](#database-schema)
6. [API Design](#api-design)
7. [Security Architecture](#security-architecture)
8. [Scalability & Performance](#scalability--performance)
9. [Deployment Architecture](#deployment-architecture)
10. [Monitoring & Observability](#monitoring--observability)

---

## System Overview

LogWatch is a distributed, microservices-based log analysis platform designed for high throughput, low latency, and intelligent analysis of application logs.

### Design Goals

- **Performance**: Handle 10,000+ logs/second with sub-100ms query latency
- **Scalability**: Support 10M+ logs with horizontal scaling
- **Reliability**: 99.9% uptime with automatic failover
- **Usability**: Natural language interface for non-technical users
- **Extensibility**: Plugin architecture for custom parsers and AI providers

---

## Architecture Principles

### 1. Separation of Concerns
- **Frontend**: Pure presentation layer, no business logic
- **Backend**: REST API, stateless services
- **Search**: Dedicated OpenSearch cluster
- **AI**: External service (Groq API)

### 2. Statelessness
- Backend services are stateless (except checkpoint DB)
- Enables horizontal scaling
- Session state in client or Redis (optional)

### 3. Fail-Fast
- Input validation at API boundary
- Pydantic models for type safety
- Graceful error handling with meaningful messages

### 4. Idempotency
- Log ingestion is idempotent (checkpoint-based)
- API operations designed for retry safety
- Duplicate detection for critical operations

### 5. Observability First
- Structured logging throughout
- Health checks for all components
- Metrics exported for Prometheus

---

## Component Architecture

### High-Level Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                        Load Balancer                          │
│                      (Nginx/HAProxy)                          │
└────────────────┬──────────────────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
    ↓                         ↓
┌─────────────┐         ┌─────────────┐
│  Frontend   │         │  Frontend   │
│  (React)    │         │  (React)    │
│  Instance 1 │         │  Instance 2 │
└─────────────┘         └─────────────┘
         │                     │
         └──────────┬──────────┘
                    │ REST API
                    ↓
         ┌──────────────────────┐
         │   API Gateway        │
         │   (Optional)         │
         └──────────┬───────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
    ↓               ↓               ↓
┌─────────┐   ┌─────────┐   ┌─────────┐
│Backend  │   │Backend  │   │Backend  │
│Instance1│   │Instance2│   │Instance3│
└────┬────┘   └────┬────┘   └────┬────┘
     │             │             │
     └─────────────┼─────────────┘
                   │
        ┌──────────┴──────────────┬──────────────┐
        │                         │              │
        ↓                         ↓              ↓
┌───────────────┐      ┌────────────────┐   ┌────────┐
│  OpenSearch   │      │   Groq API     │   │SQLite/ │
│   Cluster     │      │  (Llama 3.3)   │   │Redis   │
│  (3 nodes)    │      │                │   │(State) │
└───────────────┘      └────────────────┘   └────────┘
```

### Component Responsibilities

#### Frontend (React + Vite)
**Purpose**: User interface and visualization

**Responsibilities**:
- Render dashboard, log viewer, charts
- Handle user interactions
- Manage client-side state
- AI chatbot interface
- Real-time updates

**Technology**:
- React 18 (UI framework)
- Vite (build tool)
- Recharts (visualization)
- Axios (HTTP client)
- TailwindCSS (styling)

#### Backend (FastAPI)
**Purpose**: Business logic and API layer

**Responsibilities**:
- REST API endpoints
- Request validation
- Authentication/authorization
- Log parsing and transformation
- OpenSearch query orchestration
- AI service integration
- Rate limiting

**Technology**:
- FastAPI (web framework)
- Pydantic (validation)
- Uvicorn (ASGI server)
- Python 3.11

#### OpenSearch Cluster
**Purpose**: Log storage and search

**Responsibilities**:
- Index management
- Full-text search
- Aggregations
- Time-series queries
- Data persistence

**Configuration**:
- 3-node cluster (production)
- 1 shard per index
- Daily indices: `logs-YYYY-MM-DD`
- Refresh interval: 5s
- Compression: best_compression

#### AI Service (Groq)
**Purpose**: Intelligent log analysis

**Responsibilities**:
- Natural language understanding
- Pattern recognition
- Root cause analysis
- Recommendation generation
- Query suggestion

**Model**: Llama 3.3 70B Versatile

#### Checkpoint Database (SQLite/Redis)
**Purpose**: Ingestion state tracking

**Responsibilities**:
- Track file offsets
- Prevent duplicate processing
- Resume interrupted ingestion

---

## Data Flow

### 1. Log Ingestion Flow

```
┌──────────┐
│ Log File │
└────┬─────┘
     │
     ↓
┌────────────────┐
│  Ingestion     │  1. Read file from checkpoint
│  Worker        │  2. Parse each line
└───────┬────────┘
        │
        ↓
┌───────────────┐
│  Log Parser   │  1. Detect format (JSON/CSV/Text)
│               │  2. Extract timestamp, level, message
└───────┬───────┘
        │
        ↓
┌───────────────┐
│  Batch Buffer │  Accumulate 1000 logs
└───────┬───────┘
        │
        ↓
┌───────────────┐
│  OpenSearch   │  Bulk index operation
│  Bulk API     │  Index: logs-YYYY-MM-DD
└───────┬───────┘
        │
        ↓
┌───────────────┐
│  Checkpoint   │  Update file offset
│  Manager      │  
└───────────────┘
```

### 2. Search Query Flow

```
┌─────────┐
│ User UI │
└────┬────┘
     │ 1. Select time range, keywords
     ↓
┌────────────┐
│  REST API  │ 2. GET /api/logs?start_time=...
└─────┬──────┘
      │ 3. Validate parameters
      ↓
┌──────────────┐
│ Search       │ 4. Build OpenSearch query
│ Service      │    - Time range filter
│              │    - Keyword match
│              │    - Pagination
└──────┬───────┘
       │ 5. Execute query
       ↓
┌──────────────┐
│ OpenSearch   │ 6. Return results
└──────┬───────┘
       │ 7. Format response
       ↓
┌──────────────┐
│ REST API     │ 8. JSON response
└──────┬───────┘
       │
       ↓
┌──────────────┐
│ User UI      │ 9. Display logs
└──────────────┘
```

### 3. AI Analysis Flow

```
┌─────────┐
│ User    │ "Analyze errors from last hour"
└────┬────┘
     │
     ↓
┌────────────┐
│  Chat UI   │ 1. Parse natural language
└─────┬──────┘
      │ 2. POST /api/chat/analyze
      ↓
┌──────────────┐
│ Chat API     │ 3. Extract parameters
│              │    - keywords: "errors"
│              │    - time_window: 60 minutes
└──────┬───────┘
       │ 4. Fetch logs from OpenSearch
       ↓
┌──────────────┐
│ Log Analyzer │ 5. Prepare context (max 200 logs)
│              │ 6. Format for LLM
└──────┬───────┘
       │ 7. Call Groq API with prompt
       ↓
┌──────────────┐
│ Groq API     │ 8. LLM analysis
│ (Llama 3.3)  │    - Identify issues
│              │    - Root cause analysis
│              │    - Generate recommendations
└──────┬───────┘
       │ 9. Return analysis
       ↓
┌──────────────┐
│ Log Analyzer │ 10. Parse response
│              │ 11. Extract suggested queries
│              │ 12. Generate chart data
└──────┬───────┘
       │ 13. Return structured response
       ↓
┌──────────────┐
│ Chat UI      │ 14. Display analysis
│              │ 15. Show charts
│              │ 16. Render suggested queries
└──────────────┘
```

---

## Database Schema

### OpenSearch Index Structure

#### Index Template: `logs-*`

```json
{
  "index_patterns": ["logs-*"],
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
              "type": "keyword"
            }
          }
        },
        "fields": {
          "type": "object",
          "properties": {
            "level": { "type": "keyword" },
            "service": { "type": "keyword" },
            "user": { "type": "keyword" },
            "status_code": { "type": "integer" },
            "response_time_ms": { "type": "integer" }
          }
        },
        "ingest_id": {
          "type": "keyword"
        }
      }
    }
  }
}
```

### SQLite Checkpoint Schema

```sql
CREATE TABLE checkpoints (
    file_path TEXT PRIMARY KEY,
    offset INTEGER NOT NULL,
    last_modified REAL NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_updated_at ON checkpoints(updated_at);
```

---

## API Design

### REST API Endpoints

#### 1. Log Search
```
GET /api/logs

Query Parameters:
- start_time (ISO 8601): Start timestamp
- end_time (ISO 8601): End timestamp
- query (string): Keyword search
- source_file (string): Filter by file
- page (integer): Page number (default: 1)
- page_size (integer): Results per page (default: 50, max: 1000)

Response:
{
  "logs": [
    {
      "timestamp": "2025-10-24T12:00:00Z",
      "source_file": "app.log",
      "line_number": 123,
      "raw_line": "ERROR: Database connection failed",
      "fields": { "level": "ERROR" }
    }
  ],
  "total": 1000,
  "page": 1,
  "page_size": 50
}
```

#### 2. AI Analysis
```
POST /api/chat/analyze

Request Body:
{
  "timestamp": "2025-10-24T12:00:00Z",  // Optional
  "keywords": "error database",          // Optional
  "time_window_minutes": 60,             // Default: 30
  "chat_history": [...]                  // Optional, for context
}

Response:
{
  "analysis": "Markdown formatted analysis...",
  "summary": {
    "total_logs": 1000,
    "errors": 50,
    "warnings": 100
  },
  "suggested_queries": [
    "level:ERROR AND service:database"
  ],
  "chart_data": {
    "timeline": [...]
  },
  "timestamp": "2025-10-24T12:05:00Z"
}
```

#### 3. Statistics
```
GET /api/stats

Response:
{
  "total_logs": 1000000,
  "indices": ["logs-2025-10-24", "logs-2025-10-23"],
  "storage_bytes": 1073741824,
  "logs_by_level": {
    "ERROR": 1000,
    "WARN": 5000,
    "INFO": 994000
  }
}
```

#### 4. Health Check
```
GET /health

Response:
{
  "status": "healthy",
  "opensearch": "green",
  "components": {
    "api": "up",
    "opensearch": "up",
    "ai_service": "up"
  }
}
```

---

## Security Architecture

### Authentication Flow (Optional)

```
┌─────────┐
│ User    │ 1. Login with credentials
└────┬────┘
     │ POST /auth/login
     ↓
┌──────────────┐
│ Auth API     │ 2. Validate credentials
└──────┬───────┘    (bcrypt hash compare)
       │ 3. Generate JWT token
       ↓
┌──────────────┐
│ JWT Service  │ 4. Token with claims:
│              │    - user_id
│              │    - role
│              │    - exp (1 hour)
└──────┬───────┘
       │ 5. Return token
       ↓
┌──────────────┐
│ User         │ 6. Store in localStorage
└──────────────┘
       │
       │ 7. Subsequent requests
       ↓    include: Authorization: Bearer <token>
┌──────────────┐
│ API Endpoint │ 8. Validate token
│              │ 9. Extract user context
└──────────────┘
```

### Security Layers

1. **Transport Security**: HTTPS/TLS for all communications
2. **Authentication**: JWT tokens (optional)
3. **Authorization**: Role-based access control (future)
4. **Input Validation**: Pydantic models at API boundary
5. **SQL Injection**: No raw SQL (ORMs only)
6. **XSS Protection**: React auto-escaping
7. **CSRF**: SameSite cookies
8. **API Rate Limiting**: Per-user/IP limits

---

## Scalability & Performance

### Horizontal Scaling Strategy

#### Backend Scaling
```
┌──────────────┐
│ Load Balancer│
│  (Nginx)     │
└──────┬───────┘
       │
   ┌───┴────┬────┬────┬────┐
   ↓        ↓    ↓    ↓    ↓
[API1]  [API2][API3][API4][API5]
```

**Scaling Triggers**:
- CPU > 70%
- Response time > 200ms
- Request queue > 100

**Auto-scaling**: Kubernetes HPA (2-10 replicas)

#### OpenSearch Scaling
```
┌─────────────┐
│   Master    │
│   Nodes     │  Manage cluster state
└──────┬──────┘
       │
   ┌───┴────┬────┐
   ↓        ↓    ↓
[Data1] [Data2][Data3]  Store data, execute queries
   │        │    │
   └────────┼────┘
            ↓
       [Replica]        High availability
```

**Scaling Strategy**:
- Add data nodes for storage
- Add coordinator nodes for query performance
- Shard per index = log(total_docs) / log(1M)

### Caching Strategy

#### 1. Application-Level Cache (Redis)
- Frequently accessed logs
- Aggregation results
- User sessions
- TTL: 5 minutes

#### 2. CDN Cache (CloudFlare/CloudFront)
- Static assets (JS, CSS, images)
- TTL: 1 hour

#### 3. Browser Cache
- API responses (Cache-Control headers)
- Static assets (1 year)

### Performance Optimization

#### Backend
- **Async I/O**: FastAPI async endpoints
- **Connection Pooling**: OpenSearch client pool (10 connections)
- **Batch Processing**: Bulk indexing (1000 docs/batch)
- **Compression**: gzip for API responses

#### Frontend
- **Code Splitting**: Route-based chunks
- **Lazy Loading**: Components on demand
- **Debouncing**: Search input (300ms)
- **Virtual Scrolling**: Large log lists

#### OpenSearch
- **Index Lifecycle**: Rotate daily, delete after 30 days
- **Shard Size**: 30-50GB per shard
- **Refresh Interval**: 5s (trade-off: latency vs. throughput)
- **Replicas**: 0 (single node) or 1 (cluster)

---

## Deployment Architecture

### Development Environment
```yaml
services:
  frontend:
    image: node:18
    command: npm run dev
  
  backend:
    image: python:3.11
    command: uvicorn app.main:app --reload
  
  opensearch:
    image: opensearchproject/opensearch:2.11.0
    environment:
      - discovery.type=single-node
```

### Production Environment
```yaml
services:
  frontend:
    image: nginx:alpine
    replicas: 2
    volumes:
      - ./dist:/usr/share/nginx/html
  
  backend:
    image: logwatch-backend:1.0
    replicas: 3
    environment:
      - WORKERS=4
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
  
  opensearch:
    image: opensearchproject/opensearch:2.11.0
    replicas: 3
    environment:
      - cluster.name=logwatch-prod
      - discovery.seed_hosts=opensearch-1,opensearch-2
    volumes:
      - opensearch-data:/usr/share/opensearch/data
```

### Infrastructure as Code (Terraform)
```hcl
resource "aws_ecs_cluster" "logwatch" {
  name = "logwatch-cluster"
}

resource "aws_ecs_service" "backend" {
  name            = "logwatch-backend"
  cluster         = aws_ecs_cluster.logwatch.id
  desired_count   = 3
  launch_type     = "FARGATE"
}

resource "aws_opensearch_domain" "logs" {
  domain_name    = "logwatch-logs"
  engine_version = "OpenSearch_2.11"
  
  cluster_config {
    instance_type  = "r6g.large.search"
    instance_count = 3
  }
  
  ebs_options {
    ebs_enabled = true
    volume_size = 100
  }
}
```

---

## Monitoring & Observability

### Metrics (Prometheus)

#### Application Metrics
- `logwatch_requests_total{endpoint, method, status}`
- `logwatch_request_duration_seconds{endpoint}`
- `logwatch_logs_ingested_total`
- `logwatch_ai_analysis_duration_seconds`

#### System Metrics
- `opensearch_cluster_status`
- `opensearch_docs_count`
- `opensearch_query_latency_ms`

### Logging (Structured JSON)

```json
{
  "timestamp": "2025-10-24T12:00:00Z",
  "level": "INFO",
  "service": "backend",
  "endpoint": "/api/logs",
  "method": "GET",
  "user_id": "user_123",
  "duration_ms": 45,
  "status": 200,
  "request_id": "req-abc123"
}
```

### Alerting (Prometheus Alertmanager)

```yaml
groups:
- name: logwatch
  rules:
  - alert: HighErrorRate
    expr: rate(logwatch_requests_total{status=~"5.."}[5m]) > 0.05
    annotations:
      summary: "High error rate detected"
  
  - alert: SlowQueries
    expr: histogram_quantile(0.95, logwatch_request_duration_seconds) > 1
    annotations:
      summary: "95th percentile query time > 1s"
  
  - alert: OpenSearchDown
    expr: opensearch_cluster_status != 1
    annotations:
      summary: "OpenSearch cluster unhealthy"
```

### Distributed Tracing (Jaeger - Future)
- Trace requests across services
- Identify bottlenecks
- Visualize service dependencies

---

## Appendix

### Technology Rationale

| Choice | Rationale |
|--------|-----------|
| **FastAPI** | High performance, async support, auto-docs, Pydantic integration |
| **OpenSearch** | Open-source, Elasticsearch-compatible, powerful search, aggregations |
| **React** | Component-based, large ecosystem, excellent dev tools |
| **Groq** | Fastest LLM inference (300+ tokens/sec), free tier, production-ready |
| **Docker** | Consistent environments, easy deployment, resource isolation |
| **SQLite** | Zero-config, embedded, perfect for checkpoints |

### Future Architecture Enhancements

1. **Event Streaming**: Kafka for real-time log ingestion
2. **ML Pipeline**: Custom anomaly detection models
3. **Multi-Tenancy**: Separate indices per organization
4. **GraphQL**: Alternative to REST for flexible queries
5. **WebSockets**: Real-time log streaming to UI
6. **Service Mesh**: Istio for advanced traffic management

---

**Document Version**: 1.0  
**Last Updated**: October 25, 2025  
**Maintained by**: Balaji PS
