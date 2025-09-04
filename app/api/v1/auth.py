from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_current_user
from app.schemas.auth import UserPrincipal
from app.infrastructure.auth.descope_client import DescopeAuthClient

router = APIRouter()
_auth_client = DescopeAuthClient()

@router.post("/logout")
async def logout(principal: UserPrincipal = Depends(get_current_user)):
    """
    Logout user by invalidating the refresh token.
    For anonymous users, just returns success.
    """
    # Handle anonymous users
    if principal.user_id == "anonymous" or not principal.refresh_token:
        return {"message": "Logged out successfully (anonymous user)"}
    
    success = _auth_client.logout(principal.refresh_token)
    
    if success:
        return {"message": "Logged out successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.get("/me")
async def get_current_user_info(principal: UserPrincipal = Depends(get_current_user)):
    """
    Get current user information including roles and permissions.
    """
    return {
        "user_id": principal.user_id,
        "login_id": principal.login_id,
        "email": principal.email,
        "name": principal.name,
        "tenant": principal.tenant,
        "roles": principal.roles,
        "permissions": principal.permissions,
        "scopes": principal.scopes  # For backward compatibility
    }
