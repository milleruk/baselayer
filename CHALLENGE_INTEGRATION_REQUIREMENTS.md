# Challenge Class Integration - Key Requirements

## 1. Template Filtering on Challenge Signup ⚠️ NEEDS REVIEW
**Requirement**: When a user signs up for a challenge, they should only see plan templates that are **available for that challenge**.

**Current Status**: 
- `select_challenge_template()` view in `challenges/views.py` filters by category match
- But should also check `challenge.available_templates` relationship
- **ACTION NEEDED**: Ensure only templates with seeded assignments are shown (templates that have ChallengeWorkoutAssignment records)

**Logic**:
```python
# Only show templates that:
# 1. Are in challenge.available_templates OR
# 2. Have seeded assignments for this challenge (ChallengeWorkoutAssignment records exist)
```

**File**: [challenges/views.py](challenges/views.py#L80-L210) - `select_challenge_template()` function

---

## 2. Class ID to Ride ID Mapping ⚠️ NEEDS VALIDATION
**Requirement**: Extract class IDs from Peloton URLs and match them to RideDetail records.

**URL Format**:
```
https://members.onepeloton.co.uk/classes/all?modal=classDetailsModal&classId=f9800c4a3df7410abf194c3d16eafa28
                                                                           ↑
                                                                    CLASS_ID (peloton_ride_id)
```

**Current Implementation**:
- `RideDetail.peloton_ride_id` stores the class ID
- `challenges/utils.py` has `extract_class_id()` function to parse URLs
- `ChallengeWorkoutAssignment` stores `peloton_url` (the full URL)
- Should also populate `ride_detail` FK to the matching `RideDetail` object

**Files**:
- [workouts/models.py](workouts/models.py#L97) - RideDetail model
- [challenges/utils.py](challenges/utils.py) - extract_class_id() function
- [challenges/models.py](challenges/models.py#L457) - ChallengeWorkoutAssignment.ride_detail FK

**Validation Checklist**:
- [ ] extract_class_id() correctly extracts ID from URL
- [ ] ChallengeWorkoutAssignment.ride_detail is populated when assignments are seeded
- [ ] Lookups use ride_detail FK when available

---

## 3. Peloton URL Format ✅ STANDARDIZED
**Requirement**: All Peloton links should use a consistent format.

**Standard Format**:
```
https://members.onepeloton.co.uk/classes/all?modal=classDetailsModal&classId=<CLASS_ID>
```

**Current Status**:
- Seeding command sets `peloton_url` from `RideDetail.peloton_class_url`
- Need to ensure all URL generation uses the standard format

**File**: [workouts/models.py](workouts/models.py#L130) - `peloton_class_url` field
**Action**: Verify all places that create/update peloton URLs use the standard format

---

## 4. Implementation Checklist

### Phase 1: Template Filtering (PRIORITY)
- [ ] Update `select_challenge_template()` to filter by `challenge.available_templates`
- [ ] Prevent signup for templates with no seeded assignments
- [ ] Show warning if template has incomplete seeding

### Phase 2: Class ID Validation (PRIORITY)
- [ ] Verify `extract_class_id()` works with all URL formats
- [ ] Ensure `ChallengeWorkoutAssignment.ride_detail` is populated during seeding
- [ ] Add validation in admin to check ride_detail FK

### Phase 3: URL Standardization (MEDIUM)
- [ ] Audit all places that create peloton_urls
- [ ] Ensure `RideDetail.peloton_class_url` format is correct
- [ ] Update any hardcoded URL patterns

---

## 5. Related Files

**Core Models**:
- [challenges/models.py](challenges/models.py) - Challenge, ChallengeWorkoutAssignment
- [workouts/models.py](workouts/models.py) - RideDetail
- [plans/models.py](plans/models.py) - PlanTemplate

**Views**:
- [challenges/views.py](challenges/views.py) - select_challenge_template(), join_challenge()
- [tracker/views.py](tracker/views.py) - select_template() (standalone plans)

**Services**:
- [challenges/utils.py](challenges/utils.py) - extract_class_id()
- [core/services/ride_detail.py](core/services/ride_detail.py) - ride_detail service
- [plans/services.py](plans/services.py) - generate_weekly_plan()

**Management Commands**:
- [challenges/management/commands/seed_challenges_with_classes.py](challenges/management/commands/seed_challenges_with_classes.py)
- [challenges/management/commands/regenerate_challenge_plans.py](challenges/management/commands/regenerate_challenge_plans.py)

---

## 6. Testing Notes

**Test Scenario**: User joins Winter Warrior Challenge
1. Click "Join Challenge"
2. Should only see templates with seeded assignments (currently: "3 Rides a Week")
3. Select template
4. View weekly plans
5. Verify all daily items link to seeded Peloton classes
6. Click on class → should navigate to proper Peloton URL

**Expected URL Flow**:
```
ChallengeWorkoutAssignment.peloton_url 
  → displays in DailyPlanItem 
  → user clicks 
  → navigates to https://members.onepeloton.co.uk/classes/all?modal=classDetailsModal&classId=...
```
