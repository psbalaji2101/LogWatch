"""CSV/TSV log parser"""

import csv
import io
import logging
from typing import Dict, Any

from app.ingestion.parsers.base import BaseParser

logger = logging.getLogger(__name__)


class CSVParser(BaseParser):
    """Parser for CSV/TSV logs"""
    
    def __init__(self, delimiter: str = ',', headers: list = None):
        self.delimiter = delimiter
        self.headers = headers or []
    
    def can_parse(self, line: str) -> bool:
        """Check if line looks like CSV"""
        # Simple heuristic: contains delimiter and quoted fields
        return self.delimiter in line and ('"' in line or len(line.split(self.delimiter)) > 2)
    
    def parse(self, line: str) -> Dict[str, Any]:
        """Parse CSV log line"""
        try:
            reader = csv.reader(io.StringIO(line), delimiter=self.delimiter)
            row = next(reader)
            
            fields = {}
            
            if self.headers and len(row) == len(self.headers):
                # Use provided headers
                for header, value in zip(self.headers, row):
                    fields[header] = value
            else:
                # Generic field names
                for i, value in enumerate(row):
                    fields[f'field_{i}'] = value
            
            timestamp = self.extract_timestamp(line, fields)
            
            return {
                'timestamp': timestamp,
                'fields': fields,
                'tokens': self.tokenize(line)
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse CSV: {e}")
            return {
                'timestamp': None,
                'fields': {'parse_error': str(e)},
                'tokens': []
            }
