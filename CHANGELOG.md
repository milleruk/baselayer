# Changelog

All notable changes to Chase The Zones will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Refactor `sync_workouts` view to use background tasks
- Add progress tracking UI for background sync
- Enhanced analytics and reporting features
- Additional exercise types and categories
- Improved challenge features
- Mobile app development
- Social features and community support

---

## [0.5.0-rc2] - 2026-02-02

### Enhanced
- **Chart Consistency**: Fixed power zone target lines across all views to use proper Peloton zone target percentages
  - Zone 1 now correctly shows 45% FTP (active recovery) instead of 27.5% FTP (range midpoint)
  - All zones (1-7) now use official Peloton target percentages for consistent targeting
  - History page mini-charts now match detail page target calculations exactly
- **Cycling Detail Enhancement**: Added FTP-based zone shading and visualization to standard cycling workouts
  - Zone colors toggle for output charts on non-power-zone cycling classes
  - Zone labels and %FTP context in tooltips matching power zone class experience
  - Full-canvas chart rendering with hidden axes for cleaner presentation

### Fixed
- Power zone target calculation inconsistency between history mini-charts and detail views
- Zone 1 target now properly represents active recovery effort level
- Standard cycling classes now provide zone context when user has FTP configured

---

## [0.5.0-rc1] - 2026-01-30

### Release Candidate
- Marking the project as **release-candidate ready** after stabilizing workout history ordering, chart parity, and key UI workflows.

### Highlights
- Workout history: stable “most recent activity first” ordering within the same day
- Pace target class library parity with workout detail (target line + metric box alignment)

---

## [0.4.5-alpha] - 2026-01-30

### Fixed
- Workout history: same-day ordering now reflects most recent activity first (date + sync order)

---

## [0.4.4-alpha] - 2026-01-30

### Added
- Class library pace target: client-side **Pace Level** selector to preview alternate targets (no saving)

### Changed
- Class library pace target chart target line now uses **mph pace ranges** (matches workout detail behavior)

### Fixed
- Class library pace target:
  - Target line now matches workout detail (correct zone mapping)
  - Removed one-point “dips” at segment boundaries after the \(-60s\) shift
  - Target metric box now matches the chart and shows **zone names only** (no “Level X”)

---

## [0.4.3-alpha] - 2026-01-30

### Added
- Workout history **mini chart previews** on cards (Power Zone / cycling / pace target)
  - Lightweight SVG previews with hover tooltips + crosshair
  - Target line overlays for Power Zone + Pace Target (with \(-60s\) offset)
- Workout history filtering upgrades
  - Charts toggle (only workouts with usable output/speed series)
  - Class type dropdown filter (de-duplicated by name)
  - Search suggestions endpoint with fuzzy/regex-style matching

### Changed
- Workout history filter bar + type tabs redesigned to a unified “control bar”
- Workout history reverted to standard pagination (removed infinite scroll)
- Stable ordering within a day (latest workout first)

### Fixed
- Filter/pagination links preserve all query params reliably
- Suggestions dropdown layering (no longer hidden behind cards)
- Recorded vs Completed date display on cards
  - **Recorded** uses class recorded/original air date (when available)
  - UK date format (DD/MM/YYYY)

### Technical
- Prefetch `performance_data` only for the current page (major performance improvement)
- Derived card metrics when Peloton metrics are missing
  - Estimated cycling TSS (output series + FTP at workout date)
  - Estimated running avg speed (speed series)

---

## [0.4.2-alpha] - 2026-01-30

### Added
- Enhanced workout detail templates for “charted” disciplines (layout + styling consistency)
- Dedicated cycling detail template for non–Power Zone rides

### Fixed
- Pace target chart duration and controls polish

### Changed
- Stopped tracking local notes (`debug/`) in git

---

## [0.4.1-alpha] - 2026-01-30

### Added
- Pace target workout detail layout + sharing
- Dashboard HTMX enhancements for dynamic updates
- Sync status + cooldown tracking
- Development mode banner

### Fixed
- Pace target class library: dropdown default + recovery pace calculation
- Class detail target line display
- Missing `{% load static %}` in profile template

---

## [v1.0.1-guide-submenu] - 2026-01-27

### Changed
- Move pace zones reference to Guide submenu

---

## [v1.0.0-pace-target-fixes] - 2026-01-27

### Fixed
- Pace target class library: correct pace level dropdown default and recovery pace calculation

