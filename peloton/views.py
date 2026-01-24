import logging
import secrets
from typing import Dict, Any
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from accounts.models import Profile
from .models import PelotonConnection
from .forms import PelotonConnectionForm
from .services.peloton import PelotonClient, PelotonAPIError

logger = logging.getLogger(__name__)


def _update_profile_from_overview(profile: Profile, overview_data: Dict[str, Any]) -> None:
    """Update profile with data from Peloton user overview endpoint"""
    try:
        # Extract statistics from overview
        # The overview endpoint typically returns stats like:
        # - total_workouts, total_output, total_distance, total_calories, etc.
        
        # Log the overview data structure for debugging
        logger.info(f"Overview data received. Keys: {list(overview_data.keys())}")
        
        # Extract workout_counts if present (from overview endpoint)
        workout_counts = overview_data.get('workout_counts')
        if workout_counts and isinstance(workout_counts, dict):
            logger.info(f"workout_counts (dict) keys: {list(workout_counts.keys())}")
            logger.info(f"workout_counts.total_workouts: {workout_counts.get('total_workouts')}")
        elif workout_counts:
            logger.info(f"workout_counts is {type(workout_counts)} (not a dict)")
        
        # Check for other potential stat locations
        if 'personal_records' in overview_data:
            pr_data = overview_data.get('personal_records')
            logger.info(f"personal_records present: {type(pr_data)}")
            if isinstance(pr_data, dict):
                logger.info(f"personal_records keys: {list(pr_data.keys())[:10]}")
                # Look for aggregate stats in personal_records
                for pr_key in pr_data.keys():
                    if any(term in pr_key.lower() for term in ['total', 'output', 'distance', 'calorie', 'duration']):
                        logger.info(f"personal_records.{pr_key}: {pr_data.get(pr_key)}")
        if 'streaks' in overview_data:
            streaks_data = overview_data.get('streaks')
            logger.info(f"streaks present: {type(streaks_data)}")
            if isinstance(streaks_data, dict):
                logger.info(f"streaks keys: {list(streaks_data.keys())[:10]}")
        
        # Check workout_counts for more detailed stats
        if isinstance(workout_counts, dict):
            for wc_key in workout_counts.keys():
                if any(term in wc_key.lower() for term in ['total', 'output', 'distance', 'calorie', 'duration', 'metric']):
                    logger.info(f"workout_counts.{wc_key}: {workout_counts.get(wc_key)}")
        
        # Log all top-level keys that might contain stats
        for key in overview_data.keys():
            if key not in ['id', 'workout_counts', 'first_party_or_partner_3p_workout_counts', 
                          'user_has_imported_non_partner_3p_workout', 'personal_records', 
                          'streaks', 'achievement_counts']:
                val = overview_data.get(key)
                # Log if it's a number or contains stat-related terms
                if isinstance(val, (int, float)) or (isinstance(val, str) and any(term in key.lower() for term in ['total', 'output', 'distance', 'calorie', 'duration', 'metric'])):
                    logger.info(f"Top-level stat candidate: {key} = {val} (type: {type(val)})")
        
        # Handle different possible response structures
        # The overview might have stats nested or at root level
        stats = overview_data.get('stats', {})
        if not stats:
            stats = overview_data
        
        # Total workouts - check multiple sources
        # From user details endpoint (direct field)
        # From workout_counts dict (overview endpoint)
        # From stats or root level
        total_workouts = (
            overview_data.get('total_workouts') or  # Direct from user details endpoint
            (workout_counts.get('total_workouts') if isinstance(workout_counts, dict) else None) or
            stats.get('total_workouts') or
            stats.get('total_rides') or
            stats.get('workouts_total') or
            overview_data.get('total_rides') or
            overview_data.get('workouts_total')
        )
        logger.info(f"Extracted total_workouts: {total_workouts}")
        if total_workouts is not None:
            try:
                profile.peloton_total_workouts = int(total_workouts)
            except (ValueError, TypeError):
                pass
        
        # Total output (in kilojoules)
        # NOTE: Peloton API does not provide aggregate total output in overview/user endpoints.
        # This would need to be calculated by fetching all workouts and summing their output.
        # For now, we leave this as None.
        total_output = None
        logger.info(f"Extracted total_output: {total_output} (not available in API)")
        
        # Total distance (in miles)
        # NOTE: Peloton API does not provide aggregate total distance in overview/user endpoints.
        # This would need to be calculated by fetching all workouts and summing their distance.
        # For now, we leave this as None.
        total_distance = None
        logger.info(f"Extracted total_distance: {total_distance} (not available in API)")
        
        # Total calories
        # NOTE: Peloton API does not provide aggregate total calories in overview/user endpoints.
        # This would need to be calculated by fetching all workouts and summing their calories.
        # For now, we leave this as None.
        total_calories = None
        logger.info(f"Extracted total_calories: {total_calories} (not available in API)")
        
        # Total pedaling duration (in seconds)
        # NOTE: Peloton API does not provide aggregate total pedaling duration in overview/user endpoints.
        # This would need to be calculated by fetching all workouts and summing their duration.
        # For now, we leave this as None.
        total_pedaling_duration = None
        logger.info(f"Extracted total_pedaling_duration: {total_pedaling_duration} (not available in API)")
        
        # Total pedaling/non-pedaling metric workouts (from user details)
        total_pedaling_metric_workouts = overview_data.get('total_pedaling_metric_workouts')
        if total_pedaling_metric_workouts is not None:
            try:
                profile.peloton_total_pedaling_metric_workouts = int(total_pedaling_metric_workouts)
            except (ValueError, TypeError):
                pass
        
        total_non_pedaling_metric_workouts = overview_data.get('total_non_pedaling_metric_workouts')
        if total_non_pedaling_metric_workouts is not None:
            try:
                profile.peloton_total_non_pedaling_metric_workouts = int(total_non_pedaling_metric_workouts)
            except (ValueError, TypeError):
                pass
        
        # Streaks (from overview endpoint)
        streaks = overview_data.get('streaks', {})
        if isinstance(streaks, dict):
            current_weekly = streaks.get('current_weekly')
            if current_weekly is not None:
                try:
                    profile.peloton_current_weekly_streak = int(current_weekly)
                except (ValueError, TypeError):
                    pass
            
            best_weekly = streaks.get('best_weekly')
            if best_weekly is not None:
                try:
                    profile.peloton_best_weekly_streak = int(best_weekly)
                except (ValueError, TypeError):
                    pass
            
            current_daily = streaks.get('current_daily')
            if current_daily is not None:
                try:
                    profile.peloton_current_daily_streak = int(current_daily)
                except (ValueError, TypeError):
                    pass
        
        # Achievement counts (from overview endpoint)
        achievement_counts = overview_data.get('achievement_counts', {})
        if isinstance(achievement_counts, dict):
            total_achievements = achievement_counts.get('total_count')
            if total_achievements is not None:
                try:
                    profile.peloton_total_achievements = int(total_achievements)
                except (ValueError, TypeError):
                    pass
        
        # Store workout type breakdown (from overview endpoint)
        if isinstance(workout_counts, dict):
            workouts_list = workout_counts.get('workouts', [])
            if workouts_list:
                # Create a dict mapping slug -> count for easy lookup
                workout_counts_dict = {}
                for workout in workouts_list:
                    slug = workout.get('slug')
                    count = workout.get('count', 0)
                    if slug:
                        workout_counts_dict[slug] = count
                profile.peloton_workout_counts = workout_counts_dict
                logger.info(f"Stored workout counts: {workout_counts_dict}")
        
        # Log what we found
        logger.info(f"Available metric fields: total_pedaling_metric_workouts={overview_data.get('total_pedaling_metric_workouts')}, total_non_pedaling_metric_workouts={overview_data.get('total_non_pedaling_metric_workouts')}")
        
        # Save the profile with updated stats
        profile.save()
        logger.info(
            f"Profile saved with Peloton stats: "
            f"workouts={profile.peloton_total_workouts}, "
            f"pedaling={profile.peloton_total_pedaling_metric_workouts}, "
            f"non_pedaling={profile.peloton_total_non_pedaling_metric_workouts}, "
            f"weekly_streak={profile.peloton_current_weekly_streak}, "
            f"daily_streak={profile.peloton_current_daily_streak}, "
            f"achievements={profile.peloton_total_achievements}"
        )
        
    except Exception as e:
        logger.error(f"Error updating profile from overview data: {e}", exc_info=True)
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


