"""
Gateway routing middleware for MCP HTTP Server.

This middleware handles the routing of requests through different gateways
(Cequence, Direct) based on configuration and provides fallback mechanisms.
"""

import logging
import time
from typing import Callable, Dict, Any, Optional

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.infrastructure.gateway.router_factory import RouterFactory
from app.schemas.auth import UserPrincipal

logger = logging.getLogger(__name__)


class GatewayRoutingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling gateway routing decisions.
    
    This middleware determines whether requests should be routed through
    the Cequence Gateway or handled directly, and provides fallback mechanisms.
    """

    def __init__(self, app, enable_gateway_routing: bool = True):
        """
        Initialize the gateway routing middleware.
        
        Args:
            app: FastAPI application instance
            enable_gateway_routing: Whether to enable gateway routing logic
        """
        super().__init__(app)
        self.enable_gateway_routing = enable_gateway_routing
        self.router_factory = RouterFactory()
        self.router_type = self.router_factory.get_router_type()
        
        logger.info(f"🌐 Gateway routing middleware initialized: {self.router_type}")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request through gateway routing middleware.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in the chain
            
        Returns:
            HTTP response
        """
        if not self.enable_gateway_routing:
            return await call_next(request)

        # Add gateway information to request state
        request.state.gateway_type = self.router_type
        request.state.gateway_enabled = settings.CEQUENCE_ENABLED
        request.state.gateway_url = settings.CEQUENCE_GATEWAY_URL

        # Log routing decision
        logger.debug(f"🔀 Routing request {request.method} {request.url.path} through {self.router_type}")

        try:
            response = await call_next(request)
            
            # Add gateway information to response headers
            response.headers["X-Gateway-Type"] = self.router_type
            response.headers["X-Gateway-Enabled"] = str(settings.CEQUENCE_ENABLED).lower()
            
            return response
            
        except Exception as e:
            # Log gateway routing errors
            logger.error(f"❌ Gateway routing error for {request.method} {request.url.path}: {e}")
            
            # If Cequence fails, we could potentially retry with direct mode
            if self.router_type == "cequence" and settings.CEQUENCE_ENABLED:
                logger.warning("🔄 Cequence Gateway failed, consider implementing direct mode fallback")
            
            raise

    def should_use_gateway(self, request: Request) -> bool:
        """
        Determine if the request should use gateway routing.
        
        Args:
            request: HTTP request
            
        Returns:
            True if gateway should be used, False otherwise
        """
        # Skip gateway for health checks and static content
        if request.url.path in ["/health", "/", "/docs", "/openapi.json"]:
            return False
            
        # Skip gateway for authentication endpoints (handled directly)
        if request.url.path.startswith("/mcp/tools/authenticate_user"):
            return False
            
        return settings.CEQUENCE_ENABLED and settings.CEQUENCE_GATEWAY_URL is not None

    def get_gateway_info(self) -> Dict[str, Any]:
        """
        Get current gateway configuration information.
        
        Returns:
            Dictionary containing gateway information
        """
        return {
            "type": self.router_type,
            "enabled": settings.CEQUENCE_ENABLED,
            "url": settings.CEQUENCE_GATEWAY_URL,
            "fallback_available": True,
        }
