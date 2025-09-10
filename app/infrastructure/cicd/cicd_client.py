import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from app.domain.entities.deployment import Deployment


class CICDClient:
    async def deploy_service(
        self, service_name: str, version: str, environment: str
    ) -> Tuple[Deployment, int, Dict[str, Any]]:
        """Deploy service with different responses based on request parameters."""

        # Simulate different scenarios based on service name and environment
        deployment_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)

        # Different statuses based on service name patterns
        if "test" in service_name.lower() or "demo" in service_name.lower():
            status = "SUCCESS"  # Test services always succeed
            http_status = 200
        elif "critical" in service_name.lower() or "core" in service_name.lower():
            # Critical services have higher chance of failure in production
            if environment == "production":
                status = random.choices(["SUCCESS", "FAILED"], weights=[70, 30])[0]
                http_status = 200 if status == "SUCCESS" else 500
            else:
                status = "SUCCESS"
                http_status = 200
        elif "experimental" in service_name.lower() or "beta" in service_name.lower():
            # Experimental services have higher failure rate
            status = random.choices(
                ["SUCCESS", "FAILED", "IN_PROGRESS"], weights=[60, 30, 10]
            )[0]
            if status == "IN_PROGRESS":
                http_status = 202  # Accepted - processing
            elif status == "FAILED":
                http_status = 500  # Internal Server Error
            else:
                http_status = 200  # Success
        else:
            # Default behavior - mostly successful
            status = random.choices(["SUCCESS", "FAILED"], weights=[85, 15])[0]
            http_status = 200 if status == "SUCCESS" else 500

        # Environment-specific behavior
        if environment == "production":
            # Production deployments take longer and have more validation
            if status == "IN_PROGRESS":
                status = "SUCCESS"  # Override for production
                http_status = 200
        elif environment == "staging":
            # Staging has some chance of being in progress
            if status == "FAILED":
                status = random.choices(["SUCCESS", "IN_PROGRESS"], weights=[80, 20])[0]
                if status == "IN_PROGRESS":
                    http_status = 202
                else:
                    http_status = 200

        # Create deployment object
        deployment = Deployment(
            deployment_id=deployment_id,
            service_name=service_name,
            version=version,
            environment=environment,
            status=status,
            timestamp=timestamp,
        )

        # Create JSON response
        json_response = {
            "success": status in ["SUCCESS", "IN_PROGRESS"],
            "deployment": deployment.dict(),
            "message": self._get_deployment_message(status, service_name, environment),
            "metadata": {
                "deployment_id": deployment_id,
                "timestamp": timestamp.isoformat(),
                "environment": environment,
                "service_type": self._get_service_type(service_name),
            },
        }

        return deployment, http_status, json_response

    def _get_deployment_message(
        self, status: str, service_name: str, environment: str
    ) -> str:
        """Generate appropriate message based on deployment status."""
        if status == "SUCCESS":
            return f"✅ Successfully deployed {service_name} v{service_name} to {environment}"
        elif status == "FAILED":
            return f"❌ Failed to deploy {service_name} to {environment}. Check logs for details."
        elif status == "IN_PROGRESS":
            return f"⏳ Deployment of {service_name} to {environment} is in progress..."
        else:
            return f"🔄 Deployment status for {service_name} in {environment}: {status}"

    def _get_service_type(self, service_name: str) -> str:
        """Determine service type based on name patterns."""
        name_lower = service_name.lower()
        if "test" in name_lower or "demo" in name_lower:
            return "test"
        elif "critical" in name_lower or "core" in name_lower:
            return "critical"
        elif "experimental" in name_lower or "beta" in name_lower:
            return "experimental"
        else:
            return "standard"

    async def get_deployments(self) -> Tuple[list[Deployment], int, Dict[str, Any]]:
        """Get recent deployments with varied realistic data."""
        # More diverse service names and scenarios
        services = [
            "api-service",
            "web-service",
            "worker-service",
            "auth-service",
            "payment-service",
            "notification-service",
            "test-service",
            "critical-core-service",
            "experimental-beta-service",
            "demo-service",
        ]
        environments = ["dev", "staging", "production"]

        deployments = []
        base_time = datetime.now(timezone.utc)

        for i in range(8):  # More deployments for better variety
            service = services[i % len(services)]
            environment = environments[i % len(environments)]

            # Apply same logic as deploy_service for consistency
            if "test" in service.lower() or "demo" in service.lower():
                status = "SUCCESS"
            elif "critical" in service.lower() or "core" in service.lower():
                if environment == "production":
                    status = random.choices(["SUCCESS", "FAILED"], weights=[70, 30])[0]
                else:
                    status = "SUCCESS"
            elif "experimental" in service.lower() or "beta" in service.lower():
                status = random.choices(
                    ["SUCCESS", "FAILED", "IN_PROGRESS"], weights=[60, 30, 10]
                )[0]
            else:
                status = random.choices(["SUCCESS", "FAILED"], weights=[85, 15])[0]

            # Add time variation (more recent deployments first)
            time_offset = i * 2  # 2 hours between deployments
            timestamp = base_time.replace(hour=(base_time.hour - time_offset) % 24)

            deployments.append(
                Deployment(
                    deployment_id=str(uuid.uuid4()),
                    service_name=service,
                    version=f"v{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
                    environment=environment,
                    status=status,
                    timestamp=timestamp,
                )
            )

        # Sort by timestamp (most recent first)
        sorted_deployments = sorted(
            deployments, key=lambda x: x.timestamp, reverse=True
        )

        # Create JSON response
        json_response = {
            "success": True,
            "deployments": [deployment.dict() for deployment in sorted_deployments],
            "count": len(sorted_deployments),
            "message": f"Retrieved {len(sorted_deployments)} recent deployments",
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_deployments": len(sorted_deployments),
                "environments": list(
                    set(dep.environment for dep in sorted_deployments)
                ),
                "status_summary": {
                    "success": len(
                        [d for d in sorted_deployments if d.status == "SUCCESS"]
                    ),
                    "failed": len(
                        [d for d in sorted_deployments if d.status == "FAILED"]
                    ),
                    "in_progress": len(
                        [d for d in sorted_deployments if d.status == "IN_PROGRESS"]
                    ),
                },
            },
        }

        return sorted_deployments, 200, json_response
