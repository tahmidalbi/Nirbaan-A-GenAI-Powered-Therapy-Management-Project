import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()

# Celery configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "nirbaan",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "app.resources.tasks",
        "app.intakes.tasks",
        "app.ai_ladder_review.tasks",
        "app.ai_ladder_review_v2.tasks",
        "app.education.ocd_core.tasks",
        # ERP tasks
        "app.erp.ERPCoach.tasks.erp_checkins",
        "app.erp.ERPCoach.tasks.erp_reports",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 minutes max
    task_soft_time_limit=1500,  # 25 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

# Task result expires after 24 hours
celery_app.conf.result_expires = 86400

# Beat schedule
celery_app.conf.beat_schedule = {
    "erp-checkin-dispatch-every-minute": {
        "task": "app.erp.ERPCoach.tasks.erp_checkins.dispatch_due_checkins",
        "schedule": crontab(minute="*"),  # every minute
    },
}


# Force import of tasks to ensure they're registered
def _register_tasks():
    try:
        import app.resources.tasks  # noqa: F401
        import app.intakes.tasks  # noqa: F401
        import app.ai_ladder_review.tasks  # noqa: F401
        import app.ai_ladder_review_v2.tasks  # noqa: F401
        import app.education.ocd_core.tasks  # noqa: F401

        # ERP tasks
        import app.erp.ERPCoach.tasks.erp_checkins  # noqa: F401
        import app.erp.ERPCoach.tasks.erp_reports  # noqa: F401

    except ImportError as e:
        print(f"Warning: Could not import task module: {e}")


_register_tasks()
