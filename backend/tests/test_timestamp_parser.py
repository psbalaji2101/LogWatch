import pytest
from datetime import datetime
import pytest

from app.ingestion.timestamp_parser import parse_timestamp


class TestTimestampParser:
    """Test the TimestampParseResult and scoring"""

    def test_iso_8601_z(self):
        """ISO 8601 with Z should parse with high confidence and correct UTC time"""
        res = parse_timestamp("2025-11-24T07:16:47Z")
        assert res.parsed_datetime is not None
        assert res.parsed_datetime.year == 2025
        assert res.parsed_datetime.month == 11
        assert res.parsed_datetime.day == 24
        assert res.parsed_datetime.hour == 7
        assert res.confidence >= 0.9

    def test_iso_with_offset(self):
        """ISO with offset should convert to UTC and have high confidence"""
        res = parse_timestamp("2025-11-24T12:46:47+05:30")
        assert res.parsed_datetime is not None
        # UTC should be 07:16
        assert res.parsed_datetime.hour == 7
        assert res.parsed_datetime.minute == 16
        assert res.confidence >= 0.9

    def test_unix_epoch(self):
        """Unix epoch seconds should parse to UTC datetime"""
        from datetime import timezone
        expected = 1732442387
        res = parse_timestamp(str(expected))
        assert res.parsed_datetime is not None
        # Compare epoch seconds (robust across timezone/year assumptions)
        assert int(res.parsed_datetime.astimezone(timezone.utc).timestamp()) == expected
        assert res.confidence >= 0.9

    def test_dot_format(self):
        res = parse_timestamp("2025.11.24 03:33:45")
        assert res.parsed_datetime is not None
        assert res.parsed_datetime.year == 2025
        assert res.parsed_datetime.month == 11
        assert res.parsed_datetime.day == 24
        assert res.confidence >= 0.8

    def test_go_format(self):
        res = parse_timestamp("I1124 19:55:25.125155")
        assert res.parsed_datetime is not None
        assert res.parsed_datetime.month == 11
        assert res.parsed_datetime.day == 24
        # go_format is less precise about year/timezone
        assert 0.7 <= res.confidence <= 0.85

    def test_invalid_timestamp_reports_failure(self):
        """Invalid timestamps should not silently return 'now' — should have zero confidence and error"""
        res = parse_timestamp("not-a-timestamp")
        assert res.parsed_datetime is None
        assert res.confidence == 0.0
        assert res.error is not None

