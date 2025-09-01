from __future__ import annotations
from fnmatch import fnmatchcase
from typing import Iterable, List, Sequence

from app.schemas.auth import UserPrincipal

# Optional: centralized role->scopes policy (expand as you need)
ROLE_SCOPE_MAP = {
    "observer": ["logs.read", "metrics.read"],
    "deployer": ["deploy.staging", "deploy.read"],
    "prod-deployer": ["deploy.production", "deploy.read"],
    "rollbacker": ["rollback.write", "deploy.read"],
    "admin": ["*"],
}

def expand_scopes_from_roles(roles: Iterable[str]) -> List[str]:
    scopes: List[str] = []
    for r in roles:
        scopes.extend(ROLE_SCOPE_MAP.get(r, []))
    return scopes

def _match_any(user_scopes: Sequence[str], required: Sequence[str]) -> bool:
    return any(
        fnmatchcase(us, req) or fnmatchcase(req, us)
        for us in user_scopes
        for req in required
    )

def _match_all(user_scopes: Sequence[str], required: Sequence[str]) -> bool:
    return all(
        any(fnmatchcase(us, req) or fnmatchcase(req, us) for us in user_scopes)
        for req in required
    )

def has_scopes(
    principal: UserPrincipal,
    required: Sequence[str],
    mode: str = "all",  # "all" or "any"
) -> bool:
    # Merge explicit scopes + role-derived scopes
    effective_scopes = set(principal.scopes or [])
    effective_scopes.update(expand_scopes_from_roles(principal.roles or []))

    # Admin wildcard
    if any(s == "*" or s == "admin:*" for s in effective_scopes):
        return True

    if mode == "any":
        return _match_any(tuple(effective_scopes), required)
    return _match_all(tuple(effective_scopes), required)
