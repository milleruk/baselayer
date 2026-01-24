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

2. **GET** `/api/user/{user_id}` - Get user profile by ID
   - Authentication: Bearer token required

3. **GET** `/api/user/{user_id}/workouts` - Get user's workout history
   - Parameters: `page`, `limit`, `sort_by`
   - Authentication: Bearer token required

### Workout Endpoints

1. **GET** `/api/workout/{workout_id}` - Get workout details
   - Authentication: Bearer token required

2. **GET** `/api/workout/{workout_id}/performance_graph` - Get performance data
   - Parameters: `every_n` (sampling interval in seconds)
   - Authentication: Bearer token required

3. **GET** `/api/ride/{ride_id}/details` - Get ride/class details
   - Authentication: Bearer token required

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

## Implementation Files

- **Client**: `peloton/services/peloton.py` - PelotonClient class with all API methods
- **Models**: `peloton/models.py` - PelotonConnection model for storing credentials
- **Views**: `peloton/views.py` - Django views for connection management
- **Forms**: `peloton/forms.py` - Form for entering Peloton credentials
- **Templates**: `templates/peloton/` - UI for managing Peloton connection

## Usage

### Connecting a Peloton Account

1. User navigates to `/peloton/connect/`
2. Enters Peloton username/email and password
3. System authenticates using programmatic OAuth2 flow
4. Access token and user information are stored
5. Leaderboard name is synced to user profile

### Testing Connection

- Use "Test Connection" button to refresh user data
- Automatically refreshes token if expired
- Updates profile with latest leaderboard name

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
