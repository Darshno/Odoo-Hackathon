from pydantic import BaseModel, Field

from app.models.user import UserRole
from app.schemas.auth import UserResponse


class UserListResponse(BaseModel):
    items: list[UserResponse]
    page: int
    page_size: int
    total: int
    pages: int


class UserListQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    search: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class MessageResponse(BaseModel):
    message: str
    preview_token: str | None = None
