"""Sample end-to-end run for timestamp normalization

This script demonstrates ingestion pipeline (Phase A extraction + Phase B normalization)
for sample logs across multiple formats and services. It does NOT send data to
OpenSearch; instead it prints the document that would be indexed so we can
inspect @timestamp, raw_timestamp, ingested_at, and confidence metadata.

Run with:
    SKIP_APP_IMPORT=1 PYTHONPATH=backend python scripts/sample_e2e_run.py
"""

import json
from datetime import datetime

from app.ingestion.worker import IngestionWorker

SAMPLE_LINES = [
    # Service A - ISO 8601 with Z
    '2025-11-24T07:16:47Z INFO ServiceA Request processed id=abc123',

    # Service B - Apache/Nginx combined log style
    '192.0.2.1 - - [24/Nov/2025:07:16:47 +0000] "GET /api/v1/foo HTTP/1.1" 200 1234',

    # Service A - dot format
    '2025.11.24 07:16:47 ServiceA INFO user=joe action=login',

    # Service C - Go/Kubernetes style
    'I1124 07:16:47.123456 ServiceC: started worker',

    # Ambiguous/invalid timestamp
    'no-timestamp-here ServiceB WARN something weird happened',
]


def run():
    worker = IngestionWorker()

    docs = []
    for i, line in enumerate(SAMPLE_LINES, start=1):
        doc = worker._parse_line(line)
        # Add source metadata for demonstration
        doc['source_file'] = 'sample'  # not used by _parse_line
        doc['line_number'] = i
        docs.append(doc)
        print(json.dumps(doc, default=str, indent=2))

    # Simple correlation demonstration: show @timestamp values grouped by service
    print('\nSummary: @@timestamps by service (fields.service)')
    for d in docs:
        svc = d.get('fields', {}).get('service', 'unknown')
        print(f"service={svc:10s} @timestamp={d.get('@timestamp')} confidence={d.get('timestamp_confidence')}")


if __name__ == '__main__':
    run()
