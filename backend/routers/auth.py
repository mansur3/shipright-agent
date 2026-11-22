"""Auth router: login, refresh, logout, me."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlmodel import Session, select

from auth.dependencies import get_current_user
from auth.ratelimit import limit
from db.database import DEMO_ROLES, public_demo_enabled
from auth.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    verify_password,
)
from db.database import get_session
from db.models import AuditLog, RefreshToken, User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    role:         str
    username:     str


@router.post("/login", response_model=TokenResponse)
def login(body: LoginBody, request: Request, session: Session = Depends(get_session), _: None = Depends(limit(10, 60, "login"))):
    user = session.exec(select(User).where(User.username == body.username)).first()
    if not user or not verify_password(body.password, user.hashed_password):
        # Audit failed attempt — sanitised, no password in log
        session.add(AuditLog(
            username=body.username,
            action="login_failed",
            endpoint="/api/auth/login",
            ip_address=request.client.host if request.client else None,
            success=False,
            detail="Invalid credentials",
        ))
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    access_token = create_access_token(
        subject=user.username,
        role=user.role.value,
        cnf_code=user.cnf_code,
    )
    # No refresh token is issued: no endpoint accepts one, and storing it in clear text only added risk.
    session.add(AuditLog(
        user_id=user.id,
        username=user.username,
        action="login",
        endpoint="/api/auth/login",
        ip_address=request.client.host if request.client else None,
        success=True,
    ))
    session.commit()
    return TokenResponse(
        access_token=access_token,
        role=user.role.value,
        username=user.username,
    )


@router.get("/demo-status")
def demo_status():
    """Tells the login page whether the password-free panel demo is on. Off unless SANKALP_PUBLIC_DEMO=1."""
    return {"enabled": public_demo_enabled(), "roles": list(DEMO_ROLES) if public_demo_enabled() else []}


class DemoBody(BaseModel):
    role: str


@router.post("/demo-login", response_model=TokenResponse)
def demo_login(body: DemoBody, request: Request, session: Session = Depends(get_session), _: None = Depends(limit(30, 60, "demo"))):
    """Panel demo entry as a read role (claims, supply chain or CFO). Never admin; 404 unless the demo flag is set."""
    if not public_demo_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    name = DEMO_ROLES.get(body.role)
    user = session.exec(select(User).where(User.username == name)).first() if name else None
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown demo role")
    session.add(AuditLog(user_id=user.id, username=user.username, action="demo_login", endpoint="/api/auth/demo-login",
                         ip_address=request.client.host if request.client else None, success=True))
    session.commit()
    return TokenResponse(access_token=create_access_token(subject=user.username, role=user.role.value, cnf_code=user.cnf_code),
                         role=user.role.value, username=user.username)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "username": user.username,
        "role":     user.role.value,
        "email":    user.email,
        "cnf_code": user.cnf_code,
    }


@router.post("/logout")
def logout(
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # Revoke all refresh tokens for this user
    tokens = session.exec(
        select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked == False)
    ).all()
    for t in tokens:
        t.revoked = True
    session.add(AuditLog(
        user_id=user.id,
        username=user.username,
        action="logout",
        endpoint="/api/auth/logout",
        ip_address=request.client.host if request.client else None,
        success=True,
    ))
    session.commit()
    return {"message": "Logged out"}
