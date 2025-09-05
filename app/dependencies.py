from __future__ import annotations
from typing import Sequence, Optional, List
import logging

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.schemas.auth import UserPrincipal
from app.infrastructure.auth.descope_client import descope_client, DescopeAuthError
from app.utils.scope_checker import has_scopes

# Import Descope constants
try:
    from descope import REFRESH_SESSION_TOKEN_NAME, SESSION_TOKEN_NAME
except ImportError:
    REFRESH_SESSION_TOKEN_NAME = "DSR"
    SESSION_TOKEN_NAME = "DS"

# Service dependencies
from app.domain.services.log_service import LogService
from app.domain.services.metrics_service import MetricsService
from app.domain.services.deploy_service import DeployService
from app.domain.services.rollback_service import RollbackService
from app.infrastructure.logs.logs_client import LogsClient
from app.infrastructure.metrics.metrics_client import MetricsClient
from app.infrastructure.cicd.cicd_client import CICDClient
from app.infrastructure.rollback.rollback_client import RollbackClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
_security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_security),
) -> UserPrincipal:
    """
    Clean authentication flow using Descope SDK.
    
    Supports:
      - Authorization: Bearer <session_token>
      - Optional refresh token from cookies
      - Automatic session refresh if refresh token is available
      - Role and permission extraction from JWT
    """
    logger.info("🔍 Starting authentication...")
    
    # Check if anonymous access is allowed
    if settings.AUTH_ALLOW_ANONYMOUS:
        logger.info("⚠️ Anonymous access is allowed - returning anonymous user")
        return UserPrincipal(
            user_id="anonymous",
            login_id="anonymous",
            email="",
            name="Anonymous User",
            tenant="default",
            roles=["anonymous"],
            permissions=["read_logs", "read_metrics"],  # Basic permissions for anonymous
            scopes=[],
            token="",
            claims={}
        )
    
    # Extract session token from Authorization header
    session_token: Optional[str] = None
    if creds and creds.credentials:
        session_token = creds.credentials
        logger.info(f"🔍 Found session token in Authorization header: {session_token[:20]}...{session_token[-10:] if len(session_token) > 30 else ''}")
    
    # Extract refresh token from cookies
    refresh_token: Optional[str] = None
    if REFRESH_SESSION_TOKEN_NAME in request.cookies:
        refresh_token = request.cookies[REFRESH_SESSION_TOKEN_NAME]
        logger.info(f"🔍 Found refresh token in cookies: {refresh_token[:20] if refresh_token else 'None'}...")
    
    # Check if we have at least a session token
    if not session_token:
        logger.error("❌ No session token found in Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required - no session token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if Descope client is configured
    if not descope_client.is_configured():
        logger.error("❌ Descope client not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service not configured",
        )
    
    try:
        # Validate session token (with automatic refresh if refresh token is available)
        logger.info("🔄 Validating session token with Descope...")
        jwt_response = descope_client.validate_session(
            session_token=session_token,
            refresh_token=refresh_token
        )
        
        # Extract user principal from JWT response
        logger.info("🔄 Extracting user principal from JWT response...")
        user_principal = descope_client.extract_user_principal(jwt_response, session_token)
        
        logger.info(f"✅ Authentication successful for user: {user_principal.user_id}")
        logger.info(f"👤 User roles: {user_principal.roles}")
        logger.info(f"🔑 User permissions: {user_principal.permissions}")
        
        return user_principal
        
    except DescopeAuthError as e:
        logger.error(f"❌ Authentication failed: {e.detail}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"❌ Unexpected authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error",
        )


def require_permissions(required_permissions: List[str]):
    """
    Dependency factory for requiring specific permissions.
    Uses the permissions already extracted during authentication.
    
    Args:
        required_permissions: List of permissions that the user must have
        
    Returns:
        Dependency function that validates permissions
    """
    def permission_dependency(user: UserPrincipal = Depends(get_current_user)) -> UserPrincipal:
        # Skip permission validation for anonymous users if allowed
        if user.user_id == "anonymous":
            logger.info(f"✅ Anonymous user - skipping permission validation")
            return user
        
        # Check if user has any of the required permissions
        user_permissions = set(user.permissions)
        required_permissions_set = set(required_permissions)
        
        if not user_permissions.intersection(required_permissions_set):
            logger.warning(f"❌ Permission denied for user {user.user_id}: required={required_permissions}, user_has={user.permissions}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_permissions}",
            )
        
        logger.info(f"✅ Permission granted for user {user.user_id}: {required_permissions}")
        return user
    
    return permission_dependency


def require_roles(required_roles: List[str]):
    """
    Dependency factory for requiring specific roles.
    
    Args:
        required_roles: List of roles that the user must have
        
    Returns:
        Dependency function that validates roles
    """
    def role_dependency(user: UserPrincipal = Depends(get_current_user)) -> UserPrincipal:
        user_roles = set(user.roles)
        required_roles_set = set(required_roles)
        
        if not user_roles.intersection(required_roles_set):
            logger.warning(f"❌ Role access denied for user {user.user_id}: required={required_roles}, user_has={user.roles}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient roles. Required: {required_roles}",
            )
        
        logger.info(f"✅ Role access granted for user {user.user_id}: {required_roles}")
        return user
    
    return role_dependency


def require_any_permission(required_permissions: List[str]):
    """Alias for require_permissions for backward compatibility."""
    return require_permissions(required_permissions)


def require_all_permissions(required_permissions: List[str]):
    """
    Dependency factory for requiring ALL specified permissions.
    
    Args:
        required_permissions: List of permissions that the user must have ALL of
        
    Returns:
        Dependency function that validates all permissions are present
    """
    def permission_dependency(user: UserPrincipal = Depends(get_current_user)) -> UserPrincipal:
        user_permissions = set(user.permissions)
        required_permissions_set = set(required_permissions)
        
        if not required_permissions_set.issubset(user_permissions):
            missing_permissions = required_permissions_set - user_permissions
            logger.warning(f"❌ Missing permissions for user {user.user_id}: missing={list(missing_permissions)}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {list(missing_permissions)}",
            )
        
        logger.info(f"✅ All permissions granted for user {user.user_id}: {required_permissions}")
        return user
    
    return permission_dependency


# Convenience dependencies for common permission patterns
require_read_logs = require_permissions(["read_logs"])
require_read_metrics = require_permissions(["read_metrics"])
require_read_deployments = require_permissions(["read_deployments"])
require_read_rollbacks = require_permissions(["read_rollbacks"])
require_deploy_staging = require_permissions(["deploy_staging"])
require_deploy_production = require_permissions(["deploy_production"])
require_rollback_write = require_permissions(["rollback_write"])

# Convenience dependencies for deployment and rollback access (flexible permissions)
def require_deployment_access():
    """Require any deployment-related permission."""
    def permission_dependency(user: UserPrincipal = Depends(get_current_user)) -> UserPrincipal:
        deployment_permissions = {"read_deployments", "deploy_staging", "deploy_production"}
        user_permissions = set(user.permissions)
        
        if not user_permissions.intersection(deployment_permissions):
            logger.warning(f"❌ No deployment access for user {user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No deployment access permissions",
            )
        
        return user
    return permission_dependency


def require_rollback_access():
    """Require any rollback-related permission."""
    def permission_dependency(user: UserPrincipal = Depends(get_current_user)) -> UserPrincipal:
        rollback_permissions = {"read_rollbacks", "rollback_write"}
        user_permissions = set(user.permissions)
        
        if not user_permissions.intersection(rollback_permissions):
            logger.warning(f"❌ No rollback access for user {user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No rollback access permissions",
            )
        
        return user
    return permission_dependency


# Service dependencies (unchanged)
def get_log_service() -> LogService:
    return LogService(LogsClient())

def get_metrics_service() -> MetricsService:
    return MetricsService(MetricsClient())

def get_deploy_service() -> DeployService:
    return DeployService(CICDClient())

def get_rollback_service() -> RollbackService:
    return RollbackService(RollbackClient())