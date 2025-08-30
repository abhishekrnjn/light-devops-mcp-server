from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import logs
# from app.api.v1 import logs, metrics, deploy, rollback  # To be added later

def create_app() -> FastAPI:
    app = FastAPI(
        title="DevOps MCP Server",
        description="Autonomous DevOps MCP server with Descope + Cequence integration",
        version="0.1.0",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routers
    #app.include_router(health.router, prefix="/api/v1")
    app.include_router(logs.router, prefix="/api/v1")
    # app.include_router(metrics.router, prefix="/api/v1")
    # app.include_router(deploy.router, prefix="/api/v1")
    # app.include_router(rollback.router, prefix="/api/v1")

    return app


app = create_app()
