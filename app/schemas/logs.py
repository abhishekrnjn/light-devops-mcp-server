from datetime import datetime
from pydantic import BaseModel

class LogResponse(BaseModel):
    timestamp: datetime
    level: str
    message: str
