# Quick Test Guide - Card-Based Workout Assignment

## 🎯 Access the Feature

1. Open Django admin panel
2. Navigate to: **Challenges → [Select a Challenge] → Assign Workouts**
3. URL pattern: `/challenges/admin/{challenge_id}/assign-workouts/`

---

## ✅ Testing Checklist

### Initial Load
- [ ] Page loads without JavaScript errors
- [ ] All activity containers display (Ride, Run, Yoga, Strength if template includes them)
- [ ] Empty activities show search input
- [ ] Existing assignments show cards with images
- [ ] No 404 or 500 errors in browser console

### Search Functionality
- [ ] Click in search box
- [ ] Type "power" and wait 300ms
- [ ] Results dropdown appears below search box
- [ ] Results show: Class Name, Instructor • Duration • Discipline
- [ ] Results update as you type
- [ ] Click a result

### Card Display
- [ ] Card replaces search input
- [ ] Class image displays (or placeholder if missing)
- [ ] Title shows correctly
- [ ] Format: "Instructor • 45min • Hard"
- [ ] Points field shows 50 (default)
- [ ] Peloton link (🔗) is clickable and opens new tab
- [ ] Edit button (✏️) is visible and clickable

### Chart Rendering
- [ ] If class has target metrics (has_chart: true in API)
- [ ] 📊 badge appears in top-right corner of card
- [ ] Doughnut chart displays with zones
- [ ] Chart colors are visible
- [ ] Chart legend appears below

### Edit Functionality
- [ ] Click Edit button
- [ ] Card disappears
- [ ] Search input reappears
- [ ] Can search for different class
- [ ] No page reload occurs
- [ ] Points value preserved

### Points Adjustment
- [ ] Change points value on card
- [ ] Try numbers: 0, 50, 100, 999
- [ ] Value persists when editing/returning

### Form Submission
- [ ] Assign multiple classes across different activities
- [ ] Adjust some points values
- [ ] Click "Save Assignments" button
- [ ] Page redirects to admin dashboard
- [ ] No JavaScript errors occur
- [ ] Form actually submits (check network tab)

### Verify Backend
- [ ] Open Django admin
- [ ] Go to: Challenges → Challenge Workout Assignments
- [ ] Verify records created for each assigned class
- [ ] Check `ride_detail` FK is populated
- [ ] Check points values are correct
- [ ] Check `peloton_url` is filled if from card

---

## 🔍 Testing with Different Data

### Test with Class that HAS target metrics:
- Search for: "Power Zone" 
- Expected: 📊 badge appears, doughnut chart renders

### Test with Class that DOES NOT have target metrics:
- Search for: Random class without metrics
- Expected: No 📊 badge, no chart displayed

### Test Empty Search:
- Type 1 character
- Expected: No results dropdown (need min 2 chars)
- Type 2+ characters
- Expected: Dropdown appears or shows "No results found"

### Test Points Field:
- Set to 0
- Set to 1000
- Set to "abc" (invalid)
- Expected: Form still submits with valid number

### Test Multiple Templates:
- If challenge has multiple templates
- Click template tabs at top
- Expected: Template content switches without page reload
- Different weeks/activities visible for different templates

---

## 🐛 Debug Checklist

If something doesn't work:

1. **Open Browser DevTools (F12)**
   - Check Console tab for JavaScript errors
   - Check Network tab for failed API calls
   - Check Elements tab for DOM structure

2. **Common Issues**:
   
   | Issue | Solution |
   |-------|----------|
   | Search not working | Check API endpoint returns data (see Network tab) |
   | Cards not appearing | Check if `image_url` exists in API response |
   | Chart not rendering | Verify `target_metrics_data` has `zones` array |
   | Edit button not working | Check browser console for errors |
   | Form not submitting | Check all hidden fields populated (Inspect Elements) |
   | Styling looks broken | Clear browser cache (Ctrl+Shift+Del) |

3. **API Response Check**:
   - In Network tab, find request to `/challenges/api/search-classes/?q=...`
   - Click response
   - Verify fields present:
     ```
     - id ✓
     - title ✓
     - instructor ✓
     - duration ✓
     - image_url ✓
     - peloton_url ✓
     - target_metrics_data ✓
     - has_chart ✓
     ```

---

## 📱 Mobile Testing

1. **Open DevTools** → Press F12
2. **Toggle Device Toolbar** → Ctrl+Shift+M
3. **Set to iPhone 12** (390px width)
4. **Test**:
   - [ ] Search input full width
   - [ ] Cards stack vertically (not 2 columns)
   - [ ] Chart not too large
   - [ ] Buttons easily tappable (40px+ height)
   - [ ] No horizontal scrolling
   - [ ] Points input accessible

---

## 🌙 Dark Mode Testing

1. **Open DevTools** → Ctrl+Shift+M (or F12)
2. **Settings** → Appearance → Switch to Dark
3. Or use OS dark mode settings
4. **Test**:
   - [ ] Text visible (not white on white)
   - [ ] Cards have dark background
   - [ ] Chart legend readable
   - [ ] Buttons contrast is good
   - [ ] Search results readable
   - [ ] No color bleeding

---

## 📊 Performance Testing

1. **Open DevTools** → Network tab
2. **Search for a class**
3. **Check**:
   - [ ] Request completes in < 500ms
   - [ ] Response size reasonable (< 100KB)
   - [ ] No duplicate requests (debounce working)

4. **Chart Rendering**:
   - [ ] Chart appears smoothly (no lag)
   - [ ] No console errors about Chart.js
   - [ ] Switching between cards is instant

---

## ✨ Expected Behavior Summary

| Action | Expected Result |
|--------|-----------------|
| Page Load | Cards/search boxes visible, no errors |
| Type in search | 300ms wait, then dropdown results |
| Click result | Card appears, search disappears |
| Click Edit | Search reappears, card disappears |
| Adjust points | Value changes on card |
| Save form | Submits, redirects to admin |
| Check backend | Assignments created in database |

---

## 🎬 Full Test Scenario

```
1. Load page for challenge with Ride/Run/Yoga/Strength
2. Search "power" in Ride → Select "Power Zone 45" → See card with image
3. Search "tread" in Run → Select "Treadmill" → See card
4. Search "flow" in Yoga → Select "Vinyasa Flow" → See card
5. Leave Strength empty
6. Change Ride points to 75
7. Click Ride Edit button → Search "cadence" → Select different → Card updates
8. Click Save Assignments
9. Verify 3 assignments created in Django admin
10. Edit challenge again → Previous assignments should be pre-loaded
```

---

## 🚨 Critical Issues to Report

If you encounter:
- JavaScript errors preventing search
- API returning null/empty fields
- Chart failing to render
- Form not submitting
- Points values lost
- Images not loading

→ Check `/opt/projects/pelvicplanner/challenges/admin_views.py` lines 1030-1087
→ Verify RideDetail model has `image_url` and `peloton_class_url` fields
→ Check Django logs for backend errors

---

## 📞 Files to Reference

- **Main Template**: `challenges/templates/challenges/admin/assign_workouts_cards.html`
- **API Endpoint**: `challenges/admin_views.py` → `search_ride_classes()` function
- **Backend Handler**: `challenges/admin_views.py` → `admin_assign_workouts()` POST logic
- **Model**: `challenges/models.py` → `ChallengeWorkoutAssignment`

---

**Ready to test! Navigate to admin panel and try the new card-based interface.** 🎉
