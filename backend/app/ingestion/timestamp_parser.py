"""Timestamp normalization helper.

This module implements Phase B (Normalization) of the two-phase timestamp
strategy. It accepts a raw timestamp string (Phase A extractor output) and/or
an already parsed datetime coming from existing parsers and returns a
TimestampParseResult describing the outcome. No existing parser interfaces are
changed; this module orchestrates parsing and scoring.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional
from dateutil import parser as dateutil_parser
import logging

logger = logging.getLogger(__name__)


@dataclass
class TimestampParseResult:
    parsed_datetime: Optional[datetime]
    confidence: float
    format: Optional[str]
    error: Optional[str]
    source: Optional[str] = None  # 'extracted', 'parser', 'dateutil'
    assumed_year: Optional[int] = None
    timezone_assumed: Optional[str] = None


class TimestampNormalizer:
    """Normalize timestamp strings using multiple strategies and score them.

    Confidence guide (examples):
      - Exact ISO with timezone: 1.0
      - Epoch seconds/ms: 0.95
      - Pattern match with timezone offset: 0.9
      - Pattern match without timezone (assume naive UTC): 0.8
      - dateutil fallback: 0.72
      - heuristic/ambiguous parse: 0.6
      - failure: 0.0
    """

    def __init__(self):
        self.patterns = self._compile_patterns()

    def _compile_patterns(self) -> dict:
        return {
            'iso_8601_z': re.compile(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)', re.IGNORECASE),
            'iso_8601_tz': re.compile(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?[+-]\d{2}:?\d{2})', re.IGNORECASE),
            'iso_space': re.compile(r'(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}(?:\.\d+)?)', re.IGNORECASE),
            'unix_epoch_ms': re.compile(r'\b(\d{13})\b'),
            'unix_epoch_sec': re.compile(r'\b(\d{10})\b'),
            'dot_format': re.compile(r'(\d{4}\.\d{2}\.\d{2}\s\d{2}:\d{2}:\d{2}(?:\.\d+)?)'),
            'apache_nginx': re.compile(r'(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}\s[+-]\d{4})'),
            'syslog': re.compile(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}', re.IGNORECASE),
            'rfc2822': re.compile(r'\w{3},?\s+\d{1,2}\s+\w{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2}'),
            'go_format': re.compile(r'[A-Z]\d{4}\s\d{2}:\d{2}:\d{2}\.\d+'),
            'java_format': re.compile(r'\w{3}\s+\d{1,2},?\s+\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+(?:AM|PM)', re.IGNORECASE),
        }

    def parse(self, raw_ts: Optional[str], parser_dt: Optional[datetime] = None) -> TimestampParseResult:
        """Attempt to normalize timestamp and assign confidence.

        Args:
            raw_ts: the verbatim raw timestamp substring (Phase A output)
            parser_dt: an already-parsed datetime (from existing parser), optional

        Returns:
            TimestampParseResult
        """

        if raw_ts:
            raw_ts = str(raw_ts).strip()
            # Try strict patterns first
            for name, pattern in self.patterns.items():
                m = pattern.search(raw_ts)
                if m:
                    try:
                        if name == 'iso_8601_z':
                            dt = dateutil_parser.isoparse(m.group(1))
                            dt = self._ensure_utc(dt)
                            return TimestampParseResult(dt, 1.0, 'ISO-8601-Z', None, source='extracted')

                        if name == 'iso_8601_tz':
                            dt = dateutil_parser.parse(m.group(1))
                            dt = self._ensure_utc(dt)
                            return TimestampParseResult(dt, 0.95, 'ISO-8601-TZ', None, source='extracted')

                        if name == 'unix_epoch_ms':
                            dt = datetime.fromtimestamp(int(m.group(1)) / 1000.0, tz=timezone.utc)
                            return TimestampParseResult(dt, 0.95, 'epoch_millis', None, source='extracted')

                        if name == 'unix_epoch_sec':
                            dt = datetime.fromtimestamp(int(m.group(1)), tz=timezone.utc)
                            return TimestampParseResult(dt, 0.95, 'epoch_seconds', None, source='extracted')

                        if name in ('iso_space', 'dot_format', 'apache_nginx', 'rfc2822'):
                            dt = dateutil_parser.parse(m.group(0))
                            dt = self._ensure_utc(dt)
                            # If pattern has no explicit timezone, mark slightly lower confidence
                            conf = 0.9 if 'tz' in name else 0.85
                            tz_assumed = None
                            if dt.tzinfo is None:
                                tz_assumed = 'UTC'
                            return TimestampParseResult(dt, conf, name, None, source='extracted', timezone_assumed=tz_assumed)

                        if name == 'syslog':
                            # Syslog lacks year; assume current year but lower confidence
                            year = datetime.utcnow().year
                            dt = dateutil_parser.parse(f"{year} {m.group(0)}")
                            dt = self._ensure_utc(dt)
                            return TimestampParseResult(dt, 0.75, 'syslog', None, source='extracted', assumed_year=year)

                        if name == 'go_format':
                            # Build yyyy-mm-dd from mmdd and current year
                            s = m.group(0)
                            month_day = s[1:5]
                            month = month_day[:2]
                            day = month_day[2:]
                            time_part = s.split()[1]
                            dt = dateutil_parser.parse(f"{datetime.utcnow().year}-{month}-{day} {time_part}")
                            dt = self._ensure_utc(dt)
                            return TimestampParseResult(dt, 0.7, 'go_format', None, source='extracted', assumed_year=datetime.utcnow().year)

                    except Exception as e:
                        logger.debug(f"Pattern {name} matched but parse failed: {e}")
                        # Continue to next strategy

            # dateutil general fallback
            try:
                dt = dateutil_parser.parse(raw_ts)
                dt = self._ensure_utc(dt)
                # dateutil is powerful but can be ambiguous -> moderate confidence
                tz_assumed = None
                if dt.tzinfo is None:
                    tz_assumed = 'UTC'
                return TimestampParseResult(dt, 0.72, 'dateutil', None, source='extracted', timezone_assumed=tz_assumed)
            except Exception as e:
                logger.debug(f"dateutil failed for raw_ts '{raw_ts}': {e}")

        # If parser already returned a datetime, use it with moderate confidence
        if parser_dt:
            try:
                dt = self._ensure_utc(parser_dt)
                # If there was no raw_ts provided, treat parser-only datetimes as lower-confidence
                # to avoid silently trusting ambiguous parser heuristics.
                confidence = 0.82 if raw_ts else 0.6
                return TimestampParseResult(dt, confidence, 'parser_datetime', None, source='parser')
            except Exception as e:
                logger.debug(f"parser datetime present but normalization failed: {e}")

        # All attempts failed
        return TimestampParseResult(None, 0.0, None, 'could_not_parse')

    def _ensure_utc(self, dt: datetime) -> datetime:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)


# Global instance for module-level convenience
_normalizer = None

def get_timestamp_normalizer() -> TimestampNormalizer:
    global _normalizer
    if _normalizer is None:
        _normalizer = TimestampNormalizer()
    return _normalizer


def parse_timestamp(raw_timestamp: Optional[str], parser_datetime: Optional[datetime] = None) -> TimestampParseResult:
    """Convenience wrapper to produce a TimestampParseResult.

    This function keeps backwards compatibility for callers who previously used
    parse_timestamp to get a datetime: it now returns a TimestampParseResult.
    """
    normalizer = get_timestamp_normalizer()
    return normalizer.parse(raw_timestamp, parser_datetime)

