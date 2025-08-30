from app.infrastructure.metrics.metrics_client import MetricsClient

class MetricsService:
    def __init__(self, client: MetricsClient):
        self.client = client

    async def get_recent_metrics(self):
        metrics = await self.client.fetch_metrics()
        # business rule: only show metrics above 50% (as example)
        return [metric for metric in metrics if metric.value > 50.0]
