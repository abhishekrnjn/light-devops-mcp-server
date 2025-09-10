"""
Abstract base class for gateway routing strategies.

This module defines the interface that all gateway routers must implement,
providing a consistent way to route requests through different gateways.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.schemas.auth import UserPrincipal

logger = logging.getLogger(__name__)


class GatewayRouter(ABC):
    """
    Abstract base class for gateway routing strategies.
    
    All gateway routers must implement these methods to provide
    a consistent interface for routing requests.
    """

    @abstractmethod
    async def get_logs(
        self,
        headers: Dict[str, str],
        user: UserPrincipal,
        level: Optional[str] = None,
        limit: int = 100,
        since: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get system logs through the gateway.
        
        Args:
            headers: HTTP headers from the request
            user: Authenticated user principal
            level: Optional log level filter
            limit: Maximum number of logs to return
            since: Optional timestamp filter
            
        Returns:
            Dictionary containing logs data
        """
        pass

    @abstractmethod
    async def get_metrics(
        self,
        headers: Dict[str, str],
        user: UserPrincipal,
        limit: int = 50,
        service: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get system metrics through the gateway.
        
        Args:
            headers: HTTP headers from the request
            user: Authenticated user principal
            limit: Maximum number of metrics to return
            service: Optional service filter
            
        Returns:
            Dictionary containing metrics data
        """
        pass

    @abstractmethod
    async def deploy_service(
        self,
        headers: Dict[str, str],
        user: UserPrincipal,
        service_name: str,
        version: str,
        environment: str,
    ) -> Dict[str, Any]:
        """
        Deploy a service through the gateway.
        
        Args:
            headers: HTTP headers from the request
            user: Authenticated user principal
            service_name: Name of the service to deploy
            version: Version to deploy
            environment: Target environment
            
        Returns:
            Dictionary containing deployment result
        """
        pass

    @abstractmethod
    async def rollback_deployment(
        self,
        headers: Dict[str, str],
        user: UserPrincipal,
        deployment_id: str,
        reason: str,
        environment: str,
    ) -> Dict[str, Any]:
        """
        Rollback a deployment through the gateway.
        
        Args:
            headers: HTTP headers from the request
            user: Authenticated user principal
            deployment_id: ID of the deployment to rollback
            reason: Reason for the rollback
            environment: Environment to rollback
            
        Returns:
            Dictionary containing rollback result
        """
        pass

    @abstractmethod
    async def authenticate_user(
        self,
        headers: Dict[str, str],
        user: UserPrincipal,
        session_token: str,
        refresh_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Authenticate user through the gateway.
        
        Args:
            headers: HTTP headers from the request
            user: Authenticated user principal
            session_token: Descope session token
            refresh_token: Optional refresh token
            
        Returns:
            Dictionary containing authentication result
        """
        pass

    def check_permission(
        self, user: UserPrincipal, permission: str, resource: str = None
    ) -> None:
        """
        Check if user has required permission.
        
        Args:
            user: User principal to check
            permission: Required permission
            resource: Optional resource description
            
        Raises:
            HTTPException: If user doesn't have permission
        """
        from fastapi import HTTPException
        
        if permission not in user.permissions:
            detail = f"Insufficient permissions to {resource or permission}"
            raise HTTPException(status_code=403, detail=detail)

    def validate_tool_arguments(
        self, arguments: Dict[str, Any], required_params: List[str]
    ) -> None:
        """
        Validate that all required parameters are present.
        
        Args:
            arguments: Tool arguments to validate
            required_params: List of required parameter names
            
        Raises:
            HTTPException: If required parameters are missing
        """
        from fastapi import HTTPException
        
        missing = [param for param in required_params if not arguments.get(param)]
        if missing:
            raise HTTPException(
                status_code=400, detail=f"Missing required parameters: {', '.join(missing)}"
            )
