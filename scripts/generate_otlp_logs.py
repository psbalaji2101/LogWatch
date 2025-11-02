#!/usr/bin/env python3
"""
Generate realistic OTLP (OpenTelemetry Log Protocol) format logs
3 files with 2000-5000 lines each, timestamps within last 24 hours
"""

import json
import random
import uuid
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
    "/api/users",
    "/api/products",
    "/api/orders",
    "/api/payments",
    "/api/auth/login",
    "/api/auth/logout",
    "/api/auth/refresh",
    "/api/notifications",
    "/api/profiles",
    "/api/settings",
]

# HTTP Status codes
HTTP_STATUS = [200, 201, 204, 400, 401, 403, 404, 500, 502, 503]

# Transaction types
TRANSACTION_TYPES = ["credit_card", "debit_card", "bank_transfer", "wallet", "cryptocurrency"]

# User IDs
USER_IDS = [f"user_{i:06d}" for i in range(1, 101)]


def generate_otlp_log_entry(timestamp):
    """Generate a single OTLP format log entry"""
    
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
    
    # Common attributes
    attributes = {
        "service.name": random.choice(SERVICES),
        "service.version": f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 20)}",
        "service.instance.id": random.choice(HOSTS),
        "deployment.environment": random.choice(ENVIRONMENTS),
        "service.namespace": random.choice(REGIONS),
        "host.name": random.choice(HOSTS),
        "host.arch": random.choice(["x86_64", "arm64"]),
        "os.type": random.choice(["linux", "windows", "macos"]),
        "process.pid": random.randint(1000, 99999),
        "process.runtime.name": random.choice(["CPython", "PyPy", "Java"]),
    }
    
    # Add severity-specific attributes
    if severity == "ERROR" or severity == "FATAL":
        attributes["exception.type"] = random.choice([
            "ConnectionError", "TimeoutError", "ValueError", "RuntimeError",
            "DatabaseError", "AuthenticationError", "PaymentError"
        ])
        attributes["exception.message"] = message
        attributes["error.code"] = random.randint(500, 599)
    
    # Add HTTP attributes for API logs (60% of logs)
    if random.random() < 0.6:
        attributes["http.method"] = random.choice(HTTP_METHODS)
        attributes["http.url"] = random.choice(API_ENDPOINTS)
        attributes["http.status_code"] = random.choice(HTTP_STATUS)
        attributes["http.response_content_length"] = random.randint(100, 50000)
        attributes["http.request_content_length"] = random.randint(10, 5000)
        duration_ms = random.randint(10, 5000)
        attributes["http.server_timing"] = duration_ms
    
    # Add user tracking (50% of logs)
    if random.random() < 0.5:
        attributes["user.id"] = random.choice(USER_IDS)
        attributes["user.email"] = f"{attributes['user.id']}@example.com"
    
    # Add transaction info for payment service logs
    if "payment" in attributes.get("service.name", "").lower():
        attributes["transaction.id"] = str(uuid.uuid4())
        attributes["transaction.type"] = random.choice(TRANSACTION_TYPES)
        attributes["transaction.amount"] = round(random.uniform(10.0, 1000.0), 2)
        attributes["transaction.currency"] = random.choice(["USD", "EUR", "GBP", "JPY"])
        attributes["transaction.status"] = random.choice(["completed", "pending", "failed", "cancelled"])
    
    # Add database info
    if random.random() < 0.3:
        attributes["db.system"] = random.choice(["postgresql", "mysql", "mongodb", "redis"])
        attributes["db.name"] = random.choice(["users_db", "orders_db", "payments_db", "cache_db"])
        attributes["db.operation"] = random.choice(["SELECT", "INSERT", "UPDATE", "DELETE"])
        attributes["db.rows_affected"] = random.randint(1, 1000)
    
    # Add trace info
    attributes["trace.id"] = str(uuid.uuid4())
    attributes["span.id"] = str(uuid.uuid4())[:16]
    attributes["span.status"] = "Ok" if severity not in ["ERROR", "FATAL"] else "Error"
    
    # Create OTLP log entry
    log_entry = {
        "timeUnixNano": str(int(timestamp.timestamp() * 1e9)),
        "observedTimeUnixNano": str(int(datetime.now().timestamp() * 1e9)),
        "severityNumber": ["DEBUG", "INFO", "WARN", "ERROR", "FATAL"].index(severity) + 1,
        "severityText": severity,
        "name": message[:80],  # Truncate for name field
        "body": message,
        "attributes": attributes,
        "droppedAttributesCount": 0,
        "flags": 0,
    }
    
    return log_entry


def generate_otlp_file(filename, num_lines):
    """Generate OTLP format log file"""
    print(f"📝 Generating {filename} ({num_lines} lines)...")
    
    # Generate logs from last 24 hours
    now = datetime.now()
    start_time = now - timedelta(hours=24)
    
    logs = []
    
    with open(filename, 'w') as f:
        for i in range(num_lines):
            # Random timestamp within last 24 hours
            random_seconds = random.randint(0, 86400)
            timestamp = start_time + timedelta(seconds=random_seconds)
            
            # Generate log entry
            log_entry = generate_otlp_log_entry(timestamp)
            logs.append(log_entry)
            
            # Write as NDJSON (newline delimited JSON)
            f.write(json.dumps(log_entry) + '\n')
            
            if (i + 1) % 500 == 0:
                print(f"  Generated {i + 1}/{num_lines} lines")
    
    file_size_kb = os.path.getsize(filename) / 1024
    print(f"✅ {filename}: {num_lines} lines ({file_size_kb:.2f} KB)\n")


def main():
    print("=" * 70)
    print("📦 OTLP Log Generator - Realistic OpenTelemetry Format")
    print("=" * 70)
    print()
    
    os.makedirs("otlp_logs", exist_ok=True)
    
    # Generate 3 files with different line counts
    files = [
        ("otlp_logs/application_logs.ndjson", 2500),
        ("otlp_logs/payment_service_logs.ndjson", 3500),
        ("otlp_logs/infrastructure_logs.ndjson", 4000),
    ]
    
    total_lines = 0
    
    for filename, num_lines in files:
        generate_otlp_file(filename, num_lines)
        total_lines += num_lines
    
    print("=" * 70)
    print(f"🎉 All files generated successfully!")
    print(f"   Total lines: {total_lines:,}")
    print(f"   Output directory: otlp_logs/")
    print("=" * 70)
    print()
    print("📋 File Summary:")
    for filename, num_lines in files:
        file_size_kb = os.path.getsize(filename) / 1024
        print(f"  - {filename}: {num_lines:,} lines ({file_size_kb:.2f} KB)")
    print()
    print("📖 Sample log entry:")
    print(json.dumps(generate_otlp_log_entry(datetime.now()), indent=2))


if __name__ == "__main__":
    main()
