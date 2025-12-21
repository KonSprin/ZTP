import smtplib
from email.mime.text import MIMEText
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def deliver_email(recipient: str, content: str, subject: str):
    """
    Wysyła email

    Args:
        recipient: Adres email odbiorcy
        content: Treść wiadomości
        subject: Temat wiadomości
    """
    logger.info(f"Wysyłam email do {recipient}: {subject}")

    # Email configuration
    sender = "notifier@example.com"
    msg = MIMEText(content)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient

    # SMTP server configuration (for smtp-sink)
    smtp_server = os.getenv('SMTP_SERVER', 'mailhog')
    smtp_port = int(os.getenv('SMTP_PORT', 1025))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.sendmail(sender, [recipient], msg.as_string())
        logger.info(f"Email wysłany do {recipient}")
    except Exception as e:
        logger.error(f"Błąd podczas wysyłania emaila: {e}")
        raise
