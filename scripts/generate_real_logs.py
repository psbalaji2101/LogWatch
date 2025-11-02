#!/usr/bin/env python3
"""
Generate realistic plain text log files
3 files with 2000-5000 lines each, timestamps within last 24 hours
"""

import random
import uuid
import argparse
from datetime import datetime, timedelta
import os

# Services
SERVICES = ["auth-service", "api-gateway", "payment-service", "user-service", "notification-service"]
ENVIRONMENTS = ["production", "staging", "development"]
REGIONS = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
HOSTS = ["host-001", "host-002", "host-003", "host-004", "host-005"]

# Log messages by severity
MESSAGES = {
    "DEBUG": [
        "Database query cache hit",
        "Request routing to backend",
        "Parsing authentication token",
        "Validating request schema",
        "Loading configuration from vault",
        "Thread pool size: {}",
        "Cache refresh completed",
        "Health check passed",
    ],
    "INFO": [
        "User login successful",
        "Payment processed successfully",
        "Email notification sent",
        "Database migration completed",
        "Service started successfully",
        "Configuration reloaded",
        "Request processed in {}ms",
        "New user registration completed",
        "API endpoint /api/users called",
        "Background job executed",
    ],
    "WARN": [
        "Slow query detected: {}ms",
        "High memory usage: {}%",
        "Rate limit approaching for user: {}",
        "Cache miss for key: {}",
        "Deprecated API endpoint used",
        "Database connection pool low",
        "Response time exceeded threshold",
        "Failed authentication attempt for user",
    ],
    "ERROR": [
        "Database connection failed",
        "Payment gateway timeout",
        "Invalid user credentials",
        "File not found: {}",
        "Permission denied for resource: {}",
        "Service unavailable: {}",
        "Connection refused to backend",
        "Request validation failed",
        "Email delivery failed",
        "Configuration error: {}",
    ],
    "FATAL": [
        "Critical system failure",
        "Data corruption detected",
        "Unrecoverable error in payment processing",
        "Database corruption detected",
        "Security breach detected",
        "System out of memory",
    ]
}

# HTTP Methods
HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH"]

# API Endpoints
API_ENDPOINTS = [
    "/api/users", "/api/products", "/api/orders", "/api/payments",
    "/api/auth/login", "/api/auth/logout", "/api/auth/refresh",
    "/api/notifications", "/api/profiles", "/api/settings",
]

# HTTP Status codes
HTTP_STATUS = [200, 201, 204, 400, 401, 403, 404, 500, 502, 503]

# Transaction types
TRANSACTION_TYPES = ["credit_card", "debit_card", "bank_transfer", "wallet", "cryptocurrency"]

# User IDs
USER_IDS = [f"user_{i:06d}" for i in range(1, 101)]


def generate_plain_log_line(timestamp, log_format="standard"):
    """Generate a single plain text log line"""
    
    severity = random.choices(
        ["DEBUG", "INFO", "WARN", "ERROR", "FATAL"],
        weights=[30, 40, 15, 10, 5]
    )[0]
    
    message_template = random.choice(MESSAGES[severity])
    
    # Fill in template placeholders
    if "{}" in message_template:
        if severity in ["ERROR", "WARN"]:
            if "ms" in message_template or "time" in message_template:
                message = message_template.format(random.randint(100, 5000))
            elif "%" in message_template:
                message = message_template.format(random.randint(50, 95))
            else:
                message = message_template.format(random.choice(USER_IDS))
        else:
            message = message_template.format(random.randint(10, 1000))
    else:
        message = message_template
    
    # Get service and context
    service = random.choice(SERVICES)
    environment = random.choice(ENVIRONMENTS)
    host = random.choice(HOSTS)
    
    # Format timestamp
    ts = (datetime.now() - timedelta(minutes=random.randint(0, 1440))).isoformat()
    
    # Add HTTP context (60% of logs)
    http_context = ""
    if random.random() < 0.6:
        method = random.choice(HTTP_METHODS)
        endpoint = random.choice(API_ENDPOINTS)
        status = random.choice(HTTP_STATUS)
        duration_ms = random.randint(10, 5000)
        http_context = f" | {method} {endpoint} {status} {duration_ms}ms"
    
    # Add user context (50% of logs)
    user_context = ""
    if random.random() < 0.5:
        user_id = random.choice(USER_IDS)
        user_context = f" | user={user_id}"
    
    # Add transaction context for payment service
    transaction_context = ""
    if "payment" in service.lower() and random.random() < 0.4:
        transaction_id = str(uuid.uuid4())[:8]
        amount = round(random.uniform(10.0, 1000.0), 2)
        currency = random.choice(["USD", "EUR", "GBP", "JPY"])
        transaction_context = f" | txn={transaction_id} amount={amount}{currency}"
    
    # Add trace context
    trace_id = str(uuid.uuid4())[:8]
    span_id = str(uuid.uuid4())[:8]
    trace_context = f" | trace={trace_id} span={span_id}"
    
    # Build log line based on format
    if log_format == "standard":
        # Format: 2025-11-02 16:05:30 INFO [service] message
        log_line = f"{ts} {severity:5} [{service}] {message}{http_context}{user_context}{transaction_context}{trace_context}"
    
    elif log_format == "json-like":
        # Format: timestamp="..." level="..." service="..." message="..." ...
        log_line = f'timestamp="{ts}" level="{severity}" service="{service}" environment="{environment}" host="{host}" message="{message}"'
        if http_context:
            log_line += http_context.replace(" | ", " ")
        if user_context:
            log_line += user_context.replace(" | ", " ")
        if transaction_context:
            log_line += transaction_context.replace(" | ", " ")
        log_line += trace_context.replace(" | ", " ")
    
    elif log_format == "apache":
        # Format: host - - [timestamp] "METHOD /path HTTP/1.1" status size
        if http_context:
            parts = http_context.strip(" | ").split()
            method, endpoint, status, _ = parts[0], parts[1], parts[2], parts[3]
            size = random.randint(100, 50000)
            log_line = f'{host} - - [{ts}] "{method} {endpoint} HTTP/1.1" {status} {size}'
        else:
            log_line = f"{ts} {severity:5} [{service}] {message}"
    
    else:  # simple
        # Format: timestamp LEVEL message
        log_line = f"{ts} {severity} {message}"
    
    return log_line


