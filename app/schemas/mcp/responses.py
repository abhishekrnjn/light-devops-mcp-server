"""
Response models for MCP HTTP Server.

This module contains all Pydantic models for outgoing responses,
providing consistent structure and type safety for API responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class MCPResponse(BaseModel):
    """Base response model for MCP operations."""
    success: bool = Field(..., description="Whether the operation was successful")
    message: Optional[str] = Field(None, description="Optional message about the operation")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class ErrorResponse(MCPResponse):
    """Response model for errors."""
    success: bool = Field(False, description="Always false for error responses")
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Optional error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ResourceResponse(MCPResponse):
    """Response model for resource operations."""
    uri: str = Field(..., description="Resource URI")
    type: str = Field(..., description="Resource type")
    count: int = Field(..., description="Number of items returned")
    filters: Optional[Dict[str, Any]] = Field(None, description="Applied filters")
    data: List[Any] = Field(..., description="Resource data")
    loading: Optional[bool] = Field(False, description="Whether data is still loading")
    pagination: Optional[Dict[str, Any]] = Field(None, description="Pagination information")


class ToolResponse(MCPResponse):
    """Response model for tool operations."""
    tool: str = Field(..., description="Tool name")
    result: Optional[Dict[str, Any]] = Field(None, description="Tool result")
    error: Optional[str] = Field(None, description="Error message if failed")


class LogEntry(BaseModel):
    """Model for individual log entries."""
    level: str = Field(..., description="Log level")
    message: str = Field(..., description="Log message")
    timestamp: str = Field(..., description="Log timestamp (ISO format)")
    source: str = Field(..., description="Log source")
    service: Optional[str] = Field(None, description="Service name")
    user_id: Optional[str] = Field(None, description="User ID")
    request_id: Optional[str] = Field(None, description="Request ID")
    is_loading: Optional[bool] = Field(False, description="Whether this is loading data")


class MetricEntry(BaseModel):
    """Model for individual metric entries."""
    name: str = Field(..., description="Metric name")
    value: Union[float, int] = Field(..., description="Metric value")
    unit: str = Field(..., description="Metric unit")
    timestamp: str = Field(..., description="Metric timestamp (ISO format)")
    service: Optional[str] = Field(None, description="Service name")
    tags: Optional[Dict[str, str]] = Field(None, description="Metric tags")
    is_loading: Optional[bool] = Field(False, description="Whether this is loading data")


class DeploymentData(BaseModel):
    """Model for deployment data."""
    deployment_id: str = Field(..., description="Deployment ID")
    service_name: str = Field(..., description="Service name")
    version: str = Field(..., description="Deployed version")
    environment: str = Field(..., description="Target environment")
    status: str = Field(..., description="Deployment status")
    timestamp: str = Field(..., description="Deployment timestamp (ISO format)")
    deployed_by: Optional[str] = Field(None, description="User who deployed")
    build_number: Optional[int] = Field(None, description="Build number")
    commit_hash: Optional[str] = Field(None, description="Git commit hash")
    http_status: Optional[int] = Field(None, description="HTTP status code")
    response: Optional[Dict[str, Any]] = Field(None, description="Deployment response")
    is_loading: Optional[bool] = Field(False, description="Whether this is loading data")


class RollbackData(BaseModel):
    """Model for rollback data."""
    rollback_id: str = Field(..., description="Rollback ID")
    deployment_id: str = Field(..., description="Deployment ID being rolled back")
    reason: str = Field(..., description="Rollback reason")
    environment: str = Field(..., description="Environment being rolled back")
    status: str = Field(..., description="Rollback status")
    timestamp: str = Field(..., description="Rollback timestamp (ISO format)")
    rolled_back_by: Optional[str] = Field(None, description="User who initiated rollback")
    previous_version: Optional[str] = Field(None, description="Previous version")
    http_status: Optional[int] = Field(None, description="HTTP status code")
    response: Optional[Dict[str, Any]] = Field(None, description="Rollback response")
    is_loading: Optional[bool] = Field(False, description="Whether this is loading data")


class UserData(BaseModel):
    """Model for user data."""
    user_id: str = Field(..., description="User ID")
    login_id: Optional[str] = Field(None, description="Login ID")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User name")
    tenant: str = Field(..., description="User tenant")
    roles: List[str] = Field(..., description="User roles")
    permissions: List[str] = Field(..., description="User permissions")
    scopes: Optional[List[str]] = Field(None, description="User scopes")
    authenticated: Optional[bool] = Field(True, description="Whether user is authenticated")
    last_login: Optional[str] = Field(None, description="Last login timestamp")
    is_loading: Optional[bool] = Field(False, description="Whether this is loading data")


class LogsResponse(ResourceResponse):
    """Response model for logs resource."""
    type: str = Field("logs", description="Resource type")
    data: List[LogEntry] = Field(..., description="Log entries")


class MetricsResponse(ResourceResponse):
    """Response model for metrics resource."""
    type: str = Field("metrics", description="Resource type")
    data: List[MetricEntry] = Field(..., description="Metric entries")


class DeployServiceResponse(ToolResponse):
    """Response model for deploy service tool."""
    tool: str = Field("deploy_service", description="Tool name")
    result: Optional[DeploymentData] = Field(None, description="Deployment result")


class RollbackDeploymentResponse(ToolResponse):
    """Response model for rollback deployment tool."""
    tool: str = Field("rollback_deployment", description="Tool name")
    result: Optional[RollbackData] = Field(None, description="Rollback result")


class AuthenticateUserResponse(ToolResponse):
    """Response model for authenticate user tool."""
    tool: str = Field("authenticate_user", description="Tool name")
    result: Optional[UserData] = Field(None, description="User data result")


class ServerInfoResponse(MCPResponse):
    """Response model for server information."""
    success: bool = Field(True, description="Always true for server info")
    name: str = Field(..., description="Server name")
    version: str = Field(..., description="Server version")
    protocol: str = Field(..., description="Protocol name")
    description: str = Field(..., description="Server description")
    capabilities: Dict[str, Any] = Field(..., description="Server capabilities")
    resources: Dict[str, str] = Field(..., description="Available resources")
    tools: Dict[str, str] = Field(..., description="Available tools")
    endpoints: Optional[Dict[str, str]] = Field(None, description="API endpoints")


class HealthResponse(MCPResponse):
    """Response model for health checks."""
    success: bool = Field(True, description="Always true for health checks")
    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    uptime: Optional[str] = Field(None, description="Service uptime")
    dependencies: Optional[Dict[str, str]] = Field(None, description="Dependency status")
