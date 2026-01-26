# Peloton Workout Sync Strategy

## Overview

The Peloton workout sync system implements a two-phase approach:
1. **Initial Full Sync**: When a user first connects, all historical workouts are synced
2. **Incremental Sync**: Subsequent syncs only fetch new workouts since the last sync

## How It Works

### Initial Full Sync

**Trigger**: When `PelotonConnection.last_sync_at` is `None` (first sync)

**Behavior**:
- Fetches ALL workouts from Peloton API
- Processes every workout regardless of date
- Updates `last_sync_at` after completion

**Use Case**: First-time connection, or manual full re-sync

### Incremental Sync

**Trigger**: When `PelotonConnection.last_sync_at` has a value (subsequent syncs)

**Behavior**:
- Fetches workouts from Peloton API (sorted newest first by default)
- Compares each workout's `created_at` timestamp with `last_sync_at`
- Only processes workouts newer than `last_sync_at`
- Stops early when encountering 5+ consecutive workouts older than cutoff
- Updates `last_sync_at` after completion

**Use Case**: Regular syncs to get latest workouts without re-processing entire history

## Implementation Details

### Timestamp Comparison

The system uses `created_at` (when Peloton created the workout record) for comparison, falling back to `start_time` (when user completed the workout) if `created_at` is not available.

**Why `created_at`?**
- More reliable for determining when a workout was added to Peloton's system
- Less affected by user timezone or clock settings
- Better aligns with Peloton's internal sorting (`-created_at,-pk`)

### Timezone Handling

**Critical**: All timestamp comparisons are done in **UTC** to avoid timezone-related issues. This ensures sync works correctly regardless of where the server, user, or Peloton API are located.

#### The Problem

Without proper timezone handling, sync could fail or miss workouts when:
- Server is in UTC, user is in PST (UTC-8)
- User completes a workout at 11:30 PM PST (7:30 AM next day UTC)
- Server's `last_sync_at` is stored in server timezone
- Comparison fails because timestamps are in different timezones

#### Our Solution: UTC-Only Comparisons

**1. Peloton API Timestamp Normalization**

Peloton API returns timestamps in two formats:
- **Unix timestamps** (integers/floats): Already in UTC (seconds since epoch)
- **ISO strings**: May have timezone info (e.g., `"2024-01-01T12:00:00Z"` or `"2024-01-01T12:00:00+00:00"`)

**Our parsing logic:**
```python
# For Unix timestamps (integers)
if isinstance(timestamp, (int, float)):
    workout_timestamp = timestamp  # Already UTC

# For ISO strings
else:
    dt_str = str(timestamp).replace('Z', '+00:00')
    dt = datetime.fromisoformat(dt_str)
    # Ensure UTC
    if dt.tzinfo is None:
        dt = timezone.make_aware(dt, timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    workout_timestamp = dt.timestamp()  # Convert to UTC Unix timestamp
```

**2. Django DateTimeField Handling**

Django is configured with:
- `USE_TZ = True` (timezone-aware datetimes)
- `TIME_ZONE = "UTC"` (default timezone)

This means:
- All `DateTimeField` values are stored in UTC in the database
- `last_sync_at` is automatically stored in UTC
- When we retrieve it, it's already timezone-aware (UTC)

**3. Sync Cutoff Timestamp Conversion**

When doing incremental sync, we convert `last_sync_at` to a UTC Unix timestamp:

```python
# Ensure timezone-aware (should already be UTC, but be safe)
if connection.last_sync_at.tzinfo is None:
    last_sync_utc = timezone.make_aware(connection.last_sync_at, timezone.utc)
else:
    last_sync_utc = connection.last_sync_at.astimezone(timezone.utc)

# Convert to Unix timestamp for comparison
sync_cutoff_timestamp = last_sync_utc.timestamp()
```

**4. Comparison Logic**

Both timestamps are now in UTC Unix format, so comparison is straightforward:

```python
# Add 5-second buffer for clock skew
buffer_seconds = 5
if workout_timestamp <= (sync_cutoff_timestamp + buffer_seconds):
    # Workout is older than last sync, skip it
    continue
```

**5. Clock Skew Buffer**

We add a 5-second buffer to handle:
- Minor clock differences between systems
- Rounding errors in timestamp conversion
- Network latency affecting exact timing

This ensures we don't miss workouts that were created at the exact same second as the last sync.

#### Why This Works

**Example Scenario:**
- **User location**: Los Angeles (PST, UTC-8)
- **Server location**: London (UTC)
- **User completes workout**: Jan 1, 2024 at 11:30 PM PST
- **Peloton API returns**: `start_time: 1704172200` (Unix timestamp = Jan 2, 2024 7:30 AM UTC)
- **Server's `last_sync_at`**: Jan 2, 2024 6:00 AM UTC (stored as UTC in database)
- **Comparison**: 
  - `workout_timestamp` = 1704172200 (UTC)
  - `sync_cutoff_timestamp` = 1704168000 (UTC)
  - `1704172200 > 1704168000` → Workout is newer, sync it ✅

