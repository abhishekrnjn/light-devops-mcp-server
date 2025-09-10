import random
from datetime import datetime, timedelta, timezone

from app.domain.entities.log_entry import LogEntry


class LogsClient:
    async def fetch_logs(self) -> list[LogEntry]:
        levels = ["INFO", "WARNING", "ERROR"]
        now = datetime.now(timezone.utc)
        return [
            LogEntry(
                timestamp=now - timedelta(minutes=i),
                level=random.choice(levels),
                message=f"Mock log message {i}",
            )
            for i in range(5)
        ]
