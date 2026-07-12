from datetime import datetime

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=8)


class UserOut(BaseModel):
    id: int
    username: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
