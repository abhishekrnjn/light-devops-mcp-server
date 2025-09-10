from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class UserPrincipal(BaseModel):
    user_id: str
    login_id: str | None = None
    email: str | None = None
    name: str | None = None
    tenant: str | None = None
    roles: list[str] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)  # Added for RBAC
    token: str | None = None
    refresh_token: str | None = None  # Added for session refresh
    claims: dict[str, str] = Field(default_factory=dict)
    jwt_response: Optional[Dict[str, Any]] = Field(
        default=None
    )  # Store full JWT response for RBAC
