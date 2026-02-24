#!/usr/bin/env python3
"""
Fix OpenSearch shard limit issue and optionally clean up old indices.

This script:
1. Increases the max shards per node setting in OpenSearch
2. Optionally deletes old indices to free up resources
"""

import requests
import argparse
from datetime import datetime, timedelta
from urllib3.exceptions import InsecureRequestWarning
import urllib3

# Suppress SSL warnings for self-signed certs
urllib3.disable_warnings(InsecureRequestWarning)

OPENSEARCH_URL = "https://localhost:9200"
AUTH = ("admin", "admin")


def increase_shard_limit(max_shards=5000):
    """Increase the maximum shards per node setting"""
    url = f"{OPENSEARCH_URL}/_cluster/settings"
    payload = {
        "persistent": {
            "cluster.max_shards_per_node": str(max_shards)
        }
    }
    
    try:
        response = requests.put(url, json=payload, auth=AUTH, verify=False)
        response.raise_for_status()
        print(f"✓ Successfully increased max shards per node to {max_shards}")
        return True
    except Exception as e:
        print(f"✗ Failed to increase shard limit: {e}")
        return False


def list_indices():
    """List all indices with their document counts"""
    url = f"{OPENSEARCH_URL}/_cat/indices?format=json"
    
    try:
        response = requests.get(url, auth=AUTH, verify=False)
        response.raise_for_status()
        indices = response.json()
        
        # Filter and sort by index name
        log_indices = [idx for idx in indices if idx['index'].startswith('logs-')]
        log_indices.sort(key=lambda x: x['index'])
        
        return log_indices
    except Exception as e:
        print(f"✗ Failed to list indices: {e}")
        return []


def delete_old_indices(days_to_keep=30):
    """Delete indices older than specified days"""
    indices = list_indices()
    
    if not indices:
        print("No indices found")
        return
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    deleted_count = 0
    
    for idx in indices:
        index_name = idx['index']
        
        # Extract date from index name (format: logs-YYYY-MM-DD)
        try:
            date_str = index_name.replace('logs-', '')
            index_date = datetime.strptime(date_str, '%Y-%m-%d')
            
            if index_date < cutoff_date:
                url = f"{OPENSEARCH_URL}/{index_name}"
                response = requests.delete(url, auth=AUTH, verify=False)
                
                if response.status_code == 200:
                    print(f"✓ Deleted old index: {index_name} ({idx['docs.count']} docs)")
                    deleted_count += 1
                else:
                    print(f"✗ Failed to delete {index_name}: {response.status_code}")
        except ValueError:
            # Skip indices that don't match expected date format
            continue
    
    print(f"\nDeleted {deleted_count} old indices")


def show_cluster_stats():
    """Display cluster shard statistics"""
    url = f"{OPENSEARCH_URL}/_cluster/stats"
    
    try:
        response = requests.get(url, auth=AUTH, verify=False)
        response.raise_for_status()
        stats = response.json()
        
        shards = stats['indices']['shards']
        print("\n=== Cluster Shard Statistics ===")
        print(f"Total shards: {shards['total']}")
        print(f"Primary shards: {shards['primaries']}")
        print(f"Total indices: {stats['indices']['count']}")
        print(f"Total documents: {stats['indices']['docs']['count']:,}")
        
    except Exception as e:
        print(f"✗ Failed to get cluster stats: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Fix OpenSearch shard limit and manage indices"
    )
    parser.add_argument(
        '--increase-limit',
        type=int,
        default=5000,
        help='Set max shards per node (default: 5000)'
    )
    parser.add_argument(
        '--delete-old',
        action='store_true',
        help='Delete old indices'
    )
    parser.add_argument(
        '--keep-days',
        type=int,
        default=30,
        help='Number of days of logs to keep when deleting (default: 30)'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show cluster statistics'
    )
    
    args = parser.parse_args()
    
    print("OpenSearch Shard Management Tool\n")
    
    # Show stats
    if args.stats or not any([args.delete_old]):
        show_cluster_stats()
    
    # Increase shard limit
    increase_shard_limit(args.increase_limit)
    
    # Delete old indices if requested
    if args.delete_old:
        print(f"\nDeleting indices older than {args.keep_days} days...")
        response = input("Are you sure? This cannot be undone. (yes/no): ")
        if response.lower() == 'yes':
            delete_old_indices(args.keep_days)
        else:
            print("Deletion cancelled")
    
    # Show stats again after operations
    if args.delete_old:
        print()
        show_cluster_stats()


if __name__ == '__main__':
    main()
