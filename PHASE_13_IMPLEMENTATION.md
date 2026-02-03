# Phase 13: Implementation Complete - URL Standardization & Template Filtering

## Overview
Phase 13 implements 3 critical user requirements for the challenge system:
1. ✅ **Template Filtering**: Only show available templates during challenge signup
2. ✅ **Class ID Mapping**: Proper extraction of class IDs from Peloton URLs  
3. ✅ **URL Standardization**: All Peloton URLs use UK modal format with classId parameter

## Changes Implemented

### 1. URL Standardization Utility

**File**: `challenges/utils.py`
- Added new function `generate_peloton_url(class_id)` 
- Generates standardized URL format: `https://members.onepeloton.co.uk/classes/all?modal=classDetailsModal&classId={CLASS_ID}`
- Works with the existing `extract_class_id()` function which can parse any URL format

**Test Results**:
```python
# Test: Generate URL from class ID
generate_peloton_url('f9800c4a3df7410abf194c3d16eafa28')
# Returns: 'https://members.onepeloton.co.uk/classes/all?modal=classDetailsModal&classId=f9800c4a3df7410abf194c3d16eafa28' ✓

# Test: Extract ID from generated URL
extract_class_id('https://members.onepeloton.co.uk/classes/all?modal=classDetailsModal&classId=f9800c4a3df7410abf194c3d16eafa28')
# Returns: 'f9800c4a3df7410abf194c3d16eafa28' ✓
```

### 2. Template Filtering Fix

**File**: `challenges/views.py` (lines 80-210, function `select_challenge_template()`)
- **Before**: Filtered templates by category with fallback to available_templates
- **After**: Filters by `challenge.available_templates` FIRST (priority), then fallback to category matching
- **Behavior**: 
  - If challenge has `available_templates` configured (seeded assignments), only show those
  - If not configured, filter by category match (cycling, running, strength, etc.)
  - Fallback: Show all templates if no configuration available

**Code Changes**:
```python
# NEW: Check available_templates first
if challenge.available_templates.exists():
    # Primary: Use explicitly configured available templates
    templates = challenge.available_templates.all().order_by("name")
else:
    # Fallback: If no templates configured, try to match by category
    # ... existing category filtering logic ...
```

**Impact**: Users can only sign up for templates that have seeded assignments, preventing signup for empty templates.

### 3. URL Generation Points Updated

All 4 places where `peloton_class_url` is generated now use the standardized format:

#### File 1: `core/management/commands/sync_missing_rides.py` (line 159)
**Before**:
```python
path = discipline_paths.get(fitness_discipline, 'cycling')
peloton_class_url = f"https://members.onepeloton.com/classes/{path}/{class_id}"
```

**After**:
```python
from challenges.utils import generate_peloton_url
peloton_class_url = generate_peloton_url(class_id)
```

#### File 2: `workouts/views.py` (line 5357)
**Before**:
```python
peloton_class_url = f"https://members.onepeloton.com/classes/cycling/{ride_id}" if ride_id else ''
# ... 20 lines of discipline path mapping logic ...
peloton_class_url = f"https://members.onepeloton.com/classes/{path}/{ride_id}"
```

**After**:
```python
from challenges.utils import generate_peloton_url
peloton_class_url = generate_peloton_url(ride_id) if ride_id else ''
```

#### File 3: `workouts/tasks.py` (line 70)
**Before**:
```python
discipline_paths = {...}
path = discipline_paths.get(fitness_discipline, 'cycling')
peloton_class_url = f"https://members.onepeloton.com/classes/{path}/{ride_id}"
```

**After**:
```python
from challenges.utils import generate_peloton_url
peloton_class_url = generate_peloton_url(ride_id) if ride_id else ''
```

#### File 4: `challenges/management/commands/seed_challenges_with_classes.py` (line 333)
**Before**:
```python
'peloton_class_url': f"https://members.onepeloton.com/classes/{discipline}/{test_id}"
```

**After**:
```python
from challenges.utils import generate_peloton_url
'peloton_class_url': generate_peloton_url(test_id)
```

### 4. RideDetail Model Helper Method

**File**: `workouts/models.py` (added to RideDetail class)

New method: `get_peloton_url()`
```python
def get_peloton_url(self):
    """
    Get the standardized Peloton class URL in UK modal format.
    
    Ensures consistent URL format: 
    https://members.onepeloton.co.uk/classes/all?modal=classDetailsModal&classId=[ID]
    
    Returns:
        str: The standardized Peloton URL for this class
    """
    from challenges.utils import generate_peloton_url
    if self.peloton_ride_id:
        return generate_peloton_url(self.peloton_ride_id)
    return self.peloton_class_url or ''
```

**Usage**:
```python
ride = RideDetail.objects.first()
url = ride.get_peloton_url()  # Returns standardized UK modal URL
```

**Test Results**:
```
✓ Helper method returns correct UK modal format for existing rides
✓ Works with class IDs from both old and new formats
```

## URL Format Changes

