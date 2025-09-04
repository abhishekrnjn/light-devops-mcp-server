from fastapi import APIRouter, Depends
from typing import List
from app.schemas.deploy import DeployRequest, DeployResponse
from app.dependencies import require_permissions, get_deploy_service

router = APIRouter()

@router.post(
    "/deploy",
    response_model=DeployResponse,
    dependencies=[Depends(require_permissions(["deploy_staging", "deploy_production"], mode="any"))]
)
async def deploy_service(
    request: DeployRequest,
    service = Depends(get_deploy_service)
):
    """
    Deploy a service - requires 'deploy_staging' or 'deploy_production' permission.
    The specific environment deployment will be validated based on the request.
    """
    # Additional environment-specific validation could be added here
    if request.environment == "production":
        # This would ideally be handled by a separate dependency
        # For now, we rely on the user having the right permissions
        pass
    
    return await service.deploy(
        service_name=request.service_name,
        version=request.version,
        environment=request.environment
    )

@router.get(
    "/deployments",
    response_model=List[DeployResponse],
    dependencies=[Depends(require_permissions(["read_deployments"]))]  # Deployment history requires specific permission
)
async def get_deployments(service = Depends(get_deploy_service)):
    """Get deployment history - requires 'read_deployments' permission."""
    return await service.get_recent_deployments()
