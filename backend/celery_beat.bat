@echo off
echo Starting Celery Beat Scheduler...
call venv\Scripts\activate
celery -A app.core.celery_app beat --loglevel=info
pause
