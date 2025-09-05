from fastapi import APIRouter, Depends
from typing import List
from app.schemas.rollback import RollbackRequest, RollbackResponse
from app.dependencies import require_permissions, get_rollback_service

router = APIRouter()

@router.post(
    "/rollback",
    response_model=RollbackResponse,
    dependencies=[Depends(require_permissions(["rollback_write"]))]
)
async def rollback_deployment(
    request: RollbackRequest,
    service = Depends(get_rollback_service)
):
    """Rollback a deployment - requires 'rollback_write' permission."""
    return await service.rollback(request.deployment_id, request.reason)

@router.get(
    "/rollbacks",
    response_model=List[RollbackResponse],
    dependencies=[Depends(require_permissions(["read_rollbacks"]))]  # Rollback history uses logs permission
)
async def get_rollbacks(service = Depends(get_rollback_service)):
    """Get rollback history - requires 'read_rollbacks' permission."""
    return await service.get_recent_rollbacks()
