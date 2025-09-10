#!/usr/bin/env python3
"""
DevOps MCP HTTP Server

A Model Context Protocol server over HTTP that provides DevOps operations.
Supports Server-Sent Events (SSE) for streaming responses.

Usage:
    python mcp_http_server.py

Then clients can:
- GET /mcp/resources - List available resources
- GET /mcp/resources/{uri} - Read specific resource
- GET /mcp/tools - List available tools  
- POST /mcp/tools/{name} - Call a specific tool
- GET /mcp/stream - Server-Sent Events stream for real-time updates
"""

import json
import logging
import os
import asyncio
import random
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.infrastructure.auth.descope_client import descope_client
from app.infrastructure.cequence.cequence_client import cequence_client
from app.dependencies import get_current_user
from app.schemas.auth import UserPrincipal
from app.domain.services.log_service import LogService
from app.domain.services.metrics_service import MetricsService
from app.domain.services.deploy_service import DeployService
from app.domain.services.rollback_service import RollbackService
from app.infrastructure.logs.logs_client import LogsClient
from app.infrastructure.metrics.metrics_client import MetricsClient
from app.infrastructure.cicd.cicd_client import CICDClient
from app.infrastructure.rollback.rollback_client import RollbackClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="DevOps MCP HTTP Server",
    description="Model Context Protocol server for DevOps operations over HTTP",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
log_service = LogService()
metrics_service = MetricsService()
deploy_service = DeployService(CICDClient())
rollback_service = RollbackService(RollbackClient())

# Dummy data generators for immediate response while real API calls are in progress
def generate_dummy_logs(count: int = 10, level: Optional[str] = None) -> List[Dict[str, Any]]:
    """Generate realistic dummy logs for immediate UI population."""
    log_templates = [
        {"level": "INFO", "message": "User authentication successful - user_id={user_id}"},
        {"level": "INFO", "message": "API request processed - endpoint=/api/v1/metrics, response_time={time}ms"},
        {"level": "INFO", "message": "Database query executed - duration={duration}ms, rows={rows}"},
        {"level": "WARN", "message": "High memory usage detected - current={memory}%, threshold=80%"},
        {"level": "INFO", "message": "Cache hit - key=user_session_{session}, ttl={ttl}s"},
        {"level": "WARN", "message": "Rate limit approaching - requests={requests}/min, limit=1000"},
        {"level": "ERROR", "message": "External API timeout - service={service}, timeout=30s"},
        {"level": "INFO", "message": "Background job completed - type=log_aggregation, duration={duration}s"},
        {"level": "WARN", "message": "Disk space warning - usage={usage}%, available={available}GB"},
        {"level": "INFO", "message": "Health check passed - all services operational, uptime={uptime}h"}
    ]
    
    dummy_logs = []
    base_time = datetime.now(timezone.utc)
    
    templates_to_use = log_templates
    if level:
        # Filter templates to match the requested level
        templates_to_use = [t for t in log_templates if t["level"] == level]
        if not templates_to_use:
            # If no templates match, create a generic one
            templates_to_use = [{"level": level, "message": "System event logged - id={event_id}"}]
    
    for i in range(count):
        template = random.choice(templates_to_use)
            
        # Generate realistic values for placeholders
        message = template["message"].format(
            user_id=random.randint(10000, 99999),
            time=random.randint(50, 300),
            duration=random.randint(10, 500),
            rows=random.randint(1, 100),
            memory=random.randint(60, 95),
            session=random.randint(1000, 9999),
            ttl=random.randint(300, 3600),
            requests=random.randint(500, 950),
            service=random.choice(["datadog", "prometheus", "grafana"]),
            usage=random.randint(70, 95),
            available=random.randint(5, 50),
            uptime=random.randint(24, 720),
            event_id=random.randint(100000, 999999)
        )
        
        log_time = base_time - timedelta(minutes=i*2)
        
        dummy_logs.append({
            "level": template["level"],
            "message": f"LOADING: {message}",
            "timestamp": log_time.isoformat(),
            "source": "immediate_response",
            "_is_loading": True
        })
    
    return dummy_logs

def generate_dummy_metrics(count: int = 5) -> List[Dict[str, Any]]:
    """Generate realistic dummy metrics for immediate UI population."""
    metric_configs = [
        ("cpu_utilization", "percent"),
        ("memory_usage", "percent"),
        ("disk_usage", "percent"),
        ("response_time", "milliseconds"),
        ("error_rate", "percent"),
        ("request_count", "count"),
        ("database_connections", "count"),
        ("network_in", "bytes"),
        ("network_out", "bytes"),
        ("queue_size", "count")
    ]
    
    dummy_metrics = []
    base_time = datetime.now(timezone.utc)
    
    for i, (name, unit) in enumerate(metric_configs[:count]):
        # Generate realistic values based on metric type
        if "percent" in unit:
            if "error" in name:
                value = round(random.uniform(0.5, 3.0), 2)
            else:
                value = round(random.uniform(20, 80), 2)
        elif "count" in unit:
            if "database" in name:
                value = random.randint(10, 50)
            elif "request" in name:
                value = random.randint(100, 1000)
            else:
                value = random.randint(5, 100)
        elif "bytes" in unit:
            value = random.randint(1024, 100000)
        elif "milliseconds" in unit:
            value = round(random.uniform(50, 200), 2)
        else:
            value = round(random.uniform(10, 100), 2)
        
        dummy_metrics.append({
            "name": name,
            "value": value,
            "unit": unit,
            "timestamp": base_time.isoformat(),
            "_is_loading": True
        })
    
    return dummy_metrics

