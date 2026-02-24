"""OTLP (OpenTelemetry Log Protocol) parser"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from app.ingestion.parsers.base import BaseParser

logger = logging.getLogger(__name__)


class OTLPParser(BaseParser):
    """Parse OTLP format logs (JSON)"""
    
    def can_parse(self, line: str) -> bool:
        """Check if line is valid OTLP JSON"""
        if not line.strip():
            return False
        
        try:
            data = json.loads(line)
            # Must have these OTLP fields
            return all(key in data for key in ['timeUnixNano', 'severityText', 'body'])
        except (json.JSONDecodeError, TypeError):
            return False
    
    def parse(self, line: str) -> Dict[str, Any]:
        """Parse OTLP JSON log entry"""
        
        try:
            data = json.loads(line)
            
            # Extract timestamp (convert nanoseconds to datetime)
            time_nano = int(data.get('timeUnixNano', 0))
            timestamp = datetime.fromtimestamp(time_nano / 1e9)
            
            # Extract severity
            severity = data.get('severityText', 'INFO')
            
            # Extract message
            body = data.get('body', '')
            name = data.get('name', '')
            message = name if name else body
            
            # Extract all attributes
            attributes = data.get('attributes', {})
            
            # Build fields dictionary
            fields = {
                'level': severity,
                'message': message,
                'pattern': 'otlp',
            }
            
            # Add important attributes as top-level fields
            important_attrs = [
                'service.name',
                'service.version',
                'deployment.environment',
                'http.method',
                'http.url',
                'http.status_code',
                'user.id',
                'user.email',
                'transaction.id',
                'transaction.type',
                'transaction.amount',
                'transaction.currency',
                'db.system',
                'db.operation',
                'exception.type',
                'trace.id',
                'span.id',
            ]
            
            for attr in important_attrs:
                if attr in attributes:
                    # Convert dots to underscores for field names
                    field_name = attr.replace('.', '_')
                    fields[field_name] = attributes[attr]
            
            # Store all attributes for searchability
            fields['otlp_attributes'] = attributes
            
            # Tokenize body for search
            tokens = self.tokenize(body)
            
            return {
                'timestamp': timestamp,
                'fields': fields,
                'tokens': tokens
            }
            
        except Exception as e:
            logger.error(f"OTLP parsing failed: {e}")
            return {
                'timestamp': datetime.utcnow(),
                'fields': {'level': 'ERROR', 'message': line},
                'tokens': self.tokenize(line)
            }
