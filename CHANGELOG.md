# Changelog

All notable changes to Chase The Zones will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

## [Unreleased]

### Planned
- Refactor `sync_workouts` view to use background tasks
- Add progress tracking UI for background sync
- Enhanced analytics and reporting features
- Additional exercise types and categories
- Improved challenge features
- Mobile app development
- Social features and community support
