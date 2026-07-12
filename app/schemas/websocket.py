from enum import Enum

from pydantic import BaseModel


class WSEventType(str, Enum):
    MESSAGE = "message"
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    TYPING = "typing"
    TYPING_STOP = "typing_stop"
    ERROR = "error"


class WSEvent(BaseModel):
    type: WSEventType
    room_id: int
    username: str
    content: str | None = None
    timestamp: str | None = None
