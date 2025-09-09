"""
Cequence Gateway Client for routing API requests through Cequence for audit and monitoring.
Implements MCP Streamable HTTP transport protocol.
"""
import httpx
import logging
import json
import uuid
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class CequenceClient:
    """
    HTTP client for routing requests through Cequence Gateway.
    
    This client forwards requests to the Cequence gateway which then:
    1. Validates JWT tokens
    2. Enforces scope-based policies
    3. Applies rate limiting
    4. Logs requests for audit
    5. Forwards to the actual backend services
    """
    
    def __init__(self):
        self.gateway_url = settings.CEQUENCE_GATEWAY_URL
        self.enabled = settings.CEQUENCE_ENABLED
        self.client = httpx.AsyncClient(timeout=30.0)
        self.session_id = None
        self.initialized = False
        self.protocol_version = "2024-11-05"
        
        if self.enabled:
            logger.info(f"🌐 Cequence Gateway enabled: {self.gateway_url}")
        else:
            logger.info("🔧 Cequence Gateway disabled - direct mode")
    
    async def _ensure_initialized(self):
        """Ensure the MCP gateway is initialized with proper session management."""
        if self.initialized:
            return
        
        logger.info("🔧 Initializing MCP Gateway with Streamable HTTP transport...")
        
        # MCP InitializeRequest as per protocol
        init_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "initialize",
            "params": {
                "protocolVersion": self.protocol_version,
                "capabilities": {
                    "resources": {"subscribe": True, "listChanged": True},
                    "tools": {"listChanged": True}
                },
                "clientInfo": {
                    "name": "DevOps-MCP-Server",
                    "version": "1.0.0"
                }
            }
        }
        
        try:
            # Send InitializeRequest with proper MCP headers
            response = await self.client.post(
                self.gateway_url,
                json=init_request,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "MCP-Protocol-Version": self.protocol_version,
                    "User-Agent": "DevOps-MCP-Server/1.0"
                }
            )
            
            if response.status_code == 200:
                # Extract session ID from headers as per MCP protocol
                self.session_id = response.headers.get("Mcp-Session-Id")
                self.initialized = True
                logger.info(f"✅ MCP Gateway initialized with session: {self.session_id}")
                
                # Send InitializedNotification as required by MCP protocol
                await self._send_initialized_notification()
            else:
                logger.warning(f"⚠️ MCP Gateway initialization failed: {response.status_code}")
                logger.debug(f"Response: {response.text}")
                raise Exception(f"Gateway initialization failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize MCP Gateway: {e}")
            raise
    
    async def _send_initialized_notification(self):
        """Send InitializedNotification as required by MCP protocol."""
        if not self.session_id:
            return
        
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": self.protocol_version,
            "Mcp-Session-Id": self.session_id,
            "User-Agent": "DevOps-MCP-Server/1.0"
        }
        
        response = await self.client.post(
            self.gateway_url,
            json=initialized_notification,
            headers=headers
        )
        
        if response.status_code == 202:
            logger.info("✅ InitializedNotification sent successfully")
        else:
            logger.warning(f"⚠️ InitializedNotification failed: {response.status_code}")
    
    def _get_mcp_headers(self) -> Dict[str, str]:
        """Get standard MCP headers for requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": self.protocol_version,
            "User-Agent": "DevOps-MCP-Server/1.0"
        }
        
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
            
        return headers
    
    async def forward_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> httpx.Response:
        """
        Forward a request through Cequence Gateway.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., "/resources/logs")
            headers: Request headers (including Authorization)
            params: Query parameters
            json_data: JSON request body
            
        Returns:
            httpx.Response from the gateway
        """
        if not self.enabled:
            raise ValueError("Cequence Gateway is disabled")
        
        # Construct full URL
        url = f"{self.gateway_url.rstrip('/')}{path}"
        
        # Prepare headers
        request_headers = headers or {}
        request_headers.setdefault("Content-Type", "application/json")
        request_headers.setdefault("User-Agent", "DevOps-MCP-Server/1.0")
        
        logger.info(f"🌐 Forwarding {method} {path} through Cequence Gateway")
        logger.debug(f"🔍 Full URL: {url}")
        logger.debug(f"🔍 Headers: {dict(request_headers)}")
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                headers=request_headers,
                params=params,
                json=json_data
            )
            
            logger.info(f"✅ Cequence response: {response.status_code}")
            return response
            
        except httpx.RequestError as e:
            logger.error(f"❌ Cequence Gateway request failed: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Cequence Gateway HTTP error: {e.response.status_code}")
            raise
    
    async def get_logs(
        self,
        headers: Dict[str, str],
        level: Optional[str] = None,
        limit: int = 100,
        since: Optional[str] = None
    ) -> httpx.Response:
        """Get logs through Cequence Gateway using MCP tools/call."""
        await self._ensure_initialized()
        
        # MCP tools/call request for getMcpResourcesLogs
        # Build arguments, excluding null values
        arguments = {}
        if level is not None:
            arguments["level"] = level
        if limit is not None:
            arguments["limit"] = limit
        if since is not None:
            arguments["since"] = since
        
        mcp_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": "getMcpResourcesLogs",
                "arguments": arguments
            }
        }
        
        request_headers = self._get_mcp_headers()
        # Forward authorization headers
        if "authorization" in headers:
            request_headers["Authorization"] = headers["authorization"]
        if "cookie" in headers:
            request_headers["Cookie"] = headers["cookie"]
        
        return await self.client.post(
            self.gateway_url,
            json=mcp_request,
            headers=request_headers
        )
    
    async def get_metrics(
        self,
        headers: Dict[str, str],
        limit: int = 50,
        service: Optional[str] = None
    ) -> httpx.Response:
        """Get metrics through Cequence Gateway using MCP tools/call."""
        await self._ensure_initialized()
        
        # MCP tools/call request for getMcpResourcesMetrics
        # Build arguments, excluding null values
        arguments = {}
        if limit is not None:
            arguments["limit"] = limit
        if service is not None:
            arguments["service"] = service
        
        mcp_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": "getMcpResourcesMetrics",
                "arguments": arguments
            }
        }
        
        request_headers = self._get_mcp_headers()
        # Forward authorization headers
        if "authorization" in headers:
            request_headers["Authorization"] = headers["authorization"]
        if "cookie" in headers:
            request_headers["Cookie"] = headers["cookie"]
        
        return await self.client.post(
            self.gateway_url,
            json=mcp_request,
            headers=request_headers
        )
    
    async def deploy_service(
        self,
        headers: Dict[str, str],
        service_name: str,
        version: str,
        environment: str
    ) -> httpx.Response:
        """Deploy service through Cequence Gateway using MCP tools/call."""
        await self._ensure_initialized()
        
        # MCP tools/call request for postMcpToolsDeployService
        mcp_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": "postMcpToolsDeployService",
                "arguments": {
                    "service_name": service_name,
                    "version": version,
                    "environment": environment
                }
            }
        }
        
        request_headers = self._get_mcp_headers()
        # Forward authorization headers
        if "authorization" in headers:
            request_headers["Authorization"] = headers["authorization"]
        if "cookie" in headers:
            request_headers["Cookie"] = headers["cookie"]
        
        return await self.client.post(
            self.gateway_url,
            json=mcp_request,
            headers=request_headers
        )
    
    async def rollback_deployment(
        self,
        headers: Dict[str, str],
        deployment_id: str,
        reason: str,
        environment: str
    ) -> httpx.Response:
        """Rollback deployment through Cequence Gateway using MCP tools/call with environment parameter."""
        await self._ensure_initialized()
        
        # MCP tools/call request for postMcpToolsRollbackDeployment
        mcp_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": "postMcpToolsRollbackDeployment",
                "arguments": {
                    "deployment_id": deployment_id,
                    "reason": reason,
                    "environment": environment
                }
            }
        }
        
        request_headers = self._get_mcp_headers()
        # Forward authorization headers
        if "authorization" in headers:
            request_headers["Authorization"] = headers["authorization"]
        if "cookie" in headers:
            request_headers["Cookie"] = headers["cookie"]
        
        return await self.client.post(
            self.gateway_url,
            json=mcp_request,
            headers=request_headers
        )
    
    async def rollback_staging(
        self,
        headers: Dict[str, str],
        deployment_id: str,
        reason: str
    ) -> httpx.Response:
        """Rollback staging deployment through Cequence Gateway using MCP tools/call."""
        await self._ensure_initialized()
        
        # MCP tools/call request for postMcpToolsRollbackStaging
        mcp_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": "postMcpToolsRollbackStaging",
                "arguments": {
                    "deployment_id": deployment_id,
                    "reason": reason
                }
            }
        }
        
        request_headers = self._get_mcp_headers()
        # Forward authorization headers
        if "authorization" in headers:
            request_headers["Authorization"] = headers["authorization"]
        if "cookie" in headers:
            request_headers["Cookie"] = headers["cookie"]
        
        return await self.client.post(
            self.gateway_url,
            json=mcp_request,
            headers=request_headers
        )
    
    async def rollback_production(
        self,
        headers: Dict[str, str],
        deployment_id: str,
        reason: str
    ) -> httpx.Response:
        """Rollback production deployment through Cequence Gateway using MCP tools/call."""
        await self._ensure_initialized()
        
        # MCP tools/call request for postMcpToolsRollbackProduction
        mcp_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": "postMcpToolsRollbackProduction",
                "arguments": {
                    "deployment_id": deployment_id,
                    "reason": reason
                }
            }
        }
        
        request_headers = self._get_mcp_headers()
        # Forward authorization headers
        if "authorization" in headers:
            request_headers["Authorization"] = headers["authorization"]
        if "cookie" in headers:
            request_headers["Cookie"] = headers["cookie"]
        
        return await self.client.post(
            self.gateway_url,
            json=mcp_request,
            headers=request_headers
        )
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            # Note: This might not work in async context
            # Better to explicitly call close()
            pass
        except Exception:
            pass

# Global instance
cequence_client = CequenceClient()
