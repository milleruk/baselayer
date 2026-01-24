import logging
import secrets
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
                    
                    # Update profile with leaderboard name
                    profile, _ = Profile.objects.get_or_create(user=request.user)
                    leaderboard_name = (
                        user_data.get('username') or 
                        user_data.get('leaderboard_name') or 
                        user_data.get('name') or
                        user_data.get('nickname') or
                        user_data.get('email', '').split('@')[0]  # Fallback to email username
                    )
                    if leaderboard_name:
                        profile.peloton_leaderboard_name = leaderboard_name
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
            
            messages.success(request, 'Connection test successful! Profile updated.')
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
