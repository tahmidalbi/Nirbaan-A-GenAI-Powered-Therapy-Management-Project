from app.core.celery_app import celery_app

if __name__ == '__main__':
    # Start worker
    celery_app.worker_main([
        'worker',
        '--loglevel=info',
        '--pool=solo',  # Use solo pool for Windows
        '--concurrency=4'
    ])