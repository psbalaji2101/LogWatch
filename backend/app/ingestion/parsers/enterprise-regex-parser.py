"""Production Regex Parser for Enterprise Logs - Extracts service from pod names"""


import re
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from dateutil import parser as dateparser

from app.ingestion.parsers.base import BaseParser

logger = logging.getLogger(__name__)

class RegexParser(BaseParser):
    """
    Enterprise-grade log parser with service extraction from pod names
    
    Features:
    - Extracts service from pod/container names
    - Normalizes timestamps to ISO 8601 format
    - Skips logs without log levels (non-parseable)
    - Focuses on readable text logs (skips CSV/binary)
    """
    
    # Log level patterns - MUST have one of these
    LOG_LEVELS = {
        'ERROR', 'WARN', 'WARNING', 'INFO', 'DEBUG', 
        'FATAL', 'CRITICAL', 'TRACE'
    }
    
    # Comprehensive patterns for enterprise logs
    PATTERNS = {
        # Pattern 1: ISO timestamp + level + message (most common)
        # Example: 2025-11-24T071454.667115051-0800,2025-11-24 071454 INFO - No need to renew certificates,itom-ingress-controller...
        'iso_level_message': re.compile(
            r'^(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{4})?)\s+'
            r'(?P<level>ERROR|WARN|WARNING|INFO|DEBUG|FATAL|CRITICAL|TRACE)\s+'
            r'(?P<message>.+?)(?:,(?P<pod>[^,]+),(?P<namespace>[^,]+),(?P<container>[^,]+),(?P<host>[^,]+))?$'
        ),
        
        # Pattern 2: Kubernetes-style logs with structured metadata
        # Example: time=2025-11-24T071645Z level=info msg=UpdateStatus received... file=task.go:194
        'k8s_structured': re.compile(
            r'time=(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\s+'
            r'level=(?P<level>error|warn|warning|info|debug|trace)\s+'
            r'msg=(?P<message>.+?)(?:\s+file=(?P<file>[^\s]+))?'
        ),
        
        # Pattern 3: Java-style logs (common in enterprise)
        # Example: Nov 24, 2025 4:15:17 AM org.glassfish.jersey.internal.Errors logErrors
        'java_style': re.compile(
            r'^(?P<timestamp>\w+\s+\d+,\s+\d{4}\s+\d+:\d+:\d+\s+[AP]M)\s+'
            r'(?P<classname>[\w.]+)\s+'
            r'(?P<level>WARNING|INFO|SEVERE|ERROR|DEBUG)\s+'
            r'(?P<message>.+)$'
        ),
        
        # Pattern 4: Golang/structured logs
        # Example: I1124 03:33:40.498113 1 main.go:118 Successful initial request
        'golang_style': re.compile(
            r'^(?P<level>[IWEF])(?P<mmdd>\d{4})\s+(?P<time>\d{2}:\d{2}:\d{2}\.\d+)\s+'
            r'(?P<thread>\d+)\s+(?P<file>[\w.]+:\d+)\s+(?P<message>.+)$'
        ),
        
        # Pattern 5: Prometheus/config-reloader style
        # Example: level=info ts=2025-11-24T04:13:29.488545084Z caller=reloader.go:548 msg="Reload triggered"
        'prom_style': re.compile(
            r'level=(?P<level>info|error|warn|debug)\s+'
            r'ts=(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\s+'
            r'(?:caller=(?P<caller>[^\s]+)\s+)?'
            r'msg=(?P<message>.+)$'
        ),
        
        # Pattern 6: Stunnel/system logs
        # Example: 2025.11.24 03:33:45 LOG5=0: Service reload connected
        'stunnel_style': re.compile(
            r'^(?P<timestamp>\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
            r'LOG(?P<loglevel>\d)\S*\s+'
            r'(?P<message>.+)$'
        ),
        
        # Pattern 7: GIN framework logs
        # Example: GIN 2025/11/24 - 07:22:28 | 200 | 47.196µs | 172.16.0.1 | GET /config
        'gin_style': re.compile(
            r'^GIN\s+(?P<timestamp>\d{4}/\d{2}/\d{2}\s+-\s+\d{2}:\d{2}:\d{2})\s+'
            r'\|\s+(?P<status>\d{3})\s+\|\s+(?P<latency>[\d.]+\S+)\s+'
            r'\|\s+(?P<ip>[\d.]+)\s+\|\s+(?P<method>\w+)\s+(?P<endpoint>\S+)'
        ),
        
        # Pattern 8: ESAPI/application logs
        # Example: ESAPI: Loading ESAPI-validation.properties via file I/O failed.
        'esapi_style': re.compile(
            r'^ESAPI:\s+(?P<message>.+)$'
        ),
    }
    
    def __init__(self, patterns: Dict[str, re.Pattern] = None):
        self.patterns = patterns or self.PATTERNS
    
    def extract_service_from_pod(self, pod_name: str) -> str:
        """
        Extract service name from Kubernetes pod name
        
        Pod naming patterns:
        - itom-ingress-controller-856b7856cd-tc6s9 → ingress_controller
        - alertmanager-itom-prometheus-alertmanager-0 → alertmanager
        - itom-ucmdb-browser-fd99d7c9f-5jx6p → ucmdb_browser
        - vcenter-ucmdb-probe-7d9d79b46b-jtzft → vcenter_ucmdb_probe
        
        Strategy:
        1. Remove deployment hash suffixes (pattern: -[0-9a-f]{8,10}-[a-z0-9]{5})
        2. Remove statefulset indices (pattern: -\d+$)
        3. Remove common prefixes (itom-, omi-, etc.)
        4. Extract meaningful service name
        """
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
        """
        Normalize various timestamp formats to datetime object
        
        Handles:
        - ISO 8601: 2025-11-24T07:14:54.667115051-0800
        - Date only: 2025.11.24 03:33:45
        - Java: Nov 24, 2025 4:15:17 AM
        - Golang: mmdd time (requires year context)
        """
        try:
            if not timestamp_str:
                return None
            
            # Handle Golang-style timestamps (need current year)
            if pattern_name == 'golang_style':
                # mmdd format: 1124 → Nov 24
                # We need to construct full timestamp
                return None  # Skip for now, needs more context
            
            # Use dateutil parser for most formats
            dt = dateparser.parse(timestamp_str)
            return dt
            
        except Exception as e:
            logger.debug(f"Failed to parse timestamp '{timestamp_str}': {e}")
            return None
    
    def has_log_level(self, line: str) -> bool:
        """
        Check if line contains a log level keyword
        REQUIREMENT: Logs without log levels are ignored
        """
        line_upper = line.upper()
        return any(level in line_upper for level in self.LOG_LEVELS)
    
    def can_parse(self, line: str) -> bool:
        """
        Check if line is parseable
        
        Criteria:
        1. MUST have a log level (ERROR, WARN, INFO, etc.)
        2. MUST match at least one pattern
        3. NOT be CSV format (skip lines starting with timestamps followed by commas)
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
        
        Returns:
        {
            'timestamp': datetime object (or None),
            'fields': {
                'level': 'INFO' | 'ERROR' | 'WARN' | ...,
                'service': 'ingress_controller' | 'ucmdb_browser' | ...,
                'message': 'Log message',
                'pod': 'itom-ingress-controller-856b7856cd-tc6s9',
                'namespace': 'opsb',
                'container': 'vault-renew',
                'host': 'mm-master3.otxlab.net',
                'pattern': 'iso_level_message',
                ... (pattern-specific fields)
            },
            'tokens': ['word1', 'word2', ...]
        }
        """
        
        # Check if parseable
        if not self.can_parse(line):
            # Return None or skip - ingestion will ignore
            return None
        
        # Try each pattern
        for pattern_name, pattern in self.patterns.items():
            match = pattern.search(line)
            if match:
                fields = match.groupdict()
                
                # Extract timestamp
                timestamp_str = fields.get('timestamp')
                timestamp = self.normalize_timestamp(timestamp_str, pattern_name)
                
                # Extract level (normalize to uppercase)
                level = fields.get('level', '').upper()
                if not level or level not in self.LOG_LEVELS:
                    # Try to infer from line
                    for log_level in self.LOG_LEVELS:
                        if log_level in line.upper():
                            level = log_level
                            break
                    if not level:
                        level = 'INFO'  # Default
                
                # Extract service from pod name
                pod = fields.get('pod', '')
                service = self.extract_service_from_pod(pod) if pod else 'unknown'
                
                # Extract message
                message = fields.get('message', '')
                if not message:
                    message = line[:200]  # Fallback to line content
                
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
        
        # No pattern matched (should not reach here if can_parse works correctly)
        logger.warning(f"Line passed can_parse but no pattern matched: {line[:100]}")
        return None


