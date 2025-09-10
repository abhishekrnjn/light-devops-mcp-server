"""
Request models for MCP HTTP Server.

This module contains all Pydantic models for incoming requests,
providing validation and type safety for API endpoints.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator


class ToolCallRequest(BaseModel):
    """Base request model for MCP tool calls."""
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class DeployServiceRequest(BaseModel):
    """Request model for deploy service tool."""
    service_name: str = Field(..., description="Name of the service to deploy", min_length=1)
    version: str = Field(..., description="Version to deploy", min_length=1)
    environment: str = Field(..., description="Target environment")
    
    @validator('environment')
    def validate_environment(cls, v):
        allowed_envs = ['development', 'staging', 'production']
        if v not in allowed_envs:
            raise ValueError(f'Environment must be one of: {", ".join(allowed_envs)}')
        return v


class RollbackDeploymentRequest(BaseModel):
    """Request model for rollback deployment tool."""
    deployment_id: str = Field(..., description="ID of the deployment to rollback", min_length=1)
    reason: str = Field(..., description="Reason for the rollback", min_length=1)
    environment: str = Field(..., description="Environment to rollback")
    
    @validator('environment')
    def validate_environment(cls, v):
        allowed_envs = ['staging', 'production']
        if v not in allowed_envs:
            raise ValueError(f'Environment must be one of: {", ".join(allowed_envs)}')
        return v


class AuthenticateUserRequest(BaseModel):
    """Request model for authenticate user tool."""
    session_token: str = Field(..., description="Descope session token", min_length=1)
    refresh_token: Optional[str] = Field(None, description="Descope refresh token (optional)")


class GetLogsRequest(BaseModel):
    """Request model for getting logs."""
    level: Optional[str] = Field(None, description="Log level filter")
    limit: int = Field(100, description="Maximum number of logs to return", ge=1, le=1000)
    since: Optional[str] = Field(None, description="Filter logs since timestamp (ISO format)")
    service: Optional[str] = Field(None, description="Filter by service name")
    
    @validator('level')
    def validate_level(cls, v):
        if v is not None:
            allowed_levels = ['DEBUG', 'INFO', 'WARN', 'ERROR']
            if v.upper() not in allowed_levels:
                raise ValueError(f'Level must be one of: {", ".join(allowed_levels)}')
            return v.upper()
        return v


class GetMetricsRequest(BaseModel):
    """Request model for getting metrics."""
    limit: int = Field(50, description="Maximum number of metrics to return", ge=1, le=1000)
    service: Optional[str] = Field(None, description="Filter by service name")
    metric_type: Optional[str] = Field(None, description="Type of metric to retrieve")


class MCPToolCallRequest(BaseModel):
    """Request model for MCP tool calls from Cequence Gateway."""
    params: Optional[Dict[str, Any]] = Field(None, description="MCP parameters")
    arguments: Optional[Dict[str, Any]] = Field(None, description="Tool arguments")
    
    def get_arguments(self) -> Dict[str, Any]:
        """Get arguments from either params.arguments or direct arguments."""
        if self.params and 'arguments' in self.params:
            return self.params['arguments']
        return self.arguments or {}


class ResourceRequest(BaseModel):
    """Base request model for resource operations."""
    limit: int = Field(100, description="Maximum number of items to return", ge=1, le=1000)
    offset: int = Field(0, description="Number of items to skip", ge=0)


class LogsResourceRequest(ResourceRequest):
    """Request model for logs resource."""
    level: Optional[str] = Field(None, description="Log level filter")
    since: Optional[str] = Field(None, description="Filter logs since timestamp (ISO format)")
    service: Optional[str] = Field(None, description="Filter by service name")
    
    @validator('level')
    def validate_level(cls, v):
        if v is not None:
            allowed_levels = ['DEBUG', 'INFO', 'WARN', 'ERROR']
            if v.upper() not in allowed_levels:
                raise ValueError(f'Level must be one of: {", ".join(allowed_levels)}')
            return v.upper()
        return v


class MetricsResourceRequest(ResourceRequest):
    """Request model for metrics resource."""
    service: Optional[str] = Field(None, description="Filter by service name")
    metric_type: Optional[str] = Field(None, description="Type of metric to retrieve")
    time_range: Optional[str] = Field(None, description="Time range for metrics (e.g., '1h', '24h', '7d')")
    
    @validator('time_range')
    def validate_time_range(cls, v):
        if v is not None:
            allowed_ranges = ['1h', '6h', '24h', '7d', '30d']
            if v not in allowed_ranges:
                raise ValueError(f'Time range must be one of: {", ".join(allowed_ranges)}')
        return v
