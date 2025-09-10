"""Log Aggregation Entity - Single aggregated response for logs to prevent multiple API calls."""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime

@dataclass
class LogAggregation:
    """Single aggregated response for log entries to prevent Cequence from making multiple calls."""
    
    summary: str
    total_count: int
    level_filter: Optional[str]
    time_range: str
    entries_preview: str
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
            "level_filter": self.level_filter,
            "time_range": self.time_range,
            "entries_preview": self.entries_preview,
            "filters_applied": self.filters_applied,
            "source": self.source,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
