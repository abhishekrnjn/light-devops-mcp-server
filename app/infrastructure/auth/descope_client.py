from __future__ import annotations
from typing import Any, Dict, List, Optional
import logging
logger = logging.getLogger(__name__)

try:
    from descope import (
        DescopeClient,
        AuthException,
        REFRESH_SESSION_TOKEN_NAME,
        SESSION_TOKEN_NAME
    )
    DESCOPE_AVAILABLE = True
except ImportError:
    DESCOPE_AVAILABLE = False
    DescopeClient = None
    AuthException = None

from fastapi import HTTPException, status
from app.config import settings
from app.schemas.auth import UserPrincipal


class DescopeAuthError(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(status_code=status_code, detail=detail)


class DescopeAuthClient:
    """
    Enhanced Descope client with RBAC support for B2B applications.
    Supports:
    - Session validation with audience
    - Role-based access control
    - Permission-based access control
    - Tenant-specific roles and permissions
    - Session refresh
    """

    def __init__(self) -> None:
        if DESCOPE_AVAILABLE and settings.DESCOPE_PROJECT_ID:
            try:
                self.client = DescopeClient(project_id=settings.DESCOPE_PROJECT_ID)
                logger.info(f"✅ Descope client initialized with project ID: {settings.DESCOPE_PROJECT_ID}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Descope client: {e}")
                self.client = None
        else:
            logger.warning("⚠️ Descope not available or project ID not configured")
            self.client = None

    def _claims_to_principal(self, token: str, claims: Dict[str, Any]) -> UserPrincipal:
        # Descope common claim names; adjust if your project uses custom names
        user_id = claims.get("sub") or claims.get("userId") or claims.get("uid")
        if not user_id:
            raise DescopeAuthError("Invalid token: user id not found")

        # Claims can differ; try common fields
        login_id = claims.get("login_id") or claims.get("loginId") or claims.get("email")
        email = claims.get("email")
        name = claims.get("name") or claims.get("user_name")
        tenant = claims.get("tenant") or claims.get("tnt")

        # Roles/scopes: Descope supports roles; scopes may live in custom claims or in roles-to-scopes mapping
        roles = claims.get("roles") or claims.get("role") or []
        scopes = claims.get("permissions") or claims.get("perms") or claims.get("scopes") or []

        # Normalize to list[str]
        if isinstance(roles, str):
            roles = [roles]
        if isinstance(scopes, str):
            scopes = [scopes]

        return UserPrincipal(
            user_id=str(user_id),
            login_id=login_id,
            email=email,
            name=name,
            tenant=tenant,
            roles=list(roles),
            scopes=list(scopes),
            token=token,
            claims={k: str(v) for k, v in claims.items() if isinstance(k, str)},
        )

    def validate_session(self, session_token: str, refresh_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate session token with optional refresh capability.
        Returns the JWT response for further role/permission validation.
        """
        if not self.client:
            # Mock response for development
            return {
                "sub": "dev-user",
                "email": "dev@example.com",
                "name": "Development User",
                "roles": settings.AVAILABLE_ROLES,
                "permissions": settings.AVAILABLE_PERMISSIONS,
                "tenant": "dev-tenant"
            }
        
        try:
            logger.info("🔄 Validating session token...")
            
            # Validate session with optional audience
            audience = settings.DESCOPE_AUDIENCE
            jwt_response = self.client.validate_session(
                session_token=session_token, 
                audience=audience
            )
            
            logger.info("✅ Session validation successful")
            return jwt_response
            
        except AuthException as e:
            logger.error(f"❌ Session validation failed: {e}")
            
            # Try to refresh if refresh token is provided
            if refresh_token:
                try:
                    logger.info("🔄 Attempting to refresh session...")
                    jwt_response = self.client.refresh_session(refresh_token)
                    logger.info("✅ Session refresh successful")
                    return jwt_response
                except AuthException as refresh_error:
                    logger.error(f"❌ Session refresh failed: {refresh_error}")
                    raise DescopeAuthError("Session expired and refresh failed")
            
            raise DescopeAuthError(f"Session validation failed: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Unexpected error during session validation: {e}")
            raise DescopeAuthError("Session validation error")

    def verify_bearer_token(self, token: str) -> UserPrincipal:
        """
        Validate bearer token (Authorization: Bearer <token>) with Descope SDK
        and convert claims into our normalized principal.
        """
        if not token:
            raise DescopeAuthError("Missing bearer token")

        # If Descope is not available, create a mock user for development
        if not self.client:
            return UserPrincipal(
                user_id="dev-user",
                login_id="dev@example.com",
                email="dev@example.com",
                name="Development User",
                roles=["admin"],
                scopes=["*"],
                token=token
            )

        try:
            # The SDK exposes token/session validation. Depending on your auth flow you may use:
            # - validate_session(session_token)  (if using session tokens)
            # - validate_jwt(jwt)               (if using plain JWTs)
            # We attempt validate_session first, then fallback to validate_jwt.
            claims: Optional[Dict[str, Any]] = None
            if hasattr(self.client, "validate_session"):
                claims = self.client.validate_session(token)  # type: ignore[attr-defined]
            if not claims and hasattr(self.client, "validate_jwt"):
                claims = self.client.validate_jwt(token)  # type: ignore[attr-defined]
            if not claims:
                # Some SDKs return object with 'claims' attribute; try to be resilient
                if hasattr(self.client, "validate"):  # generic fallback
                    result = self.client.validate(token)  # type: ignore[attr-defined]
                    claims = getattr(result, "claims", None)

            if not claims or not isinstance(claims, dict):
                raise DescopeAuthError("Token validation failed")

            return self._claims_to_principal(token, claims)

        except DescopeAuthError:
            raise
        except Exception as exc:
            # Don't leak internals to client
            logger.exception(f"Token validation failed: {exc}")
            raise DescopeAuthError("Token validation failed")

    def validate_roles(self, jwt_response: Dict[str, Any], required_roles: List[str]) -> bool:
        """Validate if user has any of the required roles."""
        if not self.client:
            # Mock validation - allow all roles in development
            return True
        
        try:
            return self.client.validate_roles(jwt_response, required_roles)
        except Exception as e:
            logger.error(f"❌ Role validation error: {e}")
            return False

    def validate_permissions(self, jwt_response: Dict[str, Any], required_permissions: List[str]) -> bool:
        """Validate if user has any of the required permissions."""
        if not self.client:
            # Mock validation - allow all permissions in development
            return True
        
        try:
            return self.client.validate_permissions(jwt_response, required_permissions)
        except Exception as e:
            logger.error(f"❌ Permission validation error: {e}")
            return False

    def validate_tenant_roles(self, jwt_response: Dict[str, Any], tenant_id: str, required_roles: List[str]) -> bool:
        """Validate if user has any of the required roles for a specific tenant."""
        if not self.client:
            # Mock validation - allow all tenant roles in development
            return True
        
        try:
            return self.client.validate_tenant_roles(jwt_response, tenant_id, required_roles)
        except Exception as e:
            logger.error(f"❌ Tenant role validation error: {e}")
            return False

    def validate_tenant_permissions(self, jwt_response: Dict[str, Any], tenant_id: str, required_permissions: List[str]) -> bool:
        """Validate if user has any of the required permissions for a specific tenant."""
        if not self.client:
            # Mock validation - allow all tenant permissions in development
            return True
        
        try:
            return self.client.validate_tenant_permissions(jwt_response, tenant_id, required_permissions)
        except Exception as e:
            logger.error(f"❌ Tenant permission validation error: {e}")
            return False

    def get_matched_roles(self, jwt_response: Dict[str, Any], roles_to_match: List[str]) -> List[str]:
        """Get roles from JWT that match the specified roles list."""
        if not self.client:
            # Mock - return intersection of available roles and requested roles
            return list(set(settings.AVAILABLE_ROLES) & set(roles_to_match))
        
        try:
            return self.client.get_matched_roles(jwt_response, roles_to_match)
        except Exception as e:
            logger.error(f"❌ Error getting matched roles: {e}")
            return []

    def get_matched_permissions(self, jwt_response: Dict[str, Any], permissions_to_match: List[str]) -> List[str]:
        """Get permissions from JWT that match the specified permissions list."""
        if not self.client:
            # Mock - return intersection of available permissions and requested permissions
            return list(set(settings.AVAILABLE_PERMISSIONS) & set(permissions_to_match))
        
        try:
            return self.client.get_matched_permissions(jwt_response, permissions_to_match)
        except Exception as e:
            logger.error(f"❌ Error getting matched permissions: {e}")
            return []

    def get_matched_tenant_roles(self, jwt_response: Dict[str, Any], tenant_id: str, roles_to_match: List[str]) -> List[str]:
        """Get tenant-specific roles from JWT that match the specified roles list."""
        if not self.client:
            # Mock - return intersection of available roles and requested roles
            return list(set(settings.AVAILABLE_ROLES) & set(roles_to_match))
        
        try:
            return self.client.get_matched_tenant_roles(jwt_response, tenant_id, roles_to_match)
        except Exception as e:
            logger.error(f"❌ Error getting matched tenant roles: {e}")
            return []

    def get_matched_tenant_permissions(self, jwt_response: Dict[str, Any], tenant_id: str, permissions_to_match: List[str]) -> List[str]:
        """Get tenant-specific permissions from JWT that match the specified permissions list."""
        if not self.client:
            # Mock - return intersection of available permissions and requested permissions
            return list(set(settings.AVAILABLE_PERMISSIONS) & set(permissions_to_match))
        
        try:
            return self.client.get_matched_tenant_permissions(jwt_response, tenant_id, permissions_to_match)
        except Exception as e:
            logger.error(f"❌ Error getting matched tenant permissions: {e}")
            return []

    def logout(self, refresh_token: str) -> bool:
        """Logout user by invalidating the refresh token."""
        if not self.client:
            logger.info("🔓 Mock logout successful")
            return True
        
        try:
            self.client.logout(refresh_token)
            logger.info("🔓 User logged out successfully")
            return True
        except AuthException as e:
            logger.error(f"❌ Logout failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected logout error: {e}")
            return False
