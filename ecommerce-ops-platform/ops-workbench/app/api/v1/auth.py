from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.v1.schemas import (
    BootstrapRequest,
    BootstrapStatusResponse,
    LoginRequest,
    LoginResponse,
    PasswordChangeRequest,
    UserProfileUpdateRequest,
    UserResponse,
)
from app.core.database import session_scope
from app.domain.models import AdminUser
from app.services.auth import (
    bearer_token,
    bootstrap_admin,
    bootstrap_status,
    change_admin_password,
    create_login_session,
    delete_login_session,
    require_admin,
    update_admin_profile,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def user_response(user: AdminUser) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        phone=user.phone,
        is_active=user.is_active,
    )


@router.get("/status", response_model=BootstrapStatusResponse)
def get_auth_status() -> BootstrapStatusResponse:
    with session_scope() as session:
        return BootstrapStatusResponse(initialized=bootstrap_status(session))


@router.post("/bootstrap", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def bootstrap(payload: BootstrapRequest) -> UserResponse:
    with session_scope() as session:
        try:
            user = bootstrap_admin(session, payload.username, payload.password, payload.display_name, payload.phone)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return user_response(user)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    with session_scope() as session:
        try:
            user, token, auth_session = create_login_session(session, payload.username, payload.password)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        return LoginResponse(token=token, expires_at=auth_session.expires_at, user=user_response(user))


@router.get("/me", response_model=UserResponse)
def me(admin: AdminUser = Depends(require_admin)) -> UserResponse:
    return user_response(admin)


@router.patch("/me", response_model=UserResponse)
def update_me(payload: UserProfileUpdateRequest, admin: AdminUser = Depends(require_admin)) -> UserResponse:
    with session_scope() as session:
        try:
            user = update_admin_profile(session, admin.id, payload.display_name, payload.phone)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return user_response(user)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def change_my_password(payload: PasswordChangeRequest, admin: AdminUser = Depends(require_admin)) -> Response:
    with session_scope() as session:
        try:
            change_admin_password(session, admin.id, payload.current_password, payload.new_password)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def logout(request: Request, admin: AdminUser = Depends(require_admin)) -> Response:
    token = bearer_token(request)
    with session_scope() as session:
        delete_login_session(session, token, admin.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
