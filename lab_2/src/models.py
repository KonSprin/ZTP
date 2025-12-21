# models.py
from sqlalchemy import String, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from .database import Base
from enum import Enum

class PriorityEnum(str, Enum):
    LOW = "low"
    HIGH = "high"

class NotificationStatusEnum(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Notification(Base):
    __tablename__ = "notifications"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recipient: Mapped[str] = mapped_column(String, index=True)
    channel: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(String)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, default=NotificationStatusEnum.PENDING, index=True)
    priority: Mapped[str] = mapped_column(String, default=PriorityEnum.LOW)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(String, nullable=True)

# def get_from_db(id):
#     # todo
#     notif = Notification()
#     return notif
 
# def save_to_db(notif):
#     pass
