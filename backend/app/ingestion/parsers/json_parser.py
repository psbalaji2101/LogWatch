"""JSON log parser"""

import json
import logging
from typing import Dict, Any

from app.ingestion.parsers.base import BaseParser

logger = logging.getLogger(__name__)


class JSONParser(BaseParser):
    """Parser for JSON-formatted logs"""
    
    def can_parse(self, line: str) -> bool:
        """Check if line is valid JSON"""
        line = line.strip()
        return line.startswith('{') and line.endswith('}')
    
    def parse(self, line: str) -> Dict[str, Any]:
        """Parse JSON log line"""
        try:
            data = json.loads(line)
            
            # Extract common fields
            fields = {}
            timestamp = None
            
            # Try to find timestamp
            for ts_field in ['timestamp', 'time', '@timestamp', 'datetime', 'ts']:
                if ts_field in data:
                    timestamp = self._parse_datetime(data[ts_field])
                    fields['timestamp_field'] = ts_field
                    break
            
            # Copy all fields
            for key, value in data.items():
                if isinstance(value, (str, int, float, bool)):
                    fields[key] = value
                else:
                    fields[key] = str(value)
            
            return {
                'timestamp': timestamp or self.extract_timestamp(line, fields),
                'fields': fields,
                'tokens': self.tokenize(line)
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}")
            return {
                'timestamp': None,
                'fields': {'parse_error': str(e)},
                'tokens': []
            }
