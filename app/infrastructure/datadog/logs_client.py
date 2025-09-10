"""Refactored Datadog Logs Client."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.domain.entities.log_entry import LogEntry
from app.infrastructure.datadog.base_client import BaseDatadogClient

logger = logging.getLogger(__name__)


class DatadogLogsClient(BaseDatadogClient):
    """Client for fetching real logs from Datadog API."""

    def __init__(self):
        super().__init__()
        self._base_url = "https://api.datadoghq.com/api/v2/logs/events/search"
        self._default_limit = 10
        self._default_time_range = "now-7d"

    async def fetch_data(
        self, level: Optional[str] = None, limit: Optional[int] = None
    ) -> List[LogEntry]:
        """Fetch logs from Datadog API with fallback to mock data."""
        if not self._is_api_available():
            logger.warning("Datadog API keys not available, using mock data")
            return self._get_mock_logs(level)

        query = self._build_query(level)
        effective_limit = limit or self._default_limit

        # For Cequence mode, restrict to smaller limits to ensure single call
        if limit is not None and limit <= 10:
            logger.info(
                f"🔧 CEQUENCE MODE: Restricting logs query to {limit} entries for single call"
            )
            effective_limit = limit

        payload = self._build_payload(query, effective_limit)

        try:
            logger.info(f"Fetching logs from Datadog with query: {query}")

            response = await self._make_request(
                "POST", self._base_url, headers=self._get_headers(), json=payload
            )

            if response.status_code == 200:
                return self._handle_success_response(response, level)
            else:
                logger.warning(
                    f"Datadog API error {response.status_code}, falling back to mock data"
                )
                return self._get_mock_logs(level)

        except Exception as e:
            logger.error(
                f"Error fetching logs from Datadog: {e}, falling back to mock data"
            )
            return self._get_mock_logs(level)

    def _build_query(self, level: Optional[str] = None) -> str:
        """Build Datadog query string."""
        query_parts = [f"service:{self._service_name}"]

        if level:
            if level == "WARN":
                query_parts.append("(@level:WARN OR @level:WARNING)")
            else:
                query_parts.append(f"@level:{level}")

        return " ".join(query_parts)

    def _build_payload(self, query: str, limit: int) -> Dict[str, Any]:
        """Build API request payload."""
        return {
            "filter": {"query": query, "from": self._default_time_range, "to": "now"},
            "sort": "-timestamp",
            "page": {"limit": limit},
        }

    def _handle_success_response(
        self, response: httpx.Response, level: Optional[str]
    ) -> List[LogEntry]:
        """Handle successful API response."""
        data = response.json()
        logs_data = data.get("data", [])

        if logs_data:
            log_entries = self._transform_logs(logs_data)
            logger.info(
                f"✅ Successfully fetched {len(log_entries)} real logs from Datadog"
            )
            return log_entries
        else:
            logger.info(
                f"ℹ️  No logs found in Datadog for service '{self._service_name}' in the last 7 days"
            )
            logger.info(
                "💡 This is normal if no applications are sending logs to Datadog yet"
            )
            logger.info("🔄 Falling back to mock data for demonstration")
            return self._get_mock_logs(level)

    def _transform_logs(self, datadog_logs: List[Dict[str, Any]]) -> List[LogEntry]:
        """Transform Datadog logs to LogEntry entities."""
        entries = []

        for log_data in datadog_logs:
            try:
                attrs = log_data.get("attributes", {})

                # Parse timestamp
                timestamp = self._parse_timestamp(attrs.get("timestamp"))

                # Extract and normalize level
                level = self._normalize_level(attrs.get("level", "INFO"))

                # Extract message
                message = attrs.get("message", "")

                entries.append(
                    LogEntry(timestamp=timestamp, level=level, message=message)
                )

            except Exception as e:
                logger.warning(f"Failed to parse log entry: {e}")
                continue

        return entries

    def _parse_timestamp(self, timestamp_str: Optional[str]) -> datetime:
        """Parse timestamp string to datetime object."""
        if timestamp_str:
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return datetime.now(timezone.utc)

    def _normalize_level(self, level: str) -> str:
        """Normalize log level to standard format."""
        level = level.upper()
        if level == "WARNING":
            return "WARN"
        elif level not in ["INFO", "WARN", "ERROR"]:
            return "INFO"
        return level

    def _get_mock_logs(self, level: Optional[str] = None) -> List[LogEntry]:
        """Generate mock logs when Datadog is unavailable."""
        mock_entries = [
            {
                "level": "INFO",
                "message": "User authentication successful - user_id=12345",
            },
            {
                "level": "INFO",
                "message": "Payment processed successfully - transaction_id=tx_98765",
            },
            {
                "level": "ERROR",
                "message": "Database connection failed - session_id=sess_abc123",
            },
            {
                "level": "WARN",
                "message": "High memory usage detected - request_id=req_xyz789",
            },
            {
                "level": "INFO",
                "message": "API request processed - correlation_id=corr_456def",
            },
            {
                "level": "ERROR",
                "message": "Payment processing error - transaction_id=tx_11111",
            },
            {
                "level": "WARN",
                "message": "Slow database query detected - query_id=query_22222",
            },
            {"level": "INFO", "message": "Cache hit for user session - user_id=67890"},
        ]

        logs = []
        for i, entry in enumerate(mock_entries):
            # Apply level filter if specified
            if level and entry["level"] != level:
                continue

            logs.append(
                LogEntry(
                    timestamp=datetime.now(timezone.utc) - timedelta(minutes=i * 5),
                    level=entry["level"],
                    message=f"MOCK: {entry['message']}",
                )
            )

        return logs
