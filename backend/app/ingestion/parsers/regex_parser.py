"""Production Regex Parser for Enterprise Logs - WITH STRATEGY 1 TIMESTAMP FALLBACK"""

import re
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from dateutil import parser as dateparser

from app.ingestion.parsers.base import BaseParser
from app.ingestion.timestamp_extractor import extract_timestamp

logger = logging.getLogger(__name__)


class RegexParser(BaseParser):
    """
    Enterprise-grade log parser with service extraction from pod names
    
    Features:
    - Extracts service from pod/container names
    - Normalizes timestamps to ISO 8601 format
    - Skips logs without log levels (non-parseable)
    - Focuses on readable text logs (skips CSV/binary)
    - ✅ STRATEGY 1: Falls back to ingestion time for missing timestamps
    """
    
    # Log level patterns - MUST have one of these
    LOG_LEVELS = {
        'ERROR', 'WARN', 'WARNING', 'INFO', 'DEBUG', 
        'FATAL', 'CRITICAL', 'TRACE'
    }
    
    # Comprehensive patterns for enterprise logs
    PATTERNS = {
        # Pattern 1: ISO timestamp + level + message (most common)
        'iso_level_message': re.compile(
            r'^(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{4})?)\s+'
            r'(?P<level>ERROR|WARN|WARNING|INFO|DEBUG|FATAL|CRITICAL|TRACE)\s+'
            r'(?P<message>.+?)(?:,(?P<pod>[^,]+),(?P<namespace>[^,]+),(?P<container>[^,]+),(?P<host>[^,]+))?$'
        ),
        
        # Pattern 2: Kubernetes-style logs with structured metadata
        'k8s_structured': re.compile(
            r'time=(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\s+'
            r'level=(?P<level>error|warn|warning|info|debug|trace)\s+'
            r'msg=(?P<message>.+?)(?:\s+file=(?P<file>[^\s]+))?'
        ),
        
        # Pattern 3: Java-style logs
        'java_style': re.compile(
            r'^(?P<timestamp>\w+\s+\d+,\s+\d{4}\s+\d+:\d+:\d+\s+[AP]M)\s+'
            r'(?P<classname>[\w.]+)\s+'
            r'(?P<level>WARNING|INFO|SEVERE|ERROR|DEBUG)\s+'
            r'(?P<message>.+)$'
        ),
        
        # Pattern 4: Golang/structured logs
        'golang_style': re.compile(
            r'^(?P<level>[IWEF])(?P<mmdd>\d{4})\s+(?P<time>\d{2}:\d{2}:\d{2}\.\d+)\s+'
            r'(?P<thread>\d+)\s+(?P<file>[\w.]+:\d+)\s+(?P<message>.+)$'
        ),
        
        # Pattern 5: Prometheus/config-reloader style
        'prom_style': re.compile(
            r'level=(?P<level>info|error|warn|debug)\s+'
            r'ts=(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\s+'
            r'(?:caller=(?P<caller>[^\s]+)\s+)?'
            r'msg=(?P<message>.+)$'
        ),
        
        # Pattern 6: Stunnel/system logs
        'stunnel_style': re.compile(
            r'^(?P<timestamp>\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
            r'LOG(?P<loglevel>\d)\S*\s+'
            r'(?P<message>.+)$'
        ),
        
        # Pattern 7: GIN framework logs
        'gin_style': re.compile(
            r'^GIN\s+(?P<timestamp>\d{4}/\d{2}/\d{2}\s+-\s+\d{2}:\d{2}:\d{2})\s+'
            r'\|\s+(?P<status>\d{3})\s+\|\s+(?P<latency>[\d.]+\S+)\s+'
            r'\|\s+(?P<ip>[\d.]+)\s+\|\s+(?P<method>\w+)\s+(?P<endpoint>\S+)'
        ),
        
        # Pattern 8: ESAPI/application logs
        'esapi_style': re.compile(
            r'^ESAPI:\s+(?P<message>.+)$'
        ),
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
    
    def extract_service_from_pod(self, pod_name: str) -> str:
        """Extract service name from Kubernetes pod name"""
        if not pod_name:
            return 'unknown'
        
        # Remove deployment hash: -856b7856cd-tc6s9
        service = re.sub(r'-[0-9a-f]{8,10}-[a-z0-9]{5}$', '', pod_name)
        
        # Remove statefulset index: -0, -1, -2
        service = re.sub(r'-\d+$', '', service)
        
        # Remove common prefixes
        prefixes = ['itom-', 'omi-', 'credential-', 'apphub-']
        for prefix in prefixes:
            if service.startswith(prefix):
                service = service[len(prefix):]
                break
        
        # Replace hyphens with underscores for consistency
        service = service.replace('-', '_')
        
        return service if service else 'unknown'
    
    def normalize_timestamp(self, timestamp_str: str, pattern_name: str) -> Optional[datetime]:
        """Normalize various timestamp formats to datetime object"""
        try:
            if not timestamp_str:
                return None
            
            # Use dateutil parser for most formats
            dt = dateparser.parse(timestamp_str)
            return dt
            
        except Exception as e:
            logger.debug(f"Failed to parse timestamp '{timestamp_str}': {e}")
            return None
    
    def has_log_level(self, line: str) -> bool:
        """Check if line contains a log level keyword"""
        line_upper = line.upper()
        return any(level in line_upper for level in self.LOG_LEVELS)
    
    def can_parse(self, line: str) -> bool:
        """
        Check if line is parseable
        
        Criteria:
        1. MUST have a log level
        2. MUST match at least one pattern
        3. NOT be CSV format
        """
        # Skip CSV format logs
        if re.match(r'^\d+\.\d+,', line):
            return False
        
        # MUST have log level
        if not self.has_log_level(line):
            return False
        
        # Check if any pattern matches
        for pattern in self.patterns.values():
            if pattern.search(line):
                return True
        
        return False
    
    def parse(self, line: str) -> Dict[str, Any]:
        """
        Parse log line and extract structured data
        
        ✅ WITH STRATEGY 1: Falls back to ingestion time for missing timestamps
        """
        
        # Check if parseable
        if not self.can_parse(line):
            return None
        
        # Try each pattern
        for pattern_name, pattern in self.patterns.items():
            match = pattern.search(line)
            if match:
                fields = match.groupdict()
                
                # Extract timestamp
                timestamp_str = fields.get('timestamp')
                timestamp = self.normalize_timestamp(timestamp_str, pattern_name)
                
                # ✅ STRATEGY 1: Fallback to current ingestion time
                if not timestamp:
                    timestamp = datetime.utcnow()
                    fields['timestamp_inferred'] = True
                    logger.debug(f"Using ingestion time for log: {line[:100]}")
                
                # Extract level (normalize to uppercase)
                level = fields.get('level', '').upper()
                if not level or level not in self.LOG_LEVELS:
                    for log_level in self.LOG_LEVELS:
                        if log_level in line.upper():
                            level = log_level
                            break
                    if not level:
                        level = 'INFO'
                
                # Extract service from pod name
                pod = fields.get('pod', '')
                service = self.extract_service_from_pod(pod) if pod else 'unknown'
                
                # Extract message
                message = fields.get('message', '')
                if not message:
                    message = line[:200]
                
                # Build result
                result = {
                    'timestamp': timestamp,
                    'fields': {
                        'level': level,
                        'service': service,
                        'message': message,
                        'pattern': pattern_name,
                    },
                    'tokens': self.tokenize(line)
                }
                
                # Add optional metadata fields
                optional_fields = ['pod', 'namespace', 'container', 'host', 'file', 
                                  'caller', 'status', 'method', 'endpoint', 'classname']
                for field in optional_fields:
                    if field in fields and fields[field]:
                        result['fields'][field] = fields[field]
                
                return result
        
        # No pattern matched
        logger.warning(f"Line passed can_parse but no pattern matched: {line[:100]}")
        return None
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
