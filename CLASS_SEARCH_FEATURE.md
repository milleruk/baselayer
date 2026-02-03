# Challenge Workout Assignment: Class Library Search Feature

## Overview

The challenge workout assignment admin interface now includes a **class library search** feature that allows administrators to easily link workouts from the existing RideDetail library instead of manually entering URLs.

## Features

### 1. **Search from Class Library**
- Search by **class title** (e.g., "45 min Power Zone", "Strength")
- Search by **class ID** (Peloton ride ID, e.g., "f1eee289277f41a1ae1ff19d79dd81eb")
- Search by **pasting a Peloton URL** (system extracts the class ID automatically)
- Filters results by activity type (ride, run, yoga, strength)

### 2. **Quick Selection**
- Click any result to instantly populate the workout details
- Class title automatically filled in
- URL automatically populated from the library
- Ride detail linked via `ride_detail` FK

### 3. **Fallback Option**
- If class not in library, manually paste a URL
- URL will be stored for future sync

### 4. **Visual Feedback**
- Search results show:
  - Class title
  - Fitness discipline (Cycling, Running, Yoga, Strength)
  - Instructor name
  - Duration in minutes
  - Difficulty level
- Selected classes highlighted in green
- Real-time assignment counter shows total/assigned/missing

## How It Works

### Data Model
```
ChallengeWorkoutAssignment
├── challenge (FK)
├── template (FK)
├── week_number
├── day_of_week
├── activity_type (ride, run, yoga, strength)
├── peloton_url (stored, may be from old format)
├── workout_title
├── points
├── ride_detail (FK) ← NEW: Links to RideDetail in class library
└── alternative_group (for alternative workouts)
```

### Search API
**Endpoint**: `GET /challenges/api/search-classes/`

**Parameters**:
- `q` (string): Search query (title, class ID, or URL)
- `activity` (string, optional): Filter by activity type (ride, run, yoga, strength)

**Response**:
```json
{
  "results": [
    {
      "id": 123,
      "peloton_id": "f1eee289277f41a1ae1ff19d79dd81eb",
      "title": "45 min Power Zone Endurance",
      "discipline": "Cycling",
      "instructor": "Matt Wilpers",
      "duration": 45,
      "difficulty": "intermediate"
    }
  ]
}
```

### Form Submission
When a class is selected from the library:
1. The hidden field `ride_id_[key]` is populated with the RideDetail ID
2. On form submission, the system:
   - Looks up the RideDetail object
   - Pulls the class URL and title from RideDetail
   - Creates/updates ChallengeWorkoutAssignment with `ride_detail` FK
3. The assignment now has full access to class details (instructor, duration, difficulty, etc.)

## Usage

### Admin Interface
1. Go to `/challenges/admin/74/assign-workouts/` (or your challenge)
2. For each workout slot, you'll see:
   - **Search field**: "🔍 Search class library (title, ID, or URL)..."
   - **Manual URL field**: Fallback if class not in library
   - **Points field**: Award points for completing this workout
3. Type in search field to find classes:
   - "45 min power zone" (by title)
   - "f1eee289277f41a1ae1ff19d79dd81eb" (by class ID)
   - "https://members.onepeloton.com/classes/cycling/abc123" (paste URL)
4. Click result to select
5. Repeat for all activity types and weeks
6. Click "Save Assignments" to submit

### Search Behavior
- **Debounced**: 300ms delay to avoid excessive API calls
- **Case-insensitive**: "yoga" matches "Yoga", "YOGA", etc.
- **Partial matching**: "power" finds "Power Zone", "Empower", etc.
- **URL parsing**: Automatically extracts class ID from any Peloton URL format
- **Activity filtering**: Only shows classes matching the activity type

## Benefits

### For Admins
✅ **Faster setup**: Click to select instead of finding and copying URLs
✅ **Fewer errors**: No manual URL mistakes or duplicates
✅ **Better data**: Auto-populates class details from library
✅ **Flexibility**: Can still paste URL if class not yet synced
✅ **Better linking**: Assignments linked to RideDetail for rich class data

### For Users
✅ **Better plans**: Weekly plans now have full class details
✅ **Consistency**: All classes follow standardized URL format
✅ **Correct data**: Instructor, duration, difficulty, etc. pulled from library
✅ **Future-proof**: Can sync more details from Peloton API

