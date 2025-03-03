
import os

FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "supersecretkey")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
