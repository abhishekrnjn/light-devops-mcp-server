"""
Dummy data generation utilities for MCP HTTP Server.

This module provides realistic dummy data generation for immediate UI responses
while real API calls are being processed in the background.
"""

import random
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DummyDataGenerator:
    """
    Generator for realistic dummy data used in immediate responses.
    
    This class provides methods to generate realistic dummy data for logs,
    metrics, and other data types to provide immediate UI feedback while
    real API calls are being processed in the background.
    """

    # Log templates for generating realistic log entries
    LOG_TEMPLATES = [
        {
            "level": "INFO",
            "message": "User authentication successful - user_id={user_id}",
        },
        {
            "level": "INFO",
            "message": "API request processed - endpoint=/api/v1/metrics, response_time={time}ms",
        },
        {
            "level": "INFO",
            "message": "Database query executed - duration={duration}ms, rows={rows}",
        },
        {
            "level": "WARN",
            "message": "High memory usage detected - current={memory}%, threshold=80%",
        },
        {
            "level": "INFO",
            "message": "Cache hit - key=user_session_{session}, ttl={ttl}s",
        },
        {
            "level": "WARN",
            "message": "Rate limit approaching - requests={requests}/min, limit=1000",
        },
        {
            "level": "ERROR",
            "message": "External API timeout - service={service}, timeout=30s",
        },
        {
            "level": "INFO",
            "message": "Background job completed - type=log_aggregation, duration={duration}s",
        },
        {
            "level": "WARN",
            "message": "Disk space warning - usage={usage}%, available={available}GB",
        },
        {
            "level": "INFO",
            "message": "Health check passed - all services operational, uptime={uptime}h",
        },
        {
            "level": "DEBUG",
            "message": "Debug trace - function={function}, line={line}, variable={variable}",
        },
        {
            "level": "ERROR",
            "message": "Database connection failed - host={host}, port={port}, error={error}",
        },
        {
            "level": "INFO",
            "message": "File uploaded successfully - filename={filename}, size={size}bytes",
        },
        {
            "level": "WARN",
            "message": "Slow query detected - query={query}, duration={duration}ms",
        },
        {
            "level": "INFO",
            "message": "User session expired - user_id={user_id}, session_duration={duration}m",
        },
    ]

    # Metric configurations for generating realistic metrics
    METRIC_CONFIGS = [
        ("cpu_utilization", "percent", 20, 80),
        ("memory_usage", "percent", 30, 85),
        ("disk_usage", "percent", 40, 90),
        ("response_time", "milliseconds", 50, 300),
        ("error_rate", "percent", 0.1, 5.0),
        ("request_count", "count", 100, 2000),
        ("database_connections", "count", 5, 100),
        ("network_in", "bytes", 1024, 1000000),
        ("network_out", "bytes", 1024, 1000000),
        ("queue_size", "count", 0, 50),
        ("active_sessions", "count", 10, 500),
        ("cache_hit_rate", "percent", 70, 95),
        ("throughput", "requests_per_second", 50, 500),
        ("latency_p95", "milliseconds", 100, 500),
        ("availability", "percent", 99.0, 99.99),
    ]

    # Service names for generating realistic service-related data
    SERVICE_NAMES = [
        "payment-service",
        "user-service",
        "notification-service",
        "analytics-service",
        "api-gateway",
        "database-service",
        "cache-service",
        "file-service",
        "email-service",
        "auth-service",
    ]

    # Error messages for generating realistic error scenarios
    ERROR_MESSAGES = [
        "Connection timeout",
        "Database connection lost",
        "Invalid credentials",
        "Resource not found",
        "Permission denied",
        "Rate limit exceeded",
        "Service unavailable",
        "Internal server error",
        "Validation failed",
        "Network error",
    ]

    def __init__(self):
        """Initialize the dummy data generator."""
        self.base_time = datetime.now(timezone.utc)

    def generate_logs(
        self, count: int = 10, level: Optional[str] = None, service: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate realistic dummy logs for immediate UI population.
        
        Args:
            count: Number of log entries to generate
            level: Optional log level filter (DEBUG, INFO, WARN, ERROR)
            service: Optional service name filter
            
        Returns:
            List of log entry dictionaries
        """
        logger.debug(f"Generating {count} dummy logs with level={level}, service={service}")
        
        dummy_logs = []
        templates_to_use = self.LOG_TEMPLATES

        # Filter templates by level if specified
        if level:
            templates_to_use = [t for t in self.LOG_TEMPLATES if t["level"] == level]
            if not templates_to_use:
                # If no templates match, create a generic one
                templates_to_use = [
                    {"level": level, "message": "System event logged - id={event_id}"}
                ]

        for i in range(count):
            template = random.choice(templates_to_use)
            
            # Generate realistic values for placeholders
            message = self._format_log_message(template["message"])
            
            # Generate timestamp (more recent logs first)
            log_time = self.base_time - timedelta(minutes=i * random.randint(1, 5))
            
            # Generate service name if not specified
            log_service = service or random.choice(self.SERVICE_NAMES)
            
            dummy_logs.append(
                {
                    "level": template["level"],
                    "message": f"LOADING: {message}",
                    "timestamp": log_time.isoformat(),
                    "source": log_service,
                    "_is_loading": True,
                }
            )

        return dummy_logs

    def generate_metrics(
        self, count: int = 5, service: Optional[str] = None, metric_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate realistic dummy metrics for immediate UI population.
        
        Args:
            count: Number of metrics to generate
            service: Optional service name filter
            metric_type: Optional metric type filter
            
        Returns:
            List of metric dictionaries
        """
        logger.debug(f"Generating {count} dummy metrics with service={service}, type={metric_type}")
        
        dummy_metrics = []
        configs_to_use = self.METRIC_CONFIGS

        # Filter by metric type if specified
        if metric_type:
            configs_to_use = [c for c in self.METRIC_CONFIGS if metric_type.lower() in c[0].lower()]
            if not configs_to_use:
                configs_to_use = self.METRIC_CONFIGS[:count]

        for i, (name, unit, min_val, max_val) in enumerate(configs_to_use[:count]):
            # Generate realistic values based on metric type and range
            if "percent" in unit:
                value = round(random.uniform(min_val, max_val), 2)
            elif "count" in unit:
                value = random.randint(int(min_val), int(max_val))
            elif "bytes" in unit:
                value = random.randint(int(min_val), int(max_val))
            elif "milliseconds" in unit:
                value = round(random.uniform(min_val, max_val), 2)
            else:
                value = round(random.uniform(min_val, max_val), 2)

            # Generate service name if not specified
            metric_service = service or random.choice(self.SERVICE_NAMES)

            dummy_metrics.append(
                {
                    "name": name,
                    "value": value,
                    "unit": unit,
                    "service": metric_service,
                    "timestamp": self.base_time.isoformat(),
                    "_is_loading": True,
                }
            )

        return dummy_metrics

    def generate_deployment_data(
        self, service_name: str, version: str, environment: str
    ) -> Dict[str, Any]:
        """
        Generate realistic dummy deployment data.
        
        Args:
            service_name: Name of the service being deployed
            version: Version being deployed
            environment: Target environment
            
        Returns:
            Dictionary containing deployment data
        """
        logger.debug(f"Generating dummy deployment data for {service_name} v{version} to {environment}")
        
        deployment_id = f"deploy-{random.randint(100000, 999999)}"
        statuses = ["pending", "in_progress", "completed", "failed"]
        status = random.choice(statuses)
        
        return {
            "deployment_id": deployment_id,
            "service_name": service_name,
            "version": version,
            "environment": environment,
            "status": status,
            "timestamp": self.base_time.isoformat(),
            "deployed_by": f"user-{random.randint(1000, 9999)}",
            "build_number": random.randint(1, 1000),
            "commit_hash": f"{random.randint(1000000, 9999999):x}",
            "_is_loading": True,
        }

    def generate_rollback_data(
        self, deployment_id: str, reason: str, environment: str
    ) -> Dict[str, Any]:
        """
        Generate realistic dummy rollback data.
        
        Args:
            deployment_id: ID of the deployment being rolled back
            reason: Reason for the rollback
            environment: Environment being rolled back
            
        Returns:
            Dictionary containing rollback data
        """
        logger.debug(f"Generating dummy rollback data for {deployment_id} in {environment}")
        
        rollback_id = f"rollback-{random.randint(100000, 999999)}"
        statuses = ["pending", "in_progress", "completed", "failed"]
        status = random.choice(statuses)
        
        return {
            "rollback_id": rollback_id,
            "deployment_id": deployment_id,
            "reason": reason,
            "environment": environment,
            "status": status,
            "timestamp": self.base_time.isoformat(),
            "rolled_back_by": f"user-{random.randint(1000, 9999)}",
            "previous_version": f"v{random.randint(1, 10)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
            "_is_loading": True,
        }

    def generate_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Generate realistic dummy user data.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary containing user data
        """
        logger.debug(f"Generating dummy user data for {user_id}")
        
        names = ["John Doe", "Jane Smith", "Bob Johnson", "Alice Brown", "Charlie Wilson"]
        emails = ["john@example.com", "jane@example.com", "bob@example.com", "alice@example.com", "charlie@example.com"]
        roles = ["developer", "admin", "observer", "manager"]
        
        return {
            "user_id": user_id,
            "name": random.choice(names),
            "email": random.choice(emails),
            "roles": random.sample(roles, random.randint(1, 3)),
            "permissions": random.sample([
                "read_logs", "read_metrics", "deploy_staging", "deploy_production",
                "rollback_staging", "rollback_production"
            ], random.randint(2, 5)),
            "last_login": (self.base_time - timedelta(hours=random.randint(1, 24))).isoformat(),
            "tenant": f"tenant-{random.randint(1, 10)}",
            "_is_loading": True,
        }

    def _format_log_message(self, template: str) -> str:
        """
        Format a log message template with realistic values.
        
        Args:
            template: Message template with placeholders
            
        Returns:
            Formatted message string
        """
        replacements = {
            "user_id": random.randint(10000, 99999),
            "time": random.randint(50, 300),
            "duration": random.randint(10, 500),
            "rows": random.randint(1, 100),
            "memory": random.randint(60, 95),
            "session": random.randint(1000, 9999),
            "ttl": random.randint(300, 3600),
            "requests": random.randint(500, 950),
            "service": random.choice(self.SERVICE_NAMES),
            "usage": random.randint(70, 95),
            "available": random.randint(5, 50),
            "uptime": random.randint(24, 720),
            "event_id": random.randint(100000, 999999),
            "function": random.choice(["process_request", "validate_user", "save_data", "send_notification"]),
            "line": random.randint(10, 200),
            "variable": random.choice(["user_id", "request_id", "session_token", "response_data"]),
            "host": f"db-{random.randint(1, 5)}.example.com",
            "port": random.choice([3306, 5432, 6379, 27017]),
            "error": random.choice(self.ERROR_MESSAGES),
            "filename": f"file_{random.randint(1, 1000)}.pdf",
            "size": random.randint(1024, 10485760),  # 1KB to 10MB
            "query": random.choice(["SELECT * FROM users", "UPDATE sessions SET", "INSERT INTO logs"]),
        }
        
        try:
            return template.format(**replacements)
        except KeyError as e:
            logger.warning(f"Missing replacement for placeholder: {e}")
            return template


# Convenience functions for backward compatibility
def generate_dummy_logs(count: int = 10, level: Optional[str] = None) -> List[Dict[str, Any]]:
    """Generate dummy logs using the DummyDataGenerator."""
    generator = DummyDataGenerator()
    return generator.generate_logs(count=count, level=level)


def generate_dummy_metrics(count: int = 5) -> List[Dict[str, Any]]:
    """Generate dummy metrics using the DummyDataGenerator."""
    generator = DummyDataGenerator()
    return generator.generate_metrics(count=count)
