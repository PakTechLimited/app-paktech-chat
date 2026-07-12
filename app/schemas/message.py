from datetime import datetime

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    room_id: int


class MessageOut(BaseModel):
    id: int
    content: str
    room_id: int
    author_id: int
    author_username: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
