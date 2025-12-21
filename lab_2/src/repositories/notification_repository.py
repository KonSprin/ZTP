# notification_repository.py
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from typing import List, Optional

from ..models import Notification

class NotificationRepository:
    
    def get_all(self, db: Session) -> List[Notification]:
        return db.query(Notification).all()

    def get_by_id(self, db: Session, id: int) -> Optional[Notification]:
        return db.query(Notification).filter(Notification.id == id).first()
    
    def create(self, db: Session, notification) -> Notification:
        try:
            db.add(notification)
            db.commit()
            db.refresh(notification)
            return notification
        except IntegrityError as e:
            db.rollback()
            raise ValueError("Błąd przy tworzeniu powiadomienia")
    
    def get_pending_notifications(self, db: Session):
        return db.query(Notification).filter(
            Notification.status == "pending",
            Notification.scheduled_time <= datetime.now(timezone.utc)
        ).order_by(Notification.priority.desc(), Notification.scheduled_time).all()
    
    def cancel(self, db: Session, id: int) -> bool:
        notif = db.query(Notification).filter(Notification.id == id).first()
        if notif and notif.status == "pending":
            notif.status = "cancelled"
            db.commit()
            return True
        return False
