# Sync Class Library Command

## Overview

The `sync_class_library` management command fetches and syncs Peloton class library (archived rides) into the app's database. It uses Peloton's `/api/v2/ride/archived` endpoint to retrieve classes and stores them in the `RideDetail` model.

## Usage

```bash
python manage.py sync_class_library [options]
```

## Command Options

### `--disciplines` (optional)
- **Type**: String (comma-separated)
- **Default**: `cycling,running`
- **Description**: Comma-separated list of fitness disciplines to sync
- **Examples**:
  - `--disciplines cycling,running`
  - `--disciplines cycling`
  - `--disciplines running,walking`

### `--year` (optional)
- **Type**: Integer
- **Default**: None (syncs all available classes)
- **Description**: Filter classes by year (e.g., 2025)
- **Example**: `--year 2025`

### `--month` (optional)
- **Type**: Integer (1-12)
- **Default**: None
- **Description**: Filter classes by month. **Requires `--year` to be specified**
- **Example**: `--month 12` (for December)

### `--limit` (optional)
- **Type**: Integer
- **Default**: None (syncs all available)
- **Description**: Maximum number of classes to sync (useful for testing)
- **Example**: `--limit 100`

### `--dry-run` (optional)
- **Type**: Flag
- **Default**: False
- **Description**: Preview what would be synced without making any changes to the database
- **Example**: `--dry-run`

### `--username` (optional)
- **Type**: String
- **Default**: None (uses first available Peloton connection)
- **Description**: Use a specific user's Peloton connection (by Peloton leaderboard name)
- **Example**: `--username YourPelotonUsername`

### `--delay` (optional)
- **Type**: Float (seconds)
- **Default**: 0.5
- **Description**: Delay in seconds between API calls to avoid rate limiting
- **Example**: `--delay 1.0`

## Examples

### Basic Usage
Sync all cycling and running classes:
```bash
python manage.py sync_class_library
```

### Sync Specific Year
Sync all classes from 2025:
```bash
python manage.py sync_class_library --year 2025
```

### Sync Specific Month
Sync December 2025 classes:
```bash
python manage.py sync_class_library --year 2025 --month 12
```

### Dry Run (Preview)
Preview what would be synced without saving:
```bash
python manage.py sync_class_library --year 2025 --month 12 --dry-run
```

### Test with Limit
Sync only 20 classes for testing:
```bash
python manage.py sync_class_library --year 2025 --month 12 --limit 20
```

### Specific Discipline
Sync only cycling classes:
```bash
python manage.py sync_class_library --disciplines cycling --year 2025
```

### Multiple Disciplines
Sync cycling, running, and walking:
```bash
python manage.py sync_class_library --disciplines cycling,running,walking --year 2025
```

### Use Specific User's Connection
Use a specific user's Peloton credentials:
```bash
python manage.py sync_class_library --username YourPelotonUsername --year 2025
```

### Slower Rate (Avoid Rate Limiting)
Add longer delay between requests:
```bash
python manage.py sync_class_library --year 2025 --delay 1.0
```

## How It Works

1. **Authentication**: Uses an active Peloton connection from the database
2. **API Calls**: Fetches archived rides from `/api/v2/ride/archived` endpoint
3. **Filtering**: 
   - **Note**: Peloton API date filtering doesn't work reliably - the command fetches without date filters and does client-side filtering
   - API returns classes in reverse chronological order (newest first)
   - Command paginates through pages until it finds the target date range
   - Stops early when it goes before the start date (since API returns newest first)
4. **Pagination**: Automatically handles pagination to fetch all matching classes
5. **Data Storage**: For each ride:
   - **Skips existing rides**: If a ride already exists in the library (by `peloton_ride_id`), it's skipped immediately
   - Fetches full ride details using `/api/ride/{rideId}/details` only for new rides
   - Creates `RideDetail` record (does not update existing ones)
   - Stores instructor information
   - Stores playlist data (if available)
   - Handles class types, equipment IDs, and metadata
6. **Class Filtering**:
   - **Cycling classes**: Only Power Zone classes are synced (timer only works for PZ classes)
   - **Warm-up/Cool-down**: These classes are automatically skipped
   - **Running classes**: All running classes are synced (no filtering)