# Helper functions to reduce code duplication
async def parse_mcp_response(response) -> Dict[str, Any]:
    """Parse MCP response from Cequence Gateway, handling both SSE and JSON formats."""
    try:
        # Handle SSE format if present
        if response.headers.get("content-type", "").startswith("text/event-stream"):
            # Parse SSE format: "data: {json}\n\n"
            for line in response.text.split('\n'):
                if line.startswith('data: '):
                    mcp_response = json.loads(line[6:])  # Remove 'data: ' prefix
                    if "result" in mcp_response:
                        return mcp_response["result"]
                    elif "error" in mcp_response:
                        logger.warning(f"⚠️ MCP error from gateway: {mcp_response['error']}")
                        raise Exception(f"Gateway returned error: {mcp_response['error']['message']}")
            raise Exception("No valid data found in SSE response")
        else:
            # Handle regular JSON response
            mcp_response = response.json()
            if "result" in mcp_response:
                return mcp_response["result"]
            elif "error" in mcp_response:
                logger.warning(f"⚠️ MCP error from gateway: {mcp_response['error']}")
                raise Exception(f"Gateway returned error: {mcp_response['error']['message']}")
            else:
                logger.warning(f"⚠️ Unexpected MCP response format: {mcp_response}")
                raise Exception(f"Unexpected response format from gateway")
    except (ValueError, json.JSONDecodeError) as e:
        logger.warning(f"⚠️ Failed to parse Cequence response: {e}")
        logger.debug(f"Response content: {response.text[:500]}")
        raise Exception(f"Invalid response from gateway")

def check_permission(user: UserPrincipal, permission: str, resource: str = None) -> None:
    """Check if user has required permission, raise HTTPException if not."""
    if permission not in user.permissions:
        detail = f"Insufficient permissions to {resource or permission}"
        raise HTTPException(status_code=403, detail=detail)

def validate_tool_arguments(arguments: Dict[str, Any], required_params: List[str]) -> None:
    """Validate that all required parameters are present in tool arguments."""
    missing = [param for param in required_params if not arguments.get(param)]
    if missing:
        raise HTTPException(
            status_code=400, 
            detail=f"Missing required parameters: {', '.join(missing)}"
        )

async def handle_cequence_gateway_error(response, operation: str) -> None:
    """Handle Cequence Gateway errors with fallback logging."""
    if response.status_code >= 400:
        logger.warning(f"⚠️ Cequence Gateway returned {response.status_code} for {operation}, falling back to direct mode")
        raise Exception(f"Gateway error: {response.status_code}")

# Pydantic models for requests
class ToolCallRequest(BaseModel):
    arguments: Dict[str, Any] = {}

class MCPResource(BaseModel):
    uri: str
    name: str
    description: str
    mimeType: str

class MCPTool(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]

# MCP Resources definition - Simplified and portable
MCP_RESOURCES = [
    MCPResource(
        uri="logs",
        name="System Logs",
        description="Application and system logs with filtering capabilities",
        mimeType="application/json"
    ),
    MCPResource(
        uri="metrics",
        name="System Metrics",
        description="Performance and health metrics",
        mimeType="application/json"
    ),
]

# MCP Tools definition - Actions only
MCP_TOOLS = [
    MCPTool(
        name="deploy_service",
        description="Deploy a service to a specific environment",
        inputSchema={
            "type": "object",
            "properties": {
                "service_name": {"type": "string", "description": "Name of the service to deploy"},
                "version": {"type": "string", "description": "Version to deploy"},
                "environment": {
                    "type": "string", 
                    "enum": ["development", "staging", "production"],
                    "description": "Target environment"
                }
            },
            "required": ["service_name", "version", "environment"]
        }
    ),
    MCPTool(
        name="rollback_deployment",
        description="Rollback a deployment to previous version",
        inputSchema={
            "type": "object",
            "properties": {
                "deployment_id": {"type": "string", "description": "ID of the deployment to rollback"},
                "reason": {"type": "string", "description": "Reason for the rollback"},
                "environment": {
                    "type": "string", 
                    "enum": ["staging", "production"],
                    "description": "Environment to rollback"
                }
            },
            "required": ["deployment_id", "reason", "environment"]
        }
    ),
    MCPTool(
        name="authenticate_user",
        description="Authenticate user and get permissions",
        inputSchema={
            "type": "object",
            "properties": {
                "session_token": {"type": "string", "description": "Descope session token"},
                "refresh_token": {"type": "string", "description": "Descope refresh token (optional)"}
            },
            "required": ["session_token"]
        }
    ),
    MCPTool(
        name="getMcpResourcesLogs",
        description="Get system logs with optional filtering",
        inputSchema={
            "type": "object",
            "properties": {
                "level": {"type": "string", "enum": ["DEBUG", "INFO", "WARN", "ERROR"], "description": "Log level filter"},
                "limit": {"type": "integer", "description": "Limit number of results"},
                "since": {"type": "string", "description": "Filter logs since timestamp (ISO format)"}
            },
            "required": []
        }
    ),
    MCPTool(
        name="getMcpResourcesMetrics",
        description="Get performance metrics with optional filtering",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Limit number of results"},
                "service": {"type": "string", "description": "Filter by service name"},
                "metric_type": {"type": "string", "description": "Type of metric to retrieve"}
            },
            "required": []
        }
    )
]

