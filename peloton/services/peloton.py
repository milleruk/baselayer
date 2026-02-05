from __future__ import annotations

import logging
import secrets
import base64
import hashlib
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlencode, parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.onepeloton.com"
AUTH_DOMAIN = "auth.onepeloton.com"
AUTH_CLIENT_ID = "WVoJxVDdPoFx4RNewvvg6ch2mZ7bwnsM"
AUTH_AUDIENCE = "https://api.onepeloton.com/"
AUTH_SCOPE = "offline_access openid peloton-api.members:default"
AUTH_REDIRECT_URI = "https://members.onepeloton.com/callback"
AUTH0_CLIENT_PAYLOAD = "eyJuYW1lIjoiYXV0aDAuanMtdWxwIiwidmVyc2lvbiI6IjkuMTQuMyJ9"
AUTH_AUTHORIZE_PATH = "/authorize"
AUTH_TOKEN_PATH = "/oauth/token"
BEARER_TOKEN_DEFAULT_TTL_SECONDS = 172800
SESSION_COOKIE = "peloton_session_id"


class PelotonAPIError(Exception):
    """Raised when the Peloton API returns an unexpected response."""


@dataclass
class Pagination:
    next_cursor: Optional[Dict[str, Any]]
    total: int
    count: int


@dataclass
class Token:
    """OAuth2 token response"""
    access_token: str
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int = 172800  # Default 48 hours
    scope: Optional[str] = None


