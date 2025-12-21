# schemas.py
from pydantic import BaseModel, Field, field_validator, model_validator, EmailStr
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal
from zoneinfo import ZoneInfo

class NotificationBase(BaseModel):
    recipient: str = Field(..., min_length=1)
    channel: Literal["email", "push"]
    content: str = Field(..., min_length=1)
    scheduled_time: Optional[datetime] = None
    priority: Literal["low", "high"] = "low"
    user_timezone: str = "UTC"

    @field_validator('channel')
    def validate_channel(cls, v):
        if v not in ['email', 'push']:
            raise ValueError('Kanał może być tylko jednym z [\'email\', \'push\']')
        return v

    # @field_validator('scheduled_time')
    # def validate_scheduled_time(cls, v):
    #     if v is None:
    #         return datetime.now(timezone.utc)

    #     if not v.tzinfo:
    #         v = v.replace(tzinfo=timezone.utc)

    #     if v < datetime.now(v.tzinfo or timezone.utc):
    #         return datetime.now(timezone.utc)
    #         # raise ValueError('Czas zaplanowany musi być w przyszłości')
    #     return v

    @model_validator(mode='after')
    def validate_scheduled_time_and_quiet_hours(self):
        """
        Validates that notifications aren't scheduled during quiet hours (22:00-08:00 local time)
        If scheduled during quiet hours, shifts to 08:00 next available morning
        """
        if self.scheduled_time is None:
            self.scheduled_time = datetime.now(timezone.utc)
            return self

        # Ensure timezone-aware
        if not self.scheduled_time.tzinfo:
            self.scheduled_time = self.scheduled_time.replace(tzinfo=timezone.utc)

        # If scheduled time is in the past, set to now
        if self.scheduled_time < datetime.now(timezone.utc):
            self.scheduled_time = datetime.now(timezone.utc)
            return self

        try:
            user_tz = ZoneInfo(self.user_timezone)
            local_time = self.scheduled_time.astimezone(user_tz)
            hour = local_time.hour

            # Quiet hours: 22:00-08:00
            if 22 <= hour or hour < 8:
                # Calculate next 08:00 in user's timezone
                if hour >= 22:
                    # After 22:00, shift to 08:00 next day
                    next_morning = local_time.replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=1)
                else:
                    # Between 00:00-08:00, shift to 08:00 same day
                    next_morning = local_time.replace(hour=8, minute=0, second=0, microsecond=0)
                
                # Convert back to UTC
                self.scheduled_time = next_morning.astimezone(timezone.utc)
                
        except Exception as e:
            # If timezone is invalid, default to UTC
            raise ValueError(f'Nieprawidłowa strefa czasowa: {self.user_timezone}')

        return self

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
    user_timezone: Optional[str] = None

class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1)
    timezone: str = "UTC"
    push_enabled: bool = True
    email_enabled: bool = True
    quiet_hours_enabled: bool = True

class UserCreate(UserBase):
    push_token: Optional[str] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    timezone: Optional[str] = None
    push_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    quiet_hours_enabled: Optional[bool] = None
    push_token: Optional[str] = None

class UserResponse(UserBase):
    id: int
    push_token: Optional[str]
    created_at: datetime
    last_active: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True