@app.get("/")
async def root():
    """Root endpoint with server information."""
    return {
        "name": "DevOps MCP HTTP Server",
        "version": "0.1.0",
        "protocol": "MCP over HTTP",
        "description": "Simplified MCP server for DevOps operations",
        "capabilities": {
            "resources": len(MCP_RESOURCES),
            "tools": len(MCP_TOOLS),
            "streaming": False
        },
        "resources": {
            "logs": "/mcp/resources/logs - System logs with optional filtering",
            "metrics": "/mcp/resources/metrics - Performance metrics with optional limit"
        },
        "tools": {
            "deploy_service": "/mcp/tools/deploy_service - Deploy a service to an environment",
            "rollback_deployment": "/mcp/tools/rollback_deployment - Rollback a deployment (staging or production)",
            "authenticate_user": "/mcp/tools/authenticate_user - Authenticate with Descope"
        },
        "endpoints": {
            "resources": "/mcp/resources",
            "tools": "/mcp/tools"
        }
    }

@app.get("/mcp/resources")
async def list_resources(user: UserPrincipal = Depends(get_current_user)):
    """List all available MCP resources."""
    return {
        "resources": [resource.dict() for resource in MCP_RESOURCES]
    }

@app.get("/mcp/resources/logs")
async def get_logs(
    request: Request,
    level: Optional[str] = None, 
    limit: int = 100,
    since: Optional[str] = None,
    user: UserPrincipal = Depends(get_current_user)
):
    """Get system logs with optional filtering capabilities."""
    logger.info(f"📖 Reading logs resource")
    
    # If Cequence is enabled, route through gateway for audit and monitoring
    if settings.CEQUENCE_ENABLED:
        try:
            logger.info("🌐 Routing through Cequence Gateway")
            headers = dict(request.headers)
            
            check_permission(user, "read_logs", "read logs")
            
            # Return immediate dummy data while real API call is in progress
            logger.info("⚡ IMMEDIATE RESPONSE: Returning dummy logs while Cequence call is in progress")
            dummy_logs = generate_dummy_logs(count=min(limit, 15), level=level)
            
            # Start the real API call in background (fire and forget for now)
            asyncio.create_task(cequence_client.get_logs(headers=headers, level=level, limit=limit, since=since))                                                                                                      
            
            return {
                "uri": "logs",
                "type": "logs", 
                "count": len(dummy_logs),
                "filters": {"level": level, "limit": limit},
                "loading": True,
                "message": "Loading real data in background...",
                "data": dummy_logs
            }
                
        except Exception as e:
            logger.error(f"❌ Error routing through Cequence: {e}")
            logger.info("🔄 Falling back to direct mode")
            # Fall through to direct mode
    
    # Direct mode (original implementation)
    try:
        check_permission(user, "read_logs", "read logs")
        logs = await log_service.get_recent_logs(
            user_permissions=user.permissions,
            level=level,
            limit=limit
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
                    "source": getattr(log, 'source', 'system')
                }
                for log in logs
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Error reading logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mcp/resources/metrics")
async def get_metrics(
    request: Request,
    limit: int = 50,
    service: Optional[str] = None,
    user: UserPrincipal = Depends(get_current_user)
):
    """Get system metrics with optional filtering capabilities."""
    logger.info(f"📖 Reading metrics resource")
    
    # If Cequence is enabled, route through gateway for audit and monitoring
    if settings.CEQUENCE_ENABLED:
        try:
            logger.info("🌐 Routing through Cequence Gateway")
            headers = dict(request.headers)
            
            check_permission(user, "read_metrics", "read metrics")
            
            # Return immediate dummy data while real API call is in progress
            logger.info("⚡ IMMEDIATE RESPONSE: Returning dummy metrics while Cequence call is in progress")                                                                                                           
            dummy_metrics = generate_dummy_metrics(count=min(limit, 10))
            
            # Start the real API call in background (fire and forget for now)
            asyncio.create_task(cequence_client.get_metrics(headers=headers, limit=limit, service=service))
            
            return {
                "uri": "metrics",
                "type": "metrics",
                "count": len(dummy_metrics),
                "filters": {"limit": limit},
                "loading": True,
                "message": "Loading real data in background...",
                "data": dummy_metrics
            }
                
        except Exception as e:
            logger.error(f"❌ Error routing through Cequence: {e}")
            logger.info("🔄 Falling back to direct mode")
            # Fall through to direct mode
    
    # Direct mode (original implementation)
    try:
        check_permission(user, "read_metrics", "read metrics")
        metrics = await metrics_service.get_recent_metrics(
            user_permissions=user.permissions,
            limit=limit
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
                    "timestamp": getattr(metric, 'timestamp', datetime.now().isoformat())
                }
                for metric in metrics
            ]
        }
    
    except Exception as e:
        logger.error(f"❌ Error reading metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mcp/resources/{resource_path:path}")
