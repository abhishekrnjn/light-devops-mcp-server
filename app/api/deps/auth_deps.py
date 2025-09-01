from typing import List
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from descope import DescopeClient
from app.core.config import settings


security_scheme = HTTPBearer()
descope_client = DescopeClient(project_id=settings.DESCOPE_PROJECT_ID)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
):
    token = credentials.credentials
    try:
        jwt_response = descope_client.validate_session(token)
        return jwt_response
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def require_scopes(required_scopes: List[str]):
    def _require_scopes(user=Depends(get_current_user)):
        user_scopes = user.get("claims", {}).get("scp", [])
        if not any(scope in user_scopes for scope in required_scopes):
            raise HTTPException(status_code=403, detail="Insufficient scope")
        return user
    return _require_scopes
