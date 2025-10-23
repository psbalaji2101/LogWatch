"""Test parsers"""

import pytest
from datetime import datetime

from app.ingestion.parsers import (
    JSONParser, CSVParser, RegexParser, HeuristicParser
)


def test_json_parser():
    """Test JSON parser"""
    parser = JSONParser()
    
    line = '{"timestamp": "2025-10-20T14:30:00Z", "level": "ERROR", "message": "Test"}'
    
    assert parser.can_parse(line)
    result = parser.parse(line)
    
    assert result['fields']['level'] == 'ERROR'
    assert result['fields']['message'] == 'Test'
    assert len(result['tokens']) > 0


def test_csv_parser():
    """Test CSV parser"""
    parser = CSVParser(headers=['timestamp', 'event', 'user', 'status'])
    
    line = '2025-10-20T14:30:00Z,user_login,user123,success'
    
    result = parser.parse(line)
    
    assert result['fields']['event'] == 'user_login'
    assert result['fields']['user'] == 'user123'


def test_regex_parser():
    """Test regex parser"""
    parser = RegexParser()
    
    line = '192.168.1.1 - - [20/Oct/2025:14:30:00 +0000] "GET /api HTTP/1.1" 200 1234'
    
    assert parser.can_parse(line)
    result = parser.parse(line)
    
    assert result['fields']['ip'] == '192.168.1.1'
    assert result['fields']['method'] == 'GET'
    assert result['fields']['status'] == '200'


def test_heuristic_parser():
    """Test heuristic parser"""
    parser = HeuristicParser()
    
    line = '[2025-10-20 14:30:00] ERROR: Connection failed'
    
    assert parser.can_parse(line)
    result = parser.parse(line)
    
    assert result['fields']['level'] == 'ERROR'
    assert isinstance(result['timestamp'], datetime)


def test_parser_fallback(sample_log_lines):
    """Test parser fallback chain"""
    parsers = [JSONParser(), CSVParser(), RegexParser(), HeuristicParser()]
    
    for line in sample_log_lines:
        parsed = False
        for parser in parsers:
            if parser.can_parse(line):
                result = parser.parse(line)
                assert 'timestamp' in result
                assert 'fields' in result
                assert 'tokens' in result
                parsed = True
                break
        
        assert parsed, f"No parser handled: {line}"
