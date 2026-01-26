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

## [Unreleased]

### Planned
- Enhanced analytics and reporting features
- Additional exercise types and categories
- Improved challenge features
- Mobile app development
- Social features and community support
