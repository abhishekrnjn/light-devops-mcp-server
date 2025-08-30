from datetime import datetime
from pydantic import BaseModel

class Rollback(BaseModel):
    rollback_id: str
    deployment_id: str
    status: str
    reason: str
    timestamp: datetime
