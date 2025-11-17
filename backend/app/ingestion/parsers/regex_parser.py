"""Regex-based log parser - UPDATED to extract service"""

import re
import logging
from typing import Dict, Any, List, Tuple

from app.ingestion.parsers.base import BaseParser

logger = logging.getLogger(__name__)


class RegexParser(BaseParser):
    """Parser using regex patterns - NOW EXTRACTS SERVICE"""
    
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
        'timestamp_level_service_message': re.compile(
            r'^(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+(?P<level>[A-Z]+)\s+\[(?P<service>[^\]]+)\]\s+(?P<message>.+)$'
        ),
        'timestamp_level_message': re.compile(
            r'^(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})\s+(?P<level>[A-Z]+)\s+(?P<message>.+)$'
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
    
    def extract_service_from_line(self, line: str) -> str:
        """
        Extract service name from log line using multiple strategies
        
        Patterns:
        - [service-name]
        - [auth-service]
        - service=name
        - service: name
        """
        # Pattern 1: [service-name] or [auth]
        match = re.search(r'\[([^\]]+)\]', line)
        if match:
            service = match.group(1)
            # Remove '-service' suffix if present
            service = service.replace('-service', '').replace('-', '_').strip()
            if service and service != 'unknown':
                return service
        
        # Pattern 2: service=name or service: name
        match = re.search(r'service[:\s=]+([^\s,\]]+)', line, re.IGNORECASE)
        if match:
            service = match.group(1).replace('-service', '').strip()
            if service and service != 'unknown':
                return service
        
        # Pattern 3: Common service prefixes in message
        service_patterns = [
            'api-service',
            'auth-service', 
            'notification-service',
            'payment-service',
            'user-service',
            'order-service',
            'inventory-service',
            'database',
            'cache',
            'queue',
        ]
        
        line_lower = line.lower()
        for service in service_patterns:
            if service in line_lower:
                return service.replace('-service', '').replace('-', '_')
        
        return source_file.split('/')[-1] if (source_file := re.search(r'from (\S+)', line)) else 'unknown'
    
    def parse(self, line: str) -> Dict[str, Any]:
        """
        Parse log line using regex patterns
        
        UPDATED:
        - Extracts service name from line
        - Sets level (ERROR, WARN, INFO)
        - Returns structured fields
        """
        
        for pattern_name, pattern in self.patterns.items():
            match = pattern.search(line)
            if match:
                fields = match.groupdict()
                
                # Extract timestamp
                timestamp = self.extract_timestamp(line, fields)
                
                # Extract or determine service
                service = fields.get('service')
                if not service or service == 'unknown':
                    service = self.extract_service_from_line(line)
                
                # Extract level
                level = fields.get('level', 'INFO').upper()
                
                # Extract message
                message = fields.get('message', '')
                if not message:
                    message = line[:200]
                
                return {
                    'timestamp': timestamp,
                    'fields': {
                        'level': level,
                        'service': service,
                        'message': message,
                        'pattern': pattern_name,
                        **{k: v for k, v in fields.items() if k not in ['timestamp', 'level', 'service', 'message']}
                    },
                    'tokens': self.tokenize(line)
                }
        
        # No pattern matched - try to extract what we can
        service = self.extract_service_from_line(line)
        
        # Try to detect level from line
        level = 'INFO'
        if 'ERROR' in line.upper() or 'FAILED' in line.upper():
            level = 'ERROR'
        elif 'WARN' in line.upper() or 'WARNING' in line.upper():
            level = 'WARN'
        elif 'DEBUG' in line.upper():
            level = 'DEBUG'
        
        return {
            'timestamp': self.extract_timestamp(line, {}),
            'fields': {
                'level': level,
                'service': service,
                'message': line[:200],
                'pattern': 'unknown'
            },
            'tokens': self.tokenize(line)
        }