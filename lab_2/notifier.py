from dotenv import load_dotenv
from celery import Celery

import logging
import os
from src import notifier

load_dotenv()

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
print(REDIS_URL)

app = Celery('notifier', broker=REDIS_URL, backend=REDIS_URL)
# app.conf.broker_url = REDIS_URL
# app.conf.result_backend = REDIS_URL

app.conf.beat_schedule = {
    'process-scheduled-notifications': {
        'task': 'process_scheduled_notifications',
        'schedule': 60.0,  # Every 60 seconds
    },
}

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

# Load tasks from a module
app.autodiscover_tasks(['notifier'])

@app.task
def add(x, y):
    return x + y

# # Register tasks
# @app.task(bind=True, name='send_notification')
# def send_notification_task(self, notification_id: int):
#     return notifier.send_notification(notification_id)

# @app.task(name='process_scheduled_notifications')
# def process_scheduled_notifications_task():
#     return notifier.process_scheduled_notifications()
