"""
MCP Service for handling MCP operations.

This service provides a unified interface for MCP operations,
abstracting away the complexity of gateway routing.
"""

import logging
from typing import Any, Dict, Optional

from app.infrastructure.gateway.router_factory import RouterFactory
from app.schemas.auth import UserPrincipal

logger = logging.getLogger(__name__)


class MCPResourceService:
    """
    Service for handling MCP resource operations.
    
    This service provides methods for reading MCP resources (logs, metrics)
    through the appropriate gateway router.
    """

    def __init__(self):
        """Initialize the MCP resource service."""
        self.router = RouterFactory.get_router()

    async def get_logs(
        self,
        headers: Dict[str, str],
        user: UserPrincipal,
        level: Optional[str] = None,
        limit: int = 100,
        since: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get system logs.
        
        Args:
            headers: HTTP headers from the request
            user: Authenticated user principal
            level: Optional log level filter
            limit: Maximum number of logs to return
            since: Optional timestamp filter
            
        Returns:
            Dictionary containing logs data
        """
        try:
            return await self.router.get_logs(
                headers=headers, user=user, level=level, limit=limit, since=since
            )
        except Exception as e:
            logger.error(f"❌ Error in MCP resource service getting logs: {e}")
            # Fallback to direct mode if Cequence fails
            if RouterFactory.get_router_type() == "cequence":
                logger.info("🔄 Falling back to direct mode for logs")
                from app.infrastructure.gateway.direct_router import DirectRouter
                direct_router = DirectRouter()
                return await direct_router.get_logs(
                    headers=headers, user=user, level=level, limit=limit, since=since
                )
            raise

    async def get_metrics(
        self,
        headers: Dict[str, str],
        user: UserPrincipal,
        limit: int = 50,
        service: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get system metrics.
        
        Args:
            headers: HTTP headers from the request
            user: Authenticated user principal
            limit: Maximum number of metrics to return
            service: Optional service filter
            
        Returns:
            Dictionary containing metrics data
        """
        try:
            return await self.router.get_metrics(
                headers=headers, user=user, limit=limit, service=service
            )
        except Exception as e:
            logger.error(f"❌ Error in MCP resource service getting metrics: {e}")
            # Fallback to direct mode if Cequence fails
            if RouterFactory.get_router_type() == "cequence":
                logger.info("🔄 Falling back to direct mode for metrics")
                from app.infrastructure.gateway.direct_router import DirectRouter
                direct_router = DirectRouter()
                return await direct_router.get_metrics(
                    headers=headers, user=user, limit=limit, service=service
                )
            raise


class MCPToolService:
    """
    Service for handling MCP tool operations.
    
    This service provides methods for executing MCP tools (deploy, rollback, auth)
    through the appropriate gateway router.
    """

    def __init__(self):
        """Initialize the MCP tool service."""
        self.router = RouterFactory.get_router()

    async def deploy_service(
        self,
        headers: Dict[str, str],
        user: UserPrincipal,
        service_name: str,
        version: str,
        environment: str,
    ) -> Dict[str, Any]:
        """
        Deploy a service.
        
        Args:
            headers: HTTP headers from the request
            user: Authenticated user principal
            service_name: Name of the service to deploy
            version: Version to deploy
            environment: Target environment
            
        Returns:
            Dictionary containing deployment result
        """
        try:
            return await self.router.deploy_service(
                headers=headers,
                user=user,
                service_name=service_name,
                version=version,
                environment=environment,
            )
        except Exception as e:
            logger.error(f"❌ Error in MCP tool service deploying service: {e}")
            # Fallback to direct mode if Cequence fails
            if RouterFactory.get_router_type() == "cequence":
                logger.info("🔄 Falling back to direct mode for deploy service")
                from app.infrastructure.gateway.direct_router import DirectRouter
                direct_router = DirectRouter()
                return await direct_router.deploy_service(
                    headers=headers,
                    user=user,
                    service_name=service_name,
                    version=version,
                    environment=environment,
                )
            raise

    async def rollback_deployment(
        self,
        headers: Dict[str, str],
        user: UserPrincipal,
        deployment_id: str,
        reason: str,
        environment: str,
    ) -> Dict[str, Any]:
        """
        Rollback a deployment.
        
        Args:
            headers: HTTP headers from the request
            user: Authenticated user principal
            deployment_id: ID of the deployment to rollback
            reason: Reason for the rollback
            environment: Environment to rollback
            
        Returns:
            Dictionary containing rollback result
        """
        try:
            return await self.router.rollback_deployment(
                headers=headers,
                user=user,
                deployment_id=deployment_id,
                reason=reason,
                environment=environment,
            )
        except Exception as e:
            logger.error(f"❌ Error in MCP tool service rolling back deployment: {e}")
            # Fallback to direct mode if Cequence fails
            if RouterFactory.get_router_type() == "cequence":
                logger.info("🔄 Falling back to direct mode for rollback deployment")
                from app.infrastructure.gateway.direct_router import DirectRouter
                direct_router = DirectRouter()
                return await direct_router.rollback_deployment(
                    headers=headers,
                    user=user,
                    deployment_id=deployment_id,
                    reason=reason,
                    environment=environment,
                )
            raise

    async def authenticate_user(
        self,
        headers: Dict[str, str],
        user: UserPrincipal,
        session_token: str,
        refresh_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Authenticate user.
        
        Args:
            headers: HTTP headers from the request
            user: Authenticated user principal
            session_token: Descope session token
            refresh_token: Optional refresh token
            
        Returns:
            Dictionary containing authentication result
        """
        try:
            return await self.router.authenticate_user(
                headers=headers,
                user=user,
                session_token=session_token,
                refresh_token=refresh_token,
            )
        except Exception as e:
            logger.error(f"❌ Error in MCP tool service authenticating user: {e}")
            # Fallback to direct mode if Cequence fails
            if RouterFactory.get_router_type() == "cequence":
                logger.info("🔄 Falling back to direct mode for authenticate user")
                from app.infrastructure.gateway.direct_router import DirectRouter
                direct_router = DirectRouter()
                return await direct_router.authenticate_user(
                    headers=headers,
                    user=user,
                    session_token=session_token,
                    refresh_token=refresh_token,
                )
            raise
