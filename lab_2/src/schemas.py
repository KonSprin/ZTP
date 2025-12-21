# schemas.py
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from typing import Optional, Literal

class NotificationBase(BaseModel):
    recipient: str = Field(..., min_length=1)
    channel: Literal["email", "push"]
    content: str = Field(..., min_length=1)
    scheduled_time: Optional[datetime] = None
    priority: Literal["low", "high"] = "low"

    @field_validator('channel')
    def validate_channel(cls, v):
        if v not in ['email', 'push']:
            raise ValueError('Kanał może być tylko jednym z [\'email\', \'push\']')
        return v

    @field_validator('scheduled_time')
    def validate_scheduled_time(cls, v):
        if v is None:
            return datetime.now(timezone.utc)

        if not v.tzinfo:
            v = v.replace(tzinfo=timezone.utc)

        if v < datetime.now(v.tzinfo or timezone.utc):
            return datetime.now(timezone.utc)
            # raise ValueError('Czas zaplanowany musi być w przyszłości')
        return v

class NotificationCreate(NotificationBase):
    pass


class NotificationResponse(NotificationBase):
    id: int
    status: str
    created_at: datetime
    sent_at: Optional[datetime]
    attempts: int
    error_message: Optional[str]

    class Config:
        from_attributes = True


class NotificationUpdate(BaseModel):
    scheduled_time: Optional[datetime] = None
    priority: Optional[Literal["low", "high"]] = None
