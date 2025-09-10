"""
MCP (Model Context Protocol) schemas package.

This package contains all the Pydantic models for MCP requests and responses,
providing type safety and validation for the MCP HTTP Server.
"""

from .requests import (
    AuthenticateUserRequest,
    DeployServiceRequest,
    GetLogsRequest,
    GetMetricsRequest,
    LogsResourceRequest,
    MCPToolCallRequest,
    MetricsResourceRequest,
    ResourceRequest,
    RollbackDeploymentRequest,
    ToolCallRequest,
)
from .resources import MCPResource, MCPResourceList, MCPTool, MCPToolList
from .responses import (
    AuthenticateUserResponse,
    DeploymentData,
    DeployServiceResponse,
    ErrorResponse,
    HealthResponse,
    LogEntry,
    LogsResponse,
    MCPResponse,
    MetricEntry,
    MetricsResponse,
    ResourceResponse,
    RollbackData,
    RollbackDeploymentResponse,
    ServerInfoResponse,
    ToolResponse,
    UserData,
)

__all__ = [
    # Requests
    "ToolCallRequest",
    "DeployServiceRequest",
    "RollbackDeploymentRequest",
    "AuthenticateUserRequest",
    "GetLogsRequest",
    "GetMetricsRequest",
    "MCPToolCallRequest",
    "ResourceRequest",
    "LogsResourceRequest",
    "MetricsResourceRequest",
    # Responses
    "MCPResponse",
    "ResourceResponse",
    "ToolResponse",
    "LogEntry",
    "MetricEntry",
    "DeploymentData",
    "RollbackData",
    "UserData",
    "ErrorResponse",
    "LogsResponse",
    "MetricsResponse",
    "DeployServiceResponse",
    "RollbackDeploymentResponse",
    "AuthenticateUserResponse",
    "ServerInfoResponse",
    "HealthResponse",
    # Resources
    "MCPResource",
    "MCPTool",
    "MCPResourceList",
    "MCPToolList",
]
