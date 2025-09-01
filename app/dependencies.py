from __future__ import annotations
from typing import Sequence, Optional
from typing import Literal


from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.schemas.auth import UserPrincipal
from app.infrastructure.auth.descope_client import DescopeAuthClient, DescopeAuthError
from app.utils.scope_checker import has_scopes

_security = HTTPBearer(auto_error=False)
_auth_client = DescopeAuthClient()

async def get_current_user(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_security),
) -> UserPrincipal:
    """
    Resolve the caller as a UserPrincipal by verifying the Descope token.
    Supports:
      - Authorization: Bearer <token>
      - (Optional) Cookie token if you use Descope web flows
    """
    token: Optional[str] = None

    # 1) Authorization header
    if creds and creds.scheme.lower() == "bearer" and creds.credentials:
        token = creds.credentials

    # 2) Optional cookie fallback (if you use Descope session cookies)
    if not token and settings.AUTH_ACCEPT_COOKIE_NAME:
        token = request.cookies.get(settings.AUTH_ACCEPT_COOKIE_NAME)

    if not token:
        if settings.AUTH_ALLOW_ANONYMOUS:
            # Anonymous principal for development
            return UserPrincipal(
                user_id="anonymous", 
                login_id="anonymous@localhost",
                name="Anonymous User",
                roles=["admin"], 
                scopes=["*"], 
                token=None
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        principal = _auth_client.verify_bearer_token(token)
        return principal
    except DescopeAuthError as exc:
        # bubble up 401 from verifier
        raise exc

def require_scopes(
    required: Sequence[str],
    mode: Literal["all", "any"] = "all",
):

    """
    Dependency factory: enforce scope checks at the route level.
    Usage:
        @router.post("/deploy", dependencies=[Depends(require_scopes(["deploy.staging"]))])
    """
    async def _checker(principal: UserPrincipal = Depends(get_current_user)) -> UserPrincipal:
        if not has_scopes(principal, required, mode=mode):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope(s): {', '.join(required)}",
            )
        return principal

    return _checker
