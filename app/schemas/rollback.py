from datetime import datetime
from pydantic import BaseModel

class RollbackRequest(BaseModel):
    deployment_id: str
    reason: str

class RollbackResponse(BaseModel):
    rollback_id: str
    deployment_id: str
    status: str
    reason: str
    timestamp: datetime
