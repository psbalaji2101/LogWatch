"""Regex-based log parser - stores TIMESTAMP AS STRING (no conversion)"""

import re
import logging
from typing import Dict, Any

from app.ingestion.parsers.base import BaseParser
from app.ingestion.timestamp_extractor import extract_timestamp

logger = logging.getLogger(__name__)


class RegexParser(BaseParser):
    """Parser using regex patterns - stores timestamps as strings"""
    
    # Common log patterns
    PATTERNS = {
        'iso_8601_z': re.compile(
            r'(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)\s+(?P<level>[A-Z]+)\s+(?P<message>.+)',
            re.IGNORECASE
        ),
        'iso_8601_tz': re.compile(
            r'(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?[+-]\d{2}:\d{2})\s+(?P<level>[A-Z]+)\s+(?P<message>.+)',
            re.IGNORECASE
        ),
        'k8s_structured': re.compile(
            r'time=(?P<timestamp>[^\s]+)\s+level=(?P<level>[^\s]+)\s+msg="(?P<message>[^"]*)"',
            re.IGNORECASE
        ),
        'java_style': re.compile(
            r'(?P<timestamp>\w+\s+\d{1,2},?\s+\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+(?:AM|PM))\s+(?P<level>[A-Z]+)\s+(?P<message>.+)',
            re.IGNORECASE
        ),
        'prometheus_style': re.compile(
            r'level=(?P<level>[^\s]+)\s+ts=(?P<timestamp>[^\s]+)\s+caller=(?P<caller>[^\s]+)\s+(?P<message>.+)',
            re.IGNORECASE
        ),
        'stunnel_style': re.compile(
            r'(?P<timestamp>\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})\s+LOG[0-9]+\s+(?P<message>.+)',
        ),
        'gin_style': re.compile(
            r'\[(?P<timestamp>\d{4}/\d{2}/\d{2}\s-\s\d{2}:\d{2}:\d{2})\]\s+"(?P<method>[A-Z]+)\s+(?P<path>[^\s]+).*"\s+(?P<status>\d+)\s+',
        ),
        'go_style': re.compile(
            r'(?P<level>[A-Z])\d{4}\s+(?P<timestamp>\d{2}:\d{2}:\d{2}\.\d+)\s+(?P<message>.+)',
        ),
        'timestamp_level_message': re.compile(
            r'^(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})\s+(?P<level>[A-Z]+)\s+(?P<message>.+)$',
            re.IGNORECASE
        ),
    }
    
    def __init__(self, patterns: Dict[str, re.Pattern] = None):
        """Initialize parser with optional custom patterns"""
        self.patterns = patterns or self.PATTERNS
    
    def can_parse(self, line: str) -> bool:
        """
        Check if this parser can handle the line.
        Returns True if line has a log level (required).
        """
        if not line or not isinstance(line, str):
            return False
        
        # Check if line has a log level (required for ingestion)
        has_level = bool(self._extract_level(line))
        return has_level
    
    def parse(self, line: str) -> Dict[str, Any]:
        """
        Parse log line using regex patterns.
        
        IMPORTANT: Timestamp is stored as STRING, no conversion.
        
        Returns:
            Dict with timestamp (STRING), fields, tokens
            or None if cannot parse or no level found
        """
        if not line:
            return None
        
        # Extract log level (required)
        level = self._extract_level(line)
        if not level:
            return None
        
        # Try each pattern to extract fields
        fields = {}
        pattern_name = 'custom'
        
        for pname, pattern in self.patterns.items():
            match = pattern.search(line)
            if match:
                fields = match.groupdict()
                pattern_name = pname
                break
        
        # Extract timestamp as STRING (no parsing, no conversion)
        timestamp = extract_timestamp(line)
        
        return {
            'timestamp': timestamp,  # STRING, not datetime!
            'fields': {
                **fields,
                'level': level,
                'service': self._extract_service(line, fields),
                'pattern': pattern_name
            },
            'tokens': self.tokenize(line)
        }
    
    def _extract_level(self, line: str) -> str:
        """Extract log level from line - REQUIRED"""
        levels = ['ERROR', 'FATAL', 'WARN', 'WARNING', 'INFO', 'DEBUG', 'TRACE']
        for level in levels:
            if re.search(rf'\b{level}\b', line, re.IGNORECASE):
                return level.upper()
        return None
    
    def _extract_service(self, line: str, fields: Dict) -> str:
        """
        Extract service name from pod name or container name.
        
        Examples:
        - itom-ingress-controller-856b7856cd-tc6s9 → ingress_controller
        - ucmdb-browser-fd99d7c9f-5jx6p → ucmdb_browser
        """
        # Try container field first
        container = fields.get('container', '')
        if container:
            return self._clean_service_name(container)
        
        # Try pod pattern in raw_line or message
        raw_line = fields.get('raw_line', line)
        
        # Look for pod name pattern: name-hash-hash
        pod_pattern = r'(?:pod[_=])?([a-z0-9-]+)-[a-z0-9]{10,}-[a-z0-9]{5}'
        match = re.search(pod_pattern, raw_line, re.IGNORECASE)
        if match:
            return self._clean_service_name(match.group(1))
        
        # Look for service name in brackets: [service-name]
        bracket_pattern = r'\[([a-z0-9-]+)\]'
        match = re.search(bracket_pattern, raw_line, re.IGNORECASE)
        if match:
            return self._clean_service_name(match.group(1))
        
        # Look for common keywords
        keywords = ['api', 'auth', 'gateway', 'database', 'cache', 'queue', 'worker', 'proxy']
        for keyword in keywords:
            if re.search(rf'\b{keyword}\b', raw_line, re.IGNORECASE):
                return keyword
        
        return 'unknown'
    
    def _clean_service_name(self, name: str) -> str:
        """Clean service name: remove suffixes, replace hyphens with underscores"""
        if not name:
            return 'unknown'
        
        # Remove pod hash suffixes
        name = re.sub(r'-[a-z0-9]{10,}-[a-z0-9]{5}.*$', '', name)
        
        # Replace hyphens with underscores
        name = name.replace('-', '_').lower()
        
        # Remove -service suffix
        name = name.replace('_service', '')
        
        return name or 'unknown'
