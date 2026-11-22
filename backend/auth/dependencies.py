"""FastAPI RBAC dependency injection."""
from __future__ import annotations
from typing import Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlmodel import Session, select
from auth.security import decode_access_token
from db.database import get_session
from db.models import User

bearer = HTTPBearer(auto_error=False)

PERMISSIONS: dict[str, set[str]] = {
    "read:dashboard":       {"cfo", "supply_chain", "claims_finance", "admin"},
    "read:at_risk_all":     {"cfo", "supply_chain", "admin"},
    "read:at_risk_own_cnf": {"cnf_agent"},
    "read:fill_rate":       {"cfo", "supply_chain", "admin"},
    "read:spike":           {"cfo", "supply_chain", "admin"},
    "read:stockist_any":    {"cfo", "supply_chain", "claims_finance", "admin"},
    "read:stockist_own":    {"sales_rsm", "cnf_agent"},
    "write:validate_claim": {"claims_finance", "admin"},
    "read:claims":          {"cfo", "claims_finance", "admin"},
    "write:scheme_check":   {"sales_rsm", "admin"},
    "ask:ai":               {"cfo", "supply_chain", "claims_finance", "admin"},
    "read:batch_results":   {"cfo", "supply_chain", "claims_finance", "admin"},
    "run:batch":            {"admin"},
    "manage:users":         {"admin"},
    "read:audit":           {"admin"},
    "read:report":          {"cfo", "admin"},
}


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_session),
) -> User:
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Not authenticated",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = decode_access_token(creds.credentials)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"})
    user = session.exec(select(User).where(User.username == payload.get("sub", ""))).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="User not found or inactive")
    return user


def require_role(*roles: str) -> Callable:
    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role.value not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f"Role '{user.role.value}' not permitted")
        return user
    return _dep


def require_permission(permission: str) -> Callable:
    allowed = PERMISSIONS.get(permission, set())
    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role.value not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f"Permission '{permission}' denied")
        return user
    return _dep
