import logging
import os

from datetime import datetime, timezone
from dotenv import load_dotenv
from celery import shared_task

from ..database import get_db
from ..models import Notification
from .delivery.email import deliver_email
from .delivery.push import deliver_push

load_dotenv()
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)


@shared_task(
    bind=True, 
    name='send_email_notification',
    queue='email_queue',
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True
)
def send_email_notification(self, notification_id: int):
    """
    CHANGE: Channel-specific task for email delivery
    Runs on dedicated email worker instance (Requirement 3)
    Guarantees exactly-once delivery with pessimistic locking (Requirement 4)
    
    Args:
        notification_id: ID powiadomienia do wysłania
    """
    
    db = next(get_db())
    try:
        # Use SELECT FOR UPDATE to prevent race conditions and ensure exactly-once delivery
        # with_for_update() creates pessimistic lock - only one worker can process this notification
        notif = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.status == "pending"  # Only process pending notifications
        ).with_for_update().first()
        
        if not notif:
            logger.info(f"Email notification {notification_id} already processed or not found")
            return
        
        # Mark as "processing" to prevent duplicate sends even if lock is released
        notif.status = "processing"
        notif.attempts += 1
        db.commit()
        logger.info(f"Próba wysyłki email {notif.attempts}/3 dla powiadomienia {notification_id}")
        
        try:
            deliver_email(
                notif.recipient,
                notif.content,
                subject=f"Powiadomienie #{notif.id}"
            )
            
            # Sukces
            notif.status = "sent"
            notif.sent_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Email notification {notification_id} wysłane pomyślnie")
            
        except Exception as e:
            # If max_retries exceeded, status stays "failed"
            notif.status = "failed"
            notif.error_message = str(e)
            db.commit()
            logger.error(f"Email notification {notification_id} nie powiodło się: {str(e)}")
            raise  # Let Celery handle retries
            
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd w send_email_notification: {str(e)}")
        raise
    finally:
        db.close()


@shared_task(
    bind=True, 
    name='send_push_notification',
    queue='push_queue',
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True
)
def send_push_notification(self, notification_id: int):
    """
    CHANGE: Channel-specific task for push delivery
    Runs on dedicated push worker instance (Requirement 3)
    Guarantees exactly-once delivery with pessimistic locking (Requirement 4)
    
    Args:
        notification_id: ID powiadomienia do wysłania
    """
    
    db = next(get_db())
    try:
        notif = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.status == "pending"
        ).with_for_update().first()
        
        if not notif:
            logger.info(f"Push notification {notification_id} already processed or not found")
            return
        
        notif.status = "processing"
        notif.attempts += 1
        db.commit()
        logger.info(f"Próba wysyłki push {notif.attempts}/3 dla powiadomienia {notification_id}")
        
        try:
            deliver_push(
                notif.recipient,
                notif.content,
                title=f"Powiadomienie"
            )
            
            notif.status = "sent"
            notif.sent_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Push notification {notification_id} wysłane pomyślnie")
            
        except Exception as e:
            notif.status = "failed"
            notif.error_message = str(e)
            db.commit()
            logger.error(f"Push notification {notification_id} nie powiodło się: {str(e)}")
            raise
            
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd w send_push_notification: {str(e)}")
        raise
    finally:
        db.close()


@shared_task(name='process_scheduled_notifications')
def process_scheduled_notifications():
    """
    Periodyczne zadanie (co minutę) - przetwarzające zaplanowane powiadomienia
    Uruchamiane przez Celery Beat
    Routes to appropriate channel-specific queue
    """
    
    db = next(get_db())
    try:
        now = datetime.now(timezone.utc)
        
        # SKIP LOCKED to prevent multiple beat instances from processing same notifications
        # with_for_update(skip_locked=True) skips rows that are locked by other transactions
        # limit(100) processes in batches to avoid overwhelming workers
        pending = db.query(Notification).filter(
            Notification.status == "pending",
            Notification.scheduled_time <= now
        ).with_for_update(skip_locked=True).order_by(
            Notification.priority.desc(),  # HIGH priority first
            Notification.scheduled_time     # Then by scheduled time
        ).limit(100).all()  # CHANGE: Process in batches of 100
        
        if pending:
            logger.info(f"Przetwarzam {len(pending)} zaplanowanych powiadomień")
            
            for notif in pending:
                logger.debug(f"Kolejkuję powiadomienie {notif.id} (priorytet: {notif.priority}, kanał: {notif.channel})")
                
                # CHANGE: Route to channel-specific queue (Requirement 3)
                if notif.channel == "email":
                    send_email_notification.apply_async((notif.id,), queue='email_queue')
                elif notif.channel == "push":
                    send_push_notification.apply_async((notif.id,), queue='push_queue')
                else:
                    logger.warning(f"Nieznany kanał {notif.channel} dla powiadomienia {notif.id}")
        else:
            logger.debug("Brak zaplanowanych powiadomień do przetworzenia")
            
    except Exception as e:
        logger.error(f"Błąd w process_scheduled_notifications: {str(e)}")
    finally:
        db.close()

