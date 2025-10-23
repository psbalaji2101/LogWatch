# #!/usr/bin/env python3
# """Generate sample log files"""

# import argparse
# import random
# from datetime import datetime, timedelta
# from pathlib import Path
# import json

# # Sample log generators for each format
# def generate_sample_logs(output_dir, count=10000):
#     """Generate sample log files in different formats"""
    
#     Path(output_dir).mkdir(parents=True, exist_ok=True)
    
#     # Apache access logs
#     # JSON app logs
#     # CSV events
#     # Custom text logs
    
#     # Implementation details...
#     print(f"Generated {count} sample log lines in {output_dir}")


#!/usr/bin/env python3
"""Generate sample log files"""

import argparse
import random
from datetime import datetime, timedelta
from pathlib import Path
import json
import csv

# Sample log generator
def generate_sample_logs(output_dir, count=10000):
    """Generate sample log files in different formats"""
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    log_file = Path(output_dir) / "sample_logs12.json"
    with open(log_file, "w") as f:
        for _ in range(count):
            log = {
                "timestamp": (datetime.now() - timedelta(minutes=random.randint(0, 1440))).isoformat(),
                "level": random.choice(["INFO", "WARN", "ERROR"]),
                "message": f"Sample log message {random.randint(1,10000)}",
                "source_file": f"app_{random.randint(1,5)}.py",
                "tokens": [f"token{random.randint(1,20)}" for _ in range(3)]
            }
            f.write(json.dumps(log) + "\n")
    
    print(f"Generated {count} sample log lines in {log_file}")

# Command-line interface
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate sample logs")
    parser.add_argument("--output", required=True, help="Output directory for logs")
    parser.add_argument("--count", type=int, default=1000, help="Number of log lines to generate")
    args = parser.parse_args()
    
    generate_sample_logs(args.output, args.count)