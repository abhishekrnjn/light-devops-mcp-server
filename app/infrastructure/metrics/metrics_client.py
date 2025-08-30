import random
from datetime import datetime, timedelta
from app.domain.entities.metric import Metric

class MetricsClient:
    async def fetch_metrics(self) -> list[Metric]:
        metrics = ["cpu_usage", "memory_usage", "disk_usage", "network_io"]
        now = datetime.utcnow()
        return [
            Metric(
                timestamp=now - timedelta(minutes=i),
                name=random.choice(metrics),
                value=round(random.uniform(0, 100), 2),
                unit="percent"
            )
            for i in range(5)
        ]
