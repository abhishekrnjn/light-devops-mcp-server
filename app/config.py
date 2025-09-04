import os
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    APP_NAME: str = "devops-mcp-server"
    
    # Descope - optional for development
    DESCOPE_PROJECT_ID: Optional[str] = os.getenv("DESCOPE_PROJECT_ID")
    DESCOPE_MANAGEMENT_KEY: Optional[str] = os.getenv("DESCOPE_MANAGEMENT_KEY")
    DESCOPE_ENABLE_DEBUG: bool = os.getenv("DESCOPE_ENABLE_DEBUG", "false").lower() == "true"
    DESCOPE_AUDIENCE: Optional[str] = os.getenv("DESCOPE_AUDIENCE")
    
    # Auth - development-friendly defaults
    AUTH_ALLOW_ANONYMOUS: bool = os.getenv("AUTH_ALLOW_ANONYMOUS", "true").lower() == "true"
    AUTH_ACCEPT_COOKIE_NAME: str = os.getenv("AUTH_ACCEPT_COOKIE_NAME", "DS")
    
    # RBAC Configuration
    # Available roles in the system
    AVAILABLE_ROLES: List[str] = [
        "Observer", 
        "developer", 
        "developer_prod_access"
    ]
    
    # Available permissions in the system
    AVAILABLE_PERMISSIONS: List[str] = [
        "read_metric",
        "read_logs", 
        "read_deployments",  # View deployment history
        "read_rollbacks",    # View rollback history
        "deploy_staging",
        "deploy_production",
        "rollback.write"
    ]
    
    # Role to permission mapping for reference
    ROLE_PERMISSIONS = {
        "Observer": ["read_metric", "read_logs"],
        "developer": ["read_metric", "read_logs", "read_deployments", "deploy_staging"],
        "developer_prod_access": ["read_metric", "read_logs", "read_deployments", "read_rollbacks", "deploy_staging", "deploy_production", "rollback.write"]
    }

settings = Settings()