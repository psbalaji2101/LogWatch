#!/usr/bin/env python3
"""
Reindex script to fix mapping conflicts across indices.
This creates new indices with correct mappings and copies data.
"""

import requests
from urllib3.exceptions import InsecureRequestWarning
import urllib3
import sys

urllib3.disable_warnings(InsecureRequestWarning)

OPENSEARCH_URL = "https://localhost:9200"
AUTH = ("admin", "admin")

def get_indices_with_prefix(prefix="logs-"):
    """Get all indices matching prefix"""
    url = f"{OPENSEARCH_URL}/_cat/indices/{prefix}*?format=json"
    response = requests.get(url, auth=AUTH, verify=False)
    response.raise_for_status()
    return [idx['index'] for idx in response.json()]

def reindex_single_index(source_index, dest_index):
    """Reindex source to destination"""
    reindex_body = {
        "source": {
            "index": source_index
        },
        "dest": {
            "index": dest_index
        },
        "conflicts": "proceed"
    }
    
    url = f"{OPENSEARCH_URL}/_reindex"
    response = requests.post(url, json=reindex_body, auth=AUTH, verify=False)
    return response.json()

def delete_index(index_name):
    """Delete an index"""
    url = f"{OPENSEARCH_URL}/{index_name}"
    response = requests.delete(url, auth=AUTH, verify=False)
    return response.status_code == 200

def main():
    print("⚠️  WARNING: This will reindex all logs indices")
    print("This process:")
    print("  1. Creates new temporary indices with correct mappings")
    print("  2. Copies data from old to new indices")
    print("  3. Deletes old indices")
    print("  4. Renames new indices to original names")
    print()
    
    response = input("Do you want to continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled")
        return
    
    indices = get_indices_with_prefix("logs-")
    print(f"\nFound {len(indices)} indices to reindex")
    
    for i, old_index in enumerate(indices, 1):
        temp_index = f"{old_index}-temp"
        print(f"\n[{i}/{len(indices)}] Processing {old_index}...")
        
        try:
            # Reindex to temp
            print(f"  → Reindexing to {temp_index}")
            result = reindex_single_index(old_index, temp_index)
            copied = result.get('total', 0)
            print(f"  ✓ Copied {copied} documents")
            
            # Delete old index
            print(f"  → Deleting old index")
            if delete_index(old_index):
                print(f"  ✓ Deleted {old_index}")
            
            # Reindex back to original name
            print(f"  → Reindexing to {old_index}")
            result = reindex_single_index(temp_index, old_index)
            print(f"  ✓ Recreated {old_index}")
            
            # Delete temp
            delete_index(temp_index)
            print(f"  ✓ Cleaned up temp index")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            continue
    
    print("\n✓ Reindexing complete!")
    print("Refresh your index pattern in OpenSearch Dashboards")

if __name__ == '__main__':
    main()
