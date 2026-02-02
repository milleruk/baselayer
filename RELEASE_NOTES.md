# Release Notes

## Alpha Release v0.1.0 - January 26, 2026

### 🎉 Initial Alpha Release

This is the first alpha release of Chase The Zones, a comprehensive training platform that integrates pelvic floor exercises with Power Zone and running training programmes.

---

## ✨ Major Features

### Peloton Integration
- **OAuth2 Authentication**: Secure Peloton account connection with encrypted credentials
- **Automatic Workout Syncing**: Sync workouts, classes, and performance data from Peloton
- **Performance Graph Visualization**: Interactive charts showing power zones, pace targets, and actual performance
- **Historical Data Tracking**: Accurate FTP and pace level detection based on workout dates
- **Workout History**: Complete workout library with detailed metrics and analytics
- **Class Library**: Browse and search Peloton classes with filtering and search capabilities

### Training Plans & Challenges
- **Automated Weekly Plan Generation**: Generate Power Zone-aligned weekly plans with integrated pelvic floor exercises
- **Structured Challenges**: Multi-week progressive programmes with team support
- **Progress Tracking**: Mark exercises complete, add notes, and monitor consistency
- **Challenge Analytics**: Track completion rates, points earned, and team performance

### Exercise Library
- **Comprehensive Exercise Database**: Browse pelvic floor exercises with detailed descriptions
- **Video Demonstrations**: Embedded video links for proper form and technique
- **Exercise Categories**: Organized by exercise type (basic kegels, long-hold, pulse, elevator, etc.)
- **Form Cues**: Detailed instructions for each exercise

### Analytics & Metrics
- **Dashboard Analytics**: Overview of workouts, plans, and progress
- **Power Zone Visualization**: Interactive charts with zone bands and target lines
- **Pace Target Visualization**: Running/walking pace target charts with actual vs target performance
- **FTP & Pace Level Tracking**: Historical tracking of Functional Threshold Power and pace levels
- **Personal Records**: Track peak power for 1min, 3min, 5min, 10min, 20min intervals
- **Monthly & Yearly Statistics**: Comprehensive workout statistics by discipline

### User Interface
- **Modern Design**: Clean, responsive interface with dark mode support
- **Mobile Responsive**: Fully optimized for desktop, tablet, and mobile devices
- **Landing Page**: Professional marketing page with feature highlights
- **Features Page**: Comprehensive feature documentation
- **Intuitive Navigation**: Easy-to-use sidebar and top navigation

---

## 🔧 Technical Features

### Data Management
- **Historical Data Lookup**: Accurate FTP and pace level detection using workout dates
- **Speed Data Extraction**: Correct extraction of speed data from Peloton API for running/walking workouts
- **Performance Data Refresh**: Management commands to refresh workout performance data
- **Bulk Operations**: Commands to refresh all running/walking workouts

### Chart Visualization
- **Chart.js Integration**: Interactive performance graphs with zone bands
- **Music Timeline**: Song overlay on performance charts
- **Target Line Offsets**: Accurate 60-second offset for target lines
- **Zone Compliance**: Visual progress bars showing time in target zones

### Security & Privacy
- **UK GDPR Compliance**: Privacy policy and terms following UK data protection laws
- **Encrypted Credentials**: Peloton credentials encrypted at rest
- **Medical Disclaimer**: Prominent health warnings and medical disclaimers
- **Non-Affiliation Notice**: Clear statement of non-affiliation with Peloton

---

## 📋 What's Included

### Core Functionality
- ✅ User registration and authentication
- ✅ Peloton account connection and syncing
- ✅ Weekly plan generation
- ✅ Exercise library browsing
- ✅ Challenge participation
- ✅ Workout history and analytics
- ✅ Class library browsing
- ✅ Performance graph visualization
- ✅ Progress tracking

### Management Commands
- `refresh_workout_performance` - Refresh performance data for a specific workout
- `refresh_all_running_walking` - Bulk refresh all running/walking workouts
- `download_workout_jsons` - Download raw JSON data for debugging
- `sync_workouts` - Sync workouts from Peloton API

### Documentation
- Workout Detail Page documentation
- Peloton API Integration guide
- Sync Strategy documentation
- Class Library documentation

---

## 🐛 Known Issues & Limitations

### Alpha Limitations
- This is an alpha release - some features may be incomplete or subject to change
- Performance optimization may be needed for large datasets
- Some edge cases in workout data parsing may need refinement
- UI/UX improvements are ongoing

### Browser Compatibility
- Optimized for modern browsers (Chrome, Firefox, Safari, Edge)
- Dark mode requires JavaScript
- Chart.js requires modern browser support

---

## 🚀 Getting Started

1. **Register an Account**: Create your account at the registration page
2. **Connect Peloton**: Link your Peloton account in your profile settings
3. **Sync Workouts**: Your workouts will automatically sync from Peloton
4. **Generate a Plan**: Create your first weekly plan with integrated exercises
5. **Track Progress**: Mark exercises complete and monitor your progress

---

## 📝 Notes

- **Data Privacy**: All data is stored securely and encrypted. We follow UK GDPR regulations.
- **Peloton API**: We use Peloton's API for data retrieval only. We are not affiliated with Peloton.
- **Medical Disclaimer**: All exercises and plans are for informational purposes. Always consult with a healthcare professional.

---

## 🔄 What's Next

Future releases will include:
- Enhanced analytics and reporting
- Additional exercise types and categories
- Improved challenge features
- Mobile app (planned)
- Social features and community support

---

## 📞 Support

For issues, questions, or feedback, please contact support or check the documentation.

---

