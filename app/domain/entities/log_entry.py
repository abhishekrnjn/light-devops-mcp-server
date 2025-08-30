from datetime import datetime
from pydantic import BaseModel

class LogEntry(BaseModel):
    timestamp: datetime
    level: str
    message: str
