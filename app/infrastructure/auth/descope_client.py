from __future__ import annotations
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

try:
    from descope import (
        REFRESH_SESSION_TOKEN_NAME,
        SESSION_TOKEN_NAME,
        AuthException,
        DeliveryMethod,
        DescopeClient,
        AssociatedTenant,
        RoleMapping,
        AttributeMapping,
        LoginOptions
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
    Clean Descope authentication client implementation.
    Handles session validation, refresh, and logout operations.
    """
    
    def __init__(self):
        """Initialize the Descope client with project configuration."""
        if not DESCOPE_AVAILABLE:
            logger.warning("⚠️ Descope SDK not available - authentication will be disabled")
            self.client = None
            return
        
        if not settings.DESCOPE_PROJECT_ID:
            logger.warning("⚠️ DESCOPE_PROJECT_ID not configured - authentication will be disabled")
            self.client = None
            return
        
        try:
            # Initialize Descope client with project ID
            self.client = DescopeClient(project_id=settings.DESCOPE_PROJECT_ID)
            logger.info(f"✅ Descope client initialized for project: {settings.DESCOPE_PROJECT_ID}")
        except Exception as error:
            logger.error(f"❌ Failed to initialize Descope client: {error}")
            self.client = None

    def is_configured(self) -> bool:
        """Check if Descope client is properly configured."""
        return self.client is not None

    def validate_session(self, session_token: str, refresh_token: Optional[str] = None, audience: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate session token and optionally refresh if expired.
        
        Args:
            session_token: The session token to validate
            refresh_token: Optional refresh token for automatic refresh
            audience: Optional audience claim to validate
            
        Returns:
            JWT response with user claims and permissions
            
        Raises:
            DescopeAuthError: If validation fails
        """
        if not self.client:
            raise DescopeAuthError("Descope client not configured")
        
        try:
            logger.info("🔄 Validating session token...")
            logger.info(f"🔍 Token preview: {session_token[:20]}...{session_token[-10:] if len(session_token) > 30 else ''}")
            logger.info(f"🔍 Audience: {audience or 'None'}")
            logger.info(f"🔍 Has refresh token: {bool(refresh_token)}")
            
            # Try to validate and refresh session if refresh token is available
            if refresh_token:
                logger.info("🔄 Using validate_and_refresh_session...")
                jwt_response = self.client.validate_and_refresh_session(
                    session_token=session_token,
                    refresh_token=refresh_token
                )
            else:
                # Validate session with optional audience
                logger.info("🔄 Using validate_session...")
                if audience:
                    jwt_response = self.client.validate_session(
                        session_token=session_token, 
                        audience=audience
                    )
                else:
                    jwt_response = self.client.validate_session(
                        session_token=session_token
                    )
            
            logger.info("✅ Session validation successful")
            logger.info(f"📋 JWT response keys: {list(jwt_response.keys()) if isinstance(jwt_response, dict) else 'Not a dict'}")
            
            return jwt_response
            
        except AuthException as e:
            logger.error(f"❌ Session validation failed: {e}")
            raise DescopeAuthError(f"Session validation error: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error during session validation: {e}")
            raise DescopeAuthError(f"Session validation error: {e}")

    def refresh_session(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an expired session using the refresh token.
        
        Args:
            refresh_token: The refresh token
            
        Returns:
            JWT response with new session token
            
        Raises:
            DescopeAuthError: If refresh fails
        """
        if not self.client:
            raise DescopeAuthError("Descope client not configured")
        
        try:
            logger.info("🔄 Refreshing session...")
            jwt_response = self.client.refresh_session(refresh_token)
            logger.info("✅ Session refresh successful")
            return jwt_response
            
        except AuthException as e:
            logger.error(f"❌ Session refresh failed: {e}")
            raise DescopeAuthError(f"Session refresh error: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error during session refresh: {e}")
            raise DescopeAuthError(f"Session refresh error: {e}")

    def logout(self, refresh_token: str) -> bool:
        """
        Logout user from current session.
        
        Args:
            refresh_token: The refresh token
            
        Returns:
            True if logout successful
            
        Raises:
            DescopeAuthError: If logout fails
        """
        if not self.client:
            raise DescopeAuthError("Descope client not configured")
        
        try:
            logger.info("🔄 Logging out user...")
            self.client.logout(refresh_token)
            logger.info("✅ User logged out successfully")
            return True
        
        except AuthException as e:
            logger.error(f"❌ Logout failed: {e}")
            raise DescopeAuthError(f"Logout error: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error during logout: {e}")
            raise DescopeAuthError(f"Logout error: {e}")

    def extract_user_principal(self, jwt_response: Dict[str, Any], session_token: str) -> UserPrincipal:
        """
        Extract user principal from JWT response.
        
        Args:
            jwt_response: The validated JWT response
            session_token: The original session token
            
        Returns:
            UserPrincipal with user data and permissions
        """
        try:
            # Extract basic user information
            user_id = jwt_response.get("sub") or jwt_response.get("userId")
            login_id = jwt_response.get("loginId") or jwt_response.get("email") or jwt_response.get("login_id")
            email = jwt_response.get("email")
            name = jwt_response.get("name") or jwt_response.get("user_name")
            tenant = jwt_response.get("tenant") or jwt_response.get("tenantId")
            
            # Use Descope SDK methods to get matched roles and permissions
            logger.info(f"🔍 Tenant from JWT: {tenant}")
            
            # Get matched roles from available roles in system
            roles = self.get_matched_roles(jwt_response, settings.AVAILABLE_ROLES)
            
            # Get matched permissions from available permissions in system
            permissions = self.get_matched_permissions(jwt_response, settings.AVAILABLE_PERMISSIONS)
            
            # If no permissions found but we have roles, derive from role mappings
            if not permissions and roles:
                logger.info(f"🔍 No direct permissions found, deriving from roles: {roles}")
                derived_permissions = []
                for role in roles:
                    role_permissions = settings.ROLE_PERMISSIONS.get(role, [])
                    logger.info(f"🔍 Role '{role}' maps to permissions: {role_permissions}")
                    derived_permissions.extend(role_permissions)
                
                # Get matched permissions from derived permissions
                if derived_permissions:
                    permissions = self.get_matched_permissions(jwt_response, list(set(derived_permissions)))
            
            logger.info(f"🔍 Final matched user roles: {roles}")
            logger.info(f"🔍 Final matched user permissions: {permissions}")
            
            return UserPrincipal(
                user_id=str(user_id) if user_id else "unknown",
                login_id=login_id or "unknown",
                email=email or "",
                name=name or "User",
                tenant=tenant or "default",
                roles=roles,
                permissions=permissions,
                scopes=[],  # Scopes can be added if needed
                token=session_token,
                claims={k: str(v) for k, v in jwt_response.items() if isinstance(k, str)}
            )
            
        except Exception as e:
            logger.error(f"❌ Error extracting user principal: {e}")
            raise DescopeAuthError(f"Error extracting user data: {e}")

    def validate_permissions(self, jwt_response: Dict[str, Any], required_permissions: List[str]) -> bool:
        """
        Validate if user has any of the required permissions using Descope SDK.
        
        Args:
            jwt_response: The validated JWT response from validate_session
            required_permissions: List of required permissions
            
        Returns:
            True if user has at least one required permission
        """
        if not self.client:
            logger.error("❌ Descope client not configured for permission validation")
            return False
        
        try:
            logger.info(f"🔍 Validating permissions: {required_permissions}")
            is_permission_valid = self.client.validate_permissions(jwt_response, required_permissions)
            
            if is_permission_valid:
                logger.info("✅ These permissions are valid for user")
            else:
                logger.info("❌ These permissions are invalid for user")
                
            return is_permission_valid
            
        except Exception as e:
            logger.error(f"❌ Could not confirm if permissions are valid - error prior to confirmation: {e}")
            return False

    def validate_roles(self, jwt_response: Dict[str, Any], required_roles: List[str]) -> bool:
        """
        Validate if user has any of the required roles using Descope SDK.
        
        Args:
            jwt_response: The validated JWT response from validate_session
            required_roles: List of required roles
            
        Returns:
            True if user has at least one required role
        """
        if not self.client:
            logger.error("❌ Descope client not configured for role validation")
            return False
        
        try:
            logger.info(f"🔍 Validating roles: {required_roles}")
            is_role_valid = self.client.validate_roles(jwt_response, required_roles)
            
            if is_role_valid:
                logger.info("✅ These roles are valid for user")
            else:
                logger.info("❌ These roles are invalid for user")
                
            return is_role_valid
            
        except Exception as e:
            logger.error(f"❌ Could not confirm if roles are valid - error prior to confirmation: {e}")
            return False

    def get_matched_permissions(self, jwt_response: Dict[str, Any], permissions_to_match: List[str]) -> List[str]:
        """
        Retrieve the permissions from JWT top level claims that match the specified permissions list.
        
        Args:
            jwt_response: JWT parsed info containing the permissions
            permissions_to_match: List of permissions to match against the JWT claims
            
        Returns:
            An array of permissions that are both in the JWT claims and the specified list.
            Returns an empty array if no matches are found.
        """
        if not self.client:
            logger.error("❌ Descope client not configured for permission matching")
            return []
        
        try:
            logger.info(f"🔍 Getting matched permissions for: {permissions_to_match}")
            matched_permissions = self.client.get_matched_permissions(jwt_response, permissions_to_match)
            logger.info(f"✅ Matched permissions: {matched_permissions}")
            return matched_permissions
            
        except Exception as e:
            logger.error(f"❌ Could not get matched permissions - error: {e}")
            return []

    def get_matched_roles(self, jwt_response: Dict[str, Any], roles_to_match: List[str]) -> List[str]:
        """
        Retrieve the roles from JWT top level claims that match the specified roles list.
        
        Args:
            jwt_response: JWT parsed info containing the roles
            roles_to_match: List of roles to match against the JWT claims
            
        Returns:
            An array of roles that are both in the JWT claims and the specified list.
            Returns an empty array if no matches are found.
        """
        if not self.client:
            logger.error("❌ Descope client not configured for role matching")
            return []
        
        try:
            logger.info(f"🔍 Getting matched roles for: {roles_to_match}")
            matched_roles = self.client.get_matched_roles(jwt_response, roles_to_match)
            logger.info(f"✅ Matched roles: {matched_roles}")
            return matched_roles
            
        except Exception as e:
            logger.error(f"❌ Could not get matched roles - error: {e}")
            return []


# Global instance
descope_client = DescopeAuthClient()