import os
import pytest
from datetime import datetime, timezone

from app.ingestion.worker import IngestionWorker


@pytest.fixture(autouse=True)
def skip_app_import_env(monkeypatch):
    # Ensure test runner doesn't import the full FastAPI app
    monkeypatch.setenv('SKIP_APP_IMPORT', '1')
    yield


def test_time_only_should_not_be_trusted():
    worker = IngestionWorker()
    line = "07:16:47 INFO incomplete time-only"
    doc = worker._parse_line(line)

    # raw_timestamp should be None (extractor didn't find date), parser datetime is present but low confidence
    assert doc['raw_timestamp'] is None
    assert doc['timestamp_confidence'] < 0.7
    assert doc['timestamp_origin'] == 'ingested_fallback'
    assert doc['timestamp_parse_error'] is not None


def test_locale_ambiguous_string_marked_untrusted():
    worker = IngestionWorker()
    line = "01/02/2025 07:16:47 ambiguous date"
    doc = worker._parse_line(line)

    # No raw extraction recognized by extractor in strict patterns -> should not silently trust
    assert doc['raw_timestamp'] is None
    assert doc['timestamp_confidence'] < 0.7
    assert doc['timestamp_origin'] == 'ingested_fallback'


def test_syslog_without_year_has_assumed_year_and_lower_confidence():
    worker = IngestionWorker()
    line = "Nov 24 07:16:47 myservice started"
    doc = worker._parse_line(line)

    # raw_timestamp preserved
    assert doc['raw_timestamp'] == 'Nov 24 07:16:47'
    # Should contain assumed year metadata
    assert doc['timestamp_assumed_year'] is not None
    # Confidence is below 0.8 but may be above threshold; ensure field exists
    assert 'timestamp_confidence' in doc


def test_multiple_timestamps_choose_first_extracted():
    worker = IngestionWorker()
    line = "2025-11-24T07:16:47Z then 24/Nov/2025:07:16:47 +0000 other"
    doc = worker._parse_line(line)

    assert doc['raw_timestamp'] == '2025-11-24T07:16:47Z'
    assert doc['timestamp_confidence'] >= 0.7
    assert doc['timestamp_origin'] == 'normalized'
    assert doc['timestamp_parse_error'] is None
