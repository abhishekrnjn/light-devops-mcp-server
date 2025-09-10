"""
Resource endpoints for MCP HTTP Server.

Handles all /mcp/resources/* endpoints including:
- List resources
- Get logs
- Get metrics
- Read specific resources by path
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.dependencies import get_current_user
from app.domain.services.mcp_service import MCPResourceService
from app.schemas.auth import UserPrincipal
from app.schemas.mcp import (
    LogEntry,
    LogsResourceRequest,
    LogsResponse,
    MCPResourceList,
    MetricEntry,
    MetricsResourceRequest,
    MetricsResponse,
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/mcp/resources", tags=["resources"])

# Initialize services
mcp_resource_service = MCPResourceService()


@router.get("", response_model=MCPResourceList)
async def list_resources(user: UserPrincipal = Depends(get_current_user)):
    """List all available MCP resources."""
    from app.schemas.mcp.resources import MCP_RESOURCES

    return MCPResourceList(resources=MCP_RESOURCES, total=len(MCP_RESOURCES))


@router.get("/logs", response_model=LogsResponse)
async def get_logs(
    request: Request,
    level: Optional[str] = None,
    limit: int = 100,
    since: Optional[str] = None,
    service: Optional[str] = None,
    user: UserPrincipal = Depends(get_current_user),
):
    """Get system logs with optional filtering capabilities."""
    logger.info("📖 Reading logs resource")

    try:
        # Validate request parameters
        request_data = LogsResourceRequest(
            level=level, limit=limit, since=since, service=service
        )

        headers = dict(request.headers)
        result = await mcp_resource_service.get_logs(
            headers=headers,
            user=user,
            level=request_data.level,
            limit=request_data.limit,
            since=request_data.since,
        )

        # Convert to LogsResponse model
        return LogsResponse(
            success=True,
            uri="logs",
            type="logs",
            count=result.get("count", 0),
            filters={
                "level": request_data.level,
                "limit": request_data.limit,
                "since": request_data.since,
                "service": request_data.service,
            },
            data=[LogEntry(**log) for log in result.get("data", [])],
            loading=result.get("loading", False),
            message=result.get("message"),
        )
    except Exception as e:
        logger.error(f"❌ Error reading logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    request: Request,
    limit: int = 50,
    service: Optional[str] = None,
    metric_type: Optional[str] = None,
    time_range: Optional[str] = None,
    user: UserPrincipal = Depends(get_current_user),
):
    """Get system metrics with optional filtering capabilities."""
    logger.info("📖 Reading metrics resource")

    try:
        # Validate request parameters
        request_data = MetricsResourceRequest(
            limit=limit, service=service, metric_type=metric_type, time_range=time_range
        )

        headers = dict(request.headers)
        result = await mcp_resource_service.get_metrics(
            headers=headers,
            user=user,
            limit=request_data.limit,
            service=request_data.service,
        )

        # Convert to MetricsResponse model
        return MetricsResponse(
            success=True,
            uri="metrics",
            type="metrics",
            count=result.get("count", 0),
            filters={
                "limit": request_data.limit,
                "service": request_data.service,
                "metric_type": request_data.metric_type,
                "time_range": request_data.time_range,
            },
            data=[MetricEntry(**metric) for metric in result.get("data", [])],
            loading=result.get("loading", False),
            message=result.get("message"),
        )
    except Exception as e:
        logger.error(f"❌ Error reading metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{resource_path:path}")
async def read_resource(
    resource_path: str,
    request: Request,
    level: Optional[str] = None,
    limit: int = 100,
    user: UserPrincipal = Depends(get_current_user),
):
    """Read a specific MCP resource by URI path with optional query parameters."""
    logger.info(f"📖 Reading resource: {resource_path}")

    try:
        headers = dict(request.headers)

        if resource_path == "logs":
            result = await mcp_resource_service.get_logs(
                headers=headers, user=user, level=level, limit=limit
            )
            result["uri"] = resource_path
            return result
        elif resource_path == "metrics":
            result = await mcp_resource_service.get_metrics(
                headers=headers, user=user, limit=limit
            )
            result["uri"] = resource_path
            return result
        else:
            raise HTTPException(
                status_code=404, detail=f"Resource not found: {resource_path}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error reading resource {resource_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
