# celery_config.py
from celery.schedules import crontab
from datetime import timezone
import os
from dotenv import load_dotenv

load_dotenv()

# Konfiguracja brokerów
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

# Timezone
CELERY_TIMEZONE = os.getenv('TIMEZONE', 'Europe/Warsaw')
CELERY_ENABLE_UTC = True

# Periodic tasks - scheduler
CELERY_BEAT_SCHEDULE = {
    'process-scheduled-notifications': {
        'task': 'process_scheduled_notifications',
        'schedule': crontab(minute='*/1'),  # Co minutę sprawdzaj zaplanowane
    },
}

# Retry policy - polityka ponawiania
CELERY_TASK_ACKS_LATE = True  # Potwierdzenie po wykonaniu
CELERY_TASK_REJECT_ON_WORKER_LOST = True  # Odrzuć jeśli worker padnie
CELERY_TASK_MAX_RETRIES = 3

# Timeout
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minut hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minut soft limit

# Logowanie
CELERY_WORKER_LOG_FORMAT = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'

# Import do tasks.py
# from celery_config import *
# lub
# app.config_from_object('celery_config')