@login_required
def connect_peloton(request):
    """Connect or update Peloton account"""
    connection, created = PelotonConnection.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = PelotonConnectionForm(request.POST, instance=connection, user=request.user)
        if form.is_valid():
            try:
                # Save credentials
                connection = form.save()
                
                # Test authentication and get user info using OAuth2
                # Create client and authenticate with username/password
                client = PelotonClient(
                    username=connection.username,
                    password=connection.password
                )
                
                # Store bearer token and refresh token
                if client.token:
                    connection.bearer_token = client.token.access_token
                    if client.token.refresh_token:
                        connection.refresh_token = client.token.refresh_token
                    
                    # Calculate token expiration (default 48 hours)
                    from datetime import timedelta
                    expires_in = client.token.expires_in or 172800
                    connection.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
                
                # Fetch user data to get Peloton user ID and leaderboard name
                try:
                    user_data = client.fetch_current_user()
                    
                    # Extract user ID - /api/me returns 'id' field according to Peloton API
                    peloton_user_id = (
                        user_data.get('id') or  # Primary field from /api/me endpoint
                        user_data.get('user_id') or 
                        user_data.get('sub') or  # Auth0 subject (fallback)
                        user_data.get('peloton_user_id')
                    )
                    
                    if peloton_user_id:
                        connection.peloton_user_id = str(peloton_user_id)
                    
                    # Update profile with leaderboard name from /api/me
                    profile, _ = Profile.objects.get_or_create(user=request.user)
                    
                    # Fetch user overview for additional stats (after we have user_id)
                    if peloton_user_id:
                        try:
                            overview_data = client.fetch_user_overview(str(peloton_user_id))
                            _update_profile_from_overview(profile, overview_data)
                        except Exception as overview_error:
                            logger.warning(f"Could not fetch Peloton user overview: {overview_error}")
                    leaderboard_name = (
                        user_data.get('username') or 
                        user_data.get('leaderboard_name') or 
                        user_data.get('name') or
                        user_data.get('nickname') or
                        user_data.get('email', '').split('@')[0]  # Fallback to email username
                    )
                    if leaderboard_name:
                        profile.peloton_leaderboard_name = leaderboard_name
                    
                    profile.peloton_last_synced_at = timezone.now()
                    profile.save()
                except Exception as e:
                    # If we can't fetch user details, that's okay - we'll try again later
                    logger.warning(f"Could not fetch Peloton user details: {e}")
                
                connection.is_active = True
                connection.last_sync_at = timezone.now()
                connection.save()
                
                messages.success(request, 'Peloton account connected successfully!')
                return redirect('peloton:status')
                
            except PelotonAPIError as e:
                messages.error(request, f'Failed to connect to Peloton: {str(e)}')
            except Exception as e:
                messages.error(request, f'An error occurred: {str(e)}')
    else:
        form = PelotonConnectionForm(instance=connection, user=request.user)
    
    return render(request, 'peloton/connect.html', {
        'form': form,
        'connection': connection,
    })


