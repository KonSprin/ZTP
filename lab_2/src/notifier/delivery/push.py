from tenacity import retry, stop_after_attempt, wait_exponential
from datetime import datetime, timezone
import redis
import json
import logging
import os

logger = logging.getLogger(__name__)

# Redis client for pub/sub
redis_client = redis.Redis(
    host=os.getenv('HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    password=os.getenv('REDIS_PASSWORD', '2137'),
    db=0,
    decode_responses=True
)

PUSH_CHANNEL = os.getenv('PUSH_CHANNEL', 'notifications:push')


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def deliver_push(recipient: str, content: str, title: str):
    """
    Publikuje powiadomienie push do Redis pub/sub z automatycznym retry
    
    Args:
        recipient: ID/token odbiorcy
        content: Treść powiadomienia
        title: Tytuł powiadomienia
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
            
    except redis.RedisError as e:
        logger.error(f"Błąd Redis podczas publikacji: {str(e)}")
        raise  # Tenacity will retry