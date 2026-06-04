from celery import Celery
from .config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

app = Celery(
    'pipeline_tasks',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=['pipeline.services.cvat_automation_service']
)

# Configuration for Celery Beat (Periodic Tasks)
app.conf.beat_schedule = {
    'auto-inference-every-30-seconds': {
        'task': 'pipeline.services.cvat_automation_service.auto_inference_task',
        'schedule': 30.0, # seconds
    },
    'sync-cvat-every-60-seconds': {
        'task': 'pipeline.services.cvat_automation_service.sync_cvat_task',
        'schedule': 60.0, # seconds
    },
    'export-labeled-data-every-30-seconds': {
        'task': 'pipeline.services.cvat_automation_service.export_labeled_data_task',
        'schedule': 30.0, # seconds
    },
}

app.conf.timezone = 'UTC'

if __name__ == '__main__':
    app.start()
