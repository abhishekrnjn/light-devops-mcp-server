"""
MCP (Model Context Protocol) schemas package.

This package contains all the Pydantic models for MCP requests and responses,
providing type safety and validation for the MCP HTTP Server.
"""

from .requests import (
    ToolCallRequest,
    DeployServiceRequest,
    RollbackDeploymentRequest,
    AuthenticateUserRequest,
    GetLogsRequest,
    GetMetricsRequest,
    MCPToolCallRequest,
    ResourceRequest,
    LogsResourceRequest,
    MetricsResourceRequest,
)
from .responses import (
    MCPResponse,
    ResourceResponse,
    ToolResponse,
    LogEntry,
    MetricEntry,
    DeploymentData,
    RollbackData,
    UserData,
    ErrorResponse,
    LogsResponse,
    MetricsResponse,
    DeployServiceResponse,
    RollbackDeploymentResponse,
    AuthenticateUserResponse,
    ServerInfoResponse,
    HealthResponse,
)
from .resources import MCPResource, MCPTool, MCPResourceList, MCPToolList

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
