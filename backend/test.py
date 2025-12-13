"""
Test script to validate timestamp extraction for all formats
"""

import sys
import re
from datetime import datetime

# Import your extractor
from app.ingestion.timestamp_extractor import extract_timestamp


# Test cases with different timestamp formats
TEST_CASES = [
    # ISO 8601 formats
    {
        "name": "ISO 8601 with Z (UTC)",
        "log_line": "2025-11-24T05:00:22.607Z INFO service started",
        "expected": "2025-11-24T05:00:22.607Z"
    },
    {
        "name": "ISO 8601 with comma and Z",
        "log_line": "2025-11-24T05:00:22,607Z INFO service started",
        "expected": "2025-11-24T05:00:22,607Z"
    },
    {
        "name": "ISO 8601 with timezone offset (period)",
        "log_line": "2025-11-24T07:22:33.801+0000 INFO [scheduler-2] task completed",
        "expected": "2025-11-24T07:22:33.801+0000"
    },
    {
        "name": "ISO 8601 with timezone offset (comma)",
        "log_line": "2025-11-24T07:22:33,801+0000 INFO [scheduler] task completed",
        "expected": "2025-11-24T07:22:33,801+0000"
    },
    {
        "name": "ISO 8601 with +05:30 offset",
        "log_line": "2025-11-24T12:52:33.801+05:30 INFO service running",
        "expected": "2025-11-24T12:52:33.801+05:30"
    },
    {
        "name": "ISO 8601 with space separator",
        "log_line": "2025-11-24 07:22:33.801 INFO service log",
        "expected": "2025-11-24 07:22:33.801"
    },
    {
        "name": "ISO 8601 with space, no milliseconds",
        "log_line": "2025-11-24 07:22:33 INFO service log",
        "expected": "2025-11-24 07:22:33"
    },
    
    # Dot format (sometimes used in logs)
    {
        "name": "Dot format with milliseconds",
        "log_line": "2025.11.24 03:33:45.123 INFO main process",
        "expected": "2025.11.24 03:33:45.123"
    },
    {
        "name": "Dot format without milliseconds",
        "log_line": "2025.11.24 03:33:45 INFO main process",
        "expected": "2025.11.24 03:33:45"
    },
    
    # Slash format
    {
        "name": "Slash format with hyphen",
        "log_line": "2025/11/24 - 07:22:28 INFO request processed",
        "expected": "2025/11/24 - 07:22:28"
    },
    {
        "name": "Slash format without hyphen",
        "log_line": "2025/11/24 07:22:28 INFO request processed",
        "expected": "2025/11/24 07:22:28"
    },
    
    # Apache/Nginx format
    {
        "name": "Apache/Nginx format",
        "log_line": "192.168.1.1 - - [24/Nov/2025:19:55:25 +0530] GET /api/users HTTP/1.1",
        "expected": "24/Nov/2025:19:55:25 +0530"
    },
    
    # Go/Kubernetes format
    {
        "name": "Go/Kubernetes format",
        "log_line": "I1124 19:55:25.125155 main.go:42] Starting server",
        "expected": "I1124 19:55:25.125155"
    },
    
    # Syslog format
    {
        "name": "Syslog format",
        "log_line": "Nov 24 19:55:25 hostname service[1234]: message",
        "expected": "Nov 24 19:55:25"
    },
    
    # Java format
    {
        "name": "Java format with AM/PM",
        "log_line": "Nov 24, 2025 4:15:17 PM [main] Starting application",
        "expected": "Nov 24, 2025 4:15:17 PM"
    },
    {
        "name": "Java format alternative",
        "log_line": "November 24, 2025 07:22:33 PM ERROR Database connection failed",
        "expected": None  # May not match exact pattern
    },
    
    # RFC 2822 format
    {
        "name": "RFC 2822 format",
        "log_line": "Thu, 24 Nov 2025 19:55:25 +0530 - Email sent successfully",
        "expected": "Thu, 24 Nov 2025 19:55:25"
    },
    
    # Unix epoch
    {
        "name": "Unix epoch (seconds)",
        "log_line": "1732468525 INFO background job executed",
        "expected": "1732468525"
    },
    {
        "name": "Unix epoch (milliseconds)",
        "log_line": "1732468525000 INFO background job executed",
        "expected": "1732468525000"
    },
    
    # Complex real-world examples
    {
        "name": "Java log with exception",
        "log_line": "2025-11-24T07:22:33,801+0000 ERROR [https-jsse-nio-8443-exec-6] com.hp.ccue.identity.authn.MultiTenantAuthenticationProvider [131]",
        "expected": "2025-11-24T07:22:33,801+0000"
    },
    {
        "name": "Structured JSON-like log",
        "log_line": '1763968642.585671740,"2025-11-23T23:17:22.585671774-08:00","2025-11-24 07:17:22 [INFO] - Check server certificates"',
        "expected": "1763968642.585671740"  # First timestamp match
    },
    {
        "name": "Log with multiple timestamps",
        "log_line": "2025-11-24T07:20:00,065+0000 INFO [scheduler-2] completed at 2025-11-24 07:20:01",
        "expected": "2025-11-24T07:20:00,065+0000"  # Should match first
    },
]


