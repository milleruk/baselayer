# Background Sync Architecture

## Overview

The workout sync process has been optimized to use Celery workers for background processing. This allows:
- **Immediate response**: Basic workout records are created instantly
- **Background processing**: Ride details and performance graphs are fetched asynchronously
- **Scalability**: Can handle users with 4k+ workouts without blocking the request

## Architecture

### Phase 1: Immediate Sync (Synchronous)
1. Fetch workout list from Peloton API
2. Create basic `Workout` records with minimal data:
   - Workout ID, dates, basic type
   - Link to existing `RideDetail` if available
   - Create placeholder `RideDetail` if needed

### Phase 2: Background Processing (Asynchronous)
1. **Ride Details Queue**: Fetch detailed class information
   - Instructor details
   - Class metadata
   - Playlist information
   - Target metrics

2. **Performance Graph Queue**: Fetch workout metrics
   - Summary metrics (TSS, output, calories, etc.)
   - Time-series data (cadence, resistance, heart rate over time)
   - Average and max values

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Redis (Message Broker)

```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or install locally
# Ubuntu/Debian: sudo apt-get install redis-server
# macOS: brew install redis
```

### 3. Start Celery Worker

```bash
# In project root
celery -A config worker --loglevel=info

# For production with multiple workers
celery -A config worker --loglevel=info --concurrency=4
```

### 4. Start Celery Beat (Optional - for scheduled tasks)

```bash
celery -A config beat --loglevel=info
```

## Usage

### In Sync View

The `sync_workouts` view has been refactored to:

1. **Create basic workouts immediately** (synchronous)
2. **Queue ride details fetching** (asynchronous)
3. **Queue performance graph fetching** (asynchronous)

Example:

```python
from workouts.tasks import fetch_ride_details_task, fetch_performance_graph_task

# After creating basic workout
if ride_id and not ride_detail_exists:
    fetch_ride_details_task.delay(user.id, ride_id, workout.id)

# Queue performance graph fetching
fetch_performance_graph_task.delay(user.id, workout.id, peloton_workout_id)
```

### Batch Processing

For users with many workouts, use batch tasks:

```python
from workouts.tasks import batch_fetch_ride_details, batch_fetch_performance_graphs

# Process multiple rides in parallel
ride_ids = ['ride1', 'ride2', 'ride3']
batch_fetch_ride_details.delay(user.id, ride_ids)

# Process multiple workouts in parallel
workout_data = [
    {'workout_id': 1, 'peloton_workout_id': 'workout1'},
    {'workout_id': 2, 'peloton_workout_id': 'workout2'},
]
batch_fetch_performance_graphs.delay(user.id, workout_data)
```

## Task Configuration

### Retry Logic
- Tasks automatically retry up to 3 times on failure
- Exponential backoff: 60 seconds between retries
- API errors trigger retries

### Time Limits
- Hard limit: 30 minutes per task
- Soft limit: 25 minutes (allows cleanup)

### Concurrency
- Default: 1 task per worker (better memory usage)
- Adjust with `--concurrency` flag for more parallelism

## Monitoring

### Check Task Status

```python
from celery.result import AsyncResult

result = fetch_ride_details_task.delay(user.id, ride_id)
task_id = result.id

# Check status
result = AsyncResult(task_id)
print(result.state)  # PENDING, STARTED, SUCCESS, FAILURE
print(result.result)  # Task return value
```

### View Queue Status

```bash
# Using celery command
celery -A config inspect active
celery -A config inspect scheduled
celery -A config inspect reserved

# Using Flower (optional monitoring tool)
pip install flower
celery -A config flower
# Then visit http://localhost:5555
```

## Environment Variables

Set these in your environment or `.env` file:

```bash
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Production Considerations

1. **Multiple Workers**: Run multiple worker processes for better throughput
2. **Separate Queues**: Use different queues for different priorities
3. **Monitoring**: Use Flower or similar for task monitoring
4. **Error Handling**: Set up alerts for failed tasks
5. **Rate Limiting**: Consider rate limiting to avoid Peloton API throttling

## Migration Strategy

To migrate existing sync to use background tasks:

1. **Phase 1**: Keep existing sync, add background tasks as optional
2. **Phase 2**: Make background tasks default, keep sync as fallback
3. **Phase 3**: Remove synchronous fetching entirely

This allows gradual rollout and testing.
