# Light DevOps MCP Server

A Model Context Protocol (MCP) server over HTTP that provides DevOps operations including deployment management, log monitoring, metrics collection, and rollback capabilities. Built with FastAPI and designed for autonomous DevOps operations with integrated authentication and monitoring.

## Team Information

**Team Name:** [abhishekrnjn_5879]

**Team Members:** [Abhishek Ranjan]

## Hackathon Theme / Challenge

**Theme:** [Theme 2]

**Challenge Addressed:** Building an autonomous DevOps platform that enables AI agents to perform complex DevOps operations through a standardized Model Context Protocol (MCP) interface, with integrated security, monitoring, and role-based access controls for enterprise environments.

## What We Built

This project is an autonomous DevOps MCP server that provides:


- **Authentication & Authorization**: Integrated Descope authentication with role-based access control (RBAC)
- **Cequence Gateway Integration**: Integration with Cequence Gateway for enhanced security and monitoring
- **Datadog Integration**: Optional integration with Datadog for advanced monitoring and logging
- **Deployment Management**: Deploy services to different environments (development, staging, production) with proper permission controls with chatbot and webui
- **Rollback Capabilities**: Safely rollback deployments with audit trails and environment-specific permissions
- **Log Monitoring**: Real-time log aggregation and filtering with support for different log levels
- **Metrics Collection**: Performance and health metrics monitoring with customizable filtering

### Key Features

- **MCP Protocol Compliance**: Implements Model Context Protocol over HTTP for standardized AI agent interactions
- **Dual Mode Operation**: Works both directly and through Cequence Gateway for enhanced security
- **Role-Based Access Control**: Granular permissions for different user roles (Observer, Developer, Production Access)
- **Environment-Specific Controls**: Different permission levels for staging vs production operations
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

- `GET /` - Server information and capabilities
- `GET /mcp/resources` - List available MCP resources
- `GET /mcp/resources/logs` - Get system logs with filtering
- `GET /mcp/resources/metrics` - Get performance metrics
- `GET /mcp/tools` - List available MCP tools
- `POST /mcp/tools/deploy_service` - Deploy a service
- `POST /mcp/tools/rollback_deployment` - Rollback a deployment
- `POST /mcp/tools/authenticate_user` - Authenticate user

## Tech Stack

### Required Technologies
- **Python 3.10+**: Core programming language
- **FastAPI**: Modern, fast web framework for building APIs
- **Uvicorn**: ASGI server for running FastAPI applications
- **Pydantic**: Data validation and settings management
- **HTTPX**: Async HTTP client for external API calls

### Optional Integrations
- **Descope**: Authentication and user management
- **Cequence Gateway**: Security gateway and monitoring
- **Datadog**: Advanced monitoring and logging
- **Docker**: Containerization
- **Render.com**: Cloud deployment platform

### Development Tools
- **Black**: Code formatting
- **isort**: Import sorting
- **MyPy**: Static type checking
- **Ruff**: Fast Python linter
- **Pre-commit**: Git hooks for code quality

## Demo Video

[Demo video link to be added]

## What We'd Do With More Time

### Enhanced Features
- **Real-time Streaming**: Implement Server-Sent Events (SSE) for real-time log and metrics streaming
- **Advanced Monitoring**: Add custom dashboards and alerting capabilities
- **Multi-tenant Support**: Enhanced tenant isolation and management
- **Audit Logging**: Comprehensive audit trails for all operations
- **Webhook Support**: Real-time notifications for deployment events

### Performance Improvements
- **Caching Layer**: Redis integration for improved response times
- **Database Integration**: Persistent storage for deployment history and configurations
- **Load Balancing**: Support for horizontal scaling
- **Rate Limiting**: Advanced rate limiting and throttling

### Security Enhancements
- **API Key Management**: Secure API key rotation and management
- **Encryption**: End-to-end encryption for sensitive data
- **Compliance**: SOC2, GDPR compliance features
- **Vulnerability Scanning**: Automated security scanning

### Developer Experience
- **OpenAPI Documentation**: Interactive API documentation
- **SDK Generation**: Auto-generated client SDKs
- **Testing Suite**: Comprehensive unit and integration tests
- **CI/CD Pipeline**: Automated testing and deployment

### AI/ML Integration
- **Anomaly Detection**: ML-based anomaly detection for metrics
- **Predictive Scaling**: AI-driven resource scaling recommendations
- **Intelligent Rollbacks**: Automated rollback decision making
- **Natural Language Queries**: AI-powered log and metrics querying

---

*This project demonstrates modern DevOps practices with AI integration, providing a foundation for autonomous DevOps operations in enterprise environments.*
