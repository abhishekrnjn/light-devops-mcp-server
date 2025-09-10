#!/usr/bin/env python3
"""
DevOps MCP HTTP Server - Refactored Version

A Model Context Protocol server over HTTP that provides DevOps operations.
Supports Server-Sent Events (SSE) for streaming responses.

Usage:
    python mcp_http_server_refactored.py

Then clients can:
- GET /mcp/resources - List available resources
- GET /mcp/resources/{uri} - Read specific resource
- GET /mcp/tools - List available tools
- POST /mcp/tools/{name} - Call a specific tool
- GET /mcp/stream - Server-Sent Events stream for real-time updates
"""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.middleware import (
    ErrorHandlingMiddleware,
    GatewayRoutingMiddleware,
    LoggingMiddleware,
    RequestValidationMiddleware,
)
from app.routes import health_router, resources_router, tools_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="DevOps MCP HTTP Server",
    description="Model Context Protocol server for DevOps operations over HTTP",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware (order matters - last added is first executed)
app.add_middleware(RequestValidationMiddleware, enable_validation=True)
app.add_middleware(LoggingMiddleware, enable_detailed_logging=True)
app.add_middleware(ErrorHandlingMiddleware, enable_error_logging=True)
app.add_middleware(GatewayRoutingMiddleware, enable_gateway_routing=True)

# Include routers
app.include_router(health_router)
app.include_router(resources_router)
app.include_router(tools_router)


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Refactored DevOps MCP HTTP Server...")
    print("📋 Resources (2):")
    print("   - logs    - System logs with filtering")
    print("   - metrics - Performance metrics")
    print("🔧 Tools (3):")
    print("   - deploy_service      - Deploy a service")
    print("   - rollback_deployment - Rollback a deployment (staging or production)")
    print("   - authenticate_user   - Authenticate with Descope")
    print("   - getMcpResourcesLogs - Get system logs (MCP tool)")
    print("   - getMcpResourcesMetrics - Get performance metrics (MCP tool)")
    print("   - postMcpToolsDeployService - Deploy service (Cequence MCP tool)")
    print(
        "   - postMcpToolsRollbackDeployment - Rollback deployment (Cequence MCP tool)"
    )
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
        "mcp_http_server_refactored:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info",
    )
