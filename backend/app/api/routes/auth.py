from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, generate_reset_token, hash_password, hash_reset_token, verify_password
from app.db.session import get_db
from app.models.user import PasswordResetToken, User, UserRole
from app.schemas.auth import AuthResponse, ForgotPasswordRequest, LoginRequest, RegistrationRequest, ResetPasswordRequest, UserResponse
from app.schemas.users import MessageResponse
from app.services.email import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _user_response(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegistrationRequest, db: Session = Depends(get_db)):
    try:
        payload.validate_passwords()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    email = str(payload.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with that email already exists.")
    user = User(full_name=payload.full_name, email=email, password_hash=hash_password(payload.password), role=UserRole.CUSTOMER)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with that email already exists.") from exc
    db.refresh(user)
    return AuthResponse(access_token=create_access_token(str(user.id), user.role.value), user=_user_response(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(payload.password, user.password_hash) or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return AuthResponse(access_token=create_access_token(str(user.id), user.role.value), user=_user_response(user))


@router.post("/logout", response_model=MessageResponse)
def logout():
    return MessageResponse(message="Signed out on this device. Clear the bearer token in the client.")


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return _user_response(user)


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    user = db.scalar(select(User).where(User.email == email, User.is_active.is_(True)))
    preview_token = None
    if user:
        db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None)))
        raw_token = generate_reset_token()
        reset = PasswordResetToken(
            user_id=user.id,
            hashed_token=hash_reset_token(raw_token),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.reset_token_expire_minutes),
        )
        db.add(reset)
        db.commit()
        try:
            delivered = send_password_reset_email(user.email, raw_token)
        except Exception:
            delivered = False
        if not delivered and settings.environment == "development" and settings.reset_preview_enabled:
            preview_token = raw_token
    return MessageResponse(
        message="If an active account exists for that email, reset instructions are available through the configured delivery channel.",
        preview_token=preview_token,
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        payload.validate_passwords()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    now = datetime.now(timezone.utc)
    reset = db.scalar(select(PasswordResetToken).where(PasswordResetToken.hashed_token == hash_reset_token(payload.token)))
    if not reset:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")
    consumed = db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.id == reset.id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        .values(used_at=now)
        .execution_options(synchronize_session=False)
    )
    if consumed.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")
    user = db.get(User, reset.user_id)
    if not user or not user.is_active:
        db.rollback()
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")
    user.password_hash = hash_password(payload.new_password)
    db.execute(update(PasswordResetToken).where(PasswordResetToken.user_id == user.id, PasswordResetToken.id != reset.id, PasswordResetToken.used_at.is_(None)).values(used_at=now).execution_options(synchronize_session=False))
    db.commit()
    return MessageResponse(message="Your password has been reset. You can now sign in.")
