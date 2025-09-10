"""
Resource models for MCP HTTP Server.

This module contains Pydantic models for MCP resources and tools,
providing type safety and validation for resource definitions.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MCPResource(BaseModel):
    """Model for MCP resources."""
    uri: str = Field(..., description="Resource URI")
    name: str = Field(..., description="Resource name")
    description: str = Field(..., description="Resource description")
    mimeType: str = Field(..., description="Resource MIME type")
    capabilities: Optional[Dict[str, Any]] = Field(None, description="Resource capabilities")
    filters: Optional[Dict[str, Any]] = Field(None, description="Available filters")


class MCPTool(BaseModel):
    """Model for MCP tools."""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    inputSchema: Dict[str, Any] = Field(..., description="Tool input schema")
    capabilities: Optional[Dict[str, Any]] = Field(None, description="Tool capabilities")
    examples: Optional[List[Dict[str, Any]]] = Field(None, description="Usage examples")


class MCPCapabilities(BaseModel):
    """Model for MCP server capabilities."""
    resources: int = Field(..., description="Number of available resources")
    tools: int = Field(..., description="Number of available tools")
    streaming: bool = Field(False, description="Whether streaming is supported")
    authentication: bool = Field(True, description="Whether authentication is required")
    rate_limiting: bool = Field(False, description="Whether rate limiting is enabled")
    audit_logging: bool = Field(False, description="Whether audit logging is enabled")


class MCPResourceList(BaseModel):
    """Model for listing MCP resources."""
    resources: List[MCPResource] = Field(..., description="List of available resources")
    total: int = Field(..., description="Total number of resources")
    capabilities: Optional[MCPCapabilities] = Field(None, description="Server capabilities")


class MCPToolList(BaseModel):
    """Model for listing MCP tools."""
    tools: List[MCPTool] = Field(..., description="List of available tools")
    total: int = Field(..., description="Total number of tools")
    capabilities: Optional[MCPCapabilities] = Field(None, description="Server capabilities")


# Predefined MCP resources
MCP_RESOURCES = [
    MCPResource(
        uri="logs",
        name="System Logs",
        description="Application and system logs with filtering capabilities",
        mimeType="application/json",
        capabilities={
            "filtering": ["level", "service", "since"],
            "pagination": True,
            "real_time": False,
        },
        filters={
            "level": {
                "type": "enum",
                "values": ["DEBUG", "INFO", "WARN", "ERROR"],
                "description": "Filter by log level"
            },
            "service": {
                "type": "string",
                "description": "Filter by service name"
            },
            "since": {
                "type": "datetime",
                "description": "Filter logs since timestamp (ISO format)"
            },
            "limit": {
                "type": "integer",
                "min": 1,
                "max": 1000,
                "default": 100,
                "description": "Maximum number of logs to return"
            }
        }
    ),
    MCPResource(
        uri="metrics",
        name="System Metrics",
        description="Performance and health metrics with optional filtering",
        mimeType="application/json",
        capabilities={
            "filtering": ["service", "metric_type", "time_range"],
            "pagination": True,
            "real_time": False,
        },
        filters={
            "service": {
                "type": "string",
                "description": "Filter by service name"
            },
            "metric_type": {
                "type": "string",
                "description": "Type of metric to retrieve"
            },
            "time_range": {
                "type": "enum",
                "values": ["1h", "6h", "24h", "7d", "30d"],
                "default": "1h",
                "description": "Time range for metrics"
            },
            "limit": {
                "type": "integer",
                "min": 1,
                "max": 1000,
                "default": 50,
                "description": "Maximum number of metrics to return"
            }
        }
    ),
]

# Predefined MCP tools
MCP_TOOLS = [
    MCPTool(
        name="deploy_service",
        description="Deploy a service to a specific environment",
        inputSchema={
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "Name of the service to deploy",
                    "minLength": 1
                },
                "version": {
                    "type": "string",
                    "description": "Version to deploy",
                    "minLength": 1
                },
                "environment": {
                    "type": "string",
                    "enum": ["development", "staging", "production"],
                    "description": "Target environment"
                }
            },
            "required": ["service_name", "version", "environment"],
            "additionalProperties": False
        },
        capabilities={
            "environments": ["development", "staging", "production"],
            "rollback": True,
            "validation": True,
        },
        examples=[
            {
                "service_name": "payment-service",
                "version": "v1.2.3",
                "environment": "staging"
            }
        ]
    ),
    MCPTool(
        name="rollback_deployment",
        description="Rollback a deployment to previous version",
        inputSchema={
            "type": "object",
            "properties": {
                "deployment_id": {
                    "type": "string",
                    "description": "ID of the deployment to rollback",
                    "minLength": 1
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for the rollback",
                    "minLength": 1
                },
                "environment": {
                    "type": "string",
                    "enum": ["staging", "production"],
                    "description": "Environment to rollback"
                }
            },
            "required": ["deployment_id", "reason", "environment"],
            "additionalProperties": False
        },
        capabilities={
            "environments": ["staging", "production"],
            "validation": True,
            "audit": True,
        },
        examples=[
            {
                "deployment_id": "deploy-123456",
                "reason": "Critical bug in production",
                "environment": "production"
            }
        ]
    ),
    MCPTool(
        name="authenticate_user",
        description="Authenticate user and get permissions",
        inputSchema={
            "type": "object",
            "properties": {
                "session_token": {
                    "type": "string",
                    "description": "Descope session token",
                    "minLength": 1
                },
                "refresh_token": {
                    "type": "string",
                    "description": "Descope refresh token (optional)"
                }
            },
            "required": ["session_token"],
            "additionalProperties": False
        },
        capabilities={
            "jwt_validation": True,
            "permission_extraction": True,
            "role_mapping": True,
        },
        examples=[
            {
                "session_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        ]
    ),
    MCPTool(
        name="getMcpResourcesLogs",
        description="Get system logs with optional filtering",
        inputSchema={
            "type": "object",
            "properties": {
                "level": {
                    "type": "string",
                    "enum": ["DEBUG", "INFO", "WARN", "ERROR"],
                    "description": "Log level filter"
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "default": 100,
                    "description": "Limit number of results"
                },
                "since": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Filter logs since timestamp (ISO format)"
                },
                "service": {
                    "type": "string",
                    "description": "Filter by service name"
                }
            },
            "additionalProperties": False
        },
        capabilities={
            "filtering": True,
            "pagination": True,
            "real_time": False,
        }
    ),
    MCPTool(
        name="getMcpResourcesMetrics",
        description="Get performance metrics with optional filtering",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1000,
                    "default": 50,
                    "description": "Limit number of results"
                },
                "service": {
                    "type": "string",
                    "description": "Filter by service name"
                },
                "metric_type": {
                    "type": "string",
                    "description": "Type of metric to retrieve"
                },
                "time_range": {
                    "type": "string",
                    "enum": ["1h", "6h", "24h", "7d", "30d"],
                    "default": "1h",
                    "description": "Time range for metrics"
                }
            },
            "additionalProperties": False
        },
        capabilities={
            "filtering": True,
            "pagination": True,
            "time_ranges": True,
        }
    ),
]
