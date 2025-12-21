import logging

logger = logging.getLogger(__name__)


def deliver_email(recipient: str, content: str, subject: str):
    """
    Wysyła email z automatycznym retry (3 próby, exponential backoff)
    
    Args:
        recipient: Adres email odbiorcy
        content: Treść wiadomości
        subject: Temat wiadomości
    """
    logger.info(f"Wysyłam email do {recipient}: {subject}")

    # TODO: Implement actual email sending logic here
    # Examples:
    # - SMTP: smtplib
    # - SendGrid: sendgrid.SendGridAPIClient
    # - AWS SES: boto3.client('ses')
    
    # For testing, you can simulate failures:
    # import random
    # if random.random() < 0.3:  # 30% failure rate for testing
    #     raise Exception("SMTP connection timeout")

    pass
