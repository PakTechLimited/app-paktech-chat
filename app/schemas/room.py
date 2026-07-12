from datetime import datetime

from pydantic import BaseModel, Field


class RoomCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=255)


class RoomOut(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
