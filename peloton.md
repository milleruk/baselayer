# Peloton API Integration Documentation

This document explains how the Peloton API integration was implemented, including the authentication flow and API endpoints used.

## Overview

The Peloton integration uses OAuth2 authentication with PKCE (Proof Key for Code Exchange) to securely authenticate users and access their Peloton workout data. The implementation is based on the programmatic OAuth2 flow that handles authentication server-side without requiring browser redirects.

## Authentication Flow

### OAuth2 with PKCE

Peloton uses Auth0 for authentication with the following configuration:

- **Auth Domain**: `auth.onepeloton.com`
- **Client ID**: `WVoJxVDdPoFx4RNewvvg6ch2mZ7bwnsM`
- **Audience**: `https://api.onepeloton.com/`
- **Scope**: `offline_access openid peloton-api.members:default`
- **Redirect URI**: `https://members.onepeloton.com/callback` (Peloton's own callback)

### Programmatic Authentication Flow

Since Peloton's OAuth2 client only allows their own redirect URI, we use a programmatic flow that:

1. **Initiates Auth Flow** - Makes a GET request to `/authorize` endpoint to get CSRF token from cookies
2. **Submits Credentials** - POSTs username/password to `/usernamepassword/login` with CSRF token and PKCE parameters
3. **Follows Redirects** - Programmatically follows redirects to extract the authorization code
4. **Exchanges Code for Token** - Uses the authorization code with PKCE verifier to get access token

This approach is based on the working implementation from:
- https://github.com/DadArcade/peloton-to-garmin-py (Python implementation)
- https://github.com/philosowaffle/peloton-to-garmin (C# implementation)

### Key Implementation Details

#### PKCE Generation
- Code verifier: 64-character random URL-safe string
- Code challenge: SHA256 hash of verifier, base64url encoded
- Method: S256

#### CSRF Token Handling
- Extracted from cookies after initial authorize request
- Required for the login POST request
- Cookie name: `_csrf`, domain: `.onepeloton.com`

#### Headers Required
- `User-Agent`: Browser-like user agent string
- `Peloton-Platform`: `web` (required for API access)
- `Auth0-Client`: Base64 encoded JSON `{"name":"auth0.js-ulp","version":"9.14.3"}`
- `Origin` and `Referer`: Set to Auth0 domain for login requests

## API Endpoints

### Base URL
- **API Base**: `https://api.onepeloton.com`
- **Auth Base**: `https://auth.onepeloton.com`

### Authentication Endpoints

1. **GET** `/authorize` - Initiate OAuth flow, get CSRF token
   - Parameters: `client_id`, `audience`, `scope`, `response_type`, `redirect_uri`, `state`, `nonce`, `code_challenge`, `code_challenge_method`

2. **POST** `/usernamepassword/login` - Submit credentials
   - Body: Includes username, password, CSRF token, PKCE parameters
   - Headers: `Auth0-Client`, `Origin`, `Referer`

3. **POST** `/oauth/token` - Exchange authorization code for access token
   - Body: `grant_type=authorization_code`, `client_id`, `code`, `code_verifier`, `redirect_uri`

### User Endpoints

1. **GET** `/api/me` - Get current authenticated user information
   - Returns: User object with `id`, `username`, `leaderboard_name`, etc.
   - Authentication: Bearer token in `Authorization` header
   - Used for: Getting user ID and basic profile info

2. **GET** `/api/user/{user_id}` - Get user profile by ID
   - Authentication: Bearer token required

3. **GET** `/api/user/{user_id}/overview` - Get user overview statistics
   - Returns: User statistics including total workouts, output, distance, calories, pedaling duration
   - Authentication: Bearer token required
   - Used for: Syncing lifetime Peloton statistics to user profile
   - Fields synced: `total_workouts`, `total_output`, `total_distance`, `total_calories`, `total_pedaling_duration`

4. **GET** `/api/user/{user_id}/workouts` - Get user's workout history
   - Parameters: `page`, `limit`, `sort_by`
   - Authentication: Bearer token required

### Workout Endpoints

1. **GET** `/api/workout/{workout_id}` - Get workout details
   - Authentication: Bearer token required

2. **GET** `/api/workout/{workout_id}/performance_graph` - Get performance data
   - Parameters: `every_n` (sampling interval in seconds, default: 5)
   - Authentication: Bearer token required
   - Returns: Time-series performance data with metrics (output, cadence, resistance, speed, heart rate)
   - Structure:
     - `summaries`: Array of summary metrics (total_output, total_calories, distance, etc.)
     - `metrics`: Array of time-series metrics with `slug`, `average_value`, `max_value`, and `values` arrays
     - `seconds_since_pedaling_start`: Array of timestamps for each data point
   - Used for: Extracting detailed workout metrics (TSS, output, cadence, resistance, speed, heart rate)

3. **GET** `/api/ride/{ride_id}/details` - Get ride/class details
   - Authentication: Bearer token required
   - Returns: Class/ride template information including:
     - Class title, description, duration
     - Instructor information
     - Workout type and difficulty
     - Target metrics (Power Zone ranges, cadence/resistance ranges, pace targets)
     - Class URL and metadata
   - Used for: Storing shared class details in `RideDetail` model

### Instructor Endpoints

1. **GET** `/api/instructor` - List all instructors
   - Parameters: `page`, `limit`
   - Authentication: Bearer token required

2. **GET** `/api/instructor/{instructor_id}` - Get instructor details
   - Authentication: Bearer token required

## API Reference

Full API documentation available at:
- **SwaggerHub**: https://app.swaggerhub.com/apis/DovOps/peloton-unofficial-api/0.3.0

## Token Management

### Access Tokens
- **Type**: Bearer tokens (OAuth2 access tokens)
- **Expiration**: ~48 hours (172800 seconds)
- **Storage**: Encrypted in database using Fernet encryption
- **Usage**: Sent in `Authorization: Bearer <token>` header

### Refresh Tokens
- **Purpose**: Obtain new access tokens without re-authentication
- **Storage**: Encrypted in database
- **Usage**: Exchanged via `/oauth/token` endpoint with `grant_type=refresh_token`

### Token Refresh Flow
- Automatically attempted when API calls return 401 Unauthorized
- New tokens are stored and used for subsequent requests

## Security Considerations

1. **Credential Encryption**: Username, password, and tokens are encrypted at rest using Fernet (symmetric encryption)
2. **Encryption Key**: Uses `PELOTON_ENCRYPTION_KEY` from settings, falls back to SECRET_KEY hash if not set
3. **Session Management**: Tokens are stored per-user and automatically refreshed when expired
4. **CSRF Protection**: OAuth2 state parameter prevents CSRF attacks

## Workout Syncing

### Sync Process

The workout sync process (`/workouts/sync/`) fetches all user workouts and stores detailed information:

1. **Fetches Workout List** - Uses `/api/user/{userId}/workouts` with pagination
2. **For Each Workout**:
   - Fetches detailed workout info from `/api/workout/{workoutId}`
   - Fetches ride/class details from `/api/ride/{rideId}/details`
   - Fetches performance graph from `/api/workout/{workoutId}/performance_graph` (every_n=5)
   - Creates/updates `RideDetail` record (shared class information)
   - Creates/updates `Workout` record (user-specific workout instance)
   - Extracts metrics from performance graph:
     - **Summary metrics** (from `summaries` array): total_output, total_calories, distance
     - **Average/Max metrics** (from `metrics` array): avg_output, max_output, avg_cadence, max_cadence, avg_resistance, max_resistance, avg_speed, max_speed, avg_heart_rate, max_heart_rate
     - **TSS** (Training Stress Score): from detailed_workout or performance_graph
   - Stores metrics in `WorkoutDetails` model
   - Stores time-series data in `WorkoutPerformanceData` model (5-second intervals)

### Data Models

- **RideDetail**: Stores shared class/ride template information
  - Links to `WorkoutType` and `Instructor`
  - Stores target metrics (Power Zone ranges, cadence/resistance ranges, pace targets)
  - Stores class metadata (title, duration, difficulty, description)
  
- **Workout**: Stores user-specific workout instances
  - Links to `RideDetail` (no data duplication)
  - Stores user, completion date, Peloton workout ID
  - Links to `WorkoutDetails` for metrics
  
- **WorkoutDetails**: Stores workout metrics
  - TSS, total_output, avg_output, max_output
  - Distance, total_calories
  - Heart rate (avg/max), cadence (avg/max), resistance (avg/max), speed (avg/max)
  
- **WorkoutPerformanceData**: Stores time-series performance data
  - Timestamp, output, cadence, resistance, speed, heart_rate
  - Used for performance graphs and analysis

### Target Metrics

The system extracts and stores target metrics from ride details:

- **Power Zone Classes**: Output ranges for zones 1-7 (based on user's latest FTP)
- **Non-Power Zone Cycling**: Cadence and resistance target ranges
- **Treadmill Runs/Walks**: Pace target ranges (Recovery, Easy, Moderate, etc.) based on user's latest pace target level

These are displayed on workout detail pages with interactive Chart.js graphs showing target zones and actual performance.

## Management Commands

### Debugging Commands

1. **`download_peloton_endpoints.py`** - Download JSON from various endpoints
   - Usage: `python manage.py download_peloton_endpoints <endpoint_type> <username>`
   - Endpoints: `user_overview`, `user_details`, `workouts_list`, `detailed_workout`, `ride_details`
   - Saves JSON files to `tmp/` directory for inspection

2. **`download_ride_details.py`** - Download specific ride/class details
   - Usage: `python manage.py download_ride_details <ride_id> [--workout-id] [--username]`
   - Extracts ride_id from workout_id if needed
   - Includes `--list-fields` option to inspect data structure

3. **`download_performance_graph.py`** - Download performance graph for a workout
   - Usage: `python manage.py download_performance_graph <workout_id> [--username] [--every-n] [--django-id]`
   - Downloads time-series performance data
   - Useful for debugging metric extraction

### Data Syncing Commands

1. **`sync_instructors.py`** - Sync all Peloton instructors
   - Usage: `python manage.py sync_instructors [--username]`
   - Fetches all instructors and stores/updates `Instructor` records
   - Includes detailed information (bio, location, username)

2. **`fetch_peloton_overview.py`** - Fetch and save user overview data
   - Usage: `python manage.py fetch_peloton_overview <peloton_username> [--list]`
   - Downloads user overview and user details to JSON files

## Implementation Files

- **Client**: `peloton/services/peloton.py` - PelotonClient class with all API methods
  - `authenticate()` - OAuth2 authentication flow
  - `fetch_user_overview()` - User statistics
  - `fetch_user_workouts_page()` - Paginated workout list
  - `iter_user_workouts()` - Iterator for all workouts
  - `fetch_workout()` - Detailed workout information
  - `fetch_ride_details()` - Class/ride template details
  - `fetch_performance_graph()` - Time-series performance data
  - `fetch_instructor()` - Instructor details
  - `iter_all_instructors()` - Iterator for all instructors
  
- **Models**: 
  - `peloton/models.py` - PelotonConnection model for storing credentials
  - `workouts/models.py` - Workout, RideDetail, WorkoutDetails, WorkoutPerformanceData models
  
- **Views**: 
  - `peloton/views.py` - Connection management and profile updates
  - `workouts/views.py` - Workout syncing, history, and detail views
  
- **Forms**: `peloton/forms.py` - Form for entering Peloton credentials
  
- **Templates**: 
  - `templates/peloton/` - UI for managing Peloton connection
  - `templates/workouts/` - Workout history and detail pages with charts
  - `templates/plans/dashboard.html` - Enhanced dashboard with Peloton stats

## Usage

### Connecting a Peloton Account

1. User navigates to `/peloton/connect/`
2. Enters Peloton username/email and password
3. System authenticates using programmatic OAuth2 flow
4. Access token and user information are stored
5. Fetches user data from `/api/me` endpoint
6. Fetches user statistics from `/api/user/{userId}/overview` endpoint
7. Leaderboard name and statistics are synced to user profile

### Testing Connection

- Use "Test Connection" button to refresh user data
- Automatically refreshes token if expired
- Updates profile with latest leaderboard name and statistics
- Fetches fresh data from both `/api/me` and `/api/user/{userId}/overview` endpoints

### Syncing Workouts

- Navigate to `/workouts/` page
- Click "Sync Workouts" button to start sync process
- Sync process:
  - Fetches all workouts from Peloton API
  - Creates/updates `RideDetail` records for class information
  - Creates/updates `Workout` records linked to ride details
  - Extracts metrics from performance graph endpoint
  - Stores time-series performance data
  - Shows progress via AJAX with queue status
- Workouts are displayed on:
  - Dashboard (`/dashboard/`) - Recent workouts and statistics
  - Workout History (`/workouts/`) - Full list with filters and pagination
  - Workout Detail (`/workouts/{id}/`) - Detailed view with performance graphs

### Profile Fields Synced

From `/api/me`:
- `peloton_leaderboard_name` - User's leaderboard/username

From `/api/user/{userId}/overview`:
- `peloton_total_workouts` - Total number of workouts completed
- `peloton_total_output` - Total output in kilojoules (calculated from workout details)
- `peloton_total_distance` - Total distance in miles (calculated from workout details)
- `peloton_total_calories` - Total calories burned (calculated from workout details)
- `peloton_total_pedaling_duration` - Total pedaling time in seconds
- `peloton_total_pedaling_metric_workouts` - Workouts with pedaling metrics (cycling, etc.)
- `peloton_total_non_pedaling_metric_workouts` - Workouts without pedaling metrics (meditation, strength, etc.)
- `peloton_current_weekly_streak` - Current weekly workout streak
- `peloton_best_weekly_streak` - Best weekly workout streak achieved
- `peloton_current_daily_streak` - Current daily workout streak
- `peloton_total_achievements` - Total number of Peloton achievements earned
- `peloton_workout_counts` - JSON breakdown of workouts by type (slug -> count)
- `peloton_last_synced_at` - Timestamp of last sync

## Troubleshooting

### Common Issues

1. **403 Forbidden**: 
   - Ensure `Peloton-Platform: web` header is set
   - Check that User-Agent matches browser format
   - Verify CSRF token is being extracted correctly

2. **Token Expired**:
   - Tokens expire after ~48 hours
   - System automatically refreshes on API calls
   - User can manually test connection to refresh

3. **User ID Not Found**:
   - Verify `/api/me` endpoint is accessible
   - Check that bearer token is valid
   - Ensure token has correct scopes

## References

- Peloton Unofficial API Spec: https://app.swaggerhub.com/apis/DovOps/peloton-unofficial-api/0.3.0
- Python Implementation: https://github.com/DadArcade/peloton-to-garmin-py
- C# Implementation: https://github.com/philosowaffle/peloton-to-garmin