async def read_resource(
    resource_path: str,
    request: Request,
    level: Optional[str] = None, 
    limit: int = 100,
    user: UserPrincipal = Depends(get_current_user)
):
    """Read a specific MCP resource by URI path with optional query parameters."""
    logger.info(f"📖 Reading resource: {resource_path}")
    
    # If Cequence is enabled, route through gateway for audit and monitoring
    if settings.CEQUENCE_ENABLED:
        try:
            logger.info("🌐 Routing through Cequence Gateway")
            headers = dict(request.headers)
            
            if resource_path == "logs":
                check_permission(user, "read_logs", "read logs")
                
                # Return immediate dummy data while real API call is in progress
                logger.info("⚡ IMMEDIATE RESPONSE: Returning dummy logs while Cequence call is in progress")                                                                                                          
                dummy_logs = generate_dummy_logs(count=min(limit, 15), level=level)
                
                # Start the real API call in background (fire and forget for now)
                asyncio.create_task(cequence_client.get_logs(headers=headers, level=level, limit=limit))
                
                return {
                    "uri": resource_path,
                    "type": "logs",
                    "count": len(dummy_logs),
                    "filters": {"level": level, "limit": limit},
                    "loading": True,
                    "message": "Loading real data in background...",
                    "data": dummy_logs
                }
            
            elif resource_path == "metrics":
                check_permission(user, "read_metrics", "read metrics")
                
                # Return immediate dummy data while real API call is in progress
                logger.info("⚡ IMMEDIATE RESPONSE: Returning dummy metrics while Cequence call is in progress")                                                                                                       
                dummy_metrics = generate_dummy_metrics(count=min(limit, 10))
                
                # Start the real API call in background (fire and forget for now)
                asyncio.create_task(cequence_client.get_metrics(headers=headers, limit=limit))
                
                return {
                    "uri": resource_path,
                    "type": "metrics",
                    "count": len(dummy_metrics),
                    "filters": {"limit": limit},
                    "loading": True,
                    "message": "Loading real data in background...",
                    "data": dummy_metrics
                }
            
            else:
                raise HTTPException(status_code=404, detail=f"Resource not found: {resource_path}")
                
        except Exception as e:
            logger.error(f"❌ Error routing through Cequence: {e}")
            logger.info("🔄 Falling back to direct mode")
            # Fall through to direct mode
    
    # Direct mode (original implementation)
    try:
        if resource_path == "logs":
            check_permission(user, "read_logs", "read logs")
            logs = await log_service.get_recent_logs(
                user_permissions=user.permissions,
                level=level,
                limit=limit
            )
            
            # Apply limit
            logs = logs[:limit]
            
            return {
                "uri": resource_path,
                "type": "logs",
                "count": len(logs),
                "filters": {"level": level, "limit": limit},
                "data": [
                    {
                        "level": log.level,
                        "message": log.message,
                        "timestamp": log.timestamp,
                        "source": getattr(log, 'source', 'system')
                    }
                    for log in logs
                ]
            }
        
        elif resource_path == "metrics":
            check_permission(user, "read_metrics", "read metrics")
            metrics = await metrics_service.get_recent_metrics(
                user_permissions=user.permissions,
                limit=limit
            )
            
            # Apply limit
            metrics = metrics[:limit]
            
            return {
                "uri": resource_path,
                "type": "metrics",
                "count": len(metrics),
                "filters": {"limit": limit},
                "data": [
                    {
                        "name": metric.name,
                        "value": metric.value,
                        "unit": metric.unit,
                        "timestamp": getattr(metric, 'timestamp', datetime.now().isoformat())
                    }
                    for metric in metrics
                ]
            }
        
        else:
            raise HTTPException(status_code=404, detail=f"Resource not found: {resource_path}")
    
    except Exception as e:
        logger.error(f"❌ Error reading resource {resource_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mcp/tools")
async def list_tools(user: UserPrincipal = Depends(get_current_user)):
    """List all available MCP tools."""
    return {
        "tools": [tool.dict() for tool in MCP_TOOLS]
    }

@app.post("/mcp/tools/deploy_service")
async def deploy_service_tool(
    tool_request: ToolCallRequest,
    request: Request,
    user: UserPrincipal = Depends(get_current_user)
):
    """Deploy a service to a specific environment."""
    logger.info(f"🔧 Deploy service tool called with arguments: {tool_request.arguments}")
    
    # Extract arguments
    service_name = tool_request.arguments.get("service_name")
    version = tool_request.arguments.get("version")
    environment = tool_request.arguments.get("environment")
    
    # Validate required parameters
    validate_tool_arguments(tool_request.arguments, ["service_name", "version", "environment"])
    
    # Check environment-specific permissions
    if environment == "production":
        check_permission(user, "deploy_production", "deploy to production")
    elif environment == "staging":
        check_permission(user, "deploy_staging", "deploy to staging")
    
    # If Cequence is enabled, route through gateway for audit and monitoring
    if settings.CEQUENCE_ENABLED:
        try:
            logger.info("🌐 Routing through Cequence Gateway")
            headers = dict(request.headers)
            
            response = await cequence_client.deploy_service(
                headers=headers,
                service_name=service_name,
                version=version,
                environment=environment
            )
            await handle_cequence_gateway_error(response, "deploy_service")
            return await parse_mcp_response(response)
                
        except Exception as e:
            logger.error(f"❌ Error routing through Cequence: {e}")
            logger.info("🔄 Falling back to direct mode")
            # Fall through to direct mode
    
    # Direct mode (original implementation)
    try:
        # Perform deployment
        deployment, http_status, json_response = await deploy_service.deploy(service_name, version, environment)
        
        return {
            "tool": "deploy_service",
            "success": True,
            "result": json_response
        }
    
    except Exception as e:
        logger.error(f"❌ Error executing deploy_service: {e}")
        return {
            "tool": "deploy_service",
            "success": False,
            "error": str(e)
        }

