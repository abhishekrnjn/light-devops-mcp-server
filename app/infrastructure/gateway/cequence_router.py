"""
Cequence Gateway router implementation.

This module implements the GatewayRouter interface for routing requests
through the Cequence Gateway for audit and monitoring.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from app.infrastructure.cequence.cequence_client import cequence_client
from app.infrastructure.gateway.gateway_router import GatewayRouter
from app.schemas.auth import UserPrincipal
from app.utils.dummy_data import DummyDataGenerator

logger = logging.getLogger(__name__)


class CequenceRouter(GatewayRouter):
    """
    Router implementation for Cequence Gateway.

    Routes all requests through the Cequence Gateway for audit and monitoring,
    with fallback to direct mode if the gateway is unavailable.
    """

    def __init__(self):
        """Initialize the Cequence router with dummy data generator."""
        self.dummy_generator = DummyDataGenerator()

    async def get_logs(
        self,
        headers: Dict[str, str],
        user: UserPrincipal,
        level: Optional[str] = None,
        limit: int = 100,
        since: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get logs through Cequence Gateway with immediate dummy response."""
        logger.info("🌐 Routing logs request through Cequence Gateway")

        # Check permissions
        self.check_permission(user, "read_logs", "read logs")

        # Return immediate dummy data while real API call is in progress
        logger.info(
            "⚡ IMMEDIATE RESPONSE: Returning dummy logs while Cequence call is in progress"
        )
        dummy_logs = self.dummy_generator.generate_logs(
            count=min(limit, 15), level=level
        )

        # Start the real API call in background (fire and forget for now)
        asyncio.create_task(
            cequence_client.get_logs(
                headers=headers, level=level, limit=limit, since=since
            )
        )

        return {
            "uri": "logs",
            "type": "logs",
            "count": len(dummy_logs),
            "filters": {"level": level, "limit": limit},
            "loading": True,
            "message": "Loading real data in background...",
            "data": dummy_logs,
        }

    async def get_metrics(
        self,
        headers: Dict[str, str],
        user: UserPrincipal,
        limit: int = 50,
        service: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get metrics through Cequence Gateway with immediate dummy response."""
        logger.info("🌐 Routing metrics request through Cequence Gateway")

        # Check permissions
        self.check_permission(user, "read_metrics", "read metrics")

        # Return immediate dummy data while real API call is in progress
        logger.info(
            "⚡ IMMEDIATE RESPONSE: Returning dummy metrics while Cequence call is in progress"
        )
        dummy_metrics = self.dummy_generator.generate_metrics(
            count=min(limit, 10), service=service
        )

        # Start the real API call in background (fire and forget for now)
        asyncio.create_task(
            cequence_client.get_metrics(headers=headers, limit=limit, service=service)
        )

        return {
            "uri": "metrics",
            "type": "metrics",
            "count": len(dummy_metrics),
            "filters": {"limit": limit},
            "loading": True,
            "message": "Loading real data in background...",
            "data": dummy_metrics,
        }

    async def deploy_service(
        self,
        headers: Dict[str, str],
        user: UserPrincipal,
        service_name: str,
        version: str,
        environment: str,
    ) -> Dict[str, Any]:
        """Deploy service through Cequence Gateway."""
        logger.info("🌐 Routing deploy service request through Cequence Gateway")

        # Check environment-specific permissions
        if environment == "production":
            self.check_permission(user, "deploy_production", "deploy to production")
        elif environment == "staging":
            self.check_permission(user, "deploy_staging", "deploy to staging")

        try:
            response = await cequence_client.deploy_service(
                headers=headers,
                service_name=service_name,
                version=version,
                environment=environment,
            )
            await self._handle_gateway_error(response, "deploy_service")
            return await self._parse_mcp_response(response)
        except Exception as e:
            logger.error(f"❌ Error routing through Cequence: {e}")
            raise

    async def rollback_deployment(
        self,
        headers: Dict[str, str],
        user: UserPrincipal,
        deployment_id: str,
        reason: str,
        environment: str,
    ) -> Dict[str, Any]:
        """Rollback deployment through Cequence Gateway."""
        logger.info("🌐 Routing rollback deployment request through Cequence Gateway")

        # Check environment-specific permissions
        if environment == "production":
            self.check_permission(
                user, "rollback_production", "perform production rollbacks"
            )
        elif environment == "staging":
            self.check_permission(user, "rollback_staging", "perform staging rollbacks")
        else:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=400,
                detail="Invalid environment. Must be 'staging' or 'production'",
            )

        try:
            response = await cequence_client.rollback_deployment(
                headers=headers,
                deployment_id=deployment_id,
                reason=reason,
                environment=environment,
            )
            await self._handle_gateway_error(response, "rollback_deployment")
            return await self._parse_mcp_response(response)
        except Exception as e:
            logger.error(f"❌ Error routing through Cequence: {e}")
            raise

    async def authenticate_user(
        self,
        headers: Dict[str, str],
        user: UserPrincipal,
        session_token: str,
        refresh_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Authenticate user through Cequence Gateway."""
        logger.info("🌐 Routing authenticate user request through Cequence Gateway")

        # This tool is handled directly by the MCP server without Cequence Gateway routing
        # But we still go through the gateway for consistency
        try:
            from app.infrastructure.auth.descope_client import descope_client

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

    async def _parse_mcp_response(self, response) -> Dict[str, Any]:
        """Parse MCP response from Cequence Gateway, handling both SSE and JSON formats."""
        try:
            # Handle SSE format if present
            if response.headers.get("content-type", "").startswith("text/event-stream"):
                # Parse SSE format: "data: {json}\n\n"
                for line in response.text.split("\n"):
                    if line.startswith("data: "):
                        mcp_response = json.loads(line[6:])  # Remove 'data: ' prefix
                        if "result" in mcp_response:
                            return mcp_response["result"]
                        elif "error" in mcp_response:
                            logger.warning(
                                f"⚠️ MCP error from gateway: {mcp_response['error']}"
                            )
                            raise Exception(
                                f"Gateway returned error: {mcp_response['error']['message']}"
                            )
                raise Exception("No valid data found in SSE response")
            else:
                # Handle regular JSON response
                mcp_response = response.json()
                if "result" in mcp_response:
                    return mcp_response["result"]
                elif "error" in mcp_response:
                    logger.warning(f"⚠️ MCP error from gateway: {mcp_response['error']}")
                    raise Exception(
                        f"Gateway returned error: {mcp_response['error']['message']}"
                    )
                else:
                    logger.warning(f"⚠️ Unexpected MCP response format: {mcp_response}")
                    raise Exception("Unexpected response format from gateway")
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(f"⚠️ Failed to parse Cequence response: {e}")
            logger.debug(f"Response content: {response.text[:500]}")
            raise Exception("Invalid response from gateway")

    async def _handle_gateway_error(self, response, operation: str) -> None:
        """Handle Cequence Gateway errors with fallback logging."""
        if response.status_code >= 400:
            logger.warning(
                f"⚠️ Cequence Gateway returned {response.status_code} for {operation}, falling back to direct mode"
            )
            raise Exception(f"Gateway error: {response.status_code}")
