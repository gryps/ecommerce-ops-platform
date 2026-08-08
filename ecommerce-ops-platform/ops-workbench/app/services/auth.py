from __future__ import annotations

from datetime import timedelta, timezone

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.database import session_scope
from app.core.security import (
    hash_password,
    new_session_token,
    token_digest,
    utc_now,
    verify_password,
)
from app.domain.models import AdminUser, AuthSession
from app.services.audit import record_audit


def bootstrap_status(session: Session) -> bool:
    return session.scalar(select(AdminUser.id).limit(1)) is not None


def bootstrap_admin(session: Session, username: str, password: str, display_name: str = "", phone: str = "") -> AdminUser:
    if bootstrap_status(session):
        raise ValueError("管理员账号已经初始化")
    normalized = username.strip()
    if len(normalized) < 3:
        raise ValueError("账号至少需要3个字符")
    user = AdminUser(
        username=normalized,
        display_name=display_name.strip(),
        phone=phone.strip(),
        password_hash=hash_password(password),
    )
    session.add(user)
    session.flush()
    record_audit(
        session,
        actor_id=user.id,
        action="auth.bootstrap",
        object_type="user",
        object_id=user.id,
        after={"username": user.username, "display_name": user.display_name, "phone": user.phone},
    )
    return user


def update_admin_profile(session: Session, user_id: str, display_name: str, phone: str) -> AdminUser:
    user = session.get(AdminUser, user_id)
    if user is None:
        raise ValueError("账号不存在")
    before = {"display_name": user.display_name, "phone": user.phone}
    user.display_name = display_name.strip()
    user.phone = phone.strip()
    record_audit(
        session,
        actor_id=user.id,
        action="auth.profile.update",
        object_type="user",
        object_id=user.id,
        before=before,
        after={"display_name": user.display_name, "phone": user.phone},
    )
    session.flush()
    return user


def change_admin_password(session: Session, user_id: str, current_password: str, new_password: str) -> None:
    user = session.get(AdminUser, user_id)
    if user is None:
        raise ValueError("账号不存在")
    if not verify_password(current_password, user.password_hash):
        raise ValueError("当前密码错误")
    user.password_hash = hash_password(new_password)
    record_audit(
        session,
        actor_id=user.id,
        action="auth.password.change",
        object_type="user",
        object_id=user.id,
        after={"changed": True},
    )
    session.flush()


def create_login_session(session: Session, username: str, password: str) -> tuple[AdminUser, str, AuthSession]:
    user = session.scalar(select(AdminUser).where(AdminUser.username == username.strip()))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise ValueError("账号或密码错误")
    token = new_session_token()
    auth_session = AuthSession(
        user_id=user.id,
        token_hash=token_digest(token),
        expires_at=utc_now() + timedelta(hours=settings.auth_session_hours),
    )
    session.add(auth_session)
    session.flush()
    record_audit(
        session,
        actor_id=user.id,
        action="auth.login",
        object_type="session",
        object_id=auth_session.id,
    )
    return user, token, auth_session


def delete_login_session(session: Session, token: str, actor_id: str) -> None:
    digest = token_digest(token)
    auth_session = session.scalar(select(AuthSession).where(AuthSession.token_hash == digest))
    if auth_session is not None:
        record_audit(
            session,
            actor_id=actor_id,
            action="auth.logout",
            object_type="session",
            object_id=auth_session.id,
        )
        session.delete(auth_session)


def bearer_token(request: Request) -> str:
    value = request.headers.get("Authorization", "")
    scheme, _, token = value.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="需要登录")
    return token


def require_admin(request: Request) -> AdminUser:
    token = bearer_token(request)
    with session_scope() as session:
        auth_session = session.scalar(
            select(AuthSession).where(AuthSession.token_hash == token_digest(token))
        )
        if auth_session is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效")
        expires_at = auth_session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= utc_now():
            session.delete(auth_session)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期")
        user = session.get(AdminUser, auth_session.user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不可用")
        auth_session.last_seen_at = utc_now()
        session.expunge(user)
        return user
