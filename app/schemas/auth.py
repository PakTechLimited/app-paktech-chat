from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, pattern=r"^[a-zA-Z0-9_.]+$")
    email: EmailStr
    password: str = Field(..., min_length=8)
    display_name: str | None = Field(None, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    display_name: str | None
    avatar_color: str
    role: str = "member"


class UserMeResponse(BaseModel):
    id: int
    username: str
    email: str
    display_name: str | None
    avatar_color: str | None
    bio: str | None
    is_verified: bool
    role: str

    model_config = {"from_attributes": True}
