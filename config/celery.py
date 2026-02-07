"""
Celery configuration for background task processing.
"""
import os
from celery import Celery
from kombu import Queue

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('pelvicplanner')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


# Task routing and queue configuration for prioritized syncs
app.conf.task_routes = {
    'workouts.tasks.fetch_ride_details_task': {'queue': 'ride_details'},
    'workouts.tasks.batch_fetch_ride_details': {'queue': 'ride_details'},
    'workouts.tasks.fetch_performance_graph_task': {'queue': 'performance_graphs'},
    'workouts.tasks.batch_fetch_performance_graphs': {'queue': 'performance_graphs'},
}

app.conf.task_queues = (
    Queue('ride_details'),
    Queue('workouts'),
    Queue('performance_graphs'),
)

# Tuning defaults for workers
app.conf.worker_prefetch_multiplier = 1
app.conf.task_acks_late = True