def run_tests():
    """Run all test cases"""
    
    print("=" * 80)
    print("TIMESTAMP EXTRACTION TEST SUITE")
    print("=" * 80)
    print()
    
    passed = 0
    failed = 0
    warnings = 0
    
    for i, test in enumerate(TEST_CASES, 1):
        print(f"Test {i}: {test['name']}")
        print(f"  Log line: {test['log_line'][:70]}...")
        
        result = extract_timestamp(test['log_line'])
        expected = test['expected']
        
        if expected is None:
            print(f"  Expected: (any match)")
            if result:
                print(f"  Got:      ✅ {result}")
                passed += 1
            else:
                print(f"  Got:      ❌ None")
                failed += 1
        else:
            if result == expected:
                print(f"  Expected: ✅ {expected}")
                print(f"  Got:      ✅ {result}")
                passed += 1
            else:
                print(f"  Expected: ❌ {expected}")
                print(f"  Got:      ❌ {result}")
                failed += 1
        
        print()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    total = len(TEST_CASES)
    print(f"Total tests:  {total}")
    print(f"Passed:       {passed} ✅")
    print(f"Failed:       {failed} ❌")
    print(f"Success rate: {(passed/total)*100:.1f}%")
    print()
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"⚠️  {failed} test(s) failed")
        return 1


def test_specific_format(log_line: str):
    """Test a specific log line format"""
    
    print("=" * 80)
    print("TESTING SPECIFIC LOG LINE")
    print("=" * 80)
    print(f"Input: {log_line}")
    print()
    
    result = extract_timestamp(log_line)
    
    if result:
        print(f"✅ Extracted timestamp: {result}")
        return 0
    else:
        print(f"❌ No timestamp found")
        return 1


def show_all_patterns():
    """Show all regex patterns being used"""
    
    print("=" * 80)
    print("TIMESTAMP EXTRACTION PATTERNS")
    print("=" * 80)
    print()
    
    patterns = [
        ("ISO 8601 with comma+Z", r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2},\d+Z)'),
        ("ISO 8601 with period+Z", r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)'),
        ("ISO 8601 with Z", r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)'),
        ("ISO 8601 with offset (period)", r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+[+-]\d{2}:?\d{2})'),
        ("ISO 8601 with offset (comma)", r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2},\d+[+-]\d{2}:?\d{2})'),
        ("ISO 8601 with space (period)", r'(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\.\d+)'),
        ("ISO 8601 with space", r'(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})'),
        ("Dot format", r'(\d{4}\.\d{2}\.\d{2}\s\d{2}:\d{2}:\d{2}(?:\.\d+)?)'),
        ("Slash format", r'(\d{4}/\d{2}/\d{2}\s-?\s?\d{2}:\d{2}:\d{2}(?:\.\d+)?)'),
        ("Apache/Nginx", r'(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}\s[+-]\d{4})'),
        ("Go/Kubernetes", r'([A-Z]\d{4}\s\d{2}:\d{2}:\d{2}\.\d+)'),
        ("Syslog", r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})'),
        ("Java format", r'(\w{3}\s+\d{1,2},?\s+\d{4}\s+\d{1,2}:\d{2}:\d{2}\s+(?:AM|PM))'),
        ("RFC 2822", r'(\w{3},?\s+\d{1,2}\s+\w{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2})'),
        ("Unix epoch", r'\b(\d{10}|\d{13})\b'),
    ]
    
    for i, (name, pattern) in enumerate(patterns, 1):
        print(f"{i}. {name}")
        print(f"   Pattern: {pattern}")
        print()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Test timestamp extraction')
    parser.add_argument('--test', type=str, help='Test specific log line')
    parser.add_argument('--patterns', action='store_true', help='Show all patterns')
    
    args = parser.parse_args()
    
    if args.patterns:
        show_all_patterns()
    elif args.test:
        sys.exit(test_specific_format(args.test))
    else:
        sys.exit(run_tests())
