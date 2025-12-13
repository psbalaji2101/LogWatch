"""
Timestamp extractor - STORES TIMESTAMPS AS STRINGS, NO CONVERSION
"""

import re
import logging

logger = logging.getLogger(__name__)


class SimpleTimestampExtractor:
    """
    Extracts timestamp FROM log and stores it AS-IS (STRING).
    
    NO parsing, NO conversion, NO datetime objects.
    Just find the timestamp string and return it unchanged.
    """
    
    # Regex patterns for timestamp extraction (VERY STRICT - match first)
    TIMESTAMP_PATTERNS = [
        # ISO 8601 with comma in milliseconds (YOUR format!) - 2025-11-24T05:00:22,607Z
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2},\d+Z)',
        
        # ISO 8601 with period in milliseconds - 2025-11-24T05:00:22.607Z
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)',
        
        # ISO 8601 with Z (no milliseconds)
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)',
        
        # ISO 8601 with timezone offset (period) - 2025-11-24T07:22:33.801+0000
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+[+-]\d{2}:?\d{2})',
        
        # ISO 8601 with timezone offset (comma) - 2025-11-24T07:22:33,801+0000
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2},\d+[+-]\d{2}:?\d{2})',
        
        # ISO 8601 with space (period)
        r'(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\.\d+)',
        
        # ISO 8601 with space (no milliseconds)
        r'(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})',
        
        # Dot format (2025.11.24 03:33:45)
        r'(\d{4}\.\d{2}\.\d{2}\s\d{2}:\d{2}:\d{2}(?:\.\d+)?)',
        
        # Slash format (2025/11/24 - 07:22:28)
        r'(\d{4}/\d{2}/\d{2}\s-?\s?\d{2}:\d{2}:\d{2}(?:\.\d+)?)',
        
        # Apache/Nginx (24/Nov/2025:19:55:25 +0530)
        r'(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}\s[+-]\d{4})',
        
        # Go/Kubernetes (I1124 19:55:25.125155)
        r'([A-Z]\d{4}\s\d{2}:\d{2}:\d{2}\.\d+)',
        
        # Syslog (Nov 24 19:55:25)
        r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})',
        
        # Java format (Nov 24, 2025 4:15:17 PM)
        r'(\w{3}\s+\d{1,2},?\s+\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+(?:AM|PM))',
        
        # RFC 2822 (Thu, 24 Nov 2025 19:55:25)
        r'(\w{3},?\s+\d{1,2}\s+\w{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2})',
        
        # Unix epoch (10 or 13 digits)
        r'\b(\d{10}|\d{13})\b',
    ]
    
    def __init__(self):
        """Compile regex patterns"""
        self.patterns = [re.compile(p) for p in self.TIMESTAMP_PATTERNS]
    
    def extract(self, log_line: str) -> str:
        """
        Extract timestamp STRING from log line.
        
        Returns the timestamp AS-IS, NO conversion, NO parsing.
        
        Args:
            log_line: The raw log line
        
        Returns:
            Extracted timestamp string, or None if not found
        
        Examples:
            "2025-11-24T07:22:33,801+0000 INFO ..." → "2025-11-24T07:22:33,801+0000"
            "2025-11-24T05:00:22.607Z INFO ..." → "2025-11-24T05:00:22.607Z"
        """
        if not log_line:
            return None
        
        # Try each pattern in order
        for i, pattern in enumerate(self.patterns):
            match = pattern.search(log_line)
            if match:
                timestamp_str = match.group(1)
                logger.debug(f"Pattern {i}: Extracted timestamp: {timestamp_str}")
                return timestamp_str
        
        logger.debug(f"No timestamp found in: {log_line[:150]}")
        return None


# Global instance
_extractor = None

def get_timestamp_extractor() -> SimpleTimestampExtractor:
    """Get or create extractor instance"""
    global _extractor
    if _extractor is None:
        _extractor = SimpleTimestampExtractor()
    return _extractor

def extract_timestamp(log_line: str) -> str:
    """
    Extract timestamp STRING from log line.
    
    Returns:
        Timestamp string AS-IS, no conversion, no parsing
    
    Examples:
        Input: "2025-11-24T07:22:33,801+0000 INFO [scheduler]"
        Output: "2025-11-24T07:22:33,801+0000"
        
        Input: "2025-11-24T05:00:22.607Z INFO [service]"
        Output: "2025-11-24T05:00:22.607Z"
    """
    extractor = get_timestamp_extractor()
    return extractor.extract(log_line)
