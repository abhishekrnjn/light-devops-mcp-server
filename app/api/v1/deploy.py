from fastapi import APIRouter, Depends
from typing import List
from app.schemas.deploy import DeployRequest, DeployResponse
from app.domain.services.deploy_service import DeployService
from app.infrastructure.cicd.cicd_client import CICDClient

router = APIRouter()

def get_deploy_service() -> DeployService:
    return DeployService(client=CICDClient())

@router.post("/deploy", response_model=DeployResponse)
async def deploy_service(
    request: DeployRequest,
    service: DeployService = Depends(get_deploy_service)
):
    return await service.deploy(request.service_name, request.version, request.environment)

@router.get("/deployments", response_model=List[DeployResponse])
async def get_deployments(service: DeployService = Depends(get_deploy_service)):
    return await service.get_recent_deployments()
