# Simplified Class Search Feature

## Overview
The admin panel now has a **clean, simple class search** for assigning workouts to challenges.

## How It Works

### For Admins
1. **In the admin panel** (`/challenges/admin/{challenge_id}/assign-workouts/`)
2. Click on any **search field** for a workout (labeled "🔍 Search by title or class ID...")
3. **Type to search** your local database:
   - Search by **title**: "power zone", "run", "45 min", etc.
   - Search by **class ID**: Paste exact Peloton class ID
4. **See results** with instructor, duration, difficulty
5. **Visual indicator**: 📊 = class has target metrics/chart data available
6. **Click to select** a class
7. **Confirmation**: Green checkmark ✓ shows the class is linked
8. **Alternative**: Paste URL manually if class not found

### Search Priority
1. **Exact match on class ID** (most specific)
2. **Title partial match** (case-insensitive)
3. **Activity filtering** (ride/run/yoga/strength)

## Key Features

| Feature | Behavior |
|---------|----------|
| **Search scope** | Local database only (fast AJAX) |
| **No typing needed** | Class details auto-fill from library |
| **Chart indicator** | 📊 means target metrics exist |
| **Fallback** | Manual URL paste still works |
| **No description box** | Cleaner, simpler form |
| **No duplicate boxes** | One search field per activity |

## API Endpoint

**GET** `/challenges/api/search-classes/`

### Parameters
- `q` (required): Search query (min 2 chars)
  - Class ID: `f1eee289277f41a1ae1ff19d79dd81eb`
  - Title: `power zone`, `45 min`, `core`
- `activity` (optional): Filter by `ride`, `run`, `yoga`, `strength`

### Response
```json
{
  "results": [
    {
      "id": 2411,
      "peloton_id": "97d1457e42d847cb97727e5cc0e6b958",
      "title": "45 min Power Zone Endurance Ride",
      "discipline": "Cycling",
      "instructor": "Erik Jäger",
      "duration": 45,
      "difficulty": "N/A",
      "has_chart": true
    }
  ]
}
```

## Implementation Details

### Files Modified
1. **challenges/admin_views.py** - Updated `search_ride_classes()` API
2. **challenges/templates/challenges/admin/assign_workouts.html** - Simplified JavaScript search UI

### Search Logic
```python
# Check database for class ID (exact match prioritized)
rides = RideDetail.objects.filter(peloton_ride_id__iexact=query)

# Fallback: Title search (partial match)
if not rides.exists():
    rides = RideDetail.objects.filter(title__icontains=query)

# Optional: Activity type filter
if activity_type:
    rides = rides.filter(fitness_discipline__iexact=discipline)
```

### Chart Detection
```python
has_chart = bool(ride.target_metrics_data)
# Non-empty dict means class has target metrics/chart data
```

## Usage Examples

### Example 1: Search by Title
1. Type: `power zone`
2. Results: All Power Zone classes in database
3. Select: Click on "45 min Power Zone Endurance Ride"
4. Confirm: Shows "✓ 45 min Power Zone Endurance Ride" with green border

### Example 2: Search by Class ID
1. Type: `97d1457e42d847cb97727e5cc0e6b958`
2. Results: Exact match found (class ID)
3. Select: Click result
4. Confirm: Green checkmark + class title appears

### Example 3: Class Not Found
1. Type: Search term → No results appear
2. Fallback: Paste Peloton URL in the original URL field manually
3. Form saves with URL (ride_detail FK will be empty until synced)

## Benefits Over Previous Version

| Old Approach | New Approach |
|---|---|
| Long search boxes for each field | Single clean search field |
| Description input required | No description needed |
| Complex form layout | Simple, focused layout |
| Manual URL copy-paste | Click-to-select from results |
| No indicator if chart exists | 📊 shows chart availability |
| Lots of visual clutter | Minimal, clean interface |

## Testing

### Test Search Function
```bash
curl "http://localhost:8000/challenges/api/search-classes/?q=power+zone&activity=ride"
```

### Test in Admin Panel
1. Navigate to: `/challenges/admin/74/assign-workouts/`
2. Click any workout search field
3. Type: `power`
4. Verify: Results appear within 300ms
5. Click: Class selects with visual feedback

## Notes

- Search is **debounced 300ms** to avoid excessive queries
- Results limited to **10 per query** for performance
- **Case-insensitive** for title and activity searches
- **Exact match priority** for class IDs
- **Green border** indicates selected/filled class
- Fallback manual URL entry always available
