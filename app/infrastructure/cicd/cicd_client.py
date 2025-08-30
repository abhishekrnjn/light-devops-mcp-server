import uuid
from datetime import datetime
from app.domain.entities.deployment import Deployment

class CICDClient:
    async def deploy_service(self, service_name: str, version: str, environment: str) -> Deployment:
        # Mock deployment
        return Deployment(
            deployment_id=str(uuid.uuid4()),
            service_name=service_name,
            version=version,
            environment=environment,
            status="SUCCESS",
            timestamp=datetime.utcnow()
        )
    
    async def get_deployments(self) -> list[Deployment]:
        # Mock recent deployments
        services = ["api-service", "web-service", "worker-service"]
        environments = ["dev", "staging", "prod"]
        statuses = ["SUCCESS", "FAILED", "IN_PROGRESS"]
        
        return [
            Deployment(
                deployment_id=str(uuid.uuid4()),
                service_name=f"{services[i % len(services)]}",
                version=f"v1.{i}",
                environment=environments[i % len(environments)],
                status=statuses[i % len(statuses)],
                timestamp=datetime.utcnow()
            )
            for i in range(3)
        ]
