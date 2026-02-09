@echo off
echo Starting Celery Worker...
call venv\Scripts\activate
celery -A app.core.celery_app worker --loglevel=info --pool=solo --concurrency=4
pause