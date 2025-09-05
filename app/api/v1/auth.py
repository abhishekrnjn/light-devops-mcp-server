from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.dependencies import get_current_user
from app.schemas.auth import UserPrincipal
from app.infrastructure.auth.descope_client import descope_client, DescopeAuthError

# Import Descope constants
try:
    from descope import REFRESH_SESSION_TOKEN_NAME, SESSION_TOKEN_NAME
except ImportError:
    REFRESH_SESSION_TOKEN_NAME = "DSR"
    SESSION_TOKEN_NAME = "DS"

router = APIRouter()

@router.post("/logout")
async def logout(request: Request, principal: UserPrincipal = Depends(get_current_user)):
    """
    Logout user by invalidating the refresh token.
    For anonymous users, just returns success.
    """
    # Handle anonymous users
    if principal.user_id == "anonymous":
        return {"message": "Logged out successfully (anonymous user)"}
    
    # Get refresh token from cookies
    refresh_token = request.cookies.get(REFRESH_SESSION_TOKEN_NAME)
    
    if not refresh_token:
        return {"message": "No active session to logout"}
    
    try:
        success = descope_client.logout(refresh_token)
        if success:
            return {"message": "Logged out successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Logout failed"
            )
    except DescopeAuthError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
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

@router.get("/permissions")
async def get_available_permissions(principal: UserPrincipal = Depends(get_current_user)):
    """
    Get available permissions and roles for the current user.
    This helps the frontend understand what features the user can access.
    """
    from app.config import settings
    
    # Determine what the user can access based on their permissions
    user_permissions = set(principal.permissions)
    
    return {
        "user_info": {
            "user_id": principal.user_id,
            "name": principal.name,
            "roles": principal.roles,
            "permissions": principal.permissions
        },
        "available_features": {
            "can_view_metrics": "read_metrics" in user_permissions,
            "can_view_logs": "read_logs" in user_permissions,
            "can_view_deployments": "read_deployments" in user_permissions or any(p in user_permissions for p in ["deploy_staging", "deploy_production"]),
            "can_view_rollbacks": "read_rollbacks" in user_permissions or "rollback_write" in user_permissions,
            "can_deploy_staging": "deploy_staging" in user_permissions,
            "can_deploy_production": "deploy_production" in user_permissions,
            "can_rollback": "rollback_write" in user_permissions
        },
        "available_roles": settings.AVAILABLE_ROLES,
        "available_permissions": settings.AVAILABLE_PERMISSIONS,
        "role_permissions": settings.ROLE_PERMISSIONS
    }

@router.get("/validate")
async def validate_permissions_and_roles(
    request: Request, 
    principal: UserPrincipal = Depends(get_current_user)
):
    """
    Test endpoint to validate the Descope SDK role and permission validation methods.
    This endpoint demonstrates the proper usage of validate_permissions, validate_roles,
    get_matched_permissions, and get_matched_roles.
    """
    if principal.user_id == "anonymous":
        return {"message": "Anonymous user - no JWT to validate"}
    
    # Get session token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return {"error": "No Bearer token found"}
    
    session_token = auth_header.replace("Bearer ", "")
    refresh_token = request.cookies.get(REFRESH_SESSION_TOKEN_NAME)
    
    try:
        # Validate session to get JWT response
        jwt_response = descope_client.validate_session(
            session_token=session_token,
            refresh_token=refresh_token
        )
        
        # Test all Descope SDK validation methods
        test_permissions = ["read_logs", "read_metrics", "deploy_production", "nonexistent_permission"]
        test_roles = ["Developer_prod_access", "Observer", "nonexistent_role"]
        
        # Test validate_permissions
        permissions_valid = descope_client.validate_permissions(jwt_response, test_permissions)
        
        # Test validate_roles  
        roles_valid = descope_client.validate_roles(jwt_response, test_roles)
        
        # Test get_matched_permissions
        matched_permissions = descope_client.get_matched_permissions(jwt_response, settings.AVAILABLE_PERMISSIONS)
        
        # Test get_matched_roles
        matched_roles = descope_client.get_matched_roles(jwt_response, settings.AVAILABLE_ROLES)
        
        return {
            "user_id": principal.user_id,
            "validation_results": {
                "test_permissions": test_permissions,
                "permissions_validation_result": permissions_valid,
                "test_roles": test_roles,
                "roles_validation_result": roles_valid,
                "matched_permissions": matched_permissions,
                "matched_roles": matched_roles,
                "available_permissions": settings.AVAILABLE_PERMISSIONS,
                "available_roles": settings.AVAILABLE_ROLES
            },
            "jwt_info": {
                "has_jwt_response": bool(jwt_response),
                "jwt_keys": list(jwt_response.keys()) if jwt_response else []
            }
        }
        
    except DescopeAuthError as e:
        return {"error": f"Descope validation error: {e.detail}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
