import pytest
from datetime import datetime, timezone
from app.ingestion.timestamp_parser import parse_timestamp

class TestTimestampParser:
    """Test universal timestamp parser"""
    
    def test_iso_8601_z(self):
        """Test ISO 8601 with Z (UTC)"""
        result = parse_timestamp("2025-11-24T07:16:47Z")
        assert result.year == 2025
        assert result.month == 11
        assert result.day == 24
        assert result.hour == 7
    
    def test_iso_with_offset(self):
        """Test ISO 8601 with timezone offset"""
        result = parse_timestamp("2025-11-24T12:46:47+05:30")
        # Should convert to UTC: 12:46 IST - 5:30 = 07:16 UTC
        assert result.hour == 7
        assert result.minute == 16
    
    def test_unix_epoch(self):
        """Test Unix epoch timestamps"""
        # 1732442387 = 2025-11-24 07:16:27 UTC
        result = parse_timestamp("1732442387")
        assert result.year == 2025
    
    def test_dot_format(self):
        """Test dot format (2025.11.24 03:33:45)"""
        result = parse_timestamp("2025.11.24 03:33:45")
        assert result.year == 2025
        assert result.month == 11
        assert result.day == 24
    
    def test_go_format(self):
        """Test Go format (I1124 19:55:25.125155)"""
        result = parse_timestamp("I1124 19:55:25.125155")
        assert result.month == 11
        assert result.day == 24
    
    def test_fallback_to_now(self):
        """Test fallback when parsing fails"""
        now_before = datetime.utcnow()
        result = parse_timestamp("invalid-timestamp")
        now_after = datetime.utcnow()
        
        # Should return current time
        assert now_before <= result <= now_after

# Run tests
# pytest backend/tests/test_timestamp_parser.py -v
