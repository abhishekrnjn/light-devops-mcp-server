from app.infrastructure.logs.logs_client import LogsClient

class LogService:
    def __init__(self, client: LogsClient):
        self.client = client

    async def get_recent_logs(self):
        logs = await self.client.fetch_logs()
        # business rule: only show ERROR logs (as example)
        return [log for log in logs if log.level == "ERROR"]