**Key Points:**
- User's local timezone doesn't matter for sync logic
- Server's timezone doesn't matter (always uses UTC)
- All comparisons happen in UTC
- Display can convert to user's timezone, but sync uses UTC

#### Benefits

1. **Consistency**: Same logic works regardless of server/user location
2. **Reliability**: No timezone-related sync failures
3. **Simplicity**: One timezone (UTC) for all comparisons
4. **Accuracy**: No missed workouts due to timezone confusion

### Early Stopping Logic

Since workouts are returned sorted newest first, we can stop fetching once we encounter workouts older than `last_sync_at`:

1. When a workout's timestamp ≤ `last_sync_at`, increment counter
2. If counter reaches 5 consecutive older workouts, stop fetching
3. This handles edge cases like:
   - Clock skew between systems
   - Workouts with identical timestamps
   - Minor timestamp discrepancies

### Sync Tracking

**Fields Updated**:
- `PelotonConnection.last_sync_at`: Timestamp of last successful sync
- `Profile.peloton_last_synced_at`: User profile sync timestamp

**Logging**:
- Sync type (full vs incremental) is logged
- Number of new/updated/skipped workouts
- Early stop information for incremental syncs

## Benefits

1. **Performance**: Incremental syncs are much faster (only process new workouts)
2. **API Efficiency**: Reduces API calls and processing time
3. **User Experience**: Faster sync times for regular users
4. **Scalability**: System remains performant as workout history grows

## Edge Cases Handled

1. **No Previous Sync**: Automatically does full sync
2. **Clock Skew**: Uses 5-workout buffer before stopping
3. **Missing Timestamps**: Falls back to `start_time` if `created_at` unavailable
4. **Concurrent Syncs**: Each sync updates `last_sync_at` independently
5. **Failed Syncs**: `last_sync_at` only updates on successful completion

## Future Enhancements

Potential improvements:
- Background job queue for async syncing
- Automatic periodic syncs (daily/hourly)
- Sync conflict resolution
- Partial sync retry logic
- Sync status dashboard for users

## Periodic Tasks

### Syncing Class Types from Peloton API

The system can automatically sync class types (e.g., "Power Zone", "Climb", "Flow", etc.) from Peloton's `/api/ride/filters` endpoint. This ensures your class type database stays in sync with Peloton's current offerings without manual updates.

#### Manual Sync

To sync class types manually:

```bash
# Sync using the first available Peloton connection
python manage.py sync_class_types

# Sync using a specific user's connection
python manage.py sync_class_types --username <peloton_leaderboard_name>

# Dry run to see what would be synced without making changes
python manage.py sync_class_types --dry-run
```

#### Automated Periodic Sync

To set up automatic syncing, add a cron job or scheduled task:

**Using cron (Linux/Mac):**
```bash
# Edit crontab
crontab -e

# Add line to sync class types daily at 2 AM
0 2 * * * cd /opt/projects/pelvicplanner && /opt/projects/pelvicplanner/.venv/bin/python manage.py sync_class_types >> /var/log/pelvicplanner/sync_class_types.log 2>&1
```

**Using systemd timer (Linux):**
Create `/etc/systemd/system/pelvicplanner-sync-class-types.service`:
```ini
[Unit]
Description=PelvicPlanner Sync Class Types
After=network.target

[Service]
Type=oneshot
User=www-data
WorkingDirectory=/opt/projects/pelvicplanner
Environment="PATH=/opt/projects/pelvicplanner/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/projects/pelvicplanner/.venv/bin/python manage.py sync_class_types
```

Create `/etc/systemd/system/pelvicplanner-sync-class-types.timer`:
```ini
[Unit]
Description=Daily sync of Peloton class types
Requires=pelvicplanner-sync-class-types.service

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

Then enable and start:
```bash
sudo systemctl enable pelvicplanner-sync-class-types.timer
sudo systemctl start pelvicplanner-sync-class-types.timer
```

**Using Celery (if you have Celery configured):**
Add to your Celery tasks:
```python
from celery import shared_task
from django.core.management import call_command

@shared_task
def sync_class_types():
    call_command('sync_class_types')
```

Then schedule it in your Celery beat configuration:
```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'sync-class-types-daily': {
        'task': 'workouts.tasks.sync_class_types',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}
```

#### What Gets Synced

The command:
- Fetches all class types from Peloton's `/api/ride/filters` endpoint
- Creates or updates `ClassType` records in the database
- Deactivates class types that are no longer in Peloton's API (sets `is_active=False`)
- Stores metadata from the API response for future reference

#### Class Type Model

Class types are stored in the `ClassType` model with:
- `peloton_id`: Unique identifier from Peloton API
- `name`: Display name (e.g., "Power Zone", "Climb")
- `slug`: URL-friendly version of the name
- `fitness_discipline`: Which discipline this type belongs to (cycling, running, strength, etc.)
- `metadata`: Additional data from Peloton API (stored as JSON)
- `is_active`: Whether this type is currently available

#### Using Synced Class Types

Once synced, you can:
- View and manage class types in Django admin (`/admin/workouts/classtype/`)
- Filter classes by class type in your application
- Use the synced data to improve class type detection in `detect_class_type()` function
- Reference class types programmatically instead of hardcoded choices
