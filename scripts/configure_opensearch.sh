#!/bin/bash
# Startup script to ensure OpenSearch shard limit is set correctly

echo "Waiting for OpenSearch to be ready..."
until curl -k -u admin:admin -s 'https://opensearch-node1:9200/_cluster/health' > /dev/null 2>&1; do
    sleep 2
done

echo "OpenSearch is ready. Setting shard limit to 10000..."
curl -k -u admin:admin -X PUT 'https://opensearch-node1:9200/_cluster/settings' \
    -H 'Content-Type: application/json' \
    -d '{"persistent":{"cluster.max_shards_per_node":"10000"}}' \
    > /dev/null 2>&1

echo "Shard limit configured successfully"
