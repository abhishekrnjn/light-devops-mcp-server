from __future__ import annotations
from typing import Any, Dict, List, Optional
import logging
logger = logging.getLogger(__name__)

try:
    from descope import DescopeClient
    DESCOPE_AVAILABLE = True
except ImportError:
    DESCOPE_AVAILABLE = False
    DescopeClient = None

from fastapi import HTTPException, status
from app.config import settings
from app.schemas.auth import UserPrincipal


class DescopeAuthError(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(status_code=status_code, detail=detail)


class DescopeAuthClient:
    """
    Thin wrapper over Descope SDK to:
    - validate session/JWT
    - extract normalized principal (id, roles, scopes, etc.)
    Keep SDK specifics here so the rest of the app is decoupled.
    """

    def __init__(self) -> None:
        # NOTE: For validating end-user tokens, project_id is sufficient.
        # Management key is only needed for management API calls.
        if DESCOPE_AVAILABLE and settings.DESCOPE_PROJECT_ID:
            self.client = DescopeClient(project_id=settings.DESCOPE_PROJECT_ID)
        else:
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
            logger.exception("Token validation error with Descope")
            raise DescopeAuthError("Invalid or expired token") from exc
