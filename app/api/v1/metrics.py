from fastapi import APIRouter, Depends
from typing import List
from app.schemas.metrics import MetricResponse
from app.domain.services.metrics_service import MetricsService
from app.infrastructure.metrics.metrics_client import MetricsClient
from app.api.deps.auth_deps import require_scopes

router = APIRouter()

def get_metrics_service() -> MetricsService:
    return MetricsService(client=MetricsClient())

@router.get(
    "/metrics",
    response_model=List[MetricResponse],
    dependencies=[Depends(require_scopes(["metrics:read"]))]
)
async def get_metrics(service: MetricsService = Depends(get_metrics_service)):
    return await service.get_recent_metrics()
