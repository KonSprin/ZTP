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

app.conf.task_routes = {
    'send_email_notification': {'queue': 'email_queue'},
    'send_push_notification': {'queue': 'push_queue'},
}

app.conf.task_default_queue = 'default'
app.conf.task_default_exchange = 'default'
app.conf.task_default_routing_key = 'default'

app.conf.beat_schedule = {
    'process-scheduled-notifications': {
        'task': 'process_scheduled_notifications',
        'schedule': 60.0,  # Every 60 seconds
    },
}

app.conf.task_acks_late = True  # Task acknowledged after completion, not before
app.conf.worker_prefetch_multiplier = 1  # Workers fetch one task at a time (ensures fair distribution)

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

# Load tasks from a module
app.autodiscover_tasks(['notifier'])

@app.task
def add(x, y):
    return x + y
