from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.api.v1 import logs, health, metrics, deploy, rollback, auth
from app.dependencies import get_current_user, get_log_service, get_metrics_service, get_deploy_service, get_rollback_service
from app.schemas.auth import UserPrincipal
from app.utils.scope_checker import has_scopes

def create_app() -> FastAPI:
    app = FastAPI(
        title="DevOps MCP Server",
        description="Autonomous DevOps MCP server with mock data",
        version="0.1.0",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


    # Main dashboard endpoint
    @app.get("/", response_class=HTMLResponse)
    async def main_dashboard(
        principal: UserPrincipal = Depends(get_current_user),
        log_service = Depends(get_log_service),
        metrics_service = Depends(get_metrics_service),
        deploy_service = Depends(get_deploy_service),
        rollback_service = Depends(get_rollback_service)
    ):
        # Determine permissions for this user based on RBAC
        user_permissions = set(principal.permissions)
        can_view_logs = "read_logs" in user_permissions
        can_view_metrics = "read_metric" in user_permissions
        can_view_deploys = bool({"deploy_staging", "deploy_production"}.intersection(user_permissions))
        can_rollback = "rollback.write" in user_permissions

        # Fetch only the data the user is allowed to see
        logs_data = await log_service.get_recent_logs() if can_view_logs else []
        metrics_data = await metrics_service.get_recent_metrics() if can_view_metrics else []
        deployments_data = await deploy_service.get_recent_deployments() if can_view_deploys else []
        rollbacks_data = await rollback_service.get_recent_rollbacks() if can_rollback else []

        # Create HTML dashboard
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>DevOps MCP Server Dashboard</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .header {{ text-align: center; color: #333; margin-bottom: 30px; }}
                .section {{ background: white; margin: 20px 0; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .section h2 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                .item {{ background: #f8f9fa; margin: 10px 0; padding: 15px; border-radius: 5px; border-left: 4px solid #3498db; }}
                .timestamp {{ color: #7f8c8d; font-size: 0.9em; }}
                .status-success {{ color: #27ae60; font-weight: bold; }}
                .status-error {{ color: #e74c3c; font-weight: bold; }}
                .metric-value {{ font-size: 1.2em; font-weight: bold; color: #2980b9; }}
                .no-data {{ color: #95a5a6; font-style: italic; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 DevOps MCP Server Dashboard</h1>
                    <p>Real-time monitoring and deployment management</p>
                    <div style="text-align:right; font-size:0.9em; color:#555; margin-top:10px;">
                        Signed in as: <strong>{principal.name or principal.login_id or principal.user_id}</strong>
                        &nbsp;|&nbsp; Tenant: <code>{principal.tenant or 'N/A'}</code>
                        <br/>
                        Roles: <code>{', '.join(principal.roles) or '—'}</code>
                        &nbsp;|&nbsp; Permissions: <code>{', '.join(principal.permissions) or '—'}</code>
                    </div>
                </div>

                <div class="section">
                    <h2>📊 System Metrics</h2>
                    {_format_metrics(metrics_data)}
                </div>

                <div class="section">
                    <h2>🚀 Recent Deployments</h2>
                    {_format_deployments(deployments_data)}
                </div>

                <div class="section">
                    <h2>🔄 Recent Rollbacks</h2>
                    {_format_rollbacks(rollbacks_data)}
                </div>

                <div class="section">
                    <h2>📝 System Logs</h2>
                    {_format_logs(logs_data)}
                </div>

                <div style="text-align: center; margin-top: 30px; color: #7f8c8d;">
                    <p>API Documentation: <a href="/docs" target="_blank">Swagger UI</a> | <a href="/redoc" target="_blank">ReDoc</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        return html_content

    def _format_metrics(metrics_data):
        if not metrics_data:
            return '<p class="no-data">No metrics data available</p>'
        
        items = []
        for metric in metrics_data:
            items.append(f'''
                <div class="item">
                    <strong>{metric.name}</strong>: 
                    <span class="metric-value">{metric.value} {metric.unit}</span>
                    <div class="timestamp">{metric.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</div>
                </div>
            ''')
        return ''.join(items)

    def _format_deployments(deployments_data):
        if not deployments_data:
            return '<p class="no-data">No deployment data available</p>'
        
        items = []
        for deployment in deployments_data:
            status_class = "status-success" if deployment.status == "SUCCESS" else "status-error"
            items.append(f'''
                <div class="item">
                    <strong>{deployment.service_name}</strong> v{deployment.version} 
                    → <strong>{deployment.environment}</strong>
                    <span class="{status_class}">({deployment.status})</span>
                    <div class="timestamp">ID: {deployment.deployment_id[:8]}... | {deployment.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</div>
                </div>
            ''')
        return ''.join(items)

    def _format_rollbacks(rollbacks_data):
        if not rollbacks_data:
            return '<p class="no-data">No rollback data available</p>'
        
        items = []
        for rollback in rollbacks_data:
            status_class = "status-success" if rollback.status == "SUCCESS" else "status-error"
            items.append(f'''
                <div class="item">
                    <strong>Rollback:</strong> {rollback.reason}
                    <span class="{status_class}">({rollback.status})</span>
                    <div class="timestamp">Deployment: {rollback.deployment_id[:8]}... | {rollback.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</div>
                </div>
            ''')
        return ''.join(items)

    def _format_logs(logs_data):
        if not logs_data:
            return '<p class="no-data">No log data available</p>'
        
        items = []
        for log in logs_data:
            status_class = "status-error" if log.level == "ERROR" else "status-success"
            items.append(f'''
                <div class="item">
                    <span class="{status_class}">[{log.level}]</span> {log.message}
                    <div class="timestamp">{log.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</div>
                </div>
            ''')
        return ''.join(items)

    # Mount routers
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(logs.router, prefix="/api/v1")
    app.include_router(metrics.router, prefix="/api/v1")
    app.include_router(deploy.router, prefix="/api/v1")
    app.include_router(rollback.router, prefix="/api/v1")

    return app

app = create_app()