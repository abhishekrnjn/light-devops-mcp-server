"""
Direct mode router implementation.

This module implements the GatewayRouter interface for direct service calls
without going through any external gateway.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from app.domain.services.deploy_service import DeployService
from app.domain.services.log_service import LogService
from app.domain.services.metrics_service import MetricsService
from app.domain.services.rollback_service import RollbackService
from app.infrastructure.auth.descope_client import descope_client
from app.infrastructure.cicd.cicd_client import CICDClient
from app.infrastructure.gateway.gateway_router import GatewayRouter
from app.infrastructure.rollback.rollback_client import RollbackClient
from app.schemas.auth import UserPrincipal

logger = logging.getLogger(__name__)


class DirectRouter(GatewayRouter):
    """
    Router implementation for direct service calls.
    
    Routes all requests directly to the appropriate services without
    going through any external gateway.
    """

    def __init__(self):
        """Initialize the direct router with service dependencies."""
        self.log_service = LogService()
        self.metrics_service = MetricsService()
        self.deploy_service = DeployService(CICDClient())
        self.rollback_service = RollbackService(RollbackClient())

    async def get_logs(
        self,
        headers: Dict[str, str],
        user: UserPrincipal,
        level: Optional[str] = None,
        limit: int = 100,
        since: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get logs directly from the log service."""
        logger.info("📖 Reading logs resource (direct mode)")
        
        # Check permissions
        self.check_permission(user, "read_logs", "read logs")
        
        try:
            logs = await self.log_service.get_recent_logs(
                user_permissions=user.permissions, level=level, limit=limit
            )

            # Apply limit
            logs = logs[:limit]

            return {
                "uri": "logs",
                "type": "logs",
                "count": len(logs),
                "filters": {"level": level, "limit": limit},
                "data": [
                    {
                        "level": log.level,
                        "message": log.message,
                        "timestamp": log.timestamp,
                        "source": getattr(log, "source", "system"),
                    }
                    for log in logs
                ],
            }
        except Exception as e:
            logger.error(f"❌ Error reading logs: {e}")
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=str(e))

    async def get_metrics(
        self,
        headers: Dict[str, str],
        user: UserPrincipal,
        limit: int = 50,
        service: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get metrics directly from the metrics service."""
        logger.info("📖 Reading metrics resource (direct mode)")
        
        # Check permissions
        self.check_permission(user, "read_metrics", "read metrics")
        
        try:
            metrics = await self.metrics_service.get_recent_metrics(
                user_permissions=user.permissions, limit=limit
            )

            # Apply limit
            metrics = metrics[:limit]

            return {
                "uri": "metrics",
                "type": "metrics",
                "count": len(metrics),
                "filters": {"limit": limit},
                "data": [
                    {
                        "name": metric.name,
                        "value": metric.value,
                        "unit": metric.unit,
                        "timestamp": getattr(
                            metric, "timestamp", datetime.now().isoformat()
                        ),
                    }
                    for metric in metrics
                ],
            }
        except Exception as e:
            logger.error(f"❌ Error reading metrics: {e}")
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=str(e))

    async def deploy_service(
        self,
        headers: Dict[str, str],
        user: UserPrincipal,
        service_name: str,
        version: str,
        environment: str,
    ) -> Dict[str, Any]:
        """Deploy service directly through the deploy service."""
        logger.info("🔧 Deploy service (direct mode)")
        
        # Check environment-specific permissions
        if environment == "production":
            self.check_permission(user, "deploy_production", "deploy to production")
        elif environment == "staging":
            self.check_permission(user, "deploy_staging", "deploy to staging")
        
        try:
            # Perform deployment
            deployment, http_status, json_response = await self.deploy_service.deploy(
                service_name, version, environment
            )

            return {"tool": "deploy_service", "success": True, "result": json_response}
        except Exception as e:
            logger.error(f"❌ Error executing deploy_service: {e}")
            return {"tool": "deploy_service", "success": False, "error": str(e)}

    async def rollback_deployment(
        self,
        headers: Dict[str, str],
        user: UserPrincipal,
        deployment_id: str,
        reason: str,
        environment: str,
    ) -> Dict[str, Any]:
        """Rollback deployment directly through the rollback service."""
        logger.info("🔧 Rollback deployment (direct mode)")
        
        # Check environment-specific permissions
        if environment == "production":
            self.check_permission(user, "rollback_production", "perform production rollbacks")
        elif environment == "staging":
            self.check_permission(user, "rollback_staging", "perform staging rollbacks")
        else:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail="Invalid environment. Must be 'staging' or 'production'",
            )
        
        try:
            # Perform rollback using unified service method
            rollback, http_status, json_response = await self.rollback_service.rollback(
                deployment_id, reason, environment=environment
            )

            return {"tool": "rollback_deployment", "success": True, "result": json_response}
        except Exception as e:
            logger.error(f"❌ Error executing rollback_deployment: {e}")
            return {"tool": "rollback_deployment", "success": False, "error": str(e)}

    async def authenticate_user(
        self,
        headers: Dict[str, str],
        user: UserPrincipal,
        session_token: str,
        refresh_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Authenticate user directly through Descope."""
        logger.info("🔧 Authenticate user (direct mode)")
        
        try:
            # Validate session with Descope
            jwt_response = descope_client.validate_session(
                session_token=session_token, refresh_token=refresh_token
            )

            # Extract user principal
            user_principal = descope_client.extract_user_principal(
                jwt_response, session_token
            )

            return {
                "tool": "authenticate_user",
                "success": True,
                "result": {
                    "user_id": user_principal.user_id,
                    "name": user_principal.name,
                    "email": user_principal.email,
                    "roles": user_principal.roles,
                    "permissions": user_principal.permissions,
                    "tenant": user_principal.tenant,
                },
            }
        except Exception as e:
            return {
                "tool": "authenticate_user",
                "success": False,
                "error": f"Authentication failed: {str(e)}",
            }
