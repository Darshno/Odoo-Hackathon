from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import ProfileUpdateRequest, UserResponse

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("", response_model=UserResponse)
def get_profile(user: User = Depends(get_current_user)):
    return user


@router.patch("", response_model=UserResponse)
def update_profile(payload: ProfileUpdateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.full_name = payload.full_name
    db.commit()
    db.refresh(user)
    return user