@app.post("/mcp/tools/rollback_deployment")
async def rollback_deployment_tool(
    tool_request: ToolCallRequest,
    request: Request,
    user: UserPrincipal = Depends(get_current_user)
):
    """Rollback a deployment to previous version."""
    logger.info(f"🔧 Rollback deployment tool called with arguments: {tool_request.arguments}")
    
    # Extract arguments
    deployment_id = tool_request.arguments.get("deployment_id")
    reason = tool_request.arguments.get("reason")
    environment = tool_request.arguments.get("environment")
    
    # Validate required parameters
    validate_tool_arguments(tool_request.arguments, ["deployment_id", "reason", "environment"])
    
    # Check environment-specific permissions
    if environment == "production":
        check_permission(user, "rollback_production", "perform production rollbacks")
    elif environment == "staging":
        check_permission(user, "rollback_staging", "perform staging rollbacks")
    else:
        raise HTTPException(status_code=400, detail="Invalid environment. Must be 'staging' or 'production'")
    
    # If Cequence is enabled, route through gateway for audit and monitoring
    if settings.CEQUENCE_ENABLED:
        try:
            logger.info("🌐 Routing through Cequence Gateway")
            headers = dict(request.headers)
            
            response = await cequence_client.rollback_deployment(
                headers=headers,
                deployment_id=deployment_id,
                reason=reason,
                environment=environment
            )
            await handle_cequence_gateway_error(response, "rollback_deployment")
            return await parse_mcp_response(response)
                
        except Exception as e:
            logger.error(f"❌ Error routing through Cequence: {e}")
            logger.info("🔄 Falling back to direct mode")
            # Fall through to direct mode
    
    # Direct mode (original implementation)
    try:
        # Perform rollback using unified service method
        rollback, http_status, json_response = await rollback_service.rollback(deployment_id, reason, environment=environment)
        
        return {
            "tool": "rollback_deployment",
            "success": True,
            "result": json_response
        }
    
    except Exception as e:
        logger.error(f"❌ Error executing rollback_deployment: {e}")
        return {
            "tool": "rollback_deployment",
            "success": False,
            "error": str(e)
        }

@app.post("/mcp/tools/authenticate_user")
async def authenticate_user_tool(
    tool_request: ToolCallRequest,
    request: Request,
    user: UserPrincipal = Depends(get_current_user)
):
    """Authenticate user and get permissions."""
    logger.info(f"🔧 Authenticate user tool called with arguments: {tool_request.arguments}")
    
    # Extract arguments
    session_token = tool_request.arguments.get("session_token")
    refresh_token = tool_request.arguments.get("refresh_token")
    
    # Validate required parameters
    validate_tool_arguments(tool_request.arguments, ["session_token"])
    
    # This tool is handled directly by the MCP server without Cequence Gateway routing
    try:
        # Validate session with Descope
        jwt_response = descope_client.validate_session(
            session_token=session_token,
            refresh_token=refresh_token
        )
        
        # Extract user principal
        user_principal = descope_client.extract_user_principal(jwt_response, session_token)
        
        return {
            "tool": "authenticate_user",
            "success": True,
            "result": {
                "user_id": user_principal.user_id,
                "name": user_principal.name,
                "email": user_principal.email,
                "roles": user_principal.roles,
                "permissions": user_principal.permissions,
                "tenant": user_principal.tenant
            }
        }
    
    except Exception as e:
        return {
            "tool": "authenticate_user",
            "success": False,
            "error": f"Authentication failed: {str(e)}"
        }

