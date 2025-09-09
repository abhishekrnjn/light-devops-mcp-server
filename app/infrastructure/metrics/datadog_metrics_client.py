"""Datadog Metrics Client - Fetches real metrics from Datadog API"""
import asyncio
import httpx
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from app.domain.entities.metric import Metric
from app.config import settings

logger = logging.getLogger(__name__)

class DatadogMetricsClient:
    """Client for fetching real metrics from Datadog API."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Simple cache to reduce API calls
        self._cache: Optional[List[Metric]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=2)  # Cache for 2 minutes
        
        # Metrics to fetch with their units
        self.metrics = [
            ("cpu_utilization", "percent"),
            ("memory_usage", "percent"), 
            ("disk_usage", "percent"),
            ("network_in", "bytes"),
            ("network_out", "bytes"),
            ("response_time", "milliseconds"),
            ("request_count", "count"),
            ("error_rate", "percent"),
            ("database_connections", "count"),
            ("queue_size", "count")
        ]
        
    async def fetch_metrics(self, user_permissions: List[str] = None, fetch_historical: bool = False) -> List[Metric]:
        """Fetch metrics from Datadog API with fallback to mock data.
        
        Args:
            user_permissions: User's permissions (for future use)
            fetch_historical: If True, fetch multiple data points. If False, fetch only latest value per metric.
        """
        
        # Check cache first (only for non-historical requests)
        if not fetch_historical and self._cache and self._cache_timestamp:
            if datetime.now(timezone.utc) - self._cache_timestamp < self._cache_ttl:
                logger.info(f"🚀 CACHE HIT: Returning cached metrics (age: {datetime.now(timezone.utc) - self._cache_timestamp})")
                return self._cache
        
        # Prepare headers
        headers = {"DD-API-KEY": settings.datadog_api_key}
        if settings.datadog_app_key:
            headers["DD-APPLICATION-KEY"] = settings.datadog_app_key
        
        # Time range - adjust based on whether historical data is requested
        now = datetime.now(timezone.utc)
        if fetch_historical:
            # Fetch last 24 hours for historical view
            from_time = int((now - timedelta(hours=24)).timestamp())
        else:
            # Fetch only last 10 minutes for latest values
            from_time = int((now - timedelta(minutes=10)).timestamp())
        to_time = int(now.timestamp())
        
        logger.info(f"🚀 OPTIMIZED: Fetching {len(self.metrics)} metrics from Datadog in a SINGLE batch call")
        
        try:
            # OPTIMIZATION: Build a single query with all metrics
            # Create a multi-metric query that fetches all metrics at once
            metric_queries = []
            for metric_name, unit in self.metrics:
                metric_queries.append(f"avg:{metric_name}{{service:{settings.DATADOG_SERVICE_NAME}}}")
            
            # Join all metric queries with commas for batch query
            batch_query = ",".join(metric_queries)
            
            params = {
                "query": batch_query,
                "from": str(from_time),
                "to": str(to_time)
            }
            
            logger.info(f"🔍 Batch query: {batch_query}")
            
            # Make SINGLE API call instead of multiple calls
            response = await self.client.get(
                "https://api.datadoghq.com/api/v1/query",
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                series = data.get("series", [])
                
                if series:
                    all_metrics = []
                    # Process all series from the single response
                    for s in series:
                        metric_name = s.get("metric", "unknown")
                        # Find the unit for this metric
                        unit = "unknown"
                        for name, u in self.metrics:
                            if name == metric_name:
                                unit = u
                                break
                        
                        metrics = self._transform_metrics(metric_name, unit, [s], fetch_historical)
                        all_metrics.extend(metrics)
                    
                    logger.info(f"✅ Successfully fetched {len(all_metrics)} real metrics from Datadog in 1 API call")
                    
                    # If not fetching historical data, ensure only one value per metric name
                    if not fetch_historical:
                        all_metrics = self._deduplicate_latest_metrics(all_metrics)
                        logger.info(f"📊 Deduplicated to {len(all_metrics)} latest metrics (one per type)")
                        
                        # Update cache for non-historical requests
                        self._cache = all_metrics
                        self._cache_timestamp = datetime.now(timezone.utc)
                        logger.info("💾 Updated metrics cache")
                    
                    return all_metrics
                else:
                    logger.info("No metrics data returned from Datadog batch query")
                    return self._get_mock_metrics()
            else:
                logger.warning(f"Datadog batch API error {response.status_code}, falling back to mock data")
                return self._get_mock_metrics()
                
        except Exception as e:
            logger.error(f"Error fetching metrics from Datadog batch query: {e}, falling back to mock data")
            return self._get_mock_metrics()
    
    def _transform_metrics(self, name: str, unit: str, series: List[Dict[str, Any]], fetch_historical: bool = False) -> List[Metric]:
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
                        timestamp = datetime.fromtimestamp(point[0] / 1000, tz=timezone.utc)
                        value = float(point[1])
                        
                        metrics.append(Metric(
                            timestamp=timestamp,
                            name=name,
                            value=value,
                            unit=unit
                        ))
            else:
                # Return only the latest (most recent) data point
                latest_point = pointlist[-1]  # Last point is most recent due to sorting
                if len(latest_point) >= 2 and latest_point[1] is not None:
                    timestamp = datetime.fromtimestamp(latest_point[0] / 1000, tz=timezone.utc)
                    value = float(latest_point[1])
                    
                    metrics.append(Metric(
                        timestamp=timestamp,
                        name=name,
                        value=value,
                        unit=unit
                    ))
        
        return metrics
    
    def _deduplicate_latest_metrics(self, metrics: List[Metric]) -> List[Metric]:
        """Keep only the latest (most recent) metric for each metric name."""
        latest_metrics = {}
        
        for metric in metrics:
            metric_name = metric.name
            
            # If we haven't seen this metric before, or this one is more recent
            if (metric_name not in latest_metrics or 
                metric.timestamp > latest_metrics[metric_name].timestamp):
                latest_metrics[metric_name] = metric
        
        # Return as list, sorted by metric name for consistency
        return sorted(latest_metrics.values(), key=lambda m: m.name)
    
    def _get_mock_metrics(self) -> List[Metric]:
        """Generate mock metrics when Datadog is unavailable."""
        import random
        
        mock_metrics = []
        now = datetime.now(timezone.utc)
        
        # Generate ONE mock data point per metric type (latest value only)
        for metric_name, unit in self.metrics:
            # Generate realistic values based on metric type
            if "percent" in unit or "rate" in metric_name:
                value = round(random.uniform(10, 90), 2)
            elif "count" in unit:
                value = random.randint(1, 100)
            elif "bytes" in unit:
                value = random.randint(1000, 10000)
            elif "milliseconds" in unit:
                value = round(random.uniform(50, 500), 2)
            else:
                value = round(random.uniform(10, 100), 2)
            
            mock_metrics.append(Metric(
                timestamp=now,  # All use current timestamp as "latest"
                name=metric_name,
                value=value,
                unit=unit
            ))
        
        return mock_metrics
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()