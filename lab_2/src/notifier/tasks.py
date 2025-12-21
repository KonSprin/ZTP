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



@shared_task(bind=True, name='send_notification')
def send_notification(self, notification_id: int):
    """
    Główne zadanie Celery - wysyła powiadomienie
    
    Args:
        notification_id: ID powiadomienia do wysłania
    """
    
    db = next(get_db())
    try:
        notif = db.query(Notification).filter(Notification.id == notification_id).first()
        
        if not notif:
            logger.warning(f"Powiadomienie {notification_id} nie znalezione")
            return
        
        if notif.status != "pending":
            logger.info(f"Powiadomienie {notification_id} ma status {notif.status}, pomijam")
            return
        
        notif.attempts += 1
        db.commit()
        logger.info(f"Próba wysyłki {notif.attempts}/3 dla powiadomienia {notification_id}")
        
        try:
            if notif.channel == "email":
                deliver_email(
                    notif.recipient,
                    notif.content,
                    subject=f"Powiadomienie #{notif.id}"
                )
            elif notif.channel == "push":
                deliver_push(
                    notif.recipient,
                    notif.content,
                    title=f"Powiadomienie"
                )
            
            # Sukces
            notif.status = "sent"
            notif.sent_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Powiadomienie {notification_id} wysłane pomyślnie")
            
        except Exception as e:
            notif.status = "failed"
            notif.error_message = str(e)
            db.commit()
            logger.error(f"Powiadomienie {notification_id} nie powiodło się: {str(e)}")
            raise  # Let tenacity handle retries
            
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd w send_notification: {str(e)}")
        raise
    finally:
        db.close()

@shared_task(name='process_scheduled_notifications')
def process_scheduled_notifications():
    """
    Periodyczne zadanie (co minutę) - przetwarzające zaplanowane powiadomienia
    Uruchamiane przez Celery Beat
    """
    
    db = next(get_db())
    try:
        now = datetime.now(timezone.utc)
        
        pending = db.query(Notification).filter(
            Notification.status == "pending",
            Notification.scheduled_time <= now
        ).order_by(
            Notification.priority.desc(),  # HIGH priority first
            Notification.scheduled_time     # Then by scheduled time
        ).all()
        
        if pending:
            logger.info(f"Przetwarzam {len(pending)} zaplanowanych powiadomień")
            
            for notif in pending:
                logger.debug(f"Kolejkuję powiadomienie {notif.id} (priorytet: {notif.priority})")
                send_notification.apply_async((notif.id,))
        else:
            logger.debug("Brak zaplanowanych powiadomień do przetworzenia")
            
    except Exception as e:
        logger.error(f"Błąd w process_scheduled_notifications: {str(e)}")
    finally:
        db.close()

