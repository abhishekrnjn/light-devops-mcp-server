# Light DevOps MCP Server

A comprehensive Model Context Protocol (MCP) server over HTTP that provides autonomous DevOps operations including deployment management, log monitoring, metrics collection, and rollback capabilities. Built with FastAPI using clean architecture principles and designed for enterprise environments with integrated authentication, security, and monitoring.

## Team Information

**Team Name:** [abhishekrnjn_5879]

**Team Members:** [Abhishek Ranjan]

## Hackathon Theme / Challenge

**Theme:** [Theme 2]

**Challenge Addressed:** Building an autonomous DevOps platform that enables AI agents to perform complex DevOps operations through a standardized Model Context Protocol (MCP) interface, with integrated security, monitoring, and role-based access controls for enterprise environments.

## Demo Video Link

[Demo video will be added here]

## Github Repo link

[https://github.com/abhishekrnjn/light-devops-mcp-server]

## What We Built

This project is a production-ready autonomous DevOps MCP server that provides:

### Core Capabilities
- **MCP Protocol Compliance**: Full implementation of Model Context Protocol over HTTP with 2 resources and 12 tools
- **Dual Mode Operation**: Seamless switching between direct mode and Cequence Gateway routing for enhanced security
- **Real-time Data Streaming**: Immediate dummy data responses while real API calls execute in background
- **Comprehensive Error Handling**: Robust fallback mechanisms and detailed error reporting

### DevOps Operations
- **Deployment Management**: Deploy services to multiple environments (development, staging, production) with environment-specific permissions
- **Rollback Capabilities**: Safe deployment rollbacks with comprehensive audit trails and reason validation
- **Log Monitoring**: Real-time log aggregation with level filtering (DEBUG, INFO, WARN, ERROR) and source tracking
- **Metrics Collection**: Performance and health metrics monitoring with customizable filtering and unit support

### Security & Authentication
- **Descope Integration**: Enterprise-grade authentication with JWT token validation and automatic refresh
- **Role-Based Access Control**: Granular permissions for different user roles (Observer, Developer, Developer_prod_access)
- **Environment-Specific Controls**: Staging vs production permission separation
- **Anonymous Access Support**: Development-friendly anonymous access mode

### Monitoring & Observability
- **Datadog Integration**: Optional advanced monitoring and logging with automatic fallback to mock data
- **Cequence Gateway**: Security gateway integration for audit trails and policy enforcement
- **Comprehensive Logging**: Structured logging with emoji indicators for easy debugging
- **Health Checks**: Built-in health monitoring and status reporting

### Key Features
- **Clean Architecture**: Domain-driven design with separated concerns (domain, infrastructure, schemas)
- **Async/Await**: Full asynchronous operation for high performance
- **Type Safety**: Comprehensive type hints and Pydantic models
- **Configuration Management**: Environment-based configuration with sensible defaults
- **Docker Support**: Containerized deployment with Dockerfile and production configuration
## How to Run

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd light-devops-mcp-server
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables** (optional for development)
   ```bash
   # Create .env file with optional configurations
   echo "AUTH_ALLOW_ANONYMOUS=true" > .env
   echo "CEQUENCE_ENABLED=false" >> .env
   ```

5. **Run the server**
   ```bash
   python mcp_http_server.py
   ```

   The server will start on `http://localhost:8001` (or port specified by `PORT` environment variable)

### Docker Deployment

1. **Build the Docker image**
   ```bash
   docker build -t light-devops-mcp-server .
   ```

2. **Run the container**
   ```bash
   docker run -p 8000:8000 light-devops-mcp-server
   ```

### Production Deployment (Render.com)

The project includes `render.yaml` configuration for easy deployment on Render.com:

1. Connect your GitHub repository to Render
2. Set the required environment variables in Render dashboard:
   - `CEQUENCE_GATEWAY_URL` (if using Cequence)
   - `DESCOPE_PROJECT_ID` (if using Descope auth)
   - `DESCOPE_MANAGEMENT_KEY` (if using Descope auth)
   - `DD_API_KEY` and `DD_APP_KEY` (if using Datadog)

### API Endpoints

#### Core MCP Endpoints
- `GET /` - Server information, capabilities, and available endpoints
- `GET /mcp/resources` - List all available MCP resources (logs, metrics)
- `GET /mcp/resources/logs` - Get system logs with optional filtering (level, limit, since)
- `GET /mcp/resources/metrics` - Get performance metrics with optional filtering (limit, service)
- `GET /mcp/resources/{resource_path}` - Read specific resource by URI path
- `GET /mcp/tools` - List all available MCP tools

#### DevOps Operations
- `POST /mcp/tools/deploy_service` - Deploy a service to specific environment
- `POST /mcp/tools/rollback_deployment` - Rollback a deployment with reason and environment
- `POST /mcp/tools/authenticate_user` - Authenticate user and get permissions

#### Cequence Gateway MCP Tools (for gateway integration)
- `POST /mcp/tools/getMcpResourcesLogs` - Get logs via MCP tool call
- `POST /mcp/tools/getMcpResourcesMetrics` - Get metrics via MCP tool call
- `POST /mcp/tools/postMcpToolsDeployService` - Deploy service via MCP tool call
- `POST /mcp/tools/postMcpToolsRollbackDeployment` - Rollback via MCP tool call
- `POST /mcp/tools/postMcpToolsAuthenticateUser` - Authenticate via MCP tool call
- `POST /mcp/tools/get` - Server information via MCP tool call
- `POST /mcp/tools/getMcpResources` - List resources via MCP tool call
- `POST /mcp/tools/getMcpTools` - List tools via MCP tool call

## Tech Stack

### Core Technologies
- **Python 3.10+**: Core programming language with async/await support
- **FastAPI**: Modern, fast web framework with automatic OpenAPI documentation
- **Uvicorn**: High-performance ASGI server for production deployment
- **Pydantic**: Data validation, serialization, and settings management
- **HTTPX**: Async HTTP client for external API calls and Cequence Gateway integration

### Authentication & Security
- **Descope**: Enterprise authentication platform with JWT token management
- **JWT**: JSON Web Tokens for secure session management
- **RBAC**: Role-based access control with granular permissions
- **Cequence Gateway**: Security gateway for audit trails and policy enforcement

### Monitoring & Observability
- **Datadog API**: Advanced monitoring, logging, and metrics collection
- **Structured Logging**: Comprehensive logging with emoji indicators
- **Mock Data Generation**: Realistic dummy data for immediate UI responses
- **Health Monitoring**: Built-in health checks and status reporting

### Infrastructure & Deployment
- **Docker**: Containerization with multi-stage builds
- **Render.com**: Cloud deployment platform with automatic scaling
- **Environment Configuration**: Flexible configuration management
- **CORS Support**: Cross-origin resource sharing for frontend integration

### Development & Code Quality
- **Black**: Code formatting with 88-character line length
- **isort**: Import sorting with Black profile compatibility
- **MyPy**: Static type checking with strict mode
- **Ruff**: Fast Python linter and formatter
- **Pre-commit**: Git hooks for automated code quality checks
- **Type Hints**: Comprehensive type annotations throughout codebase



## What We'd Do With More Time

### Enhanced Real-time Features
- **Server-Sent Events (SSE)**: Implement true real-time streaming for logs and metrics
- **WebSocket Support**: Bidirectional communication for live updates
- **Real-time Notifications**: Push notifications for deployment status changes
- **Live Dashboard Updates**: Automatic UI refresh without manual polling

### Advanced Monitoring & Observability
- **Custom Dashboards**: User-configurable monitoring dashboards with drag-and-drop widgets
- **Alert Management**: Intelligent alerting with AI-powered noise reduction
- **Performance Analytics**: Advanced performance trend analysis and reporting
- **Cost Optimization**: AI-driven resource optimization recommendations

### Enterprise Features
- **Multi-tenant Architecture**: Enhanced tenant isolation with dedicated resources
- **Audit Logging**: Comprehensive audit trails with searchable history
- **Compliance Frameworks**: Built-in support for SOC2, GDPR, HIPAA compliance
- **Integration Hub**: Pre-built connectors for popular DevOps tools (Jenkins, GitLab, etc.)

### Performance & Scalability
- **Redis Caching**: Distributed caching layer for improved response times
- **Database Integration**: PostgreSQL/MongoDB for persistent storage and history
- **Load Balancing**: Horizontal scaling with multiple server instances
- **Rate Limiting**: Advanced rate limiting with per-user and per-endpoint controls

### Security Enhancements
- **API Key Management**: Secure API key rotation and management system
- **End-to-End Encryption**: Encryption for sensitive data in transit and at rest
- **Vulnerability Scanning**: Automated security scanning and dependency updates




