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

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.infrastructure.auth.descope_client import descope_client
from app.dependencies import get_current_user, require_permissions
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
log_service = LogService(LogsClient())
metrics_service = MetricsService(MetricsClient())
deploy_service = DeployService(CICDClient())
rollback_service = RollbackService(RollbackClient())

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
                "reason": {"type": "string", "description": "Reason for the rollback"}
            },
            "required": ["deployment_id", "reason"]
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
            "logs": "System logs with optional filtering (?level=ERROR&limit=10)",
            "metrics": "Performance metrics with optional limit (?limit=50)"
        },
        "tools": {
            "deploy_service": "Deploy a service to an environment",
            "rollback_deployment": "Rollback a deployment",
            "authenticate_user": "Authenticate with Descope"
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

@app.get("/mcp/resources/{resource_path:path}")
async def read_resource(
    resource_path: str, 
    level: Optional[str] = None, 
    limit: int = 100,
    user: UserPrincipal = Depends(get_current_user)
):
    """Read a specific MCP resource by URI path with optional query parameters."""
    logger.info(f"📖 Reading resource: {resource_path}")
    
    try:
        if resource_path == "logs":
            # Check specific permission for logs
            if "read_logs" not in user.permissions:
                raise HTTPException(status_code=403, detail="Insufficient permissions to read logs")
            
            logs = await log_service.get_recent_logs()
            
            # Apply optional filtering
            if level:
                logs = [log for log in logs if log.level == level]
            
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
            # Check specific permission for metrics
            if "read_metrics" not in user.permissions:
                raise HTTPException(status_code=403, detail="Insufficient permissions to read metrics")
                
            metrics = await metrics_service.get_recent_metrics()
            
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

@app.post("/mcp/tools/{tool_name}")
async def call_tool(
    tool_name: str, 
    request: ToolCallRequest,
    user: UserPrincipal = Depends(get_current_user)
):
    """Call a specific MCP tool."""
    logger.info(f"🔧 Tool called: {tool_name} with arguments: {request.arguments}")
    
    try:
        if tool_name == "deploy_service":
            # Check deployment permissions based on environment
            service_name = request.arguments.get("service_name")
            version = request.arguments.get("version")
            environment = request.arguments.get("environment")
            
            if not all([service_name, version, environment]):
                return {
                    "tool": tool_name,
                    "success": False,
                    "error": "Missing required parameters: service_name, version, environment"
                }
            
            # Check environment-specific permissions
            if environment == "production":
                if "deploy_production" not in user.permissions:
                    return {
                        "tool": tool_name,
                        "success": False,
                        "error": "Insufficient permissions to deploy to production"
                    }
            elif environment == "staging":
                if "deploy_staging" not in user.permissions:
                    return {
                        "tool": tool_name,
                        "success": False,
                        "error": "Insufficient permissions to deploy to staging"
                    }
            
            # Perform deployment
            result = await deploy_service.deploy(service_name, version, environment)
            
            return {
                "tool": tool_name,
                "success": True,
                "result": {
                    "service_name": result.service_name,
                    "version": result.version,
                    "environment": result.environment,
                    "status": result.status,
                    "timestamp": result.timestamp
                }
            }
        
        elif tool_name == "rollback_deployment":
            # Check rollback permissions
            if "rollback_write" not in user.permissions:
                return {
                    "tool": tool_name,
                    "success": False,
                    "error": "Insufficient permissions to perform rollbacks"
                }
                
            deployment_id = request.arguments.get("deployment_id")
            reason = request.arguments.get("reason")
            
            if not all([deployment_id, reason]):
                return {
                    "tool": tool_name,
                    "success": False,
                    "error": "Missing required parameters: deployment_id, reason"
                }
            
            # Perform rollback
            result = await rollback_service.rollback(deployment_id, reason)
            
            return {
                "tool": tool_name,
                "success": True,
                "result": {
                    "deployment_id": deployment_id,
                    "reason": result.reason,
                    "status": result.status,
                    "timestamp": result.timestamp
                }
            }
        
        elif tool_name == "authenticate_user":
            session_token = request.arguments.get("session_token")
            refresh_token = request.arguments.get("refresh_token")
            
            if not session_token:
                return {
                    "tool": tool_name,
                    "success": False,
                    "error": "Missing required parameter: session_token"
                }
            
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


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Simplified DevOps MCP HTTP Server...")
    print("📋 Resources (2):")
    print("   - logs    - System logs with filtering")
    print("   - metrics - Performance metrics")
    print("🔧 Tools (3):")
    print("   - deploy_service      - Deploy a service")
    print("   - rollback_deployment - Rollback a deployment")
    print("   - authenticate_user   - Authenticate with Descope")
    print("📡 Endpoints:")
    print("   - GET  /mcp/resources - List resources")
    print("   - GET  /mcp/resources/{path} - Read resource")
    print("   - GET  /mcp/tools - List tools")
    print("   - POST /mcp/tools/{name} - Call tool")
    print("🌐 Server: http://localhost:8001")
    
    uvicorn.run(
        "mcp_http_server:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
