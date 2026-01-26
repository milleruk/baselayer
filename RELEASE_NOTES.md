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
