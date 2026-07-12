from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id"), nullable=False, index=True
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    room: Mapped["Room"] = relationship("Room", back_populates="messages")
    author: Mapped["User"] = relationship("User", back_populates="messages")
