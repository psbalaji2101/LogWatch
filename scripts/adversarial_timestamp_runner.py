"""Adversarial runner: feed many edge-case lines through the ingestion worker
and print the timestamp-related fields for inspection.

Run with:
    SKIP_APP_IMPORT=1 PYTHONPATH=backend python scripts/adversarial_timestamp_runner.py
"""

from datetime import datetime, timedelta
from app.ingestion.worker import IngestionWorker

CASES = [
    # 1. Multiple timestamps in one line (two timestamps)
    ("Multiple timestamps", "2025-11-24T07:16:47Z something 24/Nov/2025:07:16:47 +0000 INFO A"),

    # 2. Time-only (no date)
    ("Time only", "07:16:47 INFO occurred event"),

    # 3. Date without year (syslog style)
    ("No year", "Nov 24 07:16:47 service started"),

    # 4. Locale ambiguous (01/02/2025 could be Jan 2 or Feb 1)
    ("Locale ambiguous", "01/02/2025 07:16:47 service event"),

    # 5. Crossing DST boundary (example: assuming DST change)
    ("DST boundary", "2025-03-30 01:30:00 service event"),

    # 6. Future timestamp (far future)
    ("Future ts", "2099-01-01T00:00:00Z service event"),

    # 7. Old timestamp (weeks/months before ingestion)
    ("Old ts", "2020-01-01T12:00:00Z service event"),

    # 8. Epoch seconds vs milliseconds confusion (10 vs 13 digits)
    ("Epoch sec", "1732442387 INFO epoch"),
    ("Epoch ms", "1732442387123 INFO epochms"),

    # 9. Mixed timezone offsets inside same service line
    ("Mixed tz", "2025-11-24T07:16:47+05:30 serviceA 2025-11-24T01:46:47Z serviceB"),

    # 10. Clock-skewed sources (two services with 10 minute skew)
    ("Clock skew 1", "2025-11-24T07:06:47Z svcA event"),
    ("Clock skew 2", "2025-11-24T07:16:47+00:00 svcB event"),

    # 11. Partially truncated timestamp
    ("Truncated", "2025-11-24T07:16 service truncated"),

    # 12. No timestamp at all
    ("No ts", "ServiceX did something without timestamp"),

    # 13. Parser-provided datetime disagreeing with extracted raw timestamp
    ("Parser vs raw mismatch", '{"timestamp": "2025-11-24T07:16:47Z", "time": "24/11/2025 01:16:47 +0000", "level": "INFO"}'),
]


def run():
    worker = IngestionWorker()
    print(f"Running adversarial timestamp cases at {datetime.utcnow().isoformat()}Z")
    for name, line in CASES:
        doc = worker._parse_line(line)
        print("---")
        print(f"CASE: {name}")
        for k in ['@timestamp', 'raw_timestamp', 'ingested_at', 'timestamp_confidence', 'timestamp_format', 'timestamp_parse_error']:
            print(f"{k}: {doc.get(k)!r}")

if __name__ == '__main__':
    run()
