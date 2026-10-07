from celery import Celery
from config import get_settings

settings = get_settings()

celery_app = Celery(
    "cad_workstation",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["tasks.cad_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_routes={"tasks.cad_tasks.*": {"queue": "cad_generation"}},
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)
