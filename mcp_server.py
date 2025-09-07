#!/usr/bin/env python3
"""
DevOps MCP Server

A Model Context Protocol server that provides DevOps operations including:
- System logs monitoring
- Metrics collection 
- Deployment management
- Rollback operations
- Authentication and authorization via Descope

Supports resource discovery and tool calling via MCP protocol.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel,
)

from app.config import settings
from app.infrastructure.auth.descope_client import descope_client
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

# Initialize services
log_service = LogService(LogsClient())
metrics_service = MetricsService(MetricsClient())
deploy_service = DeployService(CICDClient())
rollback_service = RollbackService(RollbackClient())

# Create MCP server
server = Server("devops-mcp-server")

@server.list_resources()
async def handle_list_resources() -> List[Resource]:
    """
    List all available DevOps resources that clients can access.
    Resources represent data that can be read by the client.
    """
    return [
        Resource(
            uri="devops://logs/recent",
            name="Recent System Logs",
            description="Recent system logs with filtering capabilities",
            mimeType="application/json",
        ),
        Resource(
            uri="devops://logs/errors",
            name="Error Logs",
            description="System error logs for troubleshooting",
            mimeType="application/json",
        ),
        Resource(
            uri="devops://metrics/system",
            name="System Metrics",
            description="Current system performance metrics",
            mimeType="application/json",
        ),
        Resource(
            uri="devops://metrics/application",
            name="Application Metrics",
            description="Application-specific performance metrics",
            mimeType="application/json",
        ),
        Resource(
            uri="devops://deployments/history",
            name="Deployment History",
            description="Recent deployment history and status",
            mimeType="application/json",
        ),
        Resource(
            uri="devops://deployments/active",
            name="Active Deployments",
            description="Currently running deployments",
            mimeType="application/json",
        ),
        Resource(
            uri="devops://rollbacks/history",
            name="Rollback History",
            description="History of rollback operations",
            mimeType="application/json",
        ),
        Resource(
            uri="devops://health/status",
            name="System Health",
            description="Overall system health status",
            mimeType="application/json",
        ),
    ]

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """
    Read a specific DevOps resource by URI.
    This allows clients to fetch the actual data.
    """
    logger.info(f"📖 Reading resource: {uri}")
    
    try:
        if uri == "devops://logs/recent":
            logs = await log_service.get_recent_logs()
            return {
                "type": "logs",
                "count": len(logs),
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
        
        elif uri == "devops://logs/errors":
            logs = await log_service.get_recent_logs()
            error_logs = [log for log in logs if log.level == "ERROR"]
            return {
                "type": "error_logs",
                "count": len(error_logs),
                "data": [
                    {
                        "level": log.level,
                        "message": log.message,
                        "timestamp": log.timestamp,
                        "source": getattr(log, 'source', 'system')
                    }
                    for log in error_logs
                ]
            }
        
        elif uri == "devops://metrics/system":
            metrics = await metrics_service.get_recent_metrics()
            system_metrics = [m for m in metrics if m.name.startswith(('cpu', 'memory', 'disk', 'network'))]
            return {
                "type": "system_metrics",
                "count": len(system_metrics),
                "data": [
                    {
                        "name": metric.name,
                        "value": metric.value,
                        "unit": metric.unit,
                        "timestamp": getattr(metric, 'timestamp', datetime.now().isoformat())
                    }
                    for metric in system_metrics
                ]
            }
        
        elif uri == "devops://metrics/application":
            metrics = await metrics_service.get_recent_metrics()
            app_metrics = [m for m in metrics if not m.name.startswith(('cpu', 'memory', 'disk', 'network'))]
            return {
                "type": "application_metrics",
                "count": len(app_metrics),
                "data": [
                    {
                        "name": metric.name,
                        "value": metric.value,
                        "unit": metric.unit,
                        "timestamp": getattr(metric, 'timestamp', datetime.now().isoformat())
                    }
                    for metric in app_metrics
                ]
            }
        
        elif uri == "devops://deployments/history":
            deployments = await deploy_service.get_recent_deployments()
            return {
                "type": "deployment_history",
                "count": len(deployments),
                "data": [
                    {
                        "service_name": deploy.service_name,
                        "version": deploy.version,
                        "environment": deploy.environment,
                        "status": deploy.status,
                        "timestamp": deploy.timestamp
                    }
                    for deploy in deployments
                ]
            }
        
        elif uri == "devops://deployments/active":
            deployments = await deploy_service.get_recent_deployments()
            active_deployments = [d for d in deployments if d.status == "PENDING"]
            return {
                "type": "active_deployments",
                "count": len(active_deployments),
                "data": [
                    {
                        "service_name": deploy.service_name,
                        "version": deploy.version,
                        "environment": deploy.environment,
                        "status": deploy.status,
                        "timestamp": deploy.timestamp
                    }
                    for deploy in active_deployments
                ]
            }
        
        elif uri == "devops://rollbacks/history":
            rollbacks = await rollback_service.get_recent_rollbacks()
            return {
                "type": "rollback_history",
                "count": len(rollbacks),
                "data": [
                    {
                        "reason": rollback.reason,
                        "status": rollback.status,
                        "timestamp": rollback.timestamp,
                        "deployment_id": getattr(rollback, 'deployment_id', None)
                    }
                    for rollback in rollbacks
                ]
            }
        
        elif uri == "devops://health/status":
            # Aggregate health status
            try:
                logs = await log_service.get_recent_logs()
                metrics = await metrics_service.get_recent_metrics()
                deployments = await deploy_service.get_recent_deployments()
                
                error_count = len([log for log in logs if log.level == "ERROR"])
                failed_deployments = len([d for d in deployments if d.status == "FAILED"])
                
                health_score = max(0, 100 - (error_count * 5) - (failed_deployments * 10))
                status = "healthy" if health_score > 80 else "degraded" if health_score > 50 else "unhealthy"
                
                return {
                    "type": "health_status",
                    "status": status,
                    "health_score": health_score,
                    "details": {
                        "error_count": error_count,
                        "failed_deployments": failed_deployments,
                        "total_logs": len(logs),
                        "total_metrics": len(metrics),
                        "total_deployments": len(deployments)
                    },
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                return {
                    "type": "health_status",
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        else:
            raise ValueError(f"Unknown resource URI: {uri}")
    
    except Exception as e:
        logger.error(f"❌ Error reading resource {uri}: {e}")
        return {
            "type": "error",
            "error": str(e),
            "uri": uri,
            "timestamp": datetime.now().isoformat()
        }

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """
    List all available DevOps tools that clients can call.
    Tools represent actions that can be performed.
    """
    return [
        Tool(
            name="deploy_service",
            description="Deploy a service to a specific environment",
            inputSchema={
                "type": "object",
                "properties": {
                    "service_name": {
                        "type": "string",
                        "description": "Name of the service to deploy"
                    },
                    "version": {
                        "type": "string",
                        "description": "Version to deploy"
                    },
                    "environment": {
                        "type": "string",
                        "enum": ["development", "staging", "production"],
                        "description": "Target environment"
                    }
                },
                "required": ["service_name", "version", "environment"]
            }
        ),
        Tool(
            name="rollback_staging",
            description="Rollback a staging deployment to previous version",
            inputSchema={
                "type": "object",
                "properties": {
                    "deployment_id": {
                        "type": "string",
                        "description": "ID of the staging deployment to rollback"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for the rollback"
                    }
                },
                "required": ["deployment_id", "reason"]
            }
        ),
        Tool(
            name="rollback_production",
            description="Rollback a production deployment to previous version",
            inputSchema={
                "type": "object",
                "properties": {
                    "deployment_id": {
                        "type": "string",
                        "description": "ID of the production deployment to rollback"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for the rollback"
                    }
                },
                "required": ["deployment_id", "reason"]
            }
        ),
        Tool(
            name="get_logs",
            description="Get system logs with optional filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "level": {
                        "type": "string",
                        "enum": ["INFO", "WARNING", "ERROR"],
                        "description": "Filter logs by level"
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1000,
                        "default": 100,
                        "description": "Maximum number of logs to return"
                    },
                    "since": {
                        "type": "string",
                        "description": "ISO timestamp to get logs since"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_metrics",
            description="Get system metrics with optional filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "metric_type": {
                        "type": "string",
                        "enum": ["system", "application", "all"],
                        "default": "all",
                        "description": "Type of metrics to retrieve"
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1000,
                        "default": 100,
                        "description": "Maximum number of metrics to return"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="check_health",
            description="Check overall system health status",
            inputSchema={
                "type": "object",
                "properties": {
                    "detailed": {
                        "type": "boolean",
                        "default": False,
                        "description": "Return detailed health information"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="authenticate_user",
            description="Authenticate user and get permissions",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_token": {
                        "type": "string",
                        "description": "Descope session token"
                    },
                    "refresh_token": {
                        "type": "string",
                        "description": "Descope refresh token (optional)"
                    }
                },
                "required": ["session_token"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """
    Handle tool calls from clients.
    This is where the actual DevOps operations are performed.
    """
    logger.info(f"🔧 Tool called: {name} with arguments: {arguments}")
    
    try:
        if name == "deploy_service":
            service_name = arguments["service_name"]
            version = arguments["version"]
            environment = arguments["environment"]
            
            # Perform deployment
            result = await deploy_service.deploy(service_name, version, environment)
            
            return [
                TextContent(
                    type="text",
                    text=f"✅ Deployment initiated successfully!\n\n"
                         f"Service: {result.service_name}\n"
                         f"Version: {result.version}\n"
                         f"Environment: {result.environment}\n"
                         f"Status: {result.status}\n"
                         f"Timestamp: {result.timestamp}"
                )
            ]
        
        elif name == "rollback_staging":
            deployment_id = arguments["deployment_id"]
            reason = arguments["reason"]
            
            # Perform staging rollback
            result = await rollback_service.rollback(deployment_id, reason, environment="staging")
            
            return [
                TextContent(
                    type="text",
                    text=f"🔄 Staging rollback initiated successfully!\n\n"
                         f"Deployment ID: {deployment_id}\n"
                         f"Environment: staging\n"
                         f"Reason: {result.reason}\n"
                         f"Status: {result.status}\n"
                         f"Timestamp: {result.timestamp}"
                )
            ]
        
        elif name == "rollback_production":
            deployment_id = arguments["deployment_id"]
            reason = arguments["reason"]
            
            # Perform production rollback
            result = await rollback_service.rollback(deployment_id, reason, environment="production")
            
            return [
                TextContent(
                    type="text",
                    text=f"🔄 Production rollback initiated successfully!\n\n"
                         f"Deployment ID: {deployment_id}\n"
                         f"Environment: production\n"
                         f"Reason: {result.reason}\n"
                         f"Status: {result.status}\n"
                         f"Timestamp: {result.timestamp}"
                )
            ]
        
        elif name == "get_logs":
            level = arguments.get("level")
            limit = arguments.get("limit", 100)
            since = arguments.get("since")
            
            # Get logs with filtering
            logs = await log_service.get_recent_logs()
            
            # Apply filters
            if level:
                logs = [log for log in logs if log.level == level]
            
            # Apply limit
            logs = logs[:limit]
            
            log_text = "\n".join([
                f"[{log.timestamp}] {log.level}: {log.message}"
                for log in logs
            ])
            
            return [
                TextContent(
                    type="text",
                    text=f"📝 System Logs (showing {len(logs)} entries):\n\n{log_text}"
                )
            ]
        
        elif name == "get_metrics":
            metric_type = arguments.get("metric_type", "all")
            limit = arguments.get("limit", 100)
            
            # Get metrics with filtering
            metrics = await metrics_service.get_recent_metrics()
            
            # Apply type filter
            if metric_type == "system":
                metrics = [m for m in metrics if m.name.startswith(('cpu', 'memory', 'disk', 'network'))]
            elif metric_type == "application":
                metrics = [m for m in metrics if not m.name.startswith(('cpu', 'memory', 'disk', 'network'))]
            
            # Apply limit
            metrics = metrics[:limit]
            
            metrics_text = "\n".join([
                f"{metric.name}: {metric.value} {metric.unit}"
                for metric in metrics
            ])
            
            return [
                TextContent(
                    type="text",
                    text=f"📊 System Metrics (showing {len(metrics)} entries):\n\n{metrics_text}"
                )
            ]
        
        elif name == "check_health":
            detailed = arguments.get("detailed", False)
            
            # Get health status
            try:
                logs = await log_service.get_recent_logs()
                metrics = await metrics_service.get_recent_metrics()
                deployments = await deploy_service.get_recent_deployments()
                
                error_count = len([log for log in logs if log.level == "ERROR"])
                failed_deployments = len([d for d in deployments if d.status == "FAILED"])
                
                health_score = max(0, 100 - (error_count * 5) - (failed_deployments * 10))
                status = "healthy" if health_score > 80 else "degraded" if health_score > 50 else "unhealthy"
                
                if detailed:
                    health_text = f"🏥 System Health Status: {status.upper()}\n\n" \
                                f"Health Score: {health_score}/100\n" \
                                f"Error Count: {error_count}\n" \
                                f"Failed Deployments: {failed_deployments}\n" \
                                f"Total Logs: {len(logs)}\n" \
                                f"Total Metrics: {len(metrics)}\n" \
                                f"Total Deployments: {len(deployments)}"
                else:
                    health_text = f"🏥 System Health: {status.upper()} (Score: {health_score}/100)"
                
                return [
                    TextContent(
                        type="text",
                        text=health_text
                    )
                ]
            
            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=f"❌ Health check failed: {str(e)}"
                    )
                ]
        
        elif name == "authenticate_user":
            session_token = arguments["session_token"]
            refresh_token = arguments.get("refresh_token")
            
            # Validate session with Descope
            try:
                jwt_response = descope_client.validate_session(
                    session_token=session_token,
                    refresh_token=refresh_token
                )
                
                # Extract user principal
                user_principal = descope_client.extract_user_principal(jwt_response, session_token)
                
                return [
                    TextContent(
                        type="text",
                        text=f"✅ Authentication successful!\n\n"
                             f"User ID: {user_principal.user_id}\n"
                             f"Name: {user_principal.name}\n"
                             f"Email: {user_principal.email}\n"
                             f"Roles: {', '.join(user_principal.roles)}\n"
                             f"Permissions: {', '.join(user_principal.permissions)}\n"
                             f"Tenant: {user_principal.tenant}"
                    )
                ]
            
            except Exception as e:
                return [
                    TextContent(
                        type="text",
                        text=f"❌ Authentication failed: {str(e)}"
                    )
                ]
        
        else:
            return [
                TextContent(
                    type="text",
                    text=f"❌ Unknown tool: {name}"
                )
            ]
    
    except Exception as e:
        logger.error(f"❌ Error executing tool {name}: {e}")
        return [
            TextContent(
                type="text",
                text=f"❌ Error executing {name}: {str(e)}"
            )
        ]

async def main():
    """Main entry point for the MCP server."""
    logger.info("🚀 Starting DevOps MCP Server...")
    logger.info(f"📋 Server capabilities:")
    logger.info(f"   - Resources: 8 available")
    logger.info(f"   - Tools: 6 available")
    logger.info(f"   - Authentication: Descope integration")
    logger.info(f"   - Protocol: MCP over stdio")
    
    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="devops-mcp-server",
                server_version="0.1.0",
                capabilities={
                    "resources": {},
                    "tools": {},
                    "logging": {},
                }
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