@login_required
def start_oauth_flow(request):
    """Start OAuth2 authorization code flow with PKCE"""
    try:
        connection, created = PelotonConnection.objects.get_or_create(user=request.user)
        
        # Generate authorization URL with PKCE
        client = PelotonClient()
        state = secrets.token_urlsafe(32)
        redirect_uri = request.build_absolute_uri(reverse('peloton:oauth_callback'))
        
        auth_url, code_verifier = client.get_authorization_url(redirect_uri, state)
        
        # Store code_verifier and state in session for callback
        request.session['peloton_code_verifier'] = code_verifier
        request.session['peloton_oauth_state'] = state
        request.session['peloton_redirect_uri'] = redirect_uri
        
        # Redirect to Peloton authorization page
        return redirect(auth_url)
        
    except Exception as e:
        logger.error(f"Error starting OAuth flow: {e}")
        messages.error(request, f'Failed to start OAuth flow: {str(e)}')
        return redirect('peloton:connect')


@login_required
def oauth_callback(request):
    """Handle OAuth2 callback from Peloton"""
    try:
        # Get stored values from session
        code_verifier = request.session.get('peloton_code_verifier')
        expected_state = request.session.get('peloton_oauth_state')
        redirect_uri = request.session.get('peloton_redirect_uri')
        
        if not code_verifier or not redirect_uri:
            messages.error(request, 'OAuth flow session expired. Please try again.')
            return redirect('peloton:connect')
        
        # Get authorization code and state from callback
        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')
        
        if error:
            error_description = request.GET.get('error_description', '')
            messages.error(request, f'OAuth error: {error} - {error_description}')
            return redirect('peloton:connect')
        
        if not code:
            messages.error(request, 'No authorization code received.')
            return redirect('peloton:connect')
        
        if state != expected_state:
            messages.error(request, 'Invalid state parameter. Possible CSRF attack.')
            return redirect('peloton:connect')
        
        # Exchange code for token
        client = PelotonClient()
        token = client.exchange_code_for_token(code, code_verifier, redirect_uri)
        
        # Store token in connection
        connection, created = PelotonConnection.objects.get_or_create(user=request.user)
        connection.bearer_token = token.access_token
        if token.refresh_token:
            connection.refresh_token = token.refresh_token
        
        from datetime import timedelta
        expires_in = token.expires_in or 172800
        connection.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
        connection.is_active = True
        connection.last_sync_at = timezone.now()
        
        # Fetch user info
        client.token = token
        client._set_auth_header()
        try:
            user_data = client.fetch_current_user()
            
            # Extract user ID - /api/me returns 'id' field according to Peloton API
            peloton_user_id = (
                user_data.get('id') or  # Primary field from /api/me endpoint
                user_data.get('user_id') or 
                user_data.get('sub') or  # Auth0 subject (fallback)
                user_data.get('peloton_user_id')
            )
            if peloton_user_id:
                connection.peloton_user_id = str(peloton_user_id)
                
                # Fetch user overview for additional stats
                try:
                    logger.info(f"Fetching overview for user_id: {peloton_user_id}")
                    overview_data = client.fetch_user_overview(str(peloton_user_id))
                    logger.info(f"Overview data fetched successfully")
                    profile, _ = Profile.objects.get_or_create(user=request.user)
                    _update_profile_from_overview(profile, overview_data)
                except PelotonAPIError as overview_error:
                    logger.error(f"Peloton API error fetching user overview: {overview_error}")
                    messages.warning(request, f'Could not fetch Peloton statistics: {str(overview_error)}')
                except Exception as overview_error:
                    logger.error(f"Error fetching Peloton user overview: {overview_error}", exc_info=True)
                    messages.warning(request, f'Could not fetch Peloton statistics: {str(overview_error)}')
            
            profile, _ = Profile.objects.get_or_create(user=request.user)
            leaderboard_name = (
                user_data.get('username') or 
                user_data.get('leaderboard_name') or 
                user_data.get('name') or
                user_data.get('nickname') or
                user_data.get('email', '').split('@')[0]
            )
            if leaderboard_name:
                profile.peloton_leaderboard_name = leaderboard_name
            
            profile.peloton_last_synced_at = timezone.now()
            profile.save()
        except Exception as e:
            logger.warning(f"Could not fetch Peloton user details: {e}")
        
        connection.save()
        
        # Clean up session
        request.session.pop('peloton_code_verifier', None)
        request.session.pop('peloton_oauth_state', None)
        request.session.pop('peloton_redirect_uri', None)
        
        messages.success(request, 'Peloton account connected successfully via OAuth2!')
        return redirect('peloton:status')
        
    except PelotonAPIError as e:
        logger.error(f"Peloton API error in OAuth callback: {e}")
        messages.error(request, f'Failed to complete OAuth flow: {str(e)}')
        return redirect('peloton:connect')
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('peloton:connect')


