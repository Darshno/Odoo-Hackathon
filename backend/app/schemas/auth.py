from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import validate_password_policy
from app.models.user import UserRole


class RegistrationRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=1)
    confirm_password: str = Field(min_length=1)

    @field_validator("full_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.strip().split())

    def validate_passwords(self) -> None:
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        validate_password_policy(self.password)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20)
    new_password: str = Field(min_length=1)
    confirm_password: str = Field(min_length=1)

    def validate_passwords(self) -> None:
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        validate_password_policy(self.new_password)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ProfileUpdateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)

    @field_validator("full_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.strip().split())


class StaffCreateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=1)
    confirm_password: str = Field(min_length=1)

    def validate_passwords(self) -> None:
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        validate_password_policy(self.password)
