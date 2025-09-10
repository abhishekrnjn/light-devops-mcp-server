"""
Health and root endpoints for MCP HTTP Server.

Handles:
- Root endpoint with server information
- Health check endpoints
- Server status and capabilities
"""

from fastapi import APIRouter

# Create router
router = APIRouter(tags=["health"])


@router.get("/")
async def root():
    """Root endpoint with server information."""
    return {
        "name": "DevOps MCP HTTP Server",
        "version": "1.0.0",
        "protocol": "MCP over HTTP",
        "description": "Simplified MCP server for DevOps operations",
        "capabilities": {
            "resources": 2,
            "tools": 3,
            "streaming": False,
        },
        "resources": {
            "logs": "/mcp/resources/logs - System logs with optional filtering",
            "metrics": "/mcp/resources/metrics - Performance metrics with optional limit",
        },
        "tools": {
            "deploy_service": "/mcp/tools/deploy_service - Deploy a service to an environment",
            "rollback_deployment": "/mcp/tools/rollback_deployment - Rollback a deployment (staging or production)",
            "authenticate_user": "/mcp/tools/authenticate_user - Authenticate with Descope",
        },
        "endpoints": {"resources": "/mcp/resources", "tools": "/mcp/tools"},
    }


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "devops-mcp-server",
        "version": "1.0.0",
    }