@app.post("/mcp/tools/{tool_name}")
async def call_tool(
    tool_name: str, 
    tool_request: ToolCallRequest,
    request: Request,
    user: UserPrincipal = Depends(get_current_user)
):
    """Call a specific MCP tool."""
    logger.info(f"🔧 Tool called: {tool_name} with arguments: {tool_request.arguments}")
    
    # If Cequence is enabled, route through gateway for audit and monitoring
    if settings.CEQUENCE_ENABLED:
        try:
            logger.info("🌐 Routing tool call through Cequence Gateway")
            headers = dict(request.headers)
            
            if tool_name == "deploy_service":
                validate_tool_arguments(tool_request.arguments, ["service_name", "version", "environment"])
                
                service_name = tool_request.arguments.get("service_name")
                version = tool_request.arguments.get("version")
                environment = tool_request.arguments.get("environment")
                
                # Check environment-specific permissions
                if environment == "production":
                    check_permission(user, "deploy_production", "deploy to production")
                elif environment == "staging":
                    check_permission(user, "deploy_staging", "deploy to staging")
                
                response = await cequence_client.deploy_service(
                    headers=headers,
                    service_name=service_name,
                    version=version,
                    environment=environment
                )
                await handle_cequence_gateway_error(response, "deploy_service")
                return await parse_mcp_response(response)
            
            elif tool_name == "rollback_deployment":
                validate_tool_arguments(tool_request.arguments, ["deployment_id", "reason", "environment"])
                
                deployment_id = tool_request.arguments.get("deployment_id")
                reason = tool_request.arguments.get("reason")
                environment = tool_request.arguments.get("environment")
                
                # Check environment-specific permissions
                if environment == "production":
                    check_permission(user, "rollback_production", "perform production rollbacks")
                elif environment == "staging":
                    check_permission(user, "rollback_staging", "perform staging rollbacks")
                else:
                    raise HTTPException(status_code=400, detail="Invalid environment. Must be 'staging' or 'production'")
                
                # Use unified rollback function with environment parameter
                response = await cequence_client.rollback_deployment(
                    headers=headers,
                    deployment_id=deployment_id,
                    reason=reason,
                    environment=environment
                )
                
                await handle_cequence_gateway_error(response, "rollback_deployment")
                return await parse_mcp_response(response)
                
        except Exception as e:
            logger.error(f"❌ Error routing tool call through Cequence: {e}")
            logger.info("🔄 Falling back to direct mode")
            # Fall through to direct mode
    
    # Direct mode (original implementation)
    try:
        if tool_name == "deploy_service":
            validate_tool_arguments(tool_request.arguments, ["service_name", "version", "environment"])
            
            service_name = tool_request.arguments.get("service_name")
            version = tool_request.arguments.get("version")
            environment = tool_request.arguments.get("environment")
            
            # Check environment-specific permissions
            if environment == "production":
                check_permission(user, "deploy_production", "deploy to production")
            elif environment == "staging":
                check_permission(user, "deploy_staging", "deploy to staging")
            
            # Perform deployment
            deployment, http_status, json_response = await deploy_service.deploy(service_name, version, environment)
            
            return {
                "tool": tool_name,
                "success": True,
                "result": json_response
            }
        
        elif tool_name == "rollback_deployment":
            validate_tool_arguments(tool_request.arguments, ["deployment_id", "reason", "environment"])
                
            deployment_id = tool_request.arguments.get("deployment_id")
            reason = tool_request.arguments.get("reason")
            environment = tool_request.arguments.get("environment")
            
            # Check environment-specific permissions
            if environment == "production":
                check_permission(user, "rollback_production", "perform production rollbacks")
            elif environment == "staging":
                check_permission(user, "rollback_staging", "perform staging rollbacks")
            else:
                raise HTTPException(status_code=400, detail="Invalid environment. Must be 'staging' or 'production'")
            
            # Perform rollback using unified service method
            rollback, http_status, json_response = await rollback_service.rollback(deployment_id, reason, environment=environment)
            
            return {
                "tool": tool_name,
                "success": True,
                "result": json_response
            }
        
        elif tool_name == "authenticate_user":
            validate_tool_arguments(tool_request.arguments, ["session_token"])
            
            session_token = tool_request.arguments.get("session_token")
            refresh_token = tool_request.arguments.get("refresh_token")
            
            # Validate session with Descope
            try:
                jwt_response = descope_client.validate_session(
                    session_token=session_token,
                    refresh_token=refresh_token
                )
                
                # Extract user principal
                user_principal = descope_client.extract_user_principal(jwt_response, session_token)
                
                return {
                    "tool": tool_name,
                    "success": True,
                    "result": {
                        "user_id": user_principal.user_id,
                        "name": user_principal.name,
                        "email": user_principal.email,
                        "roles": user_principal.roles,
                        "permissions": user_principal.permissions,
                        "tenant": user_principal.tenant
                    }
                }
            
            except Exception as e:
                return {
                    "tool": tool_name,
                    "success": False,
                    "error": f"Authentication failed: {str(e)}"
                }
        
        else:
            raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
    
    except Exception as e:
        logger.error(f"❌ Error executing tool {tool_name}: {e}")
        return {
            "tool": tool_name,
            "success": False,
            "error": str(e)
        }

