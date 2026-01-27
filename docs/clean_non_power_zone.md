# Clean Non-Power Zone Classes Command

## Overview

The `clean_non_power_zone` management command removes non-Power Zone cycling classes from the class library. This is useful for cleaning up classes that were synced before Power Zone filtering was implemented, or for maintaining a library that only contains Power Zone classes (since the timer only works for Power Zone classes).

## Usage

```bash
python manage.py clean_non_power_zone [options]
```

## Command Options

### `--dry-run` (optional)
- **Type**: Flag
- **Default**: False
- **Description**: Preview what would be deleted without actually deleting anything
- **Example**: `--dry-run`

## Examples

### Preview What Will Be Deleted
```bash
python manage.py clean_non_power_zone --dry-run
```

### Actually Delete Non-Power Zone Classes
```bash
python manage.py clean_non_power_zone
```

## How It Works

1. **Fetches all cycling classes** from the `RideDetail` model
2. **Identifies Power Zone classes** by checking:
   - Title keywords: "power zone", "pz"
   - `class_type` field for Power Zone indicators
   - `class_type_ids` for Power Zone class type IDs
3. **Separates classes** into Power Zone and non-Power Zone groups
4. **Shows preview** of what will be deleted (first 10 examples)
5. **Deletes non-Power Zone classes** (if not in dry-run mode)

## Output

The command provides detailed statistics:

```
Total cycling classes in library: 678

Power Zone classes: 200
Non-Power Zone classes: 478

Sample non-Power Zone classes to be removed:
  - 20 min Pop Ride (ID: 2cf53cb9697847a493e09f89ba984e75)
  - 30 min Climb Ride (ID: c524b23809e0405f935925983be75eae)
  - 5 min Warm Up Ride (ID: d2092b89086d4b32963398d1416a3ed9)
  ... and 468 more

Would delete 478 non-Power Zone cycling classes
Would keep 200 Power Zone cycling classes
```

## Power Zone Detection Logic

A cycling class is considered a Power Zone class if:

1. **Title contains Power Zone keywords**:
   - "power zone" (case-insensitive)
   - " pz " (with spaces)
   - Starts with "pz "
   - Ends with " pz"

2. **Class type field**:
   - Contains both "power" and "zone"
   - Equals "pz" or starts with "pz_"

3. **Class type IDs**:
   - Any class type ID contains "power_zone", "powerzone", or "pz"

## Notes

### Safety
- Always run with `--dry-run` first to preview what will be deleted
- The command only affects cycling classes
- Power Zone classes are never deleted

### Integration
- This command complements `sync_class_library`, which now only syncs Power Zone cycling classes
- Use this command to clean up existing non-Power Zone classes that were synced before filtering was implemented

### User Sync
- User sync (via web interface) will still create `RideDetail` records for any classes users complete, even if they're not Power Zone classes
- This command only affects the class library, not user workout records

## Related Commands

- `sync_class_library` - Sync classes from Peloton API (now filters to Power Zone only for cycling)
- `sync_workouts` - Sync user's workout history (via web interface)

## Database Models

- `RideDetail` - Stores class/ride template information (this is what gets cleaned)