## Output

The command provides real-time progress updates:

```
Using connection for user: user@example.com
Filtering by December 2025: 2025-12-01 to 2025-12-31

Processing CYCLING classes...
============================================================
  ✓ Created: 20 min Pop Ride
  ↻ Updated: 30 min Climb Ride
  ✓ Created: 45 min Power Zone Endurance Ride
  ...

  CYCLING Summary:
    Fetched: 150
    Created: 120
    Updated: 30
    Skipped: 0
    Errors: 0

Processing RUNNING classes...
============================================================
  ...

============================================================
FINAL SUMMARY
============================================================
Total rides fetched: 300
Created: 250
Updated: 50
Skipped: 0
Errors: 0
```

## Notes

### Rate Limiting
- Peloton API may rate limit requests
- Default delay is 0.5 seconds between requests
- Increase `--delay` if you encounter rate limiting errors
- For large syncs (thousands of classes), consider running during off-peak hours

### Data Updates
- Existing classes are **updated** (not duplicated)
- Classes are identified by `peloton_ride_id`
- Updates include: title, description, instructor, metadata, etc.

### Error Handling
- Individual class errors don't stop the sync
- Errors are logged and counted in the summary
- Failed classes can be retried by running the command again

### Performance
- Syncing thousands of classes can take significant time
- Progress is shown every 10 classes
- Consider using `--limit` for initial testing

### Date Filtering
- Year filter: January 1 - December 31 of the specified year
- Month filter: All days of the specified month
- Filters are based on `original_air_time` timestamp
- **Important**: Peloton API date filters don't work reliably, so the command:
  - Fetches without date filters from the API
  - Does client-side filtering on `original_air_time`
  - May need to paginate through many pages to find older classes (API returns newest first)
  - Stops early when it goes before the start date

### Disciplines
Common discipline values:
- `cycling` - Cycling classes (only Power Zone classes are synced)
- `running` - Running/Treadmill classes (all classes synced)
- `walking` - Walking classes
- `yoga` - Yoga classes
- `strength` - Strength classes
- `stretching` - Stretching classes
- `meditation` - Meditation classes

### Class Filtering Rules
- **Cycling**: Only Power Zone classes are synced (identified by title keywords "power zone" or "pz", `is_power_zone_class` flag, or `class_type_ids`)
- **Running**: All running classes are synced (no filtering)
- **Warm-up/Cool-down**: Automatically skipped for all disciplines
- **Existing rides**: Skipped immediately if already in library

### Integration with User Sync
- This command populates the class library with available classes
- When users sync their workouts (via web interface), if a ride is missing from the library, it will be automatically fetched and stored
- User sync will create `RideDetail` records for any classes users have completed that aren't in the library yet

## Troubleshooting

### "No active Peloton connection found"
- Ensure at least one user has connected their Peloton account
- Check that `PelotonConnection.is_active = True`

### "Failed to get authenticated Peloton client"
- Verify Peloton credentials are valid
- Check if tokens need to be refreshed
- Try using `--username` with a different user's connection

### Rate Limiting Errors
- Increase `--delay` value (e.g., `--delay 2.0`)
- Run during off-peak hours
- Sync smaller batches using `--limit`

### No Classes Found
- Verify the year/month has classes available
- Check if filters are too restrictive
- Try without year/month filters first

### Date Display Issues
- Ensure `original_air_time` is stored correctly
- Check timestamp format (should be Unix seconds, not milliseconds)
- Verify date conversion logic in `RideDetail.original_air_date` property

## Related Commands

- `sync_class_types` - Sync class types from Peloton API
- `sync_instructors` - Sync instructor information
- `sync_workouts` - Sync user's workout history (via web interface)

## API Endpoints Used

- `GET /api/v2/ride/archived` - List archived rides with pagination and filtering
- `GET /api/ride/{rideId}/details` - Get detailed information for a specific ride
- `GET /api/ride/{rideId}/playlist` - Get playlist for a ride (optional)

## Database Models

- `RideDetail` - Stores class/ride template information
- `Instructor` - Stores instructor information
- `WorkoutType` - Stores workout type categories
- `Playlist` - Stores music playlist data
