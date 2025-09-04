from __future__ import annotations
from typing import Sequence, Optional
from typing import Literal


from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.schemas.auth import UserPrincipal
from app.infrastructure.auth.descope_client import DescopeAuthClient, DescopeAuthError
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

_security = HTTPBearer(auto_error=False)
_auth_client = DescopeAuthClient()

async def get_current_user(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_security),
) -> UserPrincipal:
    """
    Enhanced authentication with RBAC support.
    Supports:
      - Authorization: Bearer <session_token>
      - Optional refresh token from cookies
      - Role and permission extraction
      - Tenant-based access control
    """
    session_token: Optional[str] = None
    refresh_token: Optional[str] = None

    # 1) Authorization header (session token)
    if creds and creds.scheme.lower() == "bearer" and creds.credentials:
        session_token = creds.credentials

    # 2) Optional cookie fallback for session token
    if not session_token and settings.AUTH_ACCEPT_COOKIE_NAME:
        session_token = request.cookies.get(settings.AUTH_ACCEPT_COOKIE_NAME)

    # 3) Check for refresh token in cookies
    refresh_token = request.cookies.get(REFRESH_SESSION_TOKEN_NAME, None)

    if not session_token:
        if settings.AUTH_ALLOW_ANONYMOUS:
            # Anonymous principal for development - Observer role only
            observer_permissions = settings.ROLE_PERMISSIONS.get("Observer", [])
            return UserPrincipal(
                user_id="anonymous", 
                login_id="anonymous@localhost",
                name="Anonymous User (Observer)",
                tenant="dev-tenant",
                roles=["Observer"],
                scopes=observer_permissions,  # Map permissions to legacy scopes
                permissions=observer_permissions,
                token=None
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        # Validate session with Descope
        jwt_response = _auth_client.validate_session(session_token, refresh_token)
        
        # Extract user information from JWT response
        user_id = jwt_response.get("sub") or jwt_response.get("userId") or "unknown"
        login_id = jwt_response.get("loginId") or jwt_response.get("email") or jwt_response.get("login_id")
        email = jwt_response.get("email")
        name = jwt_response.get("name") or jwt_response.get("user_name")
        tenant = jwt_response.get("tenant") or jwt_response.get("tenantId")
        
        # Extract roles and permissions from JWT
        roles = jwt_response.get("roles", [])
        permissions = jwt_response.get("permissions", [])
        
        # For B2B apps, also check tenant-specific roles/permissions
        if tenant:
            tenant_roles = jwt_response.get("tenantRoles", {}).get(tenant, [])
            tenant_permissions = jwt_response.get("tenantPermissions", {}).get(tenant, [])
            roles.extend(tenant_roles)
            permissions.extend(tenant_permissions)
        
        # Remove duplicates
        roles = list(set(roles))
        permissions = list(set(permissions))
        
        return UserPrincipal(
            user_id=user_id,
            login_id=login_id,
            email=email,
            name=name,
            tenant=tenant,
            roles=roles,
            scopes=permissions,  # Keep backward compatibility
            permissions=permissions,
            token=session_token,
            refresh_token=refresh_token,
            jwt_response=jwt_response,
            claims={k: str(v) for k, v in jwt_response.items() if isinstance(k, str)}
        )
        
    except DescopeAuthError as exc:
        raise exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=f"Authentication failed: {str(e)}"
        )

def require_permissions(
    required_permissions: Sequence[str],
    mode: Literal["all", "any"] = "any",
):
    """
    RBAC: Require specific permissions.
    Usage:
        @router.get("/logs", dependencies=[Depends(require_permissions(["read_logs"]))])
    """
    async def _checker(principal: UserPrincipal = Depends(get_current_user)) -> UserPrincipal:
        # Always enforce permissions, even for anonymous users
        
        user_permissions = set(principal.permissions)
        required_set = set(required_permissions)
        
        if mode == "all":
            has_permission = required_set.issubset(user_permissions)
        else:  # "any"
            has_permission = bool(required_set.intersection(user_permissions))
        
        if not has_permission:
            # Try to validate with Descope if JWT response is available
            if principal.jwt_response:
                has_permission = _auth_client.validate_permissions(
                    principal.jwt_response, 
                    list(required_permissions)
                )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission(s): {', '.join(required_permissions)}",
            )
        return principal

    return _checker

def require_roles(
    required_roles: Sequence[str],
    mode: Literal["all", "any"] = "any",
):
    """
    RBAC: Require specific roles.
    Usage:
        @router.post("/deploy", dependencies=[Depends(require_roles(["developer"]))])
    """
    async def _checker(principal: UserPrincipal = Depends(get_current_user)) -> UserPrincipal:
        # Always enforce roles, even for anonymous users
        
        user_roles = set(principal.roles)
        required_set = set(required_roles)
        
        if mode == "all":
            has_role = required_set.issubset(user_roles)
        else:  # "any"
            has_role = bool(required_set.intersection(user_roles))
        
        if not has_role:
            # Try to validate with Descope if JWT response is available
            if principal.jwt_response:
                has_role = _auth_client.validate_roles(
                    principal.jwt_response, 
                    list(required_roles)
                )
        
        if not has_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required role(s): {', '.join(required_roles)}",
            )
        return principal

    return _checker

def require_tenant_permissions(
    tenant_id: str,
    required_permissions: Sequence[str],
    mode: Literal["all", "any"] = "any",
):
    """
    RBAC: Require specific tenant permissions for B2B apps.
    Usage:
        @router.get("/tenant-data", dependencies=[Depends(require_tenant_permissions("tenant-123", ["read_data"]))])
    """
    async def _checker(principal: UserPrincipal = Depends(get_current_user)) -> UserPrincipal:
        if settings.AUTH_ALLOW_ANONYMOUS:
            return principal  # Skip permission check in development
        
        if not principal.jwt_response:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No authentication context for tenant permission validation",
            )
        
        has_permission = _auth_client.validate_tenant_permissions(
            principal.jwt_response,
            tenant_id,
            list(required_permissions)
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required tenant permission(s) for {tenant_id}: {', '.join(required_permissions)}",
            )
        return principal

    return _checker

# Backward compatibility - keep the old scope-based function
def require_scopes(
    required: Sequence[str],
    mode: Literal["all", "any"] = "all",
):
    """
    Legacy scope checker - redirects to permission-based validation.
    Usage:
        @router.post("/deploy", dependencies=[Depends(require_scopes(["deploy.staging"]))])
    """
    # Map old scope format to new permission format
    permission_mapping = {
        "logs.read": "read_logs",
        "metrics.read": "read_metric", 
        "deploy.read": "read_logs",  # Assuming deploy read uses logs
        "deploy.write": "deploy_staging",
        "deploy.staging": "deploy_staging",
        "deploy.production": "deploy_production",
        "rollback.write": "rollback.write",
        "rollback.read": "read_logs",  # Assuming rollback read uses logs
    }
    
    mapped_permissions = [permission_mapping.get(scope, scope) for scope in required]
    return require_permissions(mapped_permissions, mode)

# Service factory functions - centralized to avoid duplication
def get_log_service() -> LogService:
    return LogService(client=LogsClient())

def get_metrics_service() -> MetricsService:
    return MetricsService(client=MetricsClient())

def get_deploy_service() -> DeployService:
    return DeployService(client=CICDClient())

def get_rollback_service() -> RollbackService:
    return RollbackService(client=RollbackClient())