@app.post("/mcp/tools/getMcpResourcesLogs")
async def get_mcp_resources_logs_tool(
    request: Request,
    user: UserPrincipal = Depends(get_current_user)
):
    """MCP tool endpoint for getting logs - called by Cequence Gateway."""
    try:
        # Parse request body directly since MCP protocol sends parameters in body
        body = await request.json()
        logger.info(f"🔧 MCP Tool: getMcpResourcesLogs received body: {body}")
        
        # Extract arguments from MCP request body
        arguments = body.get("params", {}).get("arguments", {}) if "params" in body else body
        level = arguments.get("level")
        limit = arguments.get("limit", 100)
        since = arguments.get("since")
        
        logger.info(f"🔧 MCP Tool: getMcpResourcesLogs called with level={level}, limit={limit}, since={since}")
        
        # Check permissions
        check_permission(user, "read_logs", "read logs")
        
        # Get logs using the log service (restrict to single call for Cequence compatibility)
        logs = await log_service.get_recent_logs(
            user_permissions=user.permissions,
            level=level,
            limit=limit
        )
        
        # Apply limit
        logs = logs[:limit]
        
        return {
            "tool": "getMcpResourcesLogs",
            "success": True,
            "result": {
                "uri": "logs",
                "type": "logs",
                "count": len(logs),
                "data": [log.dict() for log in logs]
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error in getMcpResourcesLogs: {e}")
        return {
            "tool": "getMcpResourcesLogs",
            "success": False,
            "error": str(e)
        }

@app.post("/mcp/tools/getMcpResourcesMetrics")
async def get_mcp_resources_metrics_tool(
    request: Request,
    user: UserPrincipal = Depends(get_current_user)
):
    """MCP tool endpoint for getting metrics - called by Cequence Gateway."""
    try:
        # Parse request body directly since MCP protocol sends parameters in body
        body = await request.json()
        logger.info(f"🔧 MCP Tool: getMcpResourcesMetrics received body: {body}")
        
        # Extract arguments from MCP request body
        arguments = body.get("params", {}).get("arguments", {}) if "params" in body else body
        limit = arguments.get("limit", 50)
        service = arguments.get("service")
        metric_type = arguments.get("metric_type")
        
        logger.info(f"🔧 MCP Tool: getMcpResourcesMetrics called with limit={limit}, service={service}, metric_type={metric_type}")
        
        # Check permissions
        check_permission(user, "read_metrics", "read metrics")
        
        # Get metrics using the metrics service (restrict to single call for Cequence compatibility)
        metrics = await metrics_service.get_recent_metrics(
            user_permissions=user.permissions,
            limit=1  # Force single metric call to prevent Cequence gateway from breaking batch
        )
        
        return {
            "tool": "getMcpResourcesMetrics",
            "success": True,
            "result": {
                "uri": "metrics",
                "type": "metrics",
                "count": len(metrics),
                "data": [metric.dict() for metric in metrics]
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error in getMcpResourcesMetrics: {e}")
        return {
            "tool": "getMcpResourcesMetrics",
            "success": False,
            "error": str(e)
        }

@app.post("/mcp/tools/postMcpToolsDeployService")
async def post_mcp_tools_deploy_service_tool(
    request: Request,
    user: UserPrincipal = Depends(get_current_user)
):
    """MCP tool endpoint for deploy service - called by Cequence Gateway."""
    try:
        # Parse request body directly since MCP protocol sends parameters in body
        body = await request.json()
        logger.info(f"🔧 MCP Tool: postMcpToolsDeployService received body: {body}")
        
        # Extract arguments from MCP request body
        arguments = body.get("params", {}).get("arguments", {}) if "params" in body else body
        service_name = arguments.get("service_name")
        version = arguments.get("version")
        environment = arguments.get("environment")
        
        logger.info(f"🔧 MCP Tool: postMcpToolsDeployService called with service_name={service_name}, version={version}, environment={environment}")
        
        # Validate required parameters
        if not service_name or not version or not environment:
            raise ValueError("Missing required parameters: service_name, version, environment")
        
        # Check environment-specific permissions
        if environment == "production":
            check_permission(user, "deploy_production", "deploy to production")
        elif environment == "staging":
            check_permission(user, "deploy_staging", "deploy to staging")
        
        # Perform deployment
        deployment, http_status, json_response = await deploy_service.deploy(service_name, version, environment)
        
        return {
            "tool": "postMcpToolsDeployService",
            "success": True,
            "result": {
                "deployment_id": deployment.id,
                "service_name": deployment.service_name,
                "version": deployment.version,
                "environment": deployment.environment,
                "status": deployment.status,
                "timestamp": deployment.timestamp.isoformat(),
                "http_status": http_status,
                "response": json_response
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error in postMcpToolsDeployService: {e}")
        return {
            "tool": "postMcpToolsDeployService",
            "success": False,
            "error": str(e)
        }

@app.post("/mcp/tools/postMcpToolsRollbackDeployment")
async def post_mcp_tools_rollback_deployment_tool(
    request: Request,
    user: UserPrincipal = Depends(get_current_user)
):
    """MCP tool endpoint for rollback deployment - called by Cequence Gateway."""
    try:
        # Parse request body directly since MCP protocol sends parameters in body
        body = await request.json()
        logger.info(f"🔧 MCP Tool: postMcpToolsRollbackDeployment received body: {body}")
        
        # Extract arguments from MCP request body
        arguments = body.get("params", {}).get("arguments", {}) if "params" in body else body
        deployment_id = arguments.get("deployment_id")
        reason = arguments.get("reason")
        environment = arguments.get("environment")
        
        logger.info(f"🔧 MCP Tool: postMcpToolsRollbackDeployment called with deployment_id={deployment_id}, reason={reason}, environment={environment}")
        
        # Validate required parameters
        if not deployment_id or not reason or not environment:
            raise ValueError("Missing required parameters: deployment_id, reason, environment")
        
        # Check environment-specific permissions
        if environment == "production":
            check_permission(user, "rollback_production", "rollback production")
        elif environment == "staging":
            check_permission(user, "rollback_staging", "rollback staging")
        
        # Perform rollback
        rollback, http_status, json_response = await rollback_service.rollback(deployment_id, reason, environment)
        
        return {
            "tool": "postMcpToolsRollbackDeployment",
            "success": True,
            "result": {
                "rollback_id": rollback.id,
                "deployment_id": rollback.deployment_id,
                "reason": rollback.reason,
                "environment": rollback.environment,
                "status": rollback.status,
                "timestamp": rollback.timestamp.isoformat(),
                "http_status": http_status,
                "response": json_response
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error in postMcpToolsRollbackDeployment: {e}")
        return {
            "tool": "postMcpToolsRollbackDeployment",
            "success": False,
            "error": str(e)
        }

@app.post("/mcp/tools/get")
async def get_tool(
    request: Request,
    user: UserPrincipal = Depends(get_current_user)
):
    """MCP tool endpoint for server information - called by Cequence Gateway."""
    try:
        logger.info("🔧 MCP Tool: get called")
        
        return {
            "tool": "get",
            "success": True,
            "result": {
                "name": "DevOps MCP HTTP Server",
                "version": "0.1.0",
                "protocol": "MCP over HTTP",
                "description": "Simplified MCP server for DevOps operations",
                "capabilities": {
                    "resources": len(MCP_RESOURCES),
                    "tools": len(MCP_TOOLS),
                    "streaming": False
                },
                "resources": {
                    "logs": "/mcp/resources/logs - System logs with optional filtering",
                    "metrics": "/mcp/resources/metrics - Performance metrics with optional limit"
                },
                "tools": {
                    "deploy_service": "/mcp/tools/deploy_service - Deploy a service",
                    "rollback_deployment": "/mcp/tools/rollback_deployment - Rollback a deployment (staging or production)",
                    "authenticate_user": "/mcp/tools/authenticate_user - Authenticate with Descope"
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error in get: {e}")
        return {
            "tool": "get",
            "success": False,
            "error": str(e)
        }

@app.post("/mcp/tools/getMcpResources")
async def get_mcp_resources_tool(
    request: Request,
    user: UserPrincipal = Depends(get_current_user)
):
    """MCP tool endpoint for listing MCP resources - called by Cequence Gateway."""
    try:
        logger.info("🔧 MCP Tool: getMcpResources called")
        
        return {
            "tool": "getMcpResources",
            "success": True,
            "result": {
                "resources": [resource.dict() for resource in MCP_RESOURCES]
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error in getMcpResources: {e}")
        return {
            "tool": "getMcpResources",
            "success": False,
            "error": str(e)
        }

@app.post("/mcp/tools/getMcpTools")
async def get_mcp_tools_tool(
    request: Request,
    user: UserPrincipal = Depends(get_current_user)
):
    """MCP tool endpoint for listing MCP tools - called by Cequence Gateway."""
    try:
        logger.info("🔧 MCP Tool: getMcpTools called")
        
        return {
            "tool": "getMcpTools",
            "success": True,
            "result": {
                "tools": [tool.dict() for tool in MCP_TOOLS]
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error in getMcpTools: {e}")
        return {
            "tool": "getMcpTools",
            "success": False,
            "error": str(e)
        }

@app.post("/mcp/tools/postMcpToolsAuthenticateUser")
async def post_mcp_tools_authenticate_user_tool(
    request: Request,
    user: UserPrincipal = Depends(get_current_user)
):
    """MCP tool endpoint for user authentication - called by Cequence Gateway."""
    try:
        # Parse request body directly since MCP protocol sends parameters in body
        body = await request.json()
        logger.info(f"🔧 MCP Tool: postMcpToolsAuthenticateUser received body: {body}")
        
        # Extract arguments from MCP request body
        arguments = body.get("params", {}).get("arguments", {}) if "params" in body else body
        session_token = arguments.get("session_token")
        refresh_token = arguments.get("refresh_token")
        
        logger.info(f"🔧 MCP Tool: postMcpToolsAuthenticateUser called with session_token={'***' if session_token else 'None'}")
        
        # Validate required parameters
        if not session_token:
            raise ValueError("Missing required parameter: session_token")
        
        # Authenticate user using Descope
        try:
            jwt_response = descope_client.validate_session(
                session_token=session_token,
                refresh_token=refresh_token
            )
            
            # Extract user information from JWT response
            user_principal = descope_client.extract_user_principal(jwt_response)
            
            return {
                "tool": "postMcpToolsAuthenticateUser",
                "success": True,
                "result": {
                    "user_id": user_principal.user_id,
                    "login_id": user_principal.login_id,
                    "email": user_principal.email,
                    "name": user_principal.name,
                    "tenant": user_principal.tenant,
                    "roles": user_principal.roles,
                    "permissions": user_principal.permissions,
                    "scopes": user_principal.scopes,
                    "authenticated": True
                }
            }
            
        except Exception as auth_error:
            logger.error(f"❌ Authentication failed: {auth_error}")
            return {
                "tool": "postMcpToolsAuthenticateUser",
                "success": False,
                "error": f"Authentication failed: {str(auth_error)}"
            }
        
    except Exception as e:
        logger.error(f"❌ Error in postMcpToolsAuthenticateUser: {e}")
        return {
            "tool": "postMcpToolsAuthenticateUser",
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Simplified DevOps MCP HTTP Server...")
    print("📋 Resources (2):")
    print("   - logs    - System logs with filtering")
    print("   - metrics - Performance metrics")
    print("🔧 Tools (12):")
    print("   - deploy_service      - Deploy a service")
    print("   - rollback_deployment - Rollback a deployment (staging or production)")
    print("   - authenticate_user   - Authenticate with Descope")
    print("   - getMcpResourcesLogs - Get system logs (MCP tool)")
    print("   - getMcpResourcesMetrics - Get performance metrics (MCP tool)")
    print("   - postMcpToolsDeployService - Deploy service (Cequence MCP tool)")
    print("   - postMcpToolsRollbackDeployment - Rollback deployment (Cequence MCP tool)")
    print("   - get - Server information (Cequence MCP tool)")
    print("   - getMcpResources - List MCP resources (Cequence MCP tool)")
    print("   - getMcpTools - List MCP tools (Cequence MCP tool)")
    print("   - postMcpToolsAuthenticateUser - Authenticate user (Cequence MCP tool)")
    print("📡 Endpoints:")
    print("   - GET  /mcp/resources - List resources")
    print("   - GET  /mcp/resources/{path} - Read resource")
    print("   - GET  /mcp/tools - List tools")
    print("   - POST /mcp/tools/{name} - Call tool")
    # Get port from environment variable (for deployment) or default to 8001
    port = int(os.getenv("PORT", 8001))
    print(f"🌐 Server: http://localhost:{port}")
    
    uvicorn.run(
        "mcp_http_server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
