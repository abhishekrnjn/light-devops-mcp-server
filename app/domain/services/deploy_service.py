from app.infrastructure.cicd.cicd_client import CICDClient

class DeployService:
    def __init__(self, client: CICDClient):
        self.client = client

    async def deploy(self, service_name: str, version: str, environment: str):
        deployment = await self.client.deploy_service(service_name, version, environment)
        # business rule: validate environment (as example)
        if environment not in ["dev", "staging", "prod"]:
            raise ValueError("Invalid environment")
        return deployment
    
    async def get_recent_deployments(self):
        deployments = await self.client.get_deployments()
        # business rule: only show successful deployments (as example)
        return [dep for dep in deployments if dep.status == "SUCCESS"]
