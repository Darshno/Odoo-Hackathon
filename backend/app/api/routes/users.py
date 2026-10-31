from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.auth import StaffCreateRequest, UserResponse
from app.schemas.users import MessageResponse, UserListResponse

router = APIRouter(prefix="/users", tags=["User management"])
admin_only = require_roles(UserRole.ADMIN)


@router.get("", response_model=UserListResponse)
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = None,
    role: UserRole | None = None,
    is_active: bool | None = None,
    _admin: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    query = select(User)
    count_query = select(func.count(User.id))
    filters = []
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(User.full_name.ilike(term), User.email.ilike(term)))
    if role:
        filters.append(User.role == role)
    if is_active is not None:
        filters.append(User.is_active == is_active)
    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)
    total = db.scalar(count_query) or 0
    users = db.scalars(query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return UserListResponse(items=users, page=page, page_size=page_size, total=total, pages=ceil(total / page_size) if total else 0)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, _admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.post("/staff", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_staff(payload: StaffCreateRequest, _admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    try:
        payload.validate_passwords()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    email = str(payload.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with that email already exists.")
    user = User(full_name=payload.full_name, email=email, password_hash=hash_password(payload.password), role=UserRole.STAFF)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with that email already exists.") from exc
    db.refresh(user)
    return user


@router.patch("/{user_id}/status", response_model=MessageResponse)
def set_user_status(user_id: int, is_active: bool, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    if user_id == admin.id and not is_active:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.is_active = is_active
    db.commit()
    return MessageResponse(message="Account activated." if is_active else "Account deactivated.")
