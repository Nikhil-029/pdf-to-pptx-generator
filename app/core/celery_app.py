# from celery import Celery
# from core.config import settings

# celery_app = Celery(
#     "pdf_pptx_worker",
#     broker=settings.REDIS_URL,
#     backend=settings.REDIS_URL,
#     include=["app.worker"],
# )

# celery_app.conf.update(
#     task_serializer="json",
#     accept_content=["json"],
#     result_serializer="json",
#     timezone="UTC",
#     enable_utc=True,
#     task_track_started=True,
#     worker_prefetch_multiplier=1,   # Process one task at a time per worker (CPU-bound)
#     task_acks_late=True,            # Re-queue if worker dies mid-task
# )

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "pdf_pptx_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["worker"],  # <-- Changed this line
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)