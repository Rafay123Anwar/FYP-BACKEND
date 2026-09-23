from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    email: str = Field(..., examples=["user@example.com"])
    full_name: str = Field(..., min_length=1, max_length=255, examples=["Jane Doe"])


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=128, examples=["secretpassword123"])
    role: Optional[UserRole] = Field(default=UserRole.JOB_SEEKER)


class UserLogin(BaseModel):
    email: str = Field(..., examples=["user@example.com"])
    password: str = Field(..., examples=["secretpassword123"])


class UserOut(UserBase):
    id: int
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[str] = None