**Release Date**: January 26, 2026  
**Version**: v0.1.0-alpha  
**Status**: Alpha Release

---

## Alpha Release v0.4.0 - January 27, 2026

### 🚀 Background Sync & Bug Fixes

This release introduces background processing capabilities and fixes critical sync issues.

### ✨ New Features

#### Background Sync Architecture
- **Celery Integration**: Full task queue system for asynchronous processing
- **Immediate Response**: Basic workout records created instantly
- **Background Processing**: Ride details and performance graphs fetched asynchronously
- **Scalability**: Handles users with 4k+ workouts without blocking requests
- **Retry Logic**: Automatic retries on API failures with exponential backoff

#### Task System
- `fetch_ride_details_task`: Background fetching of class/ride details
- `fetch_performance_graph_task`: Background fetching of workout metrics
- Batch processing support for parallel execution
- Comprehensive error handling and logging

### 🐛 Bug Fixes

#### Sync Status Issue
- **Fixed**: Adding Peloton credentials no longer incorrectly marks users as synced
- Users now see "First sync will import all your workout history" until they actually sync
- `last_sync_at` only set when workouts are actually synced

#### Database Constraint
- **Fixed**: `NOT NULL constraint failed` error for `home_peloton_id` field
- Added `null=True` to allow NULL values
- Migration created and applied

### 📚 Documentation

- Added comprehensive background sync guide (`docs/BACKGROUND_SYNC.md`)
- Setup instructions for Redis and Celery workers
- Usage examples and production considerations

### 🔧 Technical Updates

- Updated dependencies to compatible versions:
  - Celery 5.6.2
  - Kombu 5.6.2
  - Redis 7.1.0
  - tzlocal 5.3.1

### 📋 Next Steps

- Refactor sync view to use background tasks (ready for implementation)
- Add progress tracking UI for background sync
- Enhanced monitoring and error reporting

---

**Release Date**: January 27, 2026  
**Version**: v0.4.0-alpha  
**Status**: Alpha Release

---

## Alpha Release v0.4.1 - January 30, 2026

### 🎯 Pace Target Detail + Dashboard Enhancements
- Pace target workout detail page layout + sharing
- Dashboard HTMX enhancements for smoother, dynamic updates
- Sync status and cooldown tracking improvements
- Development mode banner

### 🐛 Fixes
- Pace target class library: corrected dropdown default and recovery pace calculation
- Class detail target line display fixes

---

## Alpha Release v0.4.2 - January 30, 2026

### 🧩 Workout Template Expansion
- Modernized “charted” workout detail templates for consistency
- Added a dedicated non–Power Zone cycling detail template
- Continued chart/control refinements for pace target

### 🧹 Repo Hygiene
- Stopped tracking local debug notes (`debug/`)

---

## Alpha Release v0.4.3 - January 30, 2026

### 📈 Workout History Card Charts
- Added mini chart previews directly on workout cards (Power Zone / cycling / pace target)
  - SVG-based, lightweight, fast
  - Hover tooltips + crosshair
  - Target lines for Power Zone + Pace Target (with \(-60s\) offset)

### 🔎 Better Filtering & Search
- New “Charts” toggle to show only workouts with usable output/speed series
- Class type filter dropdown (de-duplicated labels)
- Restored JSON search suggestions with fuzzy/regex-style matching
- Filter bar + type tabs redesigned to match PelvicPlanner styling

### ⚙️ Performance & Data Quality
- Prefetch `performance_data` only for the current page
- Derived metrics on cards when Peloton values are missing
  - Estimated cycling TSS (output series + FTP at workout date)
  - Estimated running avg speed (speed series)

---

## Alpha Release v0.4.4 - January 30, 2026

### 🏃 Pace Target Class Library Parity
- Class library pace target chart target line now uses **mph pace ranges** (matches workout detail)
- Added a **Pace Level** preview selector for class library pace target (client-side only; no saving)

### 🐛 Fixes
- Removed one-point “dips” in class library target line at segment boundaries (after \(-60s\) shift)
- Target metric box now matches the chart and shows only the zone name (Recovery/Easy/Moderate/Challenging/Hard/Very Hard/Max)

---

## Alpha Release v0.4.5 - January 30, 2026

### 🧭 Workout History Ordering
- Same-day workouts now order by “most recent activity first” (date + sync order)

---

## Release Candidate v0.5.0-rc2 - February 2, 2026

### 🎯 Chart Consistency & Zone Accuracy

This release candidate fixes a critical inconsistency in power zone targeting across the platform and enhances the standard cycling workout experience.

### Key Improvements

**Power Zone Target Fixes**
- Fixed Zone 1 targeting to properly show 45% FTP (active recovery) instead of incorrect 27.5% FTP
- All power zones now use official Peloton target percentages instead of zone range midpoints
- History page mini-charts now match detail page calculations exactly
- Consistent zone targeting across all workout views

**Enhanced Cycling Experience**
- Added FTP-based zone shading to standard cycling workout detail pages
- Zone colors toggle for output charts on non-power-zone cycling classes  
- Zone labels and %FTP context in tooltips matching power zone class experience
- Full-canvas chart rendering with hidden axes for cleaner presentation

### Why This Matters
Previously, Zone 1 targets showed as ~52W instead of the correct ~86W for a 190W FTP user, making active recovery efforts appear harder than intended. This fix ensures accurate pacing across all training zones.

---

## Release Candidate v0.5.0-rc1 - January 30, 2026

### ✅ Release Candidate
This release candidate focuses on **stability and parity** across core UX flows.

### Highlights
- Workout history: consistent ordering and improved browsing experience
- Pace target class library: chart parity and accurate target readouts
