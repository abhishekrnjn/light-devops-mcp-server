from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class DeployRequest(BaseModel):
    service_name: str
    version: str
    environment: str

class DeployResponse(BaseModel):
    deployment_id: str
    service_name: str
    version: str
    environment: str
    status: str
    timestamp: datetime