@login_required
def peloton_status(request):
    """View Peloton connection status"""
    try:
        connection = PelotonConnection.objects.get(user=request.user)
        profile = request.user.profile
    except PelotonConnection.DoesNotExist:
        connection = None
        profile = request.user.profile
    
    return render(request, 'peloton/status.html', {
        'connection': connection,
        'profile': profile,
    })


@login_required
def disconnect_peloton(request):
    """Disconnect Peloton account"""
    try:
        connection = PelotonConnection.objects.get(user=request.user)
        connection.delete()
        
        # Clear leaderboard name from profile
        profile = request.user.profile
        profile.peloton_leaderboard_name = None
        profile.save()
        
        messages.success(request, 'Peloton account disconnected successfully!')
    except PelotonConnection.DoesNotExist:
        messages.info(request, 'No Peloton connection found.')
    
    return redirect('peloton:status')


@login_required
def test_connection(request):
    """Test the Peloton connection and refresh user data"""
    try:
        connection = PelotonConnection.objects.get(user=request.user)
        
        # Get client
        client = connection.get_client()
        
        # Fetch current user data
        try:
            user_data = client.fetch_current_user()
            
            # Extract and update user ID if we got it
            # According to Peloton API, /api/me returns 'id' field
            peloton_user_id = (
                user_data.get('id') or  # Primary field from /api/me
                user_data.get('user_id') or 
                user_data.get('sub') or  # Auth0 subject
                user_data.get('peloton_user_id')
            )
            if peloton_user_id:
                connection.peloton_user_id = str(peloton_user_id)
                
                # Fetch user overview for additional stats
                try:
                    logger.info(f"Fetching overview for user_id: {peloton_user_id}")
                    overview_data = client.fetch_user_overview(str(peloton_user_id))
                    logger.info(f"Overview data fetched successfully")
                    
                    # Also fetch user details which might have aggregate stats
                    try:
                        user_details = client.fetch_user(str(peloton_user_id))
                        logger.info(f"User details fetched. Keys: {list(user_details.keys()) if isinstance(user_details, dict) else 'Not a dict'}")
                        # Merge user details into overview_data for extraction
                        # But preserve workout_counts from overview (it's a dict with total_workouts)
                        # while user details has workout_counts as a list
                        if isinstance(user_details, dict):
                            # Save overview workout_counts before merge
                            overview_workout_counts = overview_data.get('workout_counts')
                            # Merge user details
                            overview_data.update(user_details)
                            # Restore overview workout_counts if it was a dict
                            if isinstance(overview_workout_counts, dict):
                                overview_data['workout_counts'] = overview_workout_counts
                    except Exception as user_details_error:
                        logger.warning(f"Could not fetch user details: {user_details_error}")
                    
                    _update_profile_from_overview(request.user.profile, overview_data)
                except PelotonAPIError as overview_error:
                    logger.error(f"Peloton API error fetching user overview: {overview_error}")
                    messages.warning(request, f'Could not fetch Peloton statistics: {str(overview_error)}')
                except Exception as overview_error:
                    logger.error(f"Error fetching Peloton user overview: {overview_error}", exc_info=True)
                    messages.warning(request, f'Could not fetch Peloton statistics: {str(overview_error)}')
            
            # Update profile with leaderboard name
            profile = request.user.profile
            leaderboard_name = (
                user_data.get('username') or 
                user_data.get('leaderboard_name') or 
                user_data.get('name') or
                user_data.get('nickname') or
                user_data.get('email', '').split('@')[0]
            )
            if leaderboard_name:
                profile.peloton_leaderboard_name = leaderboard_name
            
            profile.peloton_last_synced_at = timezone.now()
            profile.save()
            
            # Update bearer token if we got a new one (from refresh)
            if client.token and client.token.access_token:
                connection.bearer_token = client.token.access_token
                if client.token.refresh_token:
                    connection.refresh_token = client.token.refresh_token
                from datetime import timedelta
                expires_in = client.token.expires_in or 172800
                connection.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
            
            connection.last_sync_at = timezone.now()
            connection.save()
            
            messages.success(request, 'Connection test successful! Profile updated with Peloton stats.')
        except Exception as e:
            logger.warning(f"Could not fetch Peloton user details: {e}")
            messages.warning(request, f'Connected but could not fetch user details: {str(e)}')
            
            connection.last_sync_at = timezone.now()
            connection.save()
            
    except PelotonConnection.DoesNotExist:
        messages.error(request, 'No Peloton connection found. Please connect your account first.')
    except PelotonAPIError as e:
        messages.error(request, f'Connection test failed: {str(e)}')
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
    
    return redirect('peloton:status')
