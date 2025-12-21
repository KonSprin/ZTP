import redis
import json
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
PUSH_CHANNEL = os.getenv('PUSH_CHANNEL', 'notifications:push')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '2137')


def listen_for_notifications():
    """
    Subskrybuje kanał Redis i wyświetla otrzymane powiadomienia push
    """
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        db=0,
        decode_responses=True
    )
    
    pubsub = redis_client.pubsub()
    pubsub.subscribe(PUSH_CHANNEL)
    
    logger.info(f"Subskrybowano kanał: {PUSH_CHANNEL}")
    logger.info(f"Oczekiwanie na powiadomienia...\n")
    
    try:
        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    
                    print("\n" + "="*60)
                    print("NOWE POWIADOMIENIE PUSH")
                    print("="*60)
                    print(f"Odbiorca:  {data['recipient']}")
                    print(f"Tytuł:     {data['title']}")
                    print(f"Treść:     {data['content']}")
                    print(f"Timestamp: {data['timestamp']}")
                    print("="*60 + "\n")
                    
                    logger.info(f"Otrzymano powiadomienie dla {data['recipient']}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Błąd parsowania JSON: {e}")
                except KeyError as e:
                    logger.error(f"Brakujące pole w wiadomości: {e}")
                    
    except KeyboardInterrupt:
        logger.info("\nZatrzymywanie subskrybenta...")
    except redis.RedisError as e:
        logger.error(f"Błąd Redis: {e}")
    finally:
        pubsub.unsubscribe()
        pubsub.close()
        redis_client.close()
        logger.info("Subskrybent zamknięty")


if __name__ == "__main__":
    listen_for_notifications()
