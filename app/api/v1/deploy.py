from fastapi import APIRouter, Depends
from typing import List
from app.schemas.deploy import DeployRequest, DeployResponse
from app.domain.services.deploy_service import DeployService
from app.infrastructure.cicd.cicd_client import CICDClient
from app.api.deps.auth_deps import require_scopes

router = APIRouter()

def get_deploy_service() -> DeployService:
    return DeployService(client=CICDClient())

@router.post(
    "/deploy",
    response_model=DeployResponse,
    dependencies=[Depends(require_scopes(["deploy:write"]))]
)
async def deploy_service(
    request: DeployRequest,
    service: DeployService = Depends(get_deploy_service)
):
    return await service.deploy(
        service_name=request.service_name,
        version=request.version,
        environment=request.environment
    )

@router.get(
    "/deployments",
    response_model=List[DeployResponse],
    dependencies=[Depends(require_scopes(["deploy:read"]))]
)
async def get_deployments(service: DeployService = Depends(get_deploy_service)):
    return await service.get_recent_deployments()
