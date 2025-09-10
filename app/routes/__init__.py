"""
Routes package for MCP HTTP Server.

This package contains all the route handlers organized by functionality:
- resources: MCP resource endpoints (/mcp/resources/*)
- tools: MCP tool endpoints (/mcp/tools/*)
- health: Health check and root endpoints
"""

from .resources import router as resources_router
from .tools import router as tools_router
from .health import router as health_router

__all__ = ["resources_router", "tools_router", "health_router"]