def generate_log_file(filename, num_lines, log_format="standard"):
    """Generate plain text log file"""
    print(f"📝 Generating {filename} ({num_lines} lines, format: {log_format})...")
    
    # Generate logs from last 24 hours
    now = datetime.now()
    start_time = now - timedelta(hours=24)
    
    with open(filename, 'w') as f:
        for i in range(num_lines):
            # Random timestamp within last 24 hours
            random_seconds = random.randint(0, 86400)
            timestamp = start_time + timedelta(seconds=random_seconds)
            
            # Generate log line
            log_line = generate_plain_log_line(timestamp, log_format)
            f.write(log_line + '\n')
            
            if (i + 1) % 500 == 0:
                print(f"  Generated {i + 1}/{num_lines} lines")
    
    file_size_kb = os.path.getsize(filename) / 1024
    print(f"✅ {filename}: {num_lines} lines ({file_size_kb:.2f} KB)\n")


def main():
    parser = argparse.ArgumentParser(
        description='Generate realistic plain text log files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate in default directory (logs_in)
  python generate_realistic_logs.py
  
  # Generate in custom directory
  python generate_realistic_logs.py --output-dir /path/to/logs
  
  # Generate with different format
  python generate_realistic_logs.py --format json-like
  
  # Generate custom line counts
  python generate_realistic_logs.py --lines 2000 3000 4000
        """
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        default='logs_in',
        help='Output directory for log files (default: logs_in)'
    )
    
    parser.add_argument(
        '--format', '-f',
        choices=['standard', 'json-like', 'apache', 'simple'],
        default='standard',
        help='Log format (default: standard)'
    )
    
    parser.add_argument(
        '--lines', '-l',
        type=int,
        nargs='+',
        default=[2500, 3500, 4000],
        help='Number of lines for each file (default: 2500 3500 4000)'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("📦 Realistic Plain Text Log Generator")
    print("=" * 70)
    print(f"Output directory: {args.output_dir}")
    print(f"Log format: {args.format}")
    print(f"Line counts: {args.lines}")
    print()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Generate files
    file_configs = [
        (f"{args.output_dir}/application_logs.log", args.lines[0] if len(args.lines) > 0 else 2500),
        (f"{args.output_dir}/payment_service_logs.log", args.lines[1] if len(args.lines) > 1 else 3500),
        (f"{args.output_dir}/infrastructure_logs.log", args.lines[2] if len(args.lines) > 2 else 4000),
    ]
    
    total_lines = 0
    
    for filename, num_lines in file_configs:
        generate_log_file(filename, num_lines, args.format)
        total_lines += num_lines
    
    print("=" * 70)
    print(f"🎉 All files generated successfully!")
    print(f"   Total lines: {total_lines:,}")
    print(f"   Output directory: {args.output_dir}/")
    print("=" * 70)
    print()
    print("📋 File Summary:")
    for filename, num_lines in file_configs:
        file_size_kb = os.path.getsize(filename) / 1024
        print(f"  - {filename}: {num_lines:,} lines ({file_size_kb:.2f} KB)")
    print()
    print("📖 Sample log lines:")
    for _ in range(3):
        print(f"  {generate_plain_log_line(datetime.now(), args.format)}")


if __name__ == "__main__":
    main()
