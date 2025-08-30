from datetime import datetime
from pydantic import BaseModel

class Metric(BaseModel):
    timestamp: datetime
    name: str
    value: float
    unit: str
