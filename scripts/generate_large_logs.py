#!/usr/bin/env python3
"""
Generate large log files in different formats
Each file will be approximately 300MB
"""

import random
from datetime import datetime, timedelta
import os

# Log messages
MESSAGES = [
    "Application started successfully",
    "Database connection established",
    "User authentication successful",
    "API request processed",
    "Cache invalidated",
    "Background job completed",
    "Configuration reloaded",
    "Connection timeout",
    "Invalid request parameters",
    "Resource not found",
    "Permission denied",
    "Database query failed",
    "Memory allocation error",
    "Disk space low",
    "Network unreachable",
    "Service unavailable",
    "Critical system failure",
    "Data corruption detected",
    "Security breach attempt",
    "Payment processing completed",
    "File uploaded successfully",
    "Email sent to user",
    "Session expired",
    "Rate limit exceeded",
    "Third-party API call failed"
]

MESSAGE_PARTS_A = [
    "Database operation",
    "User action",
    "System event",
    "API call",
    "File operation",
    "Network request",
    "Cache operation",
    "Authentication attempt",
    "Background task",
    "Payment processing"
]

MESSAGE_PARTS_B = [
    "completed successfully",
    "failed with timeout",
    "rejected due to invalid input",
    "queued for processing",
    "retrying after failure",
    "aborted by user",
    "finished with warnings",
    "encountered an error",
    "processed in 250ms",
    "waiting for response"
]

SEVERITIES = ["INFO", "DEBUG", "WARN", "ERROR", "FATAL"]
SEVERITY_WEIGHTS = [50, 30, 15, 4, 1]  # INFO is most common

def get_random_severity():
    return random.choices(SEVERITIES, weights=SEVERITY_WEIGHTS)[0]

def get_random_message():
    return random.choice(MESSAGES)

def get_random_message_parts():
    return random.choice(MESSAGE_PARTS_A), random.choice(MESSAGE_PARTS_B)


def generate_format1(output_file, target_size_mb=300):
    """
    Format 1: <timestamp(only date)> <severity> <message>
    Example: 2025-10-29 INFO Application started successfully
    """
    print(f"📝 Generating {output_file} (Format 1: date only)...")
    
    target_bytes = target_size_mb * 1024 * 1024
    current_bytes = 0
    line_count = 0
    
    # Generate logs ending NOW, spanning last 24 hours
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=24)
    
    with open(output_file, 'w') as f:
        while current_bytes < target_bytes:
            # Generate timestamp (date only)
            date = start_date + timedelta(seconds=random.randint(0, 30 * 24 * 3600))
            timestamp = date.strftime("%Y-%m-%d")
            
            severity = get_random_severity()
            message = get_random_message()
            
            log_line = f"{timestamp} {severity} {message}\n"
            f.write(log_line)
            
            current_bytes += len(log_line.encode('utf-8'))
            line_count += 1
            
            # Progress indicator
            if line_count % 100000 == 0:
                mb_written = current_bytes / (1024 * 1024)
                print(f"  Progress: {mb_written:.1f}MB / {target_size_mb}MB ({line_count:,} lines)")
    
    final_mb = current_bytes / (1024 * 1024)
    print(f"  ✅ Generated {output_file}: {final_mb:.2f}MB ({line_count:,} lines)\n")


def generate_format2(output_file, target_size_mb=300):
    """
    Format 2: <timestamp(date.time)> <severity> <message>
    Example: 2025-10-29 12:34:56 INFO Database connection established
    """
    print(f"📝 Generating {output_file} (Format 2: date + time)...")
    
    target_bytes = target_size_mb * 1024 * 1024
    current_bytes = 0
    line_count = 0
    
    # Generate logs ending NOW, spanning last 24 hours
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=24)
    
    with open(output_file, 'w') as f:
        while current_bytes < target_bytes:
            # Generate timestamp (date + time)
            date = start_date + timedelta(seconds=random.randint(0, 30 * 24 * 3600))
            timestamp = date.strftime("%Y-%m-%dT%H:%M:%S")
            
            severity = get_random_severity()
            message = get_random_message()
            
            log_line = f"{timestamp} {severity} {message}\n"
            f.write(log_line)
            
            current_bytes += len(log_line.encode('utf-8'))
            line_count += 1
            
            # Progress indicator
            if line_count % 100000 == 0:
                mb_written = current_bytes / (1024 * 1024)
                print(f"  Progress: {mb_written:.1f}MB / {target_size_mb}MB ({line_count:,} lines)")
    
    final_mb = current_bytes / (1024 * 1024)
    print(f"  ✅ Generated {output_file}: {final_mb:.2f}MB ({line_count:,} lines)\n")


def generate_format3(output_file, target_size_mb=300):
    """
    Format 3: <timestamp(date.time)> <severity> <message partA>: <message partB>
    Example: 2025-10-29 12:34:56 ERROR Database operation: failed with timeout
    """
    print(f"📝 Generating {output_file} (Format 3: date + time + structured message)...")
    
    target_bytes = target_size_mb * 1024 * 1024
    current_bytes = 0
    line_count = 0
    
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=24)
    
    with open(output_file, 'w') as f:
        while current_bytes < target_bytes:
            # Generate timestamp (date + time)
            date = start_date + timedelta(seconds=random.randint(0, 30 * 24 * 3600))
            timestamp = date.strftime("%Y-%m-%dT%H:%M:%S")
            
            severity = get_random_severity()
            part_a, part_b = get_random_message_parts()
            
            log_line = f"{timestamp} {severity} {part_a}: {part_b}\n"
            f.write(log_line)
            
            current_bytes += len(log_line.encode('utf-8'))
            line_count += 1
            
            # Progress indicator
            if line_count % 100000 == 0:
                mb_written = current_bytes / (1024 * 1024)
                print(f"  Progress: {mb_written:.1f}MB / {target_size_mb}MB ({line_count:,} lines)")
    
    final_mb = current_bytes / (1024 * 1024)
    print(f"  ✅ Generated {output_file}: {final_mb:.2f}MB ({line_count:,} lines)\n")


def main():
    print("=" * 60)
    print("📦 Large Log File Generator")
    print("=" * 60)
    print()
    
    # Create output directory
    output_dir = "logs_in"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate the three files
    generate_format1(f"{output_dir}/format1_date_only.log", target_size_mb=300)
    generate_format2(f"{output_dir}/format2_datetime.log", target_size_mb=300)
    generate_format3(f"{output_dir}/format3_structured.log", target_size_mb=300)
    
    print("=" * 60)
    print("🎉 All log files generated successfully!")
    print("=" * 60)
    print()
    print("Generated files:")
    
    for filename in ["format1_date_only.log", "format2_datetime.log", "format3_structured.log"]:
        filepath = f"{output_dir}/{filename}"
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        print(f"  - {filepath} ({size_mb:.2f}MB)")
    
    print()
    print("To ingest these logs:")
    print(f"  docker compose exec backend python -m app.cli.ingest --directory /{output_dir}")
    print()


if __name__ == "__main__":
    main()