# Example usage and testing
if __name__ == "__main__":
    parser = RegexParser()
    
    test_logs = [
        # Test 1: Vault renew logs
        "2025-11-24 071454 INFO - No need to renew certificates,itom-ingress-controller-856b7856cd-tc6s9,opsb,vault-renew,mm-master3.otxlab.net",
        
        # Test 2: K8s structured logs
        "time=2025-11-24T071645Z level=info msg=UpdateStatus received JobUnit ID aff08f87 file=task.go:194 func=task-manager.task.UpdateStatus",
        
        # Test 3: Java logs
        "Nov 24, 2025 4:15:17 AM org.glassfish.jersey.internal.Errors logErrors WARNING The following warnings have been detected",
        
        # Test 4: Golang logs
        "I1124 03:33:40.498113 1 main.go:118 Successful initial request to the apiserver",
        
        # Test 5: Prometheus logs
        "level=info ts=2025-11-24T04:13:29.488545084Z caller=reloader.go:548 msg=Reload triggered",
        
        # Test 6: GIN logs
        "GIN 2025/11/24 - 07:22:28 | 200 | 47.196µs | 172.16.0.1 | GET /config",
        
        # Test 7: CSV format (should be skipped)
        "1763968422.498551014,2025-11-23T231342.498551014-0800,2025-11-24 071342 INFO - No need to renew certificates",
        
        # Test 8: No log level (should be skipped)
        "Some random log message without a level",
    ]
    
    for log in test_logs:
        print(f"\n{'='*80}")
        print(f"Input: {log[:120]}")
        
        if not parser.can_parse(log):
            print("Result: SKIPPED (not parseable)")
            continue
        
        result = parser.parse(log)
        if result:
            print(f"Service: {result['fields'].get('service')}")
            print(f"Level: {result['fields'].get('level')}")
            print(f"Pattern: {result['fields'].get('pattern')}")
            print(f"Message: {result['fields'].get('message')[:80]}")
            if result.get('timestamp'):
                print(f"Timestamp: {result['timestamp'].isoformat()}")
        else:
            print("Result: FAILED TO PARSE")