class PelotonClient:
    """Lightweight client for the unofficial Peloton API."""

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        bearer_token: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        # Emulate browser headers – Peloton increasingly blocks non-browser clients.
        # These headers help avoid 403 responses like "Endpoint no longer accepting requests."
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Content-Type": "application/json",
                # Peloton-Platform header required for API access
                "Peloton-Platform": "web",
                # Web origin and referer expected by Peloton web endpoints
                "Origin": "https://members.onepeloton.com",
                "Referer": "https://members.onepeloton.com/",
                # Some endpoints gate on X-Requested-With to identify AJAX requests
                "X-Requested-With": "XMLHttpRequest",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site",
            }
        )
        self.token: Optional[Token] = None
        self.login_payload: Optional[Dict[str, Any]] = None
        
        if bearer_token:
            # Use provided bearer token
            self.token = Token(access_token=bearer_token)
            self._set_auth_header()
        elif username and password:
            # Authenticate using OAuth2 flow
            self.token = self.authenticate(username, password)
            self._set_auth_header()
            # Fetch user info after authentication
            self._fetch_user_info()

    # ------------------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------------------
    def _generate_random_string(self, length: int) -> str:
        """Generate a random URL-safe string"""
        res = secrets.token_urlsafe(length)
        return res[:length].replace('+', '-').replace('/', '_').replace('=', '')
    
    def _generate_code_challenge(self, verifier: str) -> str:
        """Generate PKCE code challenge from verifier"""
        sha256_hash = hashlib.sha256(verifier.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(sha256_hash).decode('utf-8').replace('=', '')
    
    def generate_pkce_pair(self) -> tuple[str, str]:
        """Generate PKCE code verifier and code challenge"""
        # Generate code verifier (random string)
        code_verifier = self._generate_random_string(64)
        code_challenge = self._generate_code_challenge(code_verifier)
        return code_verifier, code_challenge
    
    def get_authorization_url(self, redirect_uri: str, state: Optional[str] = None) -> tuple[str, str]:
        """
        Generate OAuth2 authorization URL with PKCE.
        Returns (authorization_url, code_verifier) tuple.
        """
        code_verifier, code_challenge = self.generate_pkce_pair()
        
        if state is None:
            state = secrets.token_urlsafe(32)
        
        # Generate nonce for additional security
        nonce = secrets.token_urlsafe(32)
        
        params = {
            "client_id": AUTH_CLIENT_ID,
            "audience": AUTH_AUDIENCE,
            "scope": AUTH_SCOPE,
            "response_type": "code",
            "response_mode": "query",
            "redirect_uri": redirect_uri,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "auth0Client": AUTH0_CLIENT_PAYLOAD,
        }
        
        auth_url = f"https://{AUTH_DOMAIN}{AUTH_AUTHORIZE_PATH}?{urlencode(params)}"
        return auth_url, code_verifier
    
    def exchange_code_for_token(self, code: str, code_verifier: str, redirect_uri: str) -> Token:
        """
        Exchange authorization code for access token using PKCE.
        """
        endpoint = f"https://{AUTH_DOMAIN}{AUTH_TOKEN_PATH}"
        
        auth_session = requests.Session()
        auth_session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        })
        
        payload = {
            "grant_type": "authorization_code",
            "client_id": AUTH_CLIENT_ID,
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }
        
        response = auth_session.post(endpoint, json=payload, timeout=self.timeout)
        data = self._raise_for_status(response)
        
        token = Token(
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            id_token=data.get("id_token"),
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in", BEARER_TOKEN_DEFAULT_TTL_SECONDS),
            scope=data.get("scope"),
        )
        
        if not token.access_token:
            raise PelotonAPIError("Token exchange succeeded but no access token was returned")
        
        logger.debug("Exchanged authorization code for token")
        return token
    
    def get_user_following_ids(self, user_id: str) -> list[str]:
        """
        Fetch all Peloton user IDs that a user is following.
        Uses pagination to fetch all pages.
        Returns list of user IDs only.
        """
        following_ids = []
        limit = 100  # Increased from 20 to reduce API calls
        page = 0
        
        while True:
            params = {
                "limit": limit,
                "page": page
            }
            
            try:
                url = f"{self.base_url}/api/user/{user_id}/following"
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract user IDs from results
                users_in_page = data.get("data", [])
                if not users_in_page:
                    # No more data, we're done
                    break
                
                for user in users_in_page:
                    if "id" in user:
                        following_ids.append(user["id"])
                
                logger.info(f"Fetched page {page} with {len(users_in_page)} users. Total so far: {len(following_ids)}")
                
                # Check if there are more pages
                total = data.get("total", 0)
                page_count = data.get("page_count", 0)
                
                # If we have fetched all users or no more pages, stop
                if len(following_ids) >= total or len(users_in_page) < limit:
                    break
                
                # Move to next page
                page += 1
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching following for user {user_id}: {e}")
                raise PelotonAPIError(f"Failed to fetch following: {str(e)}")
        
        logger.info(f"Finished fetching following. Total users: {len(following_ids)}")
        return following_ids
    
    def authenticate(self, username: str, password: str) -> Token:
        """
        Authenticate using OAuth2 authorization code flow with PKCE.
        This method programmatically handles the OAuth flow without requiring browser redirects.
        Based on the working Python implementation from peloton-to-garmin-py.
        """
        from bs4 import BeautifulSoup
        from urllib.parse import urlparse, parse_qs
        
        # PKCE Setup
        code_verifier = self._generate_random_string(64)
        code_challenge = self._generate_code_challenge(code_verifier)
        state = self._generate_random_string(32)
        nonce = self._generate_random_string(32)
        
        # Use a separate session for auth to avoid header conflicts
        auth_session = requests.Session()
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        auth_session.headers.update({
            "User-Agent": user_agent,
            "Peloton-Platform": "web"
        })
        
        # 1. Initiate Auth Flow to get CSRF token
        auth_params = {
            "client_id": AUTH_CLIENT_ID,
            "audience": AUTH_AUDIENCE,
            "scope": AUTH_SCOPE,
            "response_type": "code",
            "response_mode": "query",
            "redirect_uri": AUTH_REDIRECT_URI,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        auth_url = f"https://{AUTH_DOMAIN}{AUTH_AUTHORIZE_PATH}?{urlencode(auth_params)}"
        
        resp = auth_session.get(auth_url, timeout=self.timeout)
        resp.raise_for_status()
        
        # Capture updated state if redirected
        parsed_url = urlparse(str(resp.url))
        query_params = parse_qs(parsed_url.query)
        if "state" in query_params:
            state = query_params["state"][0]
        
        # Extract CSRF token from cookies
        csrf_token = None
        for cookie in auth_session.cookies:
            if cookie.name == "_csrf" and "onepeloton.com" in cookie.domain:
                csrf_token = cookie.value
                break
        
        if not csrf_token:
            raise PelotonAPIError("Failed to find CSRF token for Peloton login. Check if cookies are being blocked or site structure changed.")
        
        # 2. Submit Credentials
        login_payload = {
            "client_id": AUTH_CLIENT_ID,
            "redirect_uri": AUTH_REDIRECT_URI,
            "tenant": "peloton-prod",
            "response_type": "code",
            "scope": AUTH_SCOPE,
            "audience": AUTH_AUDIENCE,
            "username": username,
            "password": password,
            "connection": "pelo-user-password",
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "_csrf": csrf_token,
            "_intstate": "deprecated"
        }
        
        login_url = f"https://{AUTH_DOMAIN}/usernamepassword/login"
        login_headers = {
            "Origin": f"https://{AUTH_DOMAIN}",
            "Referer": str(resp.url),
            "Auth0-Client": AUTH0_CLIENT_PAYLOAD,
            "Content-Type": "application/json"
        }
        
        resp = auth_session.post(
            login_url,
            json=login_payload,
            headers=login_headers,
            allow_redirects=False,
            timeout=self.timeout
        )
        
        # 3. Follow Redirects to get Code
        next_url = None
        if resp.status_code == 302:
            next_url = resp.headers.get("Location")
        elif resp.status_code == 200:
            if "wrong email or password" in resp.text.lower():
                raise PelotonAPIError("Peloton Login Failed: Wrong email or password.")
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            form = soup.find('form')
            if form:
                action = form.get('action')
                if not action.startswith("http"):
                    action = f"https://{AUTH_DOMAIN}{action}"
                hidden_fields = {i.get('name'): i.get('value') for i in form.find_all('input', type='hidden')}
                resp = auth_session.post(action, data=hidden_fields, allow_redirects=True, timeout=self.timeout)
                next_url = str(resp.url)
        
        if next_url:
            if not next_url.startswith("http"):
                next_url = f"https://{AUTH_DOMAIN}{next_url}"
            resp = auth_session.get(next_url, allow_redirects=True, timeout=self.timeout)
        
        final_url = str(resp.url)
        parsed_final = urlparse(final_url)
        query = parse_qs(parsed_final.query)
        code = query.get("code", [None])[0]
        
        if not code:
            snippet = resp.text[:1000].replace('\n', ' ')
            raise PelotonAPIError(f"Failed to get authorization code from Peloton. status={resp.status_code}, url={final_url}, body_snippet={snippet}")
        
        # 4. Exchange Code for Token
        token_url = f"https://{AUTH_DOMAIN}{AUTH_TOKEN_PATH}"
        token_payload = {
            "grant_type": "authorization_code",
            "client_id": AUTH_CLIENT_ID,
            "code_verifier": code_verifier,
            "code": code,
            "redirect_uri": AUTH_REDIRECT_URI
        }
        
        resp = auth_session.post(token_url, json=token_payload, timeout=self.timeout)
        data = self._raise_for_status(resp)
        
        # Parse token response
        token = Token(
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            id_token=data.get("id_token"),
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in", BEARER_TOKEN_DEFAULT_TTL_SECONDS),
            scope=data.get("scope"),
        )
        
        if not token.access_token:
            raise PelotonAPIError("Authentication succeeded but no access token was returned")
        
        logger.debug("Authenticated Peloton user %s", username)
        return token
    
    def _generate_random_string(self, length: int) -> str:
        """Generate a random URL-safe string"""
        res = secrets.token_urlsafe(length)
        return res[:length].replace('+', '-').replace('/', '_').replace('=', '')
    
    def _generate_code_challenge(self, verifier: str) -> str:
        """Generate PKCE code challenge from verifier"""
        sha256_hash = hashlib.sha256(verifier.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(sha256_hash).decode('utf-8').replace('=', '')
    
    def _set_auth_header(self):
        """Set Authorization header with bearer token"""
        if self.token and self.token.access_token:
            self.session.headers["Authorization"] = f"Bearer {self.token.access_token}"
    
    def _fetch_user_info(self):
        """Fetch user information after authentication"""
        try:
            # Get user info from /api/me endpoint (standard Peloton API endpoint)
            user_data = self.fetch_current_user()
            if user_data:
                self.login_payload = user_data
                return user_data
        except Exception as e:
            logger.warning(f"Could not fetch user info: {e}")
        return None
    
    def fetch_current_user(self) -> Dict[str, Any]:
        """
        Fetch current authenticated user information from /api/me endpoint.
        According to Peloton API docs, this returns user data with 'id' field.
        """
        try:
            user_data = self._get("/api/me")
            # Ensure we have the expected structure
            if not isinstance(user_data, dict):
                raise PelotonAPIError("Unexpected response format from /api/me")
            return user_data
        except PelotonAPIError:
            raise
        except Exception as e:
            # Fallback: try to decode ID token if available
            if self.token and self.token.id_token:
                try:
                    import json
                    parts = self.token.id_token.split('.')
                    if len(parts) >= 2:
                        payload = parts[1]
                        payload += '=' * (4 - len(payload) % 4)
                        decoded = base64.urlsafe_b64decode(payload)
                        return json.loads(decoded)
                except Exception as decode_error:
                    logger.warning(f"Could not decode ID token: {decode_error}")
            raise PelotonAPIError(f"Could not fetch current user information: {str(e)}")
    
    def refresh_token(self) -> Token:
        """Refresh the access token using refresh token"""
        if not self.token or not self.token.refresh_token:
            raise PelotonAPIError("No refresh token available")
        
        endpoint = f"{AUTH_DOMAIN}/oauth/token"
        
        auth_session = requests.Session()
        auth_session.headers.update({
            "Content-Type": "application/json",
        })
        
        payload = {
            "client_id": AUTH_CLIENT_ID,
            "grant_type": "refresh_token",
            "refresh_token": self.token.refresh_token,
            "audience": AUTH_AUDIENCE,
        }
        
        response = auth_session.post(endpoint, json=payload, timeout=self.timeout)
        data = self._raise_for_status(response)
        
        self.token = Token(
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token", self.token.refresh_token),
            id_token=data.get("id_token"),
            token_type=data.get("token_type", "Bearer"),
            expires_in=data.get("expires_in", 172800),
            scope=data.get("scope"),
        )
        
        self._set_auth_header()
        return self.token

    # ------------------------------------------------------------------------------
    # Users & Workouts
    # ------------------------------------------------------------------------------
    def fetch_user_workouts_page(
        self,
        user_id: str,
        limit: int = 20,
        page: int = 0,
        sort_by: str = "-created_at,-pk",
        cursor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"page": page, "limit": limit, "sort_by": sort_by}
        if cursor:
            params.update(cursor)
        return self._get(f"/api/user/{user_id}/workouts", params=params)

    def iter_user_workouts(
        self,
        user_id: str,
        limit: int = 20,
        page: int = 0,
        page_count: Optional[int] = None,
        sort_by: str = "-created_at,-pk",
    ) -> Iterable[Dict[str, Any]]:
        """Yield individual workout list entries for the given user."""
        current_page = page
        fetched_pages = 0
        cursor = None
        while True:
            params: Dict[str, Any] = {"page": current_page, "limit": limit, "sort_by": sort_by}
            if cursor:
                params.update(cursor)
            payload = self._get(f"/api/user/{user_id}/workouts", params=params)
            data = payload.get("data", [])
            for item in data:
                yield item

            fetched_pages += 1
            cursor = payload.get("next")
            if not payload.get("show_next") or (page_count and fetched_pages >= page_count):
                break
            current_page += 1

    def fetch_workout(self, workout_id: str) -> Dict[str, Any]:
        return self._get(f"/api/workout/{workout_id}")

    def fetch_performance_graph(self, workout_id: str, every_n: int = 5) -> Dict[str, Any]:
        """
        Fetch detailed performance graph for a workout.
        `every_n` controls the sampling interval (seconds). Default: 5s.
        
        IMPORTANT: This function always uses every_n=5 for the API call.
        The raw payload from the API is saved as-is in raw_payload field.
        Normalized fields are added via setdefault for downstream processing.
        """
        # Always use every_n=5 for performance graph API call
        payload = self._get(
            f"/api/workout/{workout_id}/performance_graph",
            params={"every_n": every_n},
        )
        # Normalize a couple of keys so downstream code can depend on them.
        # setdefault only adds if key doesn't exist, so it won't overwrite existing data
        payload.setdefault("segment_length", payload.get("sample_interval", every_n))
        payload.setdefault("duration", payload.get("duration_sec") or payload.get("duration_secs"))
        payload.setdefault("metrics", payload.get("metrics") or [])
        return payload

    def fetch_ride_details(self, ride_id: str) -> Dict[str, Any]:
        return self._get(f"/api/ride/{ride_id}/details")
    
    def fetch_playlist(self, ride_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch music playlist for a ride/class.
        Returns playlist data including songs, artists, and albums.
        Returns None if playlist doesn't exist (404) - this is normal for some class types.
        Raises PelotonAPIError for other errors.
        """
        try:
            return self._get(f"/api/ride/{ride_id}/playlist")
        except PelotonAPIError as e:
            # If it's a 404, return None (class doesn't have a playlist - normal for yoga, meditation, etc.)
            error_str = str(e)
            if '404' in error_str or 'Not Found' in error_str:
                logger.debug(f"Playlist not found for ride_id {ride_id} (404) - this is normal for some class types")
                return None
            # Re-raise other errors
            raise

    def fetch_user(self, user_id: str) -> Dict[str, Any]:
        return self._get(f"/api/user/{user_id}")
    
    def fetch_user_overview(self, user_id: str) -> Dict[str, Any]:
        """Fetch user overview statistics from /api/user/{userId}/overview endpoint"""
        logger.info(f"Fetching user overview for user_id: {user_id}")
        result = self._get(f"/api/user/{user_id}/overview")
        logger.info(f"Overview endpoint returned {len(str(result))} characters of data")
        logger.debug(f"Overview response keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        return result

    # ------------------------------------------------------------------------------
    # Instructors
    # ------------------------------------------------------------------------------
    def fetch_instructor(self, instructor_id: str) -> Dict[str, Any]:
        """Fetch instructor details by instructor ID."""
        return self._get(f"/api/instructor/{instructor_id}")

    def fetch_ride_filters(self, library_type: str = "on_demand") -> Dict[str, Any]:
        """
        Fetch ride/class filters from Peloton API.
        Returns filter options including class types, instructors, durations, etc.
        
        Args:
            library_type: Type of library to get filters for. Common values:
                - "on_demand" (default): On-demand classes
                - "live": Live classes
                - "archived": Archived classes
        """
        params = {"library_type": library_type}
        return self._get("/api/ride/filters", params=params)
    
    def fetch_all_instructors(self, limit: int = 20, page: int = 0) -> Dict[str, Any]:
        """Fetch instructors from Peloton API with pagination support."""
        params = {"page": page, "limit": limit}
        return self._get("/api/instructor", params=params)
    
    def iter_all_instructors(self, limit: int = 20) -> Iterable[Dict[str, Any]]:
        """Yield individual instructor entries, handling pagination automatically."""
        current_page = 0
        cursor = None
        while True:
            params: Dict[str, Any] = {"page": current_page, "limit": limit}
            if cursor:
                params.update(cursor)
            payload = self._get("/api/instructor", params=params)
            data = payload.get("data", [])
            for item in data:
                yield item
            
            cursor = payload.get("next")
            if not payload.get("show_next"):
                break
            current_page += 1

    # ------------------------------------------------------------------------------
    # Rides/Classes Library
    # ------------------------------------------------------------------------------
    def fetch_archived_rides(
        self,
        page: int = 0,
        limit: int = 20,
        fitness_discipline: Optional[str] = None,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Fetch archived rides/classes from Peloton API with pagination and filtering.
        
        Args:
            page: Page number (0-indexed)
            limit: Number of rides per page
            fitness_discipline: Filter by discipline (e.g., 'cycling', 'running')
            start_date: Unix timestamp (milliseconds) for start date filter
            end_date: Unix timestamp (milliseconds) for end date filter
        
        Returns:
            Paginated response with rides data
        """
        params: Dict[str, Any] = {"page": page, "limit": limit}
        
        if fitness_discipline:
            params["fitness_discipline"] = fitness_discipline
        
        if start_date:
            params["start_date"] = start_date
        
        if end_date:
            params["end_date"] = end_date
        
        return self._get("/api/v2/ride/archived", params=params)
    
    def iter_archived_rides(
        self,
        limit: int = 20,
        fitness_discipline: Optional[str] = None,
        start_date: Optional[int] = None,
        end_date: Optional[int] = None,
        max_pages: Optional[int] = None,
    ) -> Iterable[Dict[str, Any]]:
        """
        Yield individual archived ride entries, handling pagination automatically.
        
        Args:
            limit: Number of rides per page
            fitness_discipline: Filter by discipline (e.g., 'cycling', 'running')
            start_date: Unix timestamp (milliseconds) for start date filter
            end_date: Unix timestamp (milliseconds) for end date filter
            max_pages: Maximum number of pages to fetch (None for all)
        
        Yields:
            Individual ride dictionaries from the API
        """
        current_page = 0
        fetched_pages = 0
        cursor = None
        
        while True:
            params: Dict[str, Any] = {"page": current_page, "limit": limit}
            
            if fitness_discipline:
                params["fitness_discipline"] = fitness_discipline
            
            if start_date:
                params["start_date"] = start_date
            
            if end_date:
                params["end_date"] = end_date
            
            if cursor:
                params.update(cursor)
            
            try:
                payload = self._get("/api/v2/ride/archived", params=params)
            except PelotonAPIError as e:
                logger.warning(f"Error fetching archived rides page {current_page}: {e}")
                break
            
            # Handle different response structures
            data = payload.get("data", [])
            if not data and isinstance(payload, list):
                # Some endpoints return a list directly
                data = payload
            
            for item in data:
                yield item
            
            fetched_pages += 1
            
            # Check for pagination
            cursor = payload.get("next")
            show_next = payload.get("show_next", False)
            
            if not show_next or (max_pages and fetched_pages >= max_pages):
                break
            
            current_page += 1

    # ------------------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------------------
    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        # Ensure Authorization header is set
        if not self.session.headers.get("Authorization") and self.token:
            self._set_auth_header()
        response = self.session.get(url, params=params or {}, timeout=self.timeout)
        
        # If we get 401, try refreshing token and retry once
        if response.status_code == 401 and self.token and self.token.refresh_token:
            try:
                self.refresh_token()
                response = self.session.get(url, params=params or {}, timeout=self.timeout)
            except Exception as e:
                logger.warning(f"Token refresh failed: {e}")
        
        return self._raise_for_status(response)

    @staticmethod
    def _raise_for_status(response: requests.Response) -> Dict[str, Any]:
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:  # network failure path
            message = PelotonClient._build_error_message(response)
            raise PelotonAPIError(message) from exc
        try:
            return response.json()
        except ValueError as exc:  # unexpected non-json response
            raise PelotonAPIError("Peloton API returned non-JSON response") from exc

    @staticmethod
    def _build_error_message(response: requests.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict) and payload.get("message"):
            return f"Peloton API error {response.status_code}: {payload['message']}"
        return f"Peloton API error {response.status_code}: {response.text[:200]}"
