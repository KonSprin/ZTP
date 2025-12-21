from datetime import datetime, timezone
import redis
import json
import logging
import os

logger = logging.getLogger(__name__)

redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    password=os.getenv('REDIS_PASSWORD', '2137'),
    db=0,
    decode_responses=True,
    socket_connect_timeout=5,  # Timeout for connecting
    socket_keepalive=True,  # Keep connections alive
    max_connections=50  # Pool size
)

PUSH_CHANNEL = os.getenv('PUSH_CHANNEL', 'notifications:push')


def deliver_push(recipient: str, content: str, title: str):
    """
    Publikuje powiadomienie push do Redis pub/sub
    
    Args:
        recipient: ID/token odbiorcy
        content: Treść powiadomienia
        title: Tytuł powiadomienia
        
    Raises:
        redis.RedisError: Will be caught by Celery and trigger retry
    """
    message = {
        'recipient': recipient,
        'title': title,
        'content': content,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    try:
        subscribers = redis_client.publish(PUSH_CHANNEL, json.dumps(message))
        logger.info(f"Opublikowano push do {recipient}, odebrane przez {subscribers} subskrybentów")
        
        if subscribers == 0:
            logger.warning(f"Brak aktywnych subskrybentów dla kanału {PUSH_CHANNEL}")
            # TODO: Consider if you want to fail/retry when no subscribers are active
            # Currently logs warning but doesn't raise exception
            
    except redis.RedisError as e:
        logger.error(f"Błąd Redis podczas publikacji: {str(e)}")
        raise  # Celery will retry