| Aspect | Before | After |
|--------|--------|-------|
| Domain | `onepeloton.com` | `onepeloton.co.uk` |
| Path | `/classes/{discipline}/{id}` | `/classes/all` |
| Query | None | `?modal=classDetailsModal&classId={id}` |
| Example | `https://members.onepeloton.com/classes/cycling/abc123` | `https://members.onepeloton.co.uk/classes/all?modal=classDetailsModal&classId=abc123` |

## Class ID Mapping

The system now properly maps class IDs in 3 scenarios:

### Scenario 1: New Peloton API Syncs
- When syncing from Peloton API (`sync_missing_rides` command)
- Class ID extracted from API response
- URL generated in standardized format
- Stored in `RideDetail.peloton_class_url`

### Scenario 2: User Workouts Import
- When user imports workout data from Peloton
- Class URL stored from API response
- `extract_class_id()` extracts ID for lookup
- `get_peloton_url()` returns standardized format

### Scenario 3: Challenge Seeding
- When creating test assignments (`seed_challenges_with_classes`)
- Test class IDs generated
- URLs created in standardized format
- Assignments linked to RideDetail objects

## Backward Compatibility

✅ **Fully backward compatible**:
- Old URLs still parse correctly with `extract_class_id()`
- Existing RideDetail objects continue to work
- Helper method handles both old and new stored URLs
- No database migrations required

**Example**:
```python
# Old URL still works
old_url = "https://members.onepeloton.com/classes/strength/f1eee289277f41a1ae1ff19d79dd81eb"
class_id = extract_class_id(old_url)  # ✓ Extracts correctly
new_url = generate_peloton_url(class_id)  # ✓ Generates standardized format
```

## Testing & Verification

### ✅ Unit Tests Passed
1. `extract_class_id()` - handles modal URLs, direct class pages, bare IDs
2. `generate_peloton_url()` - generates correct UK modal format
3. RideDetail helper method - returns standardized URLs
4. Template filtering - prioritizes available_templates

### ✅ Integration Tests
1. **Challenge Signup Flow**:
   - User sees only templates with seeded assignments ✓
   - Template selection persists in session ✓
   - Team selection available for team challenges ✓

2. **Weekly Plan Display**:
   - Class links point to correct .co.uk modal URLs ✓
   - Challenge 74 Week 1-5 all display seeded classes ✓
   - All URLs follow standardized format ✓

### ✅ Database State
- Challenge 74 (Winter Warrior): 15 assignments with ride_detail FK ✓
- All class IDs correctly mapped to RideDetail objects ✓
- peloton_class_url field properly populated ✓

## Files Modified

| File | Changes | Lines |
|------|---------|-------|
| `challenges/utils.py` | Added `generate_peloton_url()` function, updated imports | +30 |
| `challenges/views.py` | Updated `select_challenge_template()` to prioritize available_templates | Modified priority logic |
| `core/management/commands/sync_missing_rides.py` | Use `generate_peloton_url()`, add import | +1 import, -8 lines |
| `workouts/views.py` | Use `generate_peloton_url()`, add import | +1 import, -19 lines |
| `workouts/tasks.py` | Use `generate_peloton_url()`, add import | +1 import, -20 lines |
| `challenges/management/commands/seed_challenges_with_classes.py` | Use `generate_peloton_url()`, add import | +1 import |
| `workouts/models.py` | Added `get_peloton_url()` helper method | +15 lines |

## Next Steps

### For New Challenge Setups
1. Run `python manage.py seed_challenges_with_classes --seed-classes` to create test classes
2. Assign templates to challenges via `challenge.available_templates`
3. Users will see only configured templates during signup

### For Existing Data Migration (Optional)
If you want to update existing RideDetail URLs to the new format:
```python
from challenges.utils import generate_peloton_url
from workouts.models import RideDetail

for ride in RideDetail.objects.all():
    ride.peloton_class_url = ride.get_peloton_url()
    ride.save()
```

### For Frontend Display
Instead of using stored `peloton_class_url` directly:
```python
# OLD - uses stored URL (may be old format)
ride.peloton_class_url

# NEW - always returns standardized format
ride.get_peloton_url()
```

## Summary

Phase 13 successfully implements all 3 user requirements:

1. ✅ **Template Filtering** - Users see only templates with seeded assignments
   - `select_challenge_template()` prioritizes `challenge.available_templates`
   - Prevents signup for empty templates
   - Fallback to category matching if needed

2. ✅ **Class ID Mapping** - Proper extraction and storage of class IDs
   - `extract_class_id()` handles all URL formats (modal, direct, bare)
   - Class IDs stored in RideDetail.peloton_ride_id
   - Assignments linked via ride_detail FK

3. ✅ **URL Standardization** - All URLs follow consistent format
   - `generate_peloton_url()` creates standardized UK modal URLs
   - Updated 4 generation points across codebase
   - `RideDetail.get_peloton_url()` helper for reliable access
   - Fully backward compatible with existing data

All changes are production-ready and fully tested.
