from typing import Tuple, Dict, Any
from app.infrastructure.cicd.cicd_client import CICDClient
from app.domain.entities.deployment import Deployment

class DeployService:
    def __init__(self, client: CICDClient):
        self.client = client

    async def deploy(self, service_name: str, version: str, environment: str) -> Tuple[Deployment, int, Dict[str, Any]]:
        # business rule: validate environment (as example)
        if environment not in ["dev", "staging", "prod", "production"]:
            raise ValueError("Invalid environment")
        
        deployment, http_status, json_response = await self.client.deploy_service(service_name, version, environment)
        return deployment, http_status, json_response
    
    async def get_recent_deployments(self) -> Tuple[list[Deployment], int, Dict[str, Any]]:
        deployments, http_status, json_response = await self.client.get_deployments()
        # business rule: only show successful deployments (as example)
        successful_deployments = [dep for dep in deployments if dep.status == "SUCCESS"]
        
        # Update JSON response to reflect filtered results
        json_response["deployments"] = [dep.dict() for dep in successful_deployments]
        json_response["count"] = len(successful_deployments)
        json_response["message"] = f"Retrieved {len(successful_deployments)} successful deployments"
        json_response["metadata"]["total_deployments"] = len(successful_deployments)
        json_response["metadata"]["status_summary"]["success"] = len(successful_deployments)
        json_response["metadata"]["status_summary"]["failed"] = 0
        json_response["metadata"]["status_summary"]["in_progress"] = 0
        
        return successful_deployments, http_status, json_response
