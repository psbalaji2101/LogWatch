"""Regex-based log parser"""

import re
import logging
from typing import Dict, Any, List, Tuple

from app.ingestion.parsers.base import BaseParser

logger = logging.getLogger(__name__)


class RegexParser(BaseParser):
    """Parser using regex patterns"""
    
    # Common log patterns
    PATTERNS = {
        'apache_combined': re.compile(
            r'(?P<ip>\S+) \S+ \S+ \[(?P<timestamp>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+) (?P<protocol>\S+)" (?P<status>\d+) (?P<size>\S+)'
        ),
        'nginx_access': re.compile(
            r'(?P<ip>\S+) - \S+ \[(?P<timestamp>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+) (?P<protocol>\S+)" (?P<status>\d+) (?P<size>\d+)'
        ),
        'syslog': re.compile(
            r'(?P<timestamp>\w+\s+\d+\s+\d+:\d+:\d+) (?P<host>\S+) (?P<process>\S+): (?P<message>.*)'
        ),
        'timestamp_level_message': re.compile(
            r'\[?(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[^\]]*)\]?\s+(?P<level>\w+):?\s+(?P<message>.*)'
        )
    }
    
    def __init__(self, patterns: Dict[str, re.Pattern] = None):
        self.patterns = patterns or self.PATTERNS
    
    def can_parse(self, line: str) -> bool:
        """Check if any pattern matches"""
        for pattern in self.patterns.values():
            if pattern.search(line):
                return True
        return False
    
    def parse(self, line: str) -> Dict[str, Any]:
        """Parse log line using regex patterns"""
        
        for pattern_name, pattern in self.patterns.items():
            match = pattern.search(line)
            if match:
                fields = match.groupdict()
                
                # Extract timestamp
                timestamp = self.extract_timestamp(line, fields)
                
                return {
                    'timestamp': timestamp,
                    'fields': {
                        **fields,
                        'pattern': pattern_name
                    },
                    'tokens': self.tokenize(line)
                }
        
        # No pattern matched
        return {
            'timestamp': None,
            'fields': {},
            'tokens': self.tokenize(line)
        }
