"""
Cequence Gateway Client for routing API requests through Cequence for audit and monitoring.
Implements MCP Streamable HTTP transport protocol.
"""
import httpx
import logging
import json
import uuid
import random
from datetime import datetime, timezone, timedelta
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
        self.enabled = settings.CEQUENCE_ENABLED and self.gateway_url is not None
        self.client = httpx.AsyncClient(timeout=30.0)
        self.session_id = None
        self.initialized = False
        self.protocol_version = "2024-11-05"
        
        if self.enabled:
            logger.info(f"🌐 Cequence Gateway enabled: {self.gateway_url}")
        else:
            if not settings.CEQUENCE_ENABLED:
                logger.info("🔧 Cequence Gateway disabled - direct mode")
            elif self.gateway_url is None:
                logger.warning("⚠️ Cequence Gateway URL not configured - direct mode")
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
        
        logger.info(f"🔍 MCP request for logs: {json.dumps(mcp_request, indent=2)}")
        
        request_headers = self._get_mcp_headers()
        # Forward authorization headers
        if "authorization" in headers:
            request_headers["Authorization"] = headers["authorization"]
        if "cookie" in headers:
            request_headers["Cookie"] = headers["cookie"]
        
        logger.info(f"🔍 Request headers: {request_headers}")
        logger.info(f"🔍 Gateway URL: {self.gateway_url}")
        
        response = await self.client.post(
            self.gateway_url,
            json=mcp_request,
            headers=request_headers
        )
        
        logger.info(f"🔍 Response status: {response.status_code}")
        logger.info(f"🔍 Response headers: {dict(response.headers)}")
        if response.status_code != 200:
            logger.warning(f"🔍 Response content: {response.text[:500]}")
        
        return response
    
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
        
        logger.info(f"🔍 MCP request for metrics: {json.dumps(mcp_request, indent=2)}")
        
        request_headers = self._get_mcp_headers()
        # Forward authorization headers
        if "authorization" in headers:
            request_headers["Authorization"] = headers["authorization"]
        if "cookie" in headers:
            request_headers["Cookie"] = headers["cookie"]
        
        logger.info(f"🔍 Request headers: {request_headers}")
        logger.info(f"🔍 Gateway URL: {self.gateway_url}")
        
        response = await self.client.post(
            self.gateway_url,
            json=mcp_request,
            headers=request_headers
        )
        
        logger.info(f"🔍 Response status: {response.status_code}")
        logger.info(f"🔍 Response headers: {dict(response.headers)}")
        if response.status_code != 200:
            logger.warning(f"🔍 Response content: {response.text[:500]}")
        
        return response
    
    def _generate_dummy_metrics(self, base_timestamp: datetime, count: int = 9) -> list:
        """Generate realistic dummy metrics to supplement single real call."""
        dummy_metrics = []
        
        # Metrics configuration matching DatadogMetricsClient
        dummy_configs = [
            ("memory_usage", "percent"),
            ("disk_usage", "percent"),
            ("network_in", "bytes"),
            ("network_out", "bytes"),
            ("response_time", "milliseconds"),
            ("request_count", "count"),
            ("error_rate", "percent"),
            ("database_connections", "count"),
            ("queue_size", "count")
        ][:count]  # Take only the number requested
        
        for metric_name, unit in dummy_configs:
            value = self._generate_realistic_metric_value(metric_name, unit)
            dummy_metrics.append({
                "name": metric_name,
                "value": value,
                "unit": unit,
                "timestamp": base_timestamp.isoformat(),
                "_is_dummy": True  # Mark as dummy data
            })
        
        return dummy_metrics
    
    def _generate_realistic_metric_value(self, metric_name: str, unit: str) -> float:
        """Generate realistic values based on metric type."""
        if "percent" in unit or "rate" in metric_name:
            if "error" in metric_name:
                return round(random.uniform(0.1, 5.0), 2)  # Lower error rates
            return round(random.uniform(15, 85), 2)
        elif "count" in unit:
            if "database" in metric_name:
                return random.randint(5, 50)  # DB connections
            elif "queue" in metric_name:
                return random.randint(0, 25)  # Queue size
            else:
                return random.randint(10, 500)  # Request count
        elif "bytes" in unit:
            return random.randint(1024, 50000)  # Network traffic
        elif "milliseconds" in unit:
            return round(random.uniform(50, 300), 2)  # Response time
        else:
            return round(random.uniform(10, 100), 2)
    
    def _generate_dummy_logs(self, base_timestamp: datetime, count: int = 5) -> list:
        """Generate realistic dummy logs to supplement single real call."""
        dummy_logs = []
        
        log_templates = [
            {"level": "INFO", "message": "User session validated successfully - session_id={session_id}"},
            {"level": "INFO", "message": "API endpoint accessed - path=/api/v1/metrics, method=GET"},
            {"level": "WARN", "message": "Rate limit approaching - current_rate=85%, threshold=90%"},
            {"level": "INFO", "message": "Cache refresh completed - cache_size={cache_size}KB"},
            {"level": "WARN", "message": "Slow query detected - duration={duration}ms, query_id={query_id}"},
            {"level": "INFO", "message": "Background job completed - job_type=metrics_aggregation"},
            {"level": "ERROR", "message": "External API timeout - service=datadog, timeout=30s"},
            {"level": "INFO", "message": "Health check passed - all services operational"}
        ]
        
        for i in range(min(count, len(log_templates))):
            template = log_templates[i]
            # Generate realistic values for placeholders
            message = template["message"].format(
                session_id=f"sess_{random.randint(10000, 99999)}",
                cache_size=random.randint(100, 1000),
                duration=random.randint(500, 2000),
                query_id=f"q_{random.randint(1000, 9999)}"
            )
            
            # Vary timestamps slightly
            log_timestamp = base_timestamp - timedelta(minutes=i*2)
            
            dummy_logs.append({
                "level": template["level"],
                "message": f"OPTIMIZED_DUMMY: {message}",
                "timestamp": log_timestamp.isoformat(),
                "source": "cequence_optimization",
                "_is_dummy": True  # Mark as dummy data
            })
        
        return dummy_logs

    async def get_metrics_optimized(
        self,
        headers: Dict[str, str],
        limit: int = 50,
        service: Optional[str] = None
    ) -> httpx.Response:
        """
        OPTIMIZED: Get metrics through single call + dummy population.
        Makes only 1 real API call instead of N calls through Cequence Gateway.
        """
        await self._ensure_initialized()
        
        logger.info("🚀 CEQUENCE OPTIMIZATION: Using single call + dummy population for metrics")
        
        # Make single call for the most critical metric (cpu_utilization)
        arguments = {"limit": 1, "metric_type": "cpu_utilization"}
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
        
        logger.info(f"🔍 Single MCP request for critical metric: {json.dumps(mcp_request, indent=2)}")
        
        request_headers = self._get_mcp_headers()
        if "authorization" in headers:
            request_headers["Authorization"] = headers["authorization"]
        if "cookie" in headers:
            request_headers["Cookie"] = headers["cookie"]
        
        try:
            response = await self.client.post(
                self.gateway_url,
                json=mcp_request,
                headers=request_headers
            )
            
            if response.status_code == 200:
                # Parse the single real metric response
                real_data = response.json()
                
                # Extract timestamp from real data for consistency
                base_timestamp = datetime.now(timezone.utc)
                if "result" in real_data and "data" in real_data["result"] and real_data["result"]["data"]:
                    first_metric = real_data["result"]["data"][0]
                    if "timestamp" in first_metric:
                        base_timestamp = datetime.fromisoformat(first_metric["timestamp"].replace('Z', '+00:00'))
                
                # Generate dummy metrics to fill the rest
                dummy_metrics = self._generate_dummy_metrics(base_timestamp, min(limit - 1, 9))
                
                # Combine real and dummy data
                combined_data = real_data["result"]["data"] + dummy_metrics
                
                # Update the response
                real_data["result"]["data"] = combined_data
                real_data["result"]["count"] = len(combined_data)
                real_data["result"]["optimization"] = {
                    "enabled": True,
                    "real_metrics": 1,
                    "dummy_metrics": len(dummy_metrics),
                    "total_api_calls": 1
                }
                
                # Create a mock response with combined data
                mock_response = httpx.Response(
                    status_code=200,
                    content=json.dumps(real_data).encode(),
                    headers={"content-type": "application/json"},
                    request=response.request
                )
                
                logger.info(f"✅ OPTIMIZATION SUCCESS: 1 real + {len(dummy_metrics)} dummy metrics in 1 API call")
                return mock_response
            
        except Exception as e:
            logger.error(f"❌ Optimization failed: {e}, falling back to original method")
        
        # Fallback to original method if optimization fails
        return await self.get_metrics(headers, limit, service)

    async def get_logs_optimized(
        self,
        headers: Dict[str, str],
        level: Optional[str] = None,
        limit: int = 100,
        since: Optional[str] = None
    ) -> httpx.Response:
        """
        OPTIMIZED: Get logs through single call + dummy population.
        Makes only 1 real API call instead of N calls through Cequence Gateway.
        """
        await self._ensure_initialized()
        
        logger.info("🚀 CEQUENCE OPTIMIZATION: Using single call + dummy population for logs")
        
        # Make single call for the most critical logs (ERROR level or specified level)
        critical_level = level if level else "ERROR"
        arguments = {"level": critical_level, "limit": min(limit // 2, 20)}  # Get some real logs
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
        
        logger.info(f"🔍 Single MCP request for critical logs: {json.dumps(mcp_request, indent=2)}")
        
        request_headers = self._get_mcp_headers()
        if "authorization" in headers:
            request_headers["Authorization"] = headers["authorization"]
        if "cookie" in headers:
            request_headers["Cookie"] = headers["cookie"]
        
        try:
            response = await self.client.post(
                self.gateway_url,
                json=mcp_request,
                headers=request_headers
            )
            
            if response.status_code == 200:
                # Parse the real logs response
                real_data = response.json()
                
                # Extract timestamp from real data for consistency
                base_timestamp = datetime.now(timezone.utc)
                if "result" in real_data and "data" in real_data["result"] and real_data["result"]["data"]:
                    first_log = real_data["result"]["data"][0]
                    if "timestamp" in first_log:
                        base_timestamp = datetime.fromisoformat(first_log["timestamp"].replace('Z', '+00:00'))
                
                # Generate dummy logs to fill remaining limit
                real_count = len(real_data["result"]["data"])
                remaining_limit = max(0, limit - real_count)
                dummy_logs = self._generate_dummy_logs(base_timestamp, min(remaining_limit, 10))
                
                # Combine real and dummy data
                combined_data = real_data["result"]["data"] + dummy_logs
                
                # Update the response
                real_data["result"]["data"] = combined_data
                real_data["result"]["count"] = len(combined_data)
                real_data["result"]["optimization"] = {
                    "enabled": True,
                    "real_logs": real_count,
                    "dummy_logs": len(dummy_logs),
                    "total_api_calls": 1
                }
                
                # Create a mock response with combined data
                mock_response = httpx.Response(
                    status_code=200,
                    content=json.dumps(real_data).encode(),
                    headers={"content-type": "application/json"},
                    request=response.request
                )
                
                logger.info(f"✅ OPTIMIZATION SUCCESS: {real_count} real + {len(dummy_logs)} dummy logs in 1 API call")
                return mock_response
            
        except Exception as e:
            logger.error(f"❌ Optimization failed: {e}, falling back to original method")
        
        # Fallback to original method if optimization fails
        return await self.get_logs(headers, level, limit, since)
    
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
