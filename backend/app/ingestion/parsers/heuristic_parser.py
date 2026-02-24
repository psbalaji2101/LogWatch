"""Heuristic parser for unknown formats"""

import re
import logging
from typing import Dict, Any
from datetime import datetime

from app.ingestion.parsers.base import BaseParser

logger = logging.getLogger(__name__)


class HeuristicParser(BaseParser):
    """Fallback parser using heuristics"""
    
    # Timestamp patterns
    TIMESTAMP_PATTERNS = [
        re.compile(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}'),
        re.compile(r'\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}'),
        re.compile(r'\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}'),
    ]
    
    # Common field patterns
    FIELD_PATTERNS = {
        'ip': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
        'url': re.compile(r'https?://[^\s]+'),
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'status_code': re.compile(r'\b[1-5]\d{2}\b'),
        'uuid': re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.I)
    }
    
    def can_parse(self, line: str) -> bool:
        """Can always parse (fallback parser)"""
        return True
    
    def parse(self, line: str) -> Dict[str, Any]:
        """Parse using heuristics"""
        
        fields = {}
        
        # Extract timestamp
        timestamp_str = None
        for pattern in self.TIMESTAMP_PATTERNS:
            match = pattern.search(line)
            if match:
                timestamp_str = match.group()
                break
        
        timestamp = self._parse_datetime(timestamp_str) if timestamp_str else datetime.utcnow()
        
        # Extract common fields
        for field_name, pattern in self.FIELD_PATTERNS.items():
            matches = pattern.findall(line)
            if matches:
                fields[field_name] = matches[0] if len(matches) == 1 else matches
        
        # Extract log level
        level_match = re.search(r'\b(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\b', line, re.I)
        if level_match:
            fields['level'] = level_match.group().upper()
        
        # Extract key=value pairs
        kv_pairs = re.findall(r'(\w+)=(["\']?)([^"\'\s]+)\2', line)
        for key, _, value in kv_pairs:
            fields[key] = value
        
        return {
            'timestamp': timestamp,
            'fields': fields,
            'tokens': self.tokenize(line)
        }
