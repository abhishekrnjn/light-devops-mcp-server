import os
from typing import Optional

class Settings:
    APP_NAME: str = "devops-mcp-server"
    
    # Descope - optional for development
    DESCOPE_PROJECT_ID: Optional[str] = os.getenv("DESCOPE_PROJECT_ID")
    DESCOPE_MANAGEMENT_KEY: Optional[str] = os.getenv("DESCOPE_MANAGEMENT_KEY")
    DESCOPE_ENABLE_DEBUG: bool = os.getenv("DESCOPE_ENABLE_DEBUG", "false").lower() == "true"
    
    # Auth - development-friendly defaults
    AUTH_ALLOW_ANONYMOUS: bool = os.getenv("AUTH_ALLOW_ANONYMOUS", "true").lower() == "true"
    AUTH_ACCEPT_COOKIE_NAME: str = os.getenv("AUTH_ACCEPT_COOKIE_NAME", "DS")

settings = Settings()