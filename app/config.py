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
    AUTH_ALLOW_ANONYMOUS: bool = os.getenv("AUTH_ALLOW_ANONYMOUS", "false").lower() == "true"
    AUTH_ACCEPT_COOKIE_NAME: str = os.getenv("AUTH_ACCEPT_COOKIE_NAME", "DS")
    
    # Cequence Gateway Configuration
    CEQUENCE_GATEWAY_URL: Optional[str] = os.getenv("CEQUENCE_GATEWAY_URL")
    CEQUENCE_ENABLED: bool = os.getenv("CEQUENCE_ENABLED", "true").lower() == "true"
    
    # Datadog Configuration
    DATADOG_API_KEY: Optional[str] = os.getenv("DATADOG_API_KEY") or os.getenv("DD_API_KEY")
    DATADOG_APP_KEY: Optional[str] = os.getenv("DATADOG_APP_KEY") or os.getenv("DD_APP_KEY")
    DATADOG_SERVICE_NAME: str = os.getenv("DATADOG_SERVICE_NAME", "payment-service")
    
    # RBAC Configuration
    # Available roles in the system
    AVAILABLE_ROLES: List[str] = [
        "New_user",
        "Observer", 
        "developer", 
        "Developer_prod_access"
    ]
    
    # Available permissions in the system
    AVAILABLE_PERMISSIONS: List[str] = [
        "read_metrics",      
        "read_logs", 
        "read_deployments",  # View deployment history
        "read_rollbacks",    # View rollback history
        "deploy_staging",
        "deploy_production",
        "rollback_staging",  
        "rollback_production" # Rollback production deployments
    ]
    
    # Role to permission mapping for reference
    ROLE_PERMISSIONS = {
        "Observer": ["read_metrics", "read_logs"],
        "developer": ["read_metrics", "read_logs", "read_deployments", "deploy_staging", "rollback_staging"],
        "Developer_prod_access": ["read_metrics", "read_logs", "read_deployments", "read_rollbacks", "deploy_staging", "deploy_production", "rollback_staging", "rollback_production"]
    }
    
    @property
    def datadog_api_key(self) -> Optional[str]:
        """Get Datadog API key."""
        return self.DATADOG_API_KEY
    
    @property
    def datadog_app_key(self) -> Optional[str]:
        """Get Datadog Application key."""
        return self.DATADOG_APP_KEY

settings = Settings()