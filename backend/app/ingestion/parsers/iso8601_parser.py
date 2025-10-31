"""ISO8601 timestamp parser: 2025-11-08T12:18:46 LEVEL Message"""

import re
import logging
from datetime import datetime
from typing import Dict, Any

from app.ingestion.parsers.base import BaseParser

logger = logging.getLogger(__name__)


class ISO8601Parser(BaseParser):
    """Parse ISO8601 format logs with LEVEL"""
    
    # Pattern: 2025-11-08T12:18:46 FATAL Message here
    PATTERN = re.compile(
        r'^(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\s+'
        r'(?P<level>\w+)\s+'
        r'(?P<message>.+)$'
    )
    
    def can_parse(self, line: str) -> bool:
        """Check if line matches ISO8601 format"""
        return bool(self.PATTERN.match(line))
    
    def parse(self, line: str) -> Dict[str, Any]:
        """Parse ISO8601 log line"""
        match = self.PATTERN.match(line)
        
        if not match:
            return {
                'timestamp': datetime.utcnow(),
                'fields': {},
                'tokens': self.tokenize(line)
            }
        
        groups = match.groupdict()
        
        try:
            # Parse timestamp: 2025-11-08T12:18:46 → datetime object
            timestamp = datetime.strptime(
                groups['timestamp'],
                '%Y-%m-%dT%H:%M:%S'
            )
        except Exception as e:
            logger.warning(f"Failed to parse timestamp '{groups['timestamp']}': {e}")
            timestamp = datetime.utcnow()
        
        return {
            'timestamp': timestamp,
            'fields': {
                'level': groups['level'],
                'message': groups['message'],
                'pattern': 'iso8601_level_message'
            },
            'tokens': self.tokenize(groups['message'])
        }
