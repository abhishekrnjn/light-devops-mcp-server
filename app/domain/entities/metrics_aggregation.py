"""Metrics Aggregation Entity - Single aggregated response for metrics to prevent multiple API calls."""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass
class MetricsAggregation:
    """Single aggregated response for metric entries to prevent Cequence from making multiple calls."""
    
    summary: str
    total_count: int
    service_filter: Optional[str]
    time_range: str
    metrics_preview: str
    filters_applied: Dict[str, Any]
    source: str = "datadog"
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "summary": self.summary,
            "total_count": self.total_count,
            "service_filter": self.service_filter,
            "time_range": self.time_range,
            "metrics_preview": self.metrics_preview,
            "filters_applied": self.filters_applied,
            "source": self.source,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
