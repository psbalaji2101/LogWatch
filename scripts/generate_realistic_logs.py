#!/usr/bin/env python3
"""
Generate realistic log files simulating production scenarios
Perfect for testing AI log analysis chatbot
"""

import argparse
import random
import json
from datetime import datetime, timedelta
from pathlib import Path
import time


class RealisticLogGenerator:
    """Generate realistic logs with common production patterns"""
    
    # Microservices
    SERVICES = ['api-gateway', 'auth-service', 'user-service', 'payment-service', 
                'notification-service', 'database', 'cache', 'message-queue']
    
    # User activities
    USERS = [f'user_{i:04d}' for i in range(1, 101)]
    
    # API endpoints
    ENDPOINTS = [
        '/api/v1/users/login',
        '/api/v1/users/profile',
        '/api/v1/payments/process',
        '/api/v1/orders/create',
        '/api/v1/products/search',
        '/api/v1/cart/update',
        '/api/v1/notifications/send'
    ]
    
    # Error patterns
    ERROR_PATTERNS = {
        'database_timeout': {
            'service': 'database',
            'messages': [
                'Connection timeout after 30s',
                'Query execution exceeded timeout',
                'Database connection pool exhausted',
                'Failed to acquire connection from pool'
            ],
            'impact': ['auth-service', 'user-service', 'payment-service']
        },
        'memory_leak': {
            'service': 'api-gateway',
            'messages': [
                'OutOfMemoryError: Java heap space',
                'GC overhead limit exceeded',
                'Memory usage at 95%',
                'Unable to allocate memory'
            ],
            'impact': ['api-gateway']
        },
        'authentication_failure': {
            'service': 'auth-service',
            'messages': [
                'JWT token validation failed',
                'Invalid credentials provided',
                'Session expired',
                'Token signature mismatch'
            ],
            'impact': ['api-gateway', 'user-service']
        },
        'payment_gateway_error': {
            'service': 'payment-service',
            'messages': [
                'Payment gateway timeout',
                'Card declined by issuer',
                'Insufficient funds',
                'Payment processing failed'
            ],
            'impact': ['payment-service']
        },
        'rate_limit_exceeded': {
            'service': 'api-gateway',
            'messages': [
                'Rate limit exceeded for IP',
                'Too many requests from user',
                'API quota exhausted',
                'Request throttled'
            ],
            'impact': ['api-gateway']
        }
    }
    
    # Success patterns
    SUCCESS_MESSAGES = [
        'Request processed successfully',
        'User authenticated',
        'Payment completed',
        'Order created successfully',
        'Cache hit for key',
        'Message published to queue',
        'Database query executed',
        'API response sent'
    ]
    
    def __init__(self, output_dir, base_time=None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.base_time = base_time or datetime.now()
        self.current_time = self.base_time
    
    def generate_scenario_healthy_system(self, duration_minutes=30, logs_per_minute=100):
        """Scenario 1: Healthy system with normal operations"""
        print(f"\n📊 Scenario 1: Healthy System ({duration_minutes} minutes)")
        
        logs = []
        for minute in range(duration_minutes):
            timestamp = self.base_time - timedelta(minutes=duration_minutes-minute)
            
            for _ in range(logs_per_minute):
                log = self._generate_success_log(timestamp)
                logs.append(log)
                timestamp += timedelta(seconds=random.uniform(0.1, 0.9))
        
        self._write_logs('scenario1_healthy_system.json', logs)
        print(f"✅ Generated {len(logs)} healthy system logs")
        return logs
    
    def generate_scenario_database_outage(self, duration_minutes=45):
        """Scenario 2: Database connection issues causing cascading failures"""
        print(f"\n🚨 Scenario 2: Database Outage ({duration_minutes} minutes)")
        
        logs = []
        
        # Normal operation (first 10 minutes)
        for minute in range(10):
            timestamp = self.base_time - timedelta(minutes=duration_minutes-minute)
            for _ in range(80):
                logs.append(self._generate_success_log(timestamp))
                timestamp += timedelta(seconds=random.uniform(0.3, 0.9))
        
        # Database issues start (minutes 10-25)
        print("  💥 Database timeout errors starting...")
        for minute in range(10, 25):
            timestamp = self.base_time - timedelta(minutes=duration_minutes-minute)
            
            for _ in range(50):
                # 70% errors, 30% retries
                if random.random() < 0.7:
                    logs.append(self._generate_error_log(
                        timestamp, 'database_timeout'
                    ))
                else:
                    logs.append(self._generate_retry_log(timestamp))
                timestamp += timedelta(seconds=random.uniform(0.5, 1.5))
        
        # Recovery phase (minutes 25-35)
        print("  🔄 System recovering...")
        for minute in range(25, 35):
            timestamp = self.base_time - timedelta(minutes=duration_minutes-minute)
            
            for _ in range(60):
                # Gradually improving: 40% errors -> 10% errors
                error_rate = max(0.1, 0.4 - ((minute - 25) * 0.03))
                if random.random() < error_rate:
                    logs.append(self._generate_error_log(
                        timestamp, 'database_timeout'
                    ))
                else:
                    logs.append(self._generate_success_log(timestamp))
                timestamp += timedelta(seconds=random.uniform(0.4, 1.0))
        
        # Back to normal (minutes 35-45)
        for minute in range(35, 45):
            timestamp = self.base_time - timedelta(minutes=duration_minutes-minute)
            for _ in range(80):
                logs.append(self._generate_success_log(timestamp))
                timestamp += timedelta(seconds=random.uniform(0.3, 0.9))
        
        self._write_logs('scenario2_database_outage.json', logs)
        print(f"✅ Generated {len(logs)} logs with database outage pattern")
        return logs
    
    def generate_scenario_memory_leak(self, duration_minutes=60):
        """Scenario 3: Memory leak causing gradual degradation"""
        print(f"\n💾 Scenario 3: Memory Leak ({duration_minutes} minutes)")
        
        logs = []
        
        for minute in range(duration_minutes):
            timestamp = self.base_time - timedelta(minutes=duration_minutes-minute)
            
            # Memory pressure increases over time
            memory_pressure = min(0.95, 0.5 + (minute / duration_minutes) * 0.45)
            
            # More errors as memory fills up
            error_rate = max(0.02, (memory_pressure - 0.5) * 2) if memory_pressure > 0.7 else 0.02
            
            logs_this_minute = max(20, int(100 * (1 - memory_pressure * 0.5)))
            
            for _ in range(logs_this_minute):
                if random.random() < error_rate:
                    logs.append(self._generate_error_log(
                        timestamp, 'memory_leak'
                    ))
                else:
                    log = self._generate_success_log(timestamp)
                    # Add memory warnings
                    if memory_pressure > 0.8 and random.random() < 0.3:
                        log['level'] = 'WARN'
                        log['message'] = f'High memory usage: {memory_pressure*100:.1f}%'
                    logs.append(log)
                
                timestamp += timedelta(seconds=random.uniform(0.5, 2.0))
        
        self._write_logs('scenario3_memory_leak.json', logs)
        print(f"✅ Generated {len(logs)} logs with memory leak pattern")
        return logs
    
    def generate_scenario_ddos_attack(self, duration_minutes=30):
        """Scenario 4: DDoS attack with rate limiting"""
        print(f"\n⚠️  Scenario 4: DDoS Attack ({duration_minutes} minutes)")
        
        logs = []
        
        # Normal baseline (first 5 minutes)
        for minute in range(5):
            timestamp = self.base_time - timedelta(minutes=duration_minutes-minute)
            for _ in range(80):
                logs.append(self._generate_success_log(timestamp))
                timestamp += timedelta(seconds=random.uniform(0.3, 0.8))
        
        # Attack starts (minutes 5-20)
        print("  🔥 DDoS attack detected...")
        attacker_ips = [f'10.0.{random.randint(0,255)}.{random.randint(0,255)}' 
                       for _ in range(20)]
        
        for minute in range(5, 20):
            timestamp = self.base_time - timedelta(minutes=duration_minutes-minute)
            
            # High request volume (500 requests/min during attack)
            for _ in range(500):
                if random.random() < 0.7:
                    # Rate limit errors
                    logs.append(self._generate_rate_limit_log(
                        timestamp, random.choice(attacker_ips)
                    ))
                else:
                    logs.append(self._generate_success_log(timestamp))
                timestamp += timedelta(seconds=random.uniform(0.05, 0.2))
        
        # Attack mitigated (minutes 20-30)
        print("  🛡️  Attack blocked, traffic normalized...")
        for minute in range(20, 30):
            timestamp = self.base_time - timedelta(minutes=duration_minutes-minute)
            for _ in range(90):
                logs.append(self._generate_success_log(timestamp))
                timestamp += timedelta(seconds=random.uniform(0.3, 0.8))
        
        self._write_logs('scenario4_ddos_attack.json', logs)
        print(f"✅ Generated {len(logs)} logs with DDoS attack pattern")
        return logs
    
    def generate_scenario_payment_failures(self, duration_minutes=40):
        """Scenario 5: Payment gateway issues"""
        print(f"\n💳 Scenario 5: Payment Gateway Failures ({duration_minutes} minutes)")
        
        logs = []
        
        for minute in range(duration_minutes):
            timestamp = self.base_time - timedelta(minutes=duration_minutes-minute)
            
            # Payment failures spike in middle period (minutes 15-30)
            if 15 <= minute < 30:
                payment_error_rate = 0.6
                logs_per_min = 120
            else:
                payment_error_rate = 0.05
                logs_per_min = 90
            
            for _ in range(logs_per_min):
                service = random.choice(self.SERVICES)
                
                if service == 'payment-service' and random.random() < payment_error_rate:
                    logs.append(self._generate_error_log(
                        timestamp, 'payment_gateway_error'
                    ))
                else:
                    logs.append(self._generate_success_log(timestamp))
                
                timestamp += timedelta(seconds=random.uniform(0.2, 1.0))
        
        self._write_logs('scenario5_payment_failures.json', logs)
        print(f"✅ Generated {len(logs)} logs with payment failures")
        return logs
    
    def generate_scenario_mixed_errors(self, duration_minutes=60):
        """Scenario 6: Multiple simultaneous issues"""
        print(f"\n🔀 Scenario 6: Multiple Issues ({duration_minutes} minutes)")
        
        logs = []
        
        for minute in range(duration_minutes):
            timestamp = self.base_time - timedelta(minutes=duration_minutes-minute)
            
            for _ in range(100):
                # Randomly pick error type or success
                rand = random.random()
                
                if rand < 0.10:
                    error_type = random.choice(list(self.ERROR_PATTERNS.keys()))
                    logs.append(self._generate_error_log(timestamp, error_type))
                else:
                    logs.append(self._generate_success_log(timestamp))
                
                timestamp += timedelta(seconds=random.uniform(0.3, 0.9))
        
        self._write_logs('scenario6_mixed_errors.json', logs)
        print(f"✅ Generated {len(logs)} logs with mixed errors")
        return logs
    
    def _generate_success_log(self, timestamp):
        """Generate a successful operation log"""
        service = random.choice(self.SERVICES)
        user = random.choice(self.USERS)
        endpoint = random.choice(self.ENDPOINTS)
        message = random.choice(self.SUCCESS_MESSAGES)
        
        return {
            "timestamp": (datetime.now() - timedelta(minutes=random.randint(0, 1440))).isoformat() ,
            'level': 'INFO',
            'service': service,
            'user': user,
            'endpoint': endpoint,
            'message': message,
            'status_code': random.choice([200, 201, 204]),
            'response_time_ms': random.randint(10, 150),
            'request_id': f'req-{random.randint(100000, 999999)}'
        }
    
    def _generate_error_log(self, timestamp, error_pattern):
        """Generate an error log based on pattern"""
        pattern = self.ERROR_PATTERNS[error_pattern]
        affected_service = random.choice(pattern['impact'])
        message = random.choice(pattern['messages'])
        
        return {
            "timestamp": (datetime.now() - timedelta(minutes=random.randint(0, 1440))).isoformat() ,
            'level': 'ERROR',
            'service': affected_service,
            'user': random.choice(self.USERS),
            'endpoint': random.choice(self.ENDPOINTS),
            'message': message,
            'error_type': error_pattern,
            'status_code': random.choice([500, 502, 503, 504]),
            'response_time_ms': random.randint(5000, 30000),
            'request_id': f'req-{random.randint(100000, 999999)}'
        }
    
    def _generate_retry_log(self, timestamp):
        """Generate a retry attempt log"""
        return {
            "timestamp": (datetime.now() - timedelta(minutes=random.randint(0, 1440))).isoformat() ,
            'level': 'WARN',
            'service': random.choice(['auth-service', 'user-service', 'payment-service']),
            'message': 'Retrying after connection failure',
            'retry_attempt': random.randint(1, 5),
            'request_id': f'req-{random.randint(100000, 999999)}'
        }
    
    def _generate_rate_limit_log(self, timestamp, ip):
        """Generate rate limit log"""
        return {
            "timestamp": (datetime.now() - timedelta(minutes=random.randint(0, 1440))).isoformat() ,
            'level': 'WARN',
            'service': 'api-gateway',
            'message': f'Rate limit exceeded for IP {ip}',
            'source_ip': ip,
            'status_code': 429,
            'request_id': f'req-{random.randint(100000, 999999)}'
        }
    
    def _write_logs(self, filename, logs):
        """Write logs to JSON file (one per line)"""
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            for log in logs:
                f.write(json.dumps(log) + '\n')
        print(f"  📝 Wrote {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate realistic log files for testing AI log analysis'
    )
    parser.add_argument(
        '--output', '-o',
        default='./logs_in',
        help='Output directory for log files'
    )
    parser.add_argument(
        '--scenarios', '-s',
        nargs='+',
        choices=['all', '1', '2', '3', '4', '5', '6'],
        default=['all'],
        help='Which scenarios to generate (default: all)'
    )
    parser.add_argument(
        '--base-time',
        help='Base timestamp (ISO format, default: now)'
    )
    
    args = parser.parse_args()
    
    base_time = datetime.fromisoformat(args.base_time) if args.base_time else datetime.now()
    generator = RealisticLogGenerator(args.output, base_time)
    
    scenarios = args.scenarios
    if 'all' in scenarios:
        scenarios = ['1', '2', '3', '4', '5', '6']
    
    print("=" * 70)
    print("🔥 REALISTIC LOG GENERATOR")
    print("=" * 70)
    print(f"Output directory: {args.output}")
    print(f"Base timestamp: {base_time}")
    print(f"Generating scenarios: {', '.join(scenarios)}")
    
    if '1' in scenarios:
        generator.generate_scenario_healthy_system()
    
    if '2' in scenarios:
        generator.generate_scenario_database_outage()
    
    if '3' in scenarios:
        generator.generate_scenario_memory_leak()
    
    if '4' in scenarios:
        generator.generate_scenario_ddos_attack()
    
    if '5' in scenarios:
        generator.generate_scenario_payment_failures()
    
    if '6' in scenarios:
        generator.generate_scenario_mixed_errors()
    
    print("\n" + "=" * 70)
    print("✅ GENERATION COMPLETE!")
    print("=" * 70)
    print(f"\nNext steps:")
    print(f"1. Review logs in: {args.output}/")
    print(f"2. Ingest logs: python -m app.cli.ingest --directory {args.output}")
    print(f"3. Test AI chatbot with queries like:")
    print(f"   - 'Analyze logs from last 45 minutes'")
    print(f"   - 'What errors occurred?'")
    print(f"   - 'Find database issues'")


if __name__ == '__main__':
    main()
