from tenacity import retry, stop_after_attempt, wait_exponential
import logging

logger = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def deliver_email(recipient: str, content: str, subject: str):
    """
    Wysyła email z automatycznym retry (3 próby, exponential backoff)
    
    Args:
        recipient: Adres email odbiorcy
        content: Treść wiadomości
        subject: Temat wiadomości
    """
    logger.info(f"Wysyłam email do {recipient}: {subject}")
    # Implement email logic here (SMTP, SendGrid, etc.)
    # raise Exception("SMTP error") to trigger retry
    pass
