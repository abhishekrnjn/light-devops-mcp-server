from fastapi import APIRouter, Depends
from typing import List
from app.schemas.logs import LogResponse
from app.domain.services.log_service import LogService
from app.infrastructure.logs.logs_client import LogsClient
from app.api.deps.auth_deps import require_scopes

router = APIRouter()

def get_log_service() -> LogService:
    return LogService(client=LogsClient())

@router.get(
    "/logs",
    response_model=List[LogResponse],
    dependencies=[Depends(require_scopes(["logs:read"]))]
)
async def get_logs(service: LogService = Depends(get_log_service)):
    return await service.get_recent_logs()
