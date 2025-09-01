from pydantic import BaseModel, Field

class UserPrincipal(BaseModel):
    user_id: str
    login_id: str | None = None
    email: str | None = None
    name: str | None = None
    tenant: str | None = None
    roles: list[str] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=list)
    token: str | None = None
    claims: dict[str, str] = Field(default_factory=dict)
