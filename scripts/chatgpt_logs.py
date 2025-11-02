from datetime import datetime, timedelta
import random
import uuid

# Configuration for 2 days (from 2025-11-01 00:00 UTC to now UTC)
start_time = datetime(2025, 11, 1, 0, 0, 0)
end_time = datetime.utcnow()
interval = timedelta(minutes=2)

# Possible values for realistic log variety
services = ["api-gateway", "auth-service", "payment-service", "user-service", "notification-service", "inventory-service"]
methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
endpoints = [
    "/api/users", "/api/login", "/api/logout", "/api/products", "/api/payments", "/api/orders",
    "/api/notifications", "/api/profile", "/api/cart", "/api/analytics"
]
status_codes = [200, 201, 204, 400, 401, 403, 404, 409, 500, 502]
messages = [
    "New user registration completed",
    "Payment processed successfully",
    "User login failed",
    "Session token refreshed",
    "Inventory updated",
    "Email notification sent",
    "Order placed successfully",
    "Order cancelled by user",
    "Invalid API key",
    "Rate limit exceeded"
]

# Generate logs
logs = []
current_time = start_time
while current_time < end_time:
    timestamp = current_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
    level = "INFO" if random.random() > 0.2 else "ERROR"
    service = random.choice(services)
    message = random.choice(messages)
    method = random.choice(methods)
    endpoint = random.choice(endpoints)
    status = random.choice(status_codes)
    duration = random.randint(20, 5000)
    trace_id = uuid.uuid4().hex[:8]
    span_id = uuid.uuid4().hex[:8]

    log_line = f"{timestamp} {level}  [{service}] {message} | {method} {endpoint} {status} {duration}ms | trace={trace_id} span={span_id}"
    logs.append(log_line)

    current_time += interval

# Write to .log file
log_file_path = "logs_in/system_logs_2025-11-01_to_now.log"
with open(log_file_path, "w") as f:
    f.write("\n".join(logs))

log_file_path