"""Metrics Service - Uses Datadog when available, falls back to mock"""
from typing import List
from app.infrastructure.datadog.metrics_client import DatadogMetricsClient
from app.infrastructure.metrics.metrics_client import MetricsClient
from app.domain.entities.metrics_aggregation import MetricsAggregation
from app.config import settings

class MetricsService:
    def __init__(self):
        # Use Datadog if API key is available, otherwise use mock client
        if settings.datadog_api_key:
            self.client = DatadogMetricsClient()
            self.client_type = "datadog"
        else:
            self.client = MetricsClient()
            self.client_type = "mock"

    async def get_recent_metrics(self, user_permissions: List[str] = None, fetch_historical: bool = False, limit: int = None) -> MetricsAggregation:
        """Get recent metrics.
        
        Args:
            user_permissions: User's permissions (for future use)
            fetch_historical: If True, fetch historical data. If False, fetch only latest values.
            limit: If provided, limit the number of metrics returned (for Cequence optimization)
        """
        if self.client_type == "datadog":
            return await self.client.fetch_data(user_permissions=user_permissions, fetch_historical=fetch_historical, limit=limit)
        else:
            metrics = await self.client.fetch_metrics()
            
            # Create MetricsAggregation from mock metrics
            return MetricsAggregation(
                summary=f"Retrieved {len(metrics)} mock metric entries",
                total_count=len(metrics),
                service_filter="ALL",
                time_range="last 7 days",
                metrics_preview=f"{len(metrics)} mock metric entries for demonstration",
                filters_applied={
                    "limit": limit,
                    "service": "mock"
                },
                source="mock"
            )
