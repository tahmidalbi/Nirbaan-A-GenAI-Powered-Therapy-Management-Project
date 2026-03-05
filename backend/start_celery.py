from app.core.celery_app import celery_app

if __name__ == '__main__':
    # NOTE: On Windows, --beat cannot be embedded in the worker.
    # Run celery_beat.bat in a separate terminal alongside this worker.
    celery_app.worker_main([
        'worker',
        '--loglevel=info',
        '--pool=solo',  # Use solo pool for Windows
        '--concurrency=4'
    ])