"""Datadog Logs Client - Fetches real logs from Datadog API with scope permissions"""
import httpx
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from app.domain.entities.log_entry import LogEntry
from app.config import settings

logger = logging.getLogger(__name__)

class DatadogLogsClient:
    """Client for fetching real logs from Datadog API with scope-based access control."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Simple cache to reduce API calls
        self._cache: Optional[List[LogEntry]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=1)  # Cache logs for 1 minute
        
    async def fetch_logs(self, level: Optional[str] = None, user_permissions: List[str] = None) -> List[LogEntry]:
        """Fetch logs from Datadog API with scope-based access control and fallback to mock data."""
        
        # Check if user has permission to read logs
        if user_permissions and "read_logs" not in user_permissions:
            logger.warning("❌ User lacks 'read_logs' permission - returning empty logs")
            return []
        
        # Check cache first
        if self._cache and self._cache_timestamp:
            if datetime.now(timezone.utc) - self._cache_timestamp < self._cache_ttl:
                logger.info(f"🚀 CACHE HIT: Returning cached logs (age: {datetime.now(timezone.utc) - self._cache_timestamp})")
                # Apply level filter to cached logs if needed
                if level:
                    return [log for log in self._cache if log.level == level]
                return self._cache
        
        # Build query for the service
        query_parts = [f"service:{settings.DATADOG_SERVICE_NAME}"]
        if level:
            if level == "WARN":
                query_parts.append("(@level:WARN OR @level:WARNING)")
            else:
                query_parts.append(f"@level:{level}")
        
        query = " ".join(query_parts)
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "DD-API-KEY": settings.datadog_api_key,
        }
        if settings.datadog_app_key:
            headers["DD-APPLICATION-KEY"] = settings.datadog_app_key
        
        # Prepare payload
        payload = {
            "filter": {
                "query": query,
                "from": "now-7d",  # Last 7 days
                "to": "now"
            },
            "sort": "-timestamp",
            "page": {"limit": 100}
        }
        
        try:
            logger.info(f"🔍 Fetching logs from Datadog with query: {query}")
            logger.info(f"🔐 User permissions: {user_permissions}")
            
            response = await self.client.post(
                "https://api.datadoghq.com/api/v2/logs/events/search",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                logs_data = data.get("data", [])
                
                if logs_data:
                    log_entries = self._transform_logs(logs_data)
                    logger.info(f"✅ Successfully fetched {len(log_entries)} real logs from Datadog")
                    
                    # Update cache
                    self._cache = log_entries
                    self._cache_timestamp = datetime.now(timezone.utc)
                    logger.info("💾 Updated logs cache")
                    
                    # Apply level filter if needed
                    if level:
                        return [log for log in log_entries if log.level == level]
                    return log_entries
                else:
                    logger.info(f"ℹ️  No logs found in Datadog for service '{settings.DATADOG_SERVICE_NAME}' in the last 7 days")
                    logger.info("💡 This is normal if no applications are sending logs to Datadog yet")
                    logger.info("🔄 Falling back to mock data for demonstration")
                    return self._get_mock_logs(level)
            else:
                logger.warning(f"⚠️ Datadog API error {response.status_code}, falling back to mock data")
                return self._get_mock_logs(level)
                
        except Exception as e:
            logger.error(f"❌ Error fetching logs from Datadog: {e}, falling back to mock data")
            return self._get_mock_logs(level)
    
    def _transform_logs(self, datadog_logs: List[Dict[str, Any]]) -> List[LogEntry]:
        """Transform Datadog logs to LogEntry entities."""
        entries = []
        
        for log_data in datadog_logs:
            try:
                attrs = log_data.get("attributes", {})
                
                # Parse timestamp
                timestamp_str = attrs.get("timestamp")
                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    timestamp = datetime.now(timezone.utc)
                
                # Extract and normalize level
                level = attrs.get("level", "INFO").upper()
                if level == "WARNING":
                    level = "WARN"
                elif level not in ["INFO", "WARN", "ERROR"]:
                    level = "INFO"
                
                # Extract message
                message = attrs.get("message", "")
                
                entries.append(LogEntry(
                    timestamp=timestamp,
                    level=level,
                    message=message
                ))
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to parse log entry: {e}")
                continue
        
        return entries
    
    def _get_mock_logs(self, level: Optional[str] = None) -> List[LogEntry]:
        """Generate mock logs when Datadog is unavailable."""
        mock_entries = [
            {"level": "INFO", "message": "User authentication successful - user_id=12345"},
            {"level": "INFO", "message": "Payment processed successfully - transaction_id=tx_98765"},
            {"level": "ERROR", "message": "Database connection failed - session_id=sess_abc123"},
            {"level": "WARN", "message": "High memory usage detected - request_id=req_xyz789"},
            {"level": "INFO", "message": "API request processed - correlation_id=corr_456def"},
            {"level": "ERROR", "message": "Payment processing error - transaction_id=tx_11111"},
            {"level": "WARN", "message": "Slow database query detected - query_id=query_22222"},
            {"level": "INFO", "message": "Cache hit for user session - user_id=67890"},
        ]
        
        logs = []
        for i, entry in enumerate(mock_entries):
            # Apply level filter if specified
            if level and entry["level"] != level:
                continue
                
            logs.append(LogEntry(
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=i*5),
                level=entry["level"],
                message=f"MOCK: {entry['message']}"
            ))
        
        return logs
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
