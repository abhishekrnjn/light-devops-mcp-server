from fastapi import APIRouter, Depends
from typing import List
from app.schemas.metrics import MetricResponse
from app.dependencies import require_permissions, get_metrics_service

router = APIRouter()

@router.get(
    "/metrics",
    response_model=List[MetricResponse],
    dependencies=[Depends(require_permissions(["read_metrics"]))]
)
async def get_metrics(service = Depends(get_metrics_service)):
    """Get system metrics - requires 'read_metrics' permission."""
    return await service.get_recent_metrics()
