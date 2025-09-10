"""Refactored Datadog Metrics Client."""

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.domain.entities.metric import Metric
from app.infrastructure.datadog.base_client import BaseDatadogClient

logger = logging.getLogger(__name__)


class DatadogMetricsClient(BaseDatadogClient):
    """Client for fetching real metrics from Datadog API."""

    def __init__(self):
        super().__init__()
        self._base_url = "https://api.datadoghq.com/api/v1/query"
        self._cache: Optional[List[Metric]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(
            minutes=5
        )  # Increased cache time since we're fetching 7 days of data

        # Metrics configuration
        self._metrics_config = [
            ("cpu_utilization", "percent"),
            ("memory_usage", "percent"),
            ("disk_usage", "percent"),
            ("network_in", "bytes"),
            ("network_out", "bytes"),
            ("response_time", "milliseconds"),
            ("request_count", "count"),
            ("error_rate", "percent"),
            ("database_connections", "count"),
            ("queue_size", "count"),
        ]

    async def fetch_data(
        self,
        user_permissions: List[str] = None,
        fetch_historical: bool = False,
        limit: int = None,
    ) -> List[Metric]:
        """Fetch metrics from Datadog API with fallback to mock data."""
        if not self._is_api_available():
            logger.warning("Datadog API keys not available, using mock data")
            return self._get_mock_metrics()

        # Check cache first (only for non-historical requests)
        if not fetch_historical and self._is_cache_valid():
            logger.info(
                f"🚀 CACHE HIT: Returning cached metrics (age: {datetime.now(timezone.utc) - self._cache_timestamp})"
            )
            return self._cache

        try:
            return await self._fetch_metrics_from_api(fetch_historical, limit)
        except Exception as e:
            logger.error(
                f"Error fetching metrics from Datadog: {e}, falling back to mock data"
            )
            return self._get_mock_metrics()

    def _is_cache_valid(self) -> bool:
        """Check if cache is valid."""
        return (
            self._cache
            and self._cache_timestamp
            and datetime.now(timezone.utc) - self._cache_timestamp < self._cache_ttl
        )

    async def _fetch_metrics_from_api(
        self, fetch_historical: bool, limit: int = None
    ) -> List[Metric]:
        """Fetch metrics from Datadog API."""
        time_range = self._get_time_range(fetch_historical)

        # If limit is specified (Cequence mode), fetch only single metric to avoid breaking into multiple calls
        if limit is not None and limit <= 1:
            # Single metric call for Cequence Gateway compatibility
            single_metric = self._metrics_config[
                0
            ]  # Get the first (most important) metric
            query = f"avg:{single_metric[0]}{{service:{self._service_name}}}"
            logger.info(
                "🔧 CEQUENCE MODE: Fetching SINGLE metric to avoid gateway breaking batch calls"
            )
            logger.info(f"🔍 Single query: {query}")
        else:
            # Normal batch query for direct mode
            query = self._build_batch_query()
            logger.info(
                f"🚀 OPTIMIZED: Fetching {len(self._metrics_config)} metrics from Datadog in a SINGLE batch call (7-day range)"
            )
            logger.info(f"🔍 Batch query: {query}")

        logger.info(f"⏰ Time range: {time_range[0]} to {time_range[1]} (7 days)")

        params = {"query": query, "from": str(time_range[0]), "to": str(time_range[1])}

        response = await self._make_request(
            "GET",
            self._base_url,
            headers=self._get_headers(content_type=None),
            params=params,
        )

        if response.status_code == 200:
            return self._handle_success_response(response, fetch_historical, limit)
        else:
            logger.warning(
                f"Datadog API error {response.status_code}, falling back to mock data"
            )
            return self._get_mock_metrics()

    def _get_time_range(self, fetch_historical: bool) -> Tuple[int, int]:
        """Get time range for metrics query."""
        now = datetime.now(timezone.utc)
        if fetch_historical:
            # Fetch last 7 days for historical view
            from_time = int((now - timedelta(days=7)).timestamp())
        else:
            # Fetch last 7 days for latest values (increased from 10 minutes)
            from_time = int((now - timedelta(days=7)).timestamp())
        to_time = int(now.timestamp())
        return from_time, to_time

    def _build_batch_query(self) -> str:
        """Build batch query for all metrics."""
        metric_queries = [
            f"avg:{metric_name}{{service:{self._service_name}}}"
            for metric_name, _ in self._metrics_config
        ]
        return ",".join(metric_queries)

    def _handle_success_response(
        self, response: httpx.Response, fetch_historical: bool, limit: int = None
    ) -> List[Metric]:
        """Handle successful API response."""
        data = response.json()
        series = data.get("series", [])

        if series:
            all_metrics = self._process_series(series, fetch_historical)

            # If limit is specified (Cequence mode), return only the requested number
            if limit is not None and limit <= 1:
                logger.info(
                    f"✅ CEQUENCE MODE: Successfully fetched {len(all_metrics)} metric(s) from Datadog in 1 API call"
                )
                return all_metrics[:limit] if all_metrics else all_metrics
            else:
                logger.info(
                    f"✅ Successfully fetched {len(all_metrics)} real metrics from Datadog in 1 API call (7-day range)"
                )

                # Update cache for non-historical requests
                if not fetch_historical:
                    all_metrics = self._deduplicate_latest_metrics(all_metrics)
                    logger.info(
                        f"📊 Deduplicated to {len(all_metrics)} latest metrics (one per type)"
                    )
                    self._update_cache(all_metrics)

                return all_metrics
        else:
            logger.info("No metrics data returned from Datadog batch query")
            return self._get_mock_metrics()

    def _process_series(
        self, series: List[Dict[str, Any]], fetch_historical: bool
    ) -> List[Metric]:
        """Process Datadog series data."""
        all_metrics = []

        for s in series:
            metric_name = s.get("metric", "unknown")
            unit = self._get_metric_unit(metric_name)
            metrics = self._transform_metrics(metric_name, unit, [s], fetch_historical)
            all_metrics.extend(metrics)

        return all_metrics

    def _get_metric_unit(self, metric_name: str) -> str:
        """Get unit for a metric name."""
        for name, unit in self._metrics_config:
            if name == metric_name:
                return unit
        return "unknown"

    def _transform_metrics(
        self,
        name: str,
        unit: str,
        series: List[Dict[str, Any]],
        fetch_historical: bool = False,
    ) -> List[Metric]:
        """Transform Datadog series to Metric entities."""
        metrics = []

        for s in series:
            pointlist = s.get("pointlist", [])

            if not pointlist:
                continue

            if fetch_historical:
                # Return all data points
                for point in pointlist:
                    if len(point) >= 2 and point[1] is not None:
                        timestamp = datetime.fromtimestamp(
                            point[0] / 1000, tz=timezone.utc
                        )
                        value = float(point[1])

                        metrics.append(
                            Metric(
                                timestamp=timestamp, name=name, value=value, unit=unit
                            )
                        )
            else:
                # Return only the latest (most recent) data point
                latest_point = pointlist[-1]  # Last point is most recent due to sorting
                if len(latest_point) >= 2 and latest_point[1] is not None:
                    timestamp = datetime.fromtimestamp(
                        latest_point[0] / 1000, tz=timezone.utc
                    )
                    value = float(latest_point[1])

                    metrics.append(
                        Metric(timestamp=timestamp, name=name, value=value, unit=unit)
                    )

        return metrics

    def _deduplicate_latest_metrics(self, metrics: List[Metric]) -> List[Metric]:
        """Keep only the latest (most recent) metric for each metric name."""
        latest_metrics = {}

        for metric in metrics:
            metric_name = metric.name

            # If we haven't seen this metric before, or this one is more recent
            if (
                metric_name not in latest_metrics
                or metric.timestamp > latest_metrics[metric_name].timestamp
            ):
                latest_metrics[metric_name] = metric

        # Return as list, sorted by metric name for consistency
        return sorted(latest_metrics.values(), key=lambda m: m.name)

    def _update_cache(self, metrics: List[Metric]):
        """Update cache with new metrics."""
        self._cache = metrics
        self._cache_timestamp = datetime.now(timezone.utc)
        logger.info("💾 Updated metrics cache")

    def _get_mock_metrics(self) -> List[Metric]:
        """Generate mock metrics when Datadog is unavailable."""
        mock_metrics = []
        now = datetime.now(timezone.utc)

        # Generate ONE mock data point per metric type (latest value only)
        for metric_name, unit in self._metrics_config:
            value = self._generate_mock_value(metric_name, unit)

            mock_metrics.append(
                Metric(
                    timestamp=now,  # All use current timestamp as "latest"
                    name=metric_name,
                    value=value,
                    unit=unit,
                )
            )

        return mock_metrics

    def _generate_mock_value(self, metric_name: str, unit: str) -> float:
        """Generate realistic mock value based on metric type."""
        if "percent" in unit or "rate" in metric_name:
            return round(random.uniform(10, 90), 2)
        elif "count" in unit:
            return random.randint(1, 100)
        elif "bytes" in unit:
            return random.randint(1000, 10000)
        elif "milliseconds" in unit:
            return round(random.uniform(50, 500), 2)
        else:
            return round(random.uniform(10, 100), 2)
