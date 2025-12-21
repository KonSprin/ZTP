# notification_service.py
from datetime import datetime, timezone

from ..repositories.notification_repository import NotificationRepository
from ..models import Notification
from ..notifier.tasks import send_email_notification, send_push_notification

class NotificationService:
    def __init__(self):
        self.repo = NotificationRepository()
    
    def create_notification(self, db, notification_data):
        new_notification = Notification(**notification_data.dict())
        created = self.repo.create(db, new_notification)
        
        # Schedule the task immediately if scheduled_time is now/past
        # Otherwise, process_scheduled_notifications will pick it up
        if not created.scheduled_time.tzinfo:
            created.scheduled_time = created.scheduled_time.replace(tzinfo=timezone.utc)
        if created.scheduled_time <= datetime.now(timezone.utc):
            self._send_to_channel(created)
        return created
    
    def get_notifications(self, db):
        return self.repo.get_all(db)
    
    def get_notification(self, db, id: int):
        return self.repo.get_by_id(db, id)
    
    def get_pending_notifications(self, db):
        return self.repo.get_pending_notifications(db)
    
    def reschedule_notification(self, db, id: int, new_time: datetime):
        """Reschedules notification - no need to cancel/recreate task"""
        notif = self.repo.get_by_id(db, id)
        if notif and notif.status == "pending":
            notif.scheduled_time = new_time
            db.commit()
            db.refresh(notif)
            
            # If rescheduled to now/past, trigger immediately
            if new_time <= datetime.now(timezone.utc):
                self._send_to_channel(notif)
            
            return notif
        return None

    def cancel_notification(self, db, id: int) -> bool:
        return self.repo.cancel(db, id)
    
    def force_send_now(self, db, id: int):
        """
        CHANGE: Enhanced with pessimistic locking to prevent race conditions
        Forces immediate delivery by setting scheduled_time to now and triggering task
        """
        notif = db.query(Notification).filter(
            Notification.id == id,
            Notification.status == "pending"
        ).with_for_update().first()
        
        if notif:
            notif.scheduled_time = datetime.now(timezone.utc)
            db.commit()
            db.refresh(notif)
            
            self._send_to_channel(notif)
            
            return notif
        return None
    
    # CHANGE: New helper method to route notifications to correct channel queue
    def _send_to_channel(self, notification: Notification):
        """
        Routes notification to appropriate channel-specific queue (Requirement 3)
        Uses consistent .delay() pattern for all async calls
        """
        if notification.channel == "email":
            send_email_notification.delay(notification.id)
        elif notification.channel == "push":
            send_push_notification.delay(notification.id)
