"""Base parser interface"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from datetime import datetime


class BaseParser(ABC):
    """Base parser interface for log parsing"""
    
    @abstractmethod
    def can_parse(self, line: str) -> bool:
        """Check if this parser can handle the line"""
        pass
    
    @abstractmethod
    def parse(self, line: str) -> Dict[str, Any]:
        """Parse a log line and return structured data"""
        pass
    
    def extract_timestamp(self, line: str, fields: Dict[str, Any]) -> datetime:
        """Extract or infer timestamp from log line"""
        # Try common timestamp fields
        for field in ['timestamp', 'time', '@timestamp', 'datetime']:
            if field in fields:
                return self._parse_datetime(fields[field])
        
        # Fallback to current time
        return datetime.utcnow()
    
    def _parse_datetime(self, value: Any) -> datetime:
        """Parse datetime from various formats"""
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            from dateutil import parser as date_parser
            try:
                return date_parser.parse(value)
            except Exception:
                pass
        
        return datetime.utcnow()
    
    def tokenize(self, line: str) -> List[str]:
        """Extract tokens from a line"""
        import re
        # Split on whitespace and punctuation
        tokens = re.findall(r'\w+', line.lower())
        return list(set(tokens))  # Unique tokens
