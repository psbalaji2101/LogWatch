# LogWatch Troubleshooting Guide

## Common Issues and Solutions

### 1. OpenSearch Shard Limit Exceeded

**Symptoms:**
- Ingestion fails with 0 successful logs and many errors
- Error message: `this action would add [2] total shards, but this cluster currently has [1000]/[1000] maximum shards open`
- Bulk indexing returns 200 status but documents aren't indexed

**Cause:**
OpenSearch has a default limit of 1000 shards per node. When creating daily indices (one per date), this limit can be reached quickly with large log volumes.

**Solution:**

1. **Quick Fix - Increase Shard Limit:**
```bash
# Run the fix script
python scripts/fix_opensearch_shards.py --stats

# Or manually:
curl -k -u admin:admin -X PUT 'https://localhost:9200/_cluster/settings' \
  -H 'Content-Type: application/json' \
  -d '{"persistent":{"cluster.max_shards_per_node":"5000"}}'
```

2. **Long-term Fix - Delete Old Indices:**
```bash
# Delete indices older than 30 days
python scripts/fix_opensearch_shards.py --delete-old --keep-days 30
```

3. **Prevention - Set Up Index Lifecycle Management:**
Consider implementing Index State Management (ISM) policies to automatically delete or rollover old indices.

---

### 2. Circuit Breaker Exceptions (HTTP 429)

**Symptoms:**
- Warnings about `circuit_breaking_exception` in logs
- Status 429 errors during bulk indexing
- Error message: `Data too large, data for [<http_request>] would be [XXXmb], which is larger than the limit of [XXXmb]`
- Ingestion is slow but eventually succeeds with retries

**Cause:**
OpenSearch circuit breakers prevent the cluster from running out of memory by rejecting requests that would exceed JVM heap limits. This happens when:
1. JVM heap size is too small for the bulk request sizes
2. Batch sizes are too large
3. Multiple concurrent bulk operations overwhelm memory

**Solution:**

1. **Increase OpenSearch Heap Memory (Recommended):**
```yaml
# In docker-compose.yml
services:
  opensearch-node1:
    environment:
      - "OPENSEARCH_JAVA_OPTS=-Xms2g -Xmx2g"  # Increased from 512m
```

Then restart OpenSearch:
```bash
docker compose restart opensearch-node1
```

2. **Reduce Batch Size:**
```python
# In backend/app/config.py or via environment variable
BATCH_SIZE=100  # Reduced from 200 or 1000
```

3. **The System Auto-Retries:**
The bulk indexing client automatically:
- Detects 429 errors
- Backs off with exponential delays (2s, 4s, 8s, etc.)
- Reduces chunk sizes on retry
- Eventually succeeds once memory pressure reduces

4. **Monitor Memory Usage:**
```bash
# Check OpenSearch heap usage
curl -k -u admin:admin 'https://localhost:9200/_nodes/stats/jvm?pretty'

# Check circuit breaker stats
curl -k -u admin:admin 'https://localhost:9200/_nodes/stats/breaker?pretty'
```

**Prevention:**
- Start with heap size at least 2GB for production workloads
- Set batch_size between 50-100 for large log files
- Monitor circuit breaker trips and adjust accordingly

---

### 3. Field Type Conflicts (Mapper Parsing Exceptions)

**Symptoms:**
- Some logs fail to index with `mapper_parsing_exception`
- Error about field type mismatch (e.g., trying to index text into a date field)

**Cause:**
OpenSearch automatically maps field types based on the first document indexed. Subsequent documents with different types for the same field will fail.

**Solution:**

1. **Accept Some Failures:**
This is normal for heterogeneous logs. The system will log errors but continue processing.

2. **Pre-define Index Mappings:**
Create explicit mappings before ingestion:
```python
# In app/search/mappings.py, ensure dynamic mapping is set correctly
"dynamic": "true",
"dynamic_templates": [...]
```

3. **Check Error Logs:**
Enhanced error logging now shows the first 3 errors for each batch. Review these to understand which fields are causing issues.

---

### 3. Field Type Conflicts (Mapper Parsing Exceptions)

**Symptoms:**
- Ingestion completes successfully
- Count shows 0 or very few documents

**Diagnosis:**
```bash
# Check total log count
curl -k -u admin:admin 'https://localhost:9200/logs-*/_count?pretty'

# Check indices
curl -k -u admin:admin 'https://localhost:9200/_cat/indices?v' | grep logs

# Check cluster health
curl -k -u admin:admin 'https://localhost:9200/_cluster/health?pretty'
```

**Solutions:**
1. Ensure OpenSearch is running: `docker compose ps`
2. Check backend logs: `docker compose logs backend --tail=100`
3. Verify network connectivity between containers
4. Run setup script: `python scripts/setup_opensearch.py`

---

### 4. No Logs Appearing After Ingestion

**Symptoms:**
- Slow ingestion
- Backend container crashes
- OpenSearch becomes unresponsive

**Solutions:**

1. **Reduce Batch Size:**
```python
# In app/config.py or via environment variable
BATCH_SIZE=500  # Default is 1000
```

2. **Increase Docker Memory:**
```yaml
# In docker-compose.yml
services:
  opensearch-node1:
    environment:
      - "OPENSEARCH_JAVA_OPTS=-Xms2g -Xmx2g"  # Increase from default
```

3. **Limit Concurrent File Processing:**
Current implementation processes files sequentially, which is memory-efficient.

---

### 5. High Memory Usage / Performance Issues

**Symptoms:**
- Logs are re-ingested on every run
- Duplicate documents in OpenSearch

**Diagnosis:**
```bash
# Check checkpoint database
ls -lh backend/data/checkpoints.db

# Inside Docker:
docker compose exec backend sqlite3 /data/checkpoints.db "SELECT * FROM checkpoints LIMIT 5;"
```

**Solutions:**
1. Ensure checkpoint directory is writable
2. Check that incremental mode is enabled (default)
3. Clear checkpoints to force re-ingestion:
```bash
docker compose exec backend rm /data/checkpoints.db
```

---

### 6. Ingestion Checkpoint Issues

**Symptoms:**
- 401 Unauthorized errors
- Connection refused to OpenSearch

**Solutions:**

1. **Check Credentials:**
Default credentials are `admin:admin`. Verify in docker-compose.yml.

2. **Verify SSL Settings:**
```python
# In app/config.py
OPENSEARCH_VERIFY_CERTS=False  # For self-signed certs
```

3. **Test Connection:**
```bash
curl -k -u admin:admin 'https://localhost:9200/'
```

---

### 7. Authentication Errors

### View Cluster Statistics
```bash
python scripts/fix_opensearch_shards.py --stats
```

### Monitor Ingestion Progress
```bash
docker compose logs -f backend | grep "Flushed batch"
```

### Search for Specific Logs
```bash
curl -k -u admin:admin 'https://localhost:9200/logs-*/_search?pretty' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {"match": {"raw_line": "ERROR"}},
    "size": 5
  }'
```

### Check Disk Usage
```bash
curl -k -u admin:admin 'https://localhost:9200/_cat/allocation?v'
```

### Restart Services
```bash
docker compose restart backend
docker compose restart opensearch-node1
```

---

## Getting Help

1. Check the logs: `docker compose logs backend --tail=100`
2. Review OpenSearch logs: `docker compose logs opensearch-node1 --tail=100`
3. Enable debug logging:
```python
# In app/main.py
logging.basicConfig(level=logging.DEBUG)
```

4. Open an issue on GitHub with:
   - Error messages
   - Docker compose logs
   - Steps to reproduce
   - System information (OS, Docker version, etc.)
