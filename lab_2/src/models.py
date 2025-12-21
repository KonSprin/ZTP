# models.py
from sqlalchemy import String, DateTime, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from .database import Base
from enum import Enum

class PriorityEnum(str, Enum):
    LOW = "low"
    HIGH = "high"

class NotificationStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
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
    user_timezone: Mapped[str] = mapped_column(String, default="UTC")  # e.g., "Europe/Warsaw", "America/New_York"

class User(Base):
    """
    User model for managing notification recipients
    Each user can receive notifications via email or push
    """
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    
    # Push notification settings
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    push_token: Mapped[str] = mapped_column(String, nullable=True)  # For mobile apps (FCM/APNs token)
    
    # Email notification settings
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # User preferences
    timezone: Mapped[str] = mapped_column(String, default="UTC")
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_active: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
