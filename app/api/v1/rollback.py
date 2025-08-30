from fastapi import APIRouter, Depends
from typing import List
from app.schemas.rollback import RollbackRequest, RollbackResponse
from app.domain.services.rollback_service import RollbackService
from app.infrastructure.rollback.rollback_client import RollbackClient

router = APIRouter()

def get_rollback_service() -> RollbackService:
    return RollbackService(client=RollbackClient())

@router.post("/rollback", response_model=RollbackResponse)
async def rollback_deployment(
    request: RollbackRequest,
    service: RollbackService = Depends(get_rollback_service)
):
    return await service.rollback(request.deployment_id, request.reason)

@router.get("/rollbacks", response_model=List[RollbackResponse])
async def get_rollbacks(service: RollbackService = Depends(get_rollback_service)):
    return await service.get_recent_rollbacks()
