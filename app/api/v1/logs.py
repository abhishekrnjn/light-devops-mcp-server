from fastapi import APIRouter, Depends
from typing import List
from app.schemas.logs import LogResponse
from app.dependencies import require_permissions, get_log_service

router = APIRouter()

@router.get(
    "/logs",
    response_model=List[LogResponse],
    dependencies=[Depends(require_permissions(["read_logs"]))]
)
async def get_logs(service = Depends(get_log_service)):
    """Get system logs - requires 'read_logs' permission."""
    return await service.get_recent_logs()