---

## [v1.0.0-class-library-sync] - 2026-01-27

### Added
- Class library sync and cleanup features
  - Bulk sync Peloton classes from API
  - Power Zone filtering for cycling classes
  - Cleanup command for non–Power Zone classes

---

## [0.4.0-alpha] - 2026-01-27

### Added
- **Background Sync Architecture**: Celery-based task queue for asynchronous workout processing
  - Immediate workout record creation (synchronous)
  - Background fetching of ride details and performance graphs
  - Scalable solution for users with 4k+ workouts
- **Celery Integration**: Full Celery setup with Redis broker
  - `fetch_ride_details_task`: Background task for fetching class/ride details
  - `fetch_performance_graph_task`: Background task for fetching workout metrics
  - Batch processing tasks for parallel execution
  - Automatic retry logic with exponential backoff
- **Background Sync Documentation**: Comprehensive guide in `docs/BACKGROUND_SYNC.md`
  - Setup instructions for Redis and Celery workers
  - Usage examples and best practices
  - Production considerations and monitoring

### Fixed
- **Sync Status Bug**: Fixed issue where adding Peloton credentials incorrectly marked users as synced
  - `last_sync_at` now only set when workouts are actually synced
  - Users see "First sync will import all your workout history" until they click sync
- **Database Constraint**: Fixed `NOT NULL constraint failed` error for `home_peloton_id` field
  - Added `null=True` to `RideDetail.home_peloton_id` field
  - Migration created and applied
  - Code updated to handle None values gracefully

### Changed
- **Dependencies**: Updated to compatible versions
  - Celery: 5.6.2
  - Kombu: 5.6.2
  - Redis: 7.1.0
  - Added tzlocal: 5.3.1
- **Sync Flow**: Prepared for background processing (tasks created, ready for integration)

### Technical
- Celery configuration in `config/celery.py`
- Task definitions in `workouts/tasks.py`
- Redis broker configuration in settings
- Migration for `home_peloton_id` field update

---

## [0.3.1-alpha] - 2026-01-27

### Fixed
- Base template padding for consistent spacing across pages

---

## [0.3.0-alpha] - 2026-01-27

### Changed
- Recap page redesign with improved layout and chart sizing

### Added
- Documentation for Recap and Eddington pages

---

## [0.2.0-alpha] - 2026-01-26

### Added
- Yearly recap feature with shareable links
- Reorganized sidebar navigation with improved grouping
- PWA/iOS/Android icons and mobile polish
- About / FAQ / Contact / How It Works pages

### Changed
- Landing page and navbar UI improvements and responsiveness tweaks

---

## [0.1.0-alpha] - 2026-01-26

### Added
- Initial alpha release of Chase The Zones platform
- User registration and authentication system
- Peloton OAuth2 integration with encrypted credential storage
- Automatic workout syncing from Peloton API
- Weekly plan generation with integrated pelvic floor exercises
- Exercise library with video demonstrations
- Structured challenges with team support
- Workout history and detailed analytics
- Class library with search and filtering
- Performance graph visualization (Chart.js)
  - Power zone charts with zone bands
  - Pace target charts for running/walking
  - Music timeline overlay
  - Target line visualization with 60-second offset
- Historical FTP and pace level tracking
- Dashboard with comprehensive statistics
- Metrics page with personal records and progression charts
- Landing page and features page
- Privacy policy and terms and conditions (UK GDPR compliant)
- Management commands for data refresh and debugging
- Comprehensive documentation

### Fixed
- Historical pace level detection (uses workout date, not current level)
- Historical FTP detection (uses workout date, not current FTP)
- Speed data extraction from Peloton API for running/walking workouts
- Chart duration calculation from actual segments
- Chart cropping to include warm-up and cool-down
- Timezone deprecation warnings
- Template styling and responsive design
- Classes without performance data handling

### Changed
- Improved landing page design with better icons and sections
- Updated navigation to show Home and Features in top navbar
- Landing page now uses full-width layout (no sidebar)
- Enhanced workout detail page with power profile and zone targets
- Improved pace level extraction from Peloton API data

### Technical
- Django-based backend with PostgreSQL support
- Tailwind CSS for styling with dark mode support
- Chart.js for interactive data visualization
- Alpine.js for interactive UI components
- Responsive design for all screen sizes
- Encrypted credential storage using Fernet
- Comprehensive error handling and logging
