"""
Universal timestamp parser - handles ANY timestamp format
Acts as a log parsing expert - tries multiple strategies
"""

import re
from datetime import datetime, timezone, timedelta
from dateutil import parser as dateutil_parser
import logging

logger = logging.getLogger(__name__)

# IST timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

class TimestampParser:
    """
    Universal timestamp parser supporting 20+ formats
    
    Strategy:
    1. Try 12 specific patterns (fastest)
    2. Fallback to dateutil parser (catches 95% of edge cases)
    3. Use ingestion time if all fails
    """
    
    def __init__(self):
        self.patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> dict:
        """Compile regex patterns for different timestamp formats"""
        return {
            # 1. ISO 8601 with Z (UTC)
            'iso_8601_z': re.compile(
                r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)',
                re.IGNORECASE
            ),
            
            # 2. ISO 8601 with timezone offset (+05:30, -08:00)
            'iso_8601_tz': re.compile(
                r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?[+-]\d{2}:\d{2})',
                re.IGNORECASE
            ),
            
            # 3. ISO with space instead of T
            'iso_space': re.compile(
                r'(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}(?:\.\d+)?)',
                re.IGNORECASE
            ),
            
            # 4. Unix epoch (seconds)
            'unix_epoch_sec': re.compile(
                r'\b(\d{10})(?:\.\d+)?\b'
            ),
            
            # 5. Unix epoch (milliseconds)
            'unix_epoch_ms': re.compile(
                r'\b(\d{13})(?:\.\d+)?\b'
            ),
            
            # 6. Syslog format (Nov 24 19:55:25)
            'syslog': re.compile(
                r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\s+(\d{2}:\d{2}:\d{2})',
                re.IGNORECASE
            ),
            
            # 7. Apache/Nginx format (24/Nov/2025:19:55:25 +0530)
            'apache_nginx': re.compile(
                r'(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}\s[+-]\d{4})'
            ),
            
            # 8. Custom dot format (2025.11.24 03:33:45)
            'dot_format': re.compile(
                r'(\d{4}\.\d{2}\.\d{2}\s\d{2}:\d{2}:\d{2})'
            ),
            
            # 9. Date slash format (2025/11/24 - 07:22:28)
            'slash_format': re.compile(
                r'(\d{4}/\d{2}/\d{2}\s-?\s\d{2}:\d{2}:\d{2})'
            ),
            
            # 10. Go/Kubernetes format (I1124 19:55:25.125155)
            'go_format': re.compile(
                r'([A-Z]\d{4}\s\d{2}:\d{2}:\d{2}\.\d+)'
            ),
            
            # 11. Java format (Nov 24, 2025 4:15:17 PM)
            'java_format': re.compile(
                r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),?\s+(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})\s+(AM|PM)',
                re.IGNORECASE
            ),
            
            # 12. RFC 2822 format (Thu, 24 Nov 2025 19:55:25 +0530)
            'rfc2822': re.compile(
                r'(\w{3},?\s+\d{1,2}\s+\w{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2}\s+[+-]\d{4})',
                re.IGNORECASE
            ),
        }
    
    def parse(self, timestamp_str: str, fallback_to_now: bool = True) -> datetime:
        """
        Parse ANY timestamp format to datetime (UTC)
        
        Args:
            timestamp_str: Raw timestamp string from log
            fallback_to_now: If True, use current time if parsing fails
        
        Returns:
            datetime object in UTC (naive, or with UTC timezone)
        
        Raises:
            ValueError: If parsing fails and fallback_to_now=False
        """
        
        if not timestamp_str:
            if fallback_to_now:
                logger.warning("Empty timestamp, using current time")
                return datetime.utcnow()
            raise ValueError("Empty timestamp string")
        
        timestamp_str = str(timestamp_str).strip()
        
        # Strategy 1: Try specific patterns (fast)
        for pattern_name, pattern in self.patterns.items():
            match = pattern.search(timestamp_str)
            if match:
                try:
                    dt = self._parse_by_pattern(match, pattern_name, timestamp_str)
                    if dt:
                        logger.debug(f"✅ Parsed {pattern_name}: {timestamp_str} → {dt}")
                        return self._normalize_to_utc(dt)
                except Exception as e:
                    logger.debug(f"Failed {pattern_name}: {e}")
                    continue
        
        # Strategy 2: Fallback to dateutil (catches 95% of edge cases)
        try:
            dt = dateutil_parser.parse(timestamp_str)
            logger.debug(f"✅ Parsed with dateutil: {timestamp_str} → {dt}")
            return self._normalize_to_utc(dt)
        except Exception as e:
            logger.warning(f"⚠️  dateutil failed: {e}")
        
        # Strategy 3: Last resort - use ingestion time
        if fallback_to_now:
            logger.warning(f"⚠️  Could not parse timestamp '{timestamp_str}', using current time")
            return datetime.utcnow()
        else:
            raise ValueError(f"Could not parse timestamp: {timestamp_str}")
    
    def _parse_by_pattern(self, match, pattern_name: str, original: str) -> datetime:
        """Parse matched timestamp by pattern"""
        
        if pattern_name == 'iso_8601_z':
            # 2025-11-24T07:16:47Z → datetime
            return dateutil_parser.parse(match.group(1))
        
        elif pattern_name == 'iso_8601_tz':
            # 2025-11-24T07:16:47+05:30 → datetime
            return dateutil_parser.parse(match.group(1))
        
        elif pattern_name == 'iso_space':
            # 2025-11-24 07:16:47 → datetime
            return dateutil_parser.parse(match.group(1))
        
        elif pattern_name == 'unix_epoch_sec':
            # 1732442387 → datetime
            return datetime.utcfromtimestamp(int(match.group(1)))
        
        elif pattern_name == 'unix_epoch_ms':
            # 1732442387125 → datetime
            return datetime.utcfromtimestamp(int(match.group(1)) / 1000)
        
        elif pattern_name == 'syslog':
            # Nov 24 19:55:25 → datetime (add current year)
            mon, day, time_str = match.group(1), match.group(2), match.group(3)
            dt_str = f"{datetime.utcnow().year} {mon} {day} {time_str}"
            return dateutil_parser.parse(dt_str)
        
        elif pattern_name == 'apache_nginx':
            # 24/Nov/2025:19:55:25 +0530 → datetime
            return dateutil_parser.parse(match.group(1))
        
        elif pattern_name == 'dot_format':
            # 2025.11.24 03:33:45 → datetime
            ts = match.group(1).replace('.', '-')
            return dateutil_parser.parse(ts)
        
        elif pattern_name == 'slash_format':
            # 2025/11/24 - 07:22:28 → datetime
            ts = match.group(1).replace('/', '-').replace(' - ', ' ')
            return dateutil_parser.parse(ts)
        
        elif pattern_name == 'go_format':
            # I1124 19:55:25.125155 → datetime
            ts_str = match.group(1)
            month_day = ts_str[1:5]  # 1124 → 11/24
            month = month_day[:2]
            day = month_day[2:]
            time_part = ts_str.split()[1]
            dt_str = f"{datetime.utcnow().year}-{month}-{day} {time_part}"
            return dateutil_parser.parse(dt_str)
        
        elif pattern_name == 'java_format':
            # Nov 24, 2025 4:15:17 PM → datetime
            return dateutil_parser.parse(original)
        
        elif pattern_name == 'rfc2822':
            # Thu, 24 Nov 2025 19:55:25 +0530 → datetime
            return dateutil_parser.parse(match.group(1))
        
        return None
    
    def _normalize_to_utc(self, dt: datetime) -> datetime:
        """
        Normalize datetime to UTC
        Handles both naive and timezone-aware datetimes
        """
        
        if dt.tzinfo is None:
            # Naive datetime - assume UTC
            return dt.replace(tzinfo=timezone.utc)
        else:
            # Timezone-aware - convert to UTC
            return dt.astimezone(timezone.utc)
    
    def to_ist(self, dt: datetime) -> datetime:
        """Convert UTC datetime to IST (for display purposes)"""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(IST)
    
    def to_iso_string(self, dt: datetime) -> str:
        """Convert datetime to ISO string"""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

# Global instance
_parser = None

def get_timestamp_parser() -> TimestampParser:
    """Get or create parser instance"""
    global _parser
    if _parser is None:
        _parser = TimestampParser()
    return _parser

def parse_timestamp(timestamp_str: str, fallback_to_now: bool = True) -> datetime:
    """
    Parse timestamp helper function
    
    Usage:
        dt = parse_timestamp("2025-11-24T07:16:47Z")
        dt = parse_timestamp("1732442387")  # Unix epoch
        dt = parse_timestamp("Nov 24 19:55:25")  # Syslog
    """
    parser = get_timestamp_parser()
    return parser.parse(timestamp_str, fallback_to_now)
