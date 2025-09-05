# DevOps MCP Server

A **Model Context Protocol (MCP)** server that provides DevOps operations through a standardized interface. Supports both stdio and HTTP protocols for maximum compatibility.

## 🚀 Overview

This MCP server exposes DevOps operations including:
- **System Logs** monitoring and filtering
- **Metrics** collection and analysis  
- **Deployment** management and history
- **Rollback** operations and tracking
- **Health** monitoring and status
- **Authentication** via Descope integration

## 📋 Available Resources (2)

Resources represent data that clients can read:

| Resource URI | Name | Description | Query Parameters |
|--------------|------|-------------|------------------|
| `logs` | System Logs | Application and system logs | `?level=ERROR&limit=10` |
| `metrics` | System Metrics | Performance and health metrics | `?limit=50` |

## 🔧 Available Tools (3)

Tools represent actions that clients can perform:

| Tool Name | Description | Required Parameters |
|-----------|-------------|-------------------|
| `deploy_service` | Deploy a service to a specific environment | `service_name`, `version`, `environment` |
| `rollback_deployment` | Rollback a deployment to previous version | `deployment_id`, `reason` |
| `authenticate_user` | Authenticate user and get permissions | `session_token` (optional: `refresh_token`) |

## 🌐 HTTP Protocol Usage

### Start the HTTP Server

```bash
python mcp_http_server.py
```

Server runs on `http://localhost:8001`

### Discover Resources

```bash
curl http://localhost:8001/mcp/resources
```

### Read a Resource

```bash
# Get all logs
curl http://localhost:8001/mcp/resources/logs

# Get error logs only
curl "http://localhost:8001/mcp/resources/logs?level=ERROR&limit=10"

# Get metrics
curl http://localhost:8001/mcp/resources/metrics

# Get limited metrics
curl "http://localhost:8001/mcp/resources/metrics?limit=5"
```

### Discover Tools

```bash
curl http://localhost:8001/mcp/tools
```

### Call a Tool

```bash
# Deploy a service
curl -X POST http://localhost:8001/mcp/tools/deploy_service \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"service_name": "my-app", "version": "1.2.3", "environment": "staging"}}'

# Rollback a deployment
curl -X POST http://localhost:8001/mcp/tools/rollback_deployment \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"deployment_id": "deploy-123", "reason": "Critical bug found"}}'

# Authenticate user
curl -X POST http://localhost:8001/mcp/tools/authenticate_user \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"session_token": "your-jwt-token-here"}}'
```

### Authentication Required

All MCP endpoints (except root `/`) require valid JWT authentication:

```bash
# All requests need Authorization header
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" http://localhost:8001/mcp/resources

# Without token - returns 401
curl http://localhost:8001/mcp/resources
# {"detail":"Authentication required - no session token provided"}
```

### Permission-Based Access

Each resource and tool checks specific permissions:

```bash
# Logs require "read_logs" permission
curl -H "Authorization: Bearer JWT" http://localhost:8001/mcp/resources/logs

# Metrics require "read_metrics" permission  
curl -H "Authorization: Bearer JWT" http://localhost:8001/mcp/resources/metrics

# Deploy to production requires "deploy_production" permission
curl -X POST -H "Authorization: Bearer JWT" http://localhost:8001/mcp/tools/deploy_service \
  -d '{"arguments": {"environment": "production", ...}}'
```

## 📡 Stdio Protocol Usage

### Start the Stdio Server

```bash
python mcp_server.py
```

### Test with Python Client

```python
python test_mcp_client.py
```

Choose option 1 for full testing or option 2 for resource discovery only.

## 🌐 Web Client

Open `test_mcp_web_client.html` in a browser to test the HTTP server with a visual interface.

Features:
- ✅ Server status checking
- 📋 Resource discovery and reading
- 🔧 Tool discovery and execution
- 📡 Real-time streaming events
- 🎨 Interactive parameter forms

## 🔐 Authentication

The server supports Descope authentication:

1. **Session Validation**: Validate JWT tokens from Descope
2. **Permission Checking**: Check user roles and permissions
3. **Automatic Refresh**: Handle token refresh automatically

### Example Authentication

```bash
curl -X POST http://localhost:8001/mcp/tools/authenticate_user \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"session_token": "your-jwt-token-here"}}'
```

## 📊 Response Formats

### Resource Response
```json
{
  "uri": "logs",
  "type": "logs",
  "count": 3,
  "filters": {
    "level": "ERROR",
    "limit": 10
  },
  "data": [
    {
      "level": "ERROR",
      "message": "Database connection failed",
      "timestamp": "2025-09-06T01:40:10.390015",
      "source": "system"
    }
  ]
}
```

### Tool Response
```json
{
  "tool": "deploy_service",
  "success": true,
  "result": {
    "service_name": "my-app",
    "version": "1.2.3",
    "environment": "staging",
    "status": "SUCCESS",
    "timestamp": "2025-09-06T01:40:10.390015"
  }
}
```

### Error Response
```json
{
  "tool": "deploy_service",
  "success": false,
  "error": "Invalid environment specified"
}
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Client    │────│  MCP Server     │────│  DevOps Services│
│                 │    │                 │    │                 │
│ • Discovery     │    │ • 2 Resources   │    │ • Logs Client   │
│ • Tool Calls    │    │ • 3 Tools       │    │ • Metrics Client│
│ • Streaming     │    │ • Auth          │    │ • Deploy Client │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   export DESCOPE_PROJECT_ID="your-project-id"
   export DESCOPE_MANAGEMENT_KEY="your-management-key"
   ```

3. **Start HTTP server**:
   ```bash
   python mcp_http_server.py
   ```

4. **Test with web client**:
   Open `test_mcp_web_client.html` in browser

5. **Test with curl**:
   ```bash
   # Discover resources
   curl http://localhost:8001/mcp/resources
   
   # Read logs
   curl "http://localhost:8001/mcp/resources/logs?level=ERROR&limit=5"
   
   # Deploy service
   curl -X POST http://localhost:8001/mcp/tools/deploy_service \
     -H "Content-Type: application/json" \
     -d '{"arguments": {"service_name": "test-app", "version": "1.0.0", "environment": "staging"}}'
   ```

## 🎯 Use Cases

- **Infrastructure Monitoring**: Real-time system health and metrics
- **Deployment Automation**: Automated deployments with rollback capabilities  
- **Log Analysis**: Centralized log collection and filtering
- **DevOps Dashboards**: MCP-compatible dashboards and tools
- **CI/CD Integration**: Integration with existing CI/CD pipelines
- **Incident Response**: Quick access to system status and remediation tools

## 📈 Features

- ✅ **MCP Compliant**: Full MCP protocol support
- 🌐 **HTTP & Stdio**: Multiple transport protocols
- 🔐 **Secure by Default**: JWT authentication with RBAC on all endpoints
- 📊 **Clean Resources**: 2 focused resource types (logs, metrics)
- 🛠️ **Action Tools**: 3 operational tools (deploy, rollback, auth)
- 🎨 **Web Interface**: Interactive testing interface
- 📝 **Portable URIs**: Deployment-agnostic resource addressing
- 🛡️ **Permission-based Access**: Fine-grained authorization per resource/tool

## 🤝 Client Integration

Any MCP-compatible client can integrate with this server:

1. **Discover** available resources and tools
2. **Read** resource data for monitoring
3. **Execute** tools for operations
4. **Stream** real-time events
5. **Authenticate** users with Descope

The server follows MCP standards, ensuring compatibility with the growing ecosystem of MCP clients and tools.
