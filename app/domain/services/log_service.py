"""Log Service - Uses Datadog when available, falls back to mock"""
from typing import List, Optional
from app.infrastructure.logs.datadog_logs_client import DatadogLogsClient
from app.infrastructure.logs.logs_client import LogsClient
from app.config import settings

class LogService:
    def __init__(self):
        # Use Datadog if API key is available, otherwise use mock client
        if settings.datadog_api_key:
            self.client = DatadogLogsClient()
            self.client_type = "datadog"
        else:
            self.client = LogsClient()
            self.client_type = "mock"

    async def get_recent_logs(self, user_permissions: List[str] = None, level: Optional[str] = None):
        """Get recent logs with optional filtering and scope permissions."""
        if self.client_type == "datadog":
            # Datadog client handles level filtering and permissions internally
            return await self.client.fetch_logs(level, user_permissions)
        else:
            # Mock client - apply level filter manually
            logs = await self.client.fetch_logs()
            if level:
                logs = [log for log in logs if log.level == level]
            return logs
