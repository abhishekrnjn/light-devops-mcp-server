from datetime import datetime
from pydantic import BaseModel

class Deployment(BaseModel):
    deployment_id: str
    service_name: str
    version: str
    environment: str
    status: str
    timestamp: datetime