## Technical Details

### Files Modified
- `/challenges/admin_views.py`:
  - Added `search_ride_classes()` API endpoint
  - Updated form handling to accept `ride_id_*` parameters
  - Automatically populate ride_detail FK when provided

- `/challenges/urls.py`:
  - Added `/challenges/api/search-classes/` route

- `/challenges/templates/challenges/admin/assign_workouts.html`:
  - Updated description mentioning search feature
  - Added search JavaScript functionality
  - Search inputs for each activity field

- `/challenges/models.py` (no changes):
  - ChallengeWorkoutAssignment already has `ride_detail` FK
  - No migrations needed

### Database Compatibility
- ✅ **No migrations required**: ride_detail FK already exists
- ✅ **Backward compatible**: Existing data continues to work
- ✅ **Optional field**: Can still create assignments without ride_detail
- ✅ **Safe updates**: Updates only when ride_id provided

## Examples

### Example 1: Assign by Title
```
1. Click search field for "Monday Ride"
2. Type "45 min power zone"
3. Results show matching classes
4. Click "45 min Power Zone Endurance 2000s Ride"
5. Class automatically linked
```

### Example 2: Assign by Class ID
```
1. You have class ID: f1eee289277f41a1ae1ff19d79dd81eb
2. Click search field
3. Paste the class ID
4. System finds the exact match
5. Click to select
```

### Example 3: Assign by Peloton URL
```
1. You have URL: https://members.onepeloton.com/classes/strength/abc123
2. Click search field
3. Paste the full URL
4. System extracts "abc123"
5. Searches and finds the class
6. Click to select
```

### Example 4: Class Not in Library
```
1. Class not found in search results
2. Use "Or enter URL manually" field
3. Paste the Peloton URL
4. System stores it for future sync
5. Can manually sync later with sync_missing_rides command
```

## Testing Checklist

- [ ] Search by class title works
- [ ] Search by class ID works
- [ ] Search by pasting URL works
- [ ] Activity type filtering works (ride/run/yoga/strength)
- [ ] Results show instructor, duration, difficulty
- [ ] Clicking result selects it
- [ ] Selected class shows visual feedback (green highlight)
- [ ] Form submission saves with ride_detail FK
- [ ] ChallengeWorkoutAssignment.ride_detail populated correctly
- [ ] Manual URL fallback works
- [ ] Weekly plans use ride_detail when available

## Future Enhancements

1. **Bulk assign**: "Assign best matching classes to all empty slots"
2. **Recent classes**: Show recently used classes at top of results
3. **Filtering**: Filter by instructor, duration range, difficulty
4. **Alternative suggestions**: Auto-suggest alternative classes for variety
5. **Sync integration**: Button to sync missing classes from Peloton

## Troubleshooting

**"No classes found" in search**
- Check class exists in RideDetail library
- Try searching by class ID instead of title
- Use sync_missing_rides command to sync new classes

**Ride detail not linked after save**
- Verify ride_id was sent in form (check browser console)
- Check that RideDetail ID is correct
- Verify admin user has required permissions

**Search very slow**
- Check database has indexes on RideDetail.title and peloton_ride_id
- Limit search scope by activity type
- Consider caching popular searches

## API Reference

### Search Classes Endpoint

**GET** `/challenges/api/search-classes/`

**Required**:
- `q` - Search query (2+ characters)

**Optional**:
- `activity` - Filter by activity type (ride|run|yoga|strength)

**Response** (200 OK):
```json
{
  "results": [
    {
      "id": 1,
      "peloton_id": "abc123",
      "title": "45 min Ride",
      "discipline": "Cycling",
      "instructor": "Matt Wilpers",
      "duration": 45,
      "difficulty": "intermediate"
    }
  ]
}
```

**Response** (400 Bad Request):
```json
{
  "results": []
}
```

## Implementation Status

✅ **COMPLETE**
- [x] Search API endpoint implemented
- [x] Admin form updated with search fields
- [x] Form submission handles ride_detail FK
- [x] JavaScript search and selection
- [x] Visual feedback for selections
- [x] Fallback manual URL entry
- [x] Activity type filtering
- [x] Debounced search (300ms)
- [x] URL extraction from various Peloton formats
- [x] No migrations required

🎯 **READY FOR TESTING**
