"""
Onboarding wizard views for new user registration flow.
Handles 6-stage setup: Profile → Peloton → Sports → Metrics → Weight → Activation
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.db import transaction

from .models import (
    User, Profile, OnboardingWizard, FTPEntry, PaceEntry, WeightEntry
)
from .forms import (
    WizardStage1Form, WizardStage3Form, WizardStage4FTPForm, WizardStage4PaceForm,
    WizardStage4BackdatedFTPForm, WizardStage4BackdatedPaceForm,
    WizardStage5Form, WizardStage5BackdatedForm
)
from core.models import SiteSettings
from peloton.models import PelotonConnection, get_existing_peloton_connection
from peloton.forms import PelotonConnectionForm
from peloton.services.peloton import PelotonClient, PelotonAPIError
from peloton.views import _update_profile_from_overview


def _redirect_with_params(url_name, **params):
    """Helper to redirect with GET parameters"""
    url = reverse(url_name)
    if params:
        query_string = '&'.join(f'{k}={v}' for k, v in params.items())
        return HttpResponseRedirect(f'{url}?{query_string}')
    return redirect(url_name)


@login_required
def wizard_redirect(request):
    """Redirect to appropriate wizard stage"""
    wizard, created = OnboardingWizard.objects.get_or_create(user=request.user)
    
    if wizard.is_complete():
        # Wizard already complete, redirect to dashboard
        messages.success(request, 'Welcome to Chase The Zones! Your account is fully set up.')
        return redirect('core:dashboard')
    
    return redirect('wizard_stage_1')


@login_required
def wizard_stage_1(request):
    """Stage 1: User Profile Details"""
    wizard, created = OnboardingWizard.objects.get_or_create(user=request.user)
    profile, _ = Profile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = WizardStage1Form(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data.get('first_name', '').strip()
            last_name = form.cleaned_data.get('last_name', '').strip()
            # Save profile data
            profile.full_name = f"{first_name} {last_name}".strip()
            if form.cleaned_data.get('date_of_birth'):
                profile.date_of_birth = form.cleaned_data.get('date_of_birth')
            profile.save()
            
            # Update user name
            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.save()
            
            # Mark stage complete and move to next
            wizard.mark_stage_complete(1)
            wizard.current_stage = 2
            wizard.save()
            
            messages.success(request, 'Profile details saved!')
            return redirect('wizard_stage_2')
    else:
        # Pre-fill form with existing data
        first_name = request.user.first_name or ''
        last_name = request.user.last_name or ''
        if not first_name and not last_name and profile.full_name:
            parts = profile.full_name.strip().split()
            if parts:
                first_name = parts[0]
                last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''
        initial_data = {
            'first_name': first_name,
            'last_name': last_name,
            'date_of_birth': profile.date_of_birth
        }
        form = WizardStage1Form(initial=initial_data)
    
    context = {
        'form': form,
        'stage': 1,
        'total_stages': 6,
        'wizard': wizard,
    }
    return render(request, 'accounts/wizard/stage1.html', context)


@login_required
def wizard_restart(request):
    if request.method != 'POST':
        return redirect('wizard_stage_1')

    wizard, _ = OnboardingWizard.objects.get_or_create(user=request.user)
    wizard.current_stage = 1
    wizard.completed_stages = []
    wizard.stage_data = {}
    wizard.completed_at = None
    wizard.save(update_fields=['current_stage', 'completed_stages', 'stage_data', 'completed_at', 'updated_at'])
    messages.info(request, 'Wizard progress reset. Starting over at stage 1.')
    return redirect('wizard_stage_1')


@login_required
def wizard_stage_2(request):
    """Stage 2: Peloton Connection"""
    wizard, _ = OnboardingWizard.objects.get_or_create(user=request.user)
    
    # Check if peloton connection already exists and is valid
    peloton_connected = False
    try:
        connection = PelotonConnection.objects.get(user=request.user)
        # Connection is truly connected if it's active AND has a valid peloton_user_id
        peloton_connected = connection.is_active and bool(connection.peloton_user_id)
    except PelotonConnection.DoesNotExist:
        connection = None
    
    # Create connection if it doesn't exist
    if not connection:
        connection = PelotonConnection(user=request.user)
    
    form = PelotonConnectionForm(instance=connection, user=request.user)
    show_form = request.GET.get('connect') == '1'
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'skip':
            # Skip Peloton for now
            wizard.mark_stage_complete(2)
            wizard.current_stage = 3
            wizard.save()
            messages.info(request, 'You can connect Peloton later in your profile settings.')
            return redirect('wizard_stage_3')
        
        elif action == 'connect':
            form = PelotonConnectionForm(request.POST, instance=connection, user=request.user)
            if form.is_valid():
                try:
                    # Save credentials
                    connection = form.save()
                    
                    # Test authentication and get user info
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
                    user_data = client.fetch_current_user()
                    
                    peloton_user_id = (
                        user_data.get('id') or
                        user_data.get('user_id') or
                        user_data.get('sub') or
                        user_data.get('peloton_user_id')
                    )
                    if not peloton_user_id:
                        messages.error(request, 'Unable to validate your Peloton account. Please try again.')
                        connection.is_active = False
                        connection.save()
                        show_form = True
                    else:
                        existing = get_existing_peloton_connection(peloton_user_id, exclude_user_id=request.user.id)
                        if existing:
                            messages.error(
                                request,
                                "This Peloton account is already linked to another user. Please log in with the account associated with it."
                            )
                            connection.peloton_user_id = None
                            connection.is_active = False
                            connection.save()
                            return redirect('wizard_stage_2')
                        connection.peloton_user_id = str(peloton_user_id)
                        
                        profile, _ = Profile.objects.get_or_create(user=request.user)
                        
                        try:
                            overview_data = client.fetch_user_overview(str(peloton_user_id))
                            _update_profile_from_overview(profile, overview_data)
                        except Exception:
                            pass
                        
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
                        
                        connection.is_active = True
                        connection.save()
                        
                        wizard.mark_stage_complete(2)
                        wizard.current_stage = 3
                        wizard.save()
                        
                        messages.success(request, 'Peloton account connected successfully!')
                        return redirect('wizard_stage_3')
                except PelotonAPIError as e:
                    messages.error(request, f'Failed to connect to Peloton: {str(e)}')
                    connection.is_active = False
                    connection.save()
                    show_form = True
                except Exception as e:
                    messages.error(request, f'An error occurred: {str(e)}')
                    connection.is_active = False
                    connection.save()
                    show_form = True
    
    context = {
        'stage': 2,
        'total_stages': 6,
        'wizard': wizard,
        'peloton_connected': peloton_connected,
        'form': form,
        'connection': connection,
        'show_form': show_form or form.is_bound,
    }
    return render(request, 'accounts/wizard/stage2.html', context)


@login_required
def wizard_stage_3(request):
    """Stage 3: Sport Selection"""
    wizard, _ = OnboardingWizard.objects.get_or_create(user=request.user)
    profile, _ = Profile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = WizardStage3Form(request.POST)
        if form.is_valid():
            sports = form.cleaned_data.get('sports', [])
            
            # Store sports in wizard data for reference
            wizard.stage_data['selected_sports'] = sports
            wizard.mark_stage_complete(3)
            wizard.current_stage = 4
            wizard.save()
            
            messages.success(request, f'Sports selected: {", ".join(sports).title()}')
            return HttpResponseRedirect(reverse('wizard_stage_4') + '?sport_index=0')
    else:
        # Pre-populate form with previously selected sports
        selected_sports = wizard.stage_data.get('selected_sports', [])
        form = WizardStage3Form(initial={'sports': selected_sports})
    
    context = {
        'form': form,
        'stage': 3,
        'total_stages': 6,
        'wizard': wizard,
    }
    return render(request, 'accounts/wizard/stage3.html', context)


@login_required
def wizard_stage_4(request):
    """Stage 4: Sport-Specific Metrics (FTP for Cycling, Pace for Running/Walking)"""
    wizard, _ = OnboardingWizard.objects.get_or_create(user=request.user)
    profile, _ = Profile.objects.get_or_create(user=request.user)
    
    # Get selected sports from wizard data
    selected_sports = wizard.stage_data.get('selected_sports', [])
    if not selected_sports:
        return redirect('wizard_stage_3')
    
    current_sport_index = request.GET.get('sport_index', 0)
    try:
        current_sport_index = int(current_sport_index)
    except (ValueError, TypeError):
        current_sport_index = 0
    
    current_sport = selected_sports[current_sport_index] if current_sport_index < len(selected_sports) else None
    
    if not current_sport:
        # All sports processed, move to stage 5
        wizard.mark_stage_complete(4)
        wizard.current_stage = 5
        wizard.save()
        return redirect('wizard_stage_5')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if current_sport == 'cycling':
            form = WizardStage4FTPForm(request.POST)
            if form.is_valid():
                ftp_value = form.cleaned_data.get('current_ftp')
                
                # Set current FTP
                profile.ftp_score = ftp_value
                profile.save()
                
                # Create FTP entry
                today = timezone.now().date()
                FTPEntry.objects.update_or_create(
                    user=request.user,
                    recorded_date=today,
                    source='manual',
                    defaults={'ftp_value': ftp_value, 'is_active': True}
                )
                
                # Check if user wants to add backdated entries
                if form.cleaned_data.get('add_backdated'):
                    wizard.stage_data['add_backdated_ftp'] = True
                    wizard.save()
                    return _redirect_with_params('wizard_stage_4_backdated_ftp', sport_index=current_sport_index)
                else:
                    # Move to next sport
                    next_sport_index = current_sport_index + 1
                    if next_sport_index >= len(selected_sports):
                        # All sports done
                        wizard.mark_stage_complete(4)
                        wizard.current_stage = 5
                        wizard.save()
                        messages.success(request, f'FTP saved: {ftp_value}W')
                        return redirect('wizard_stage_5')
                    else:
                        messages.success(request, f'FTP saved: {ftp_value}W')
                        return _redirect_with_params('wizard_stage_4', sport_index=next_sport_index)
        else:
            # Running or Walking
            form = WizardStage4PaceForm(request.POST)
            if form.is_valid():
                pace_level = form.cleaned_data.get('pace_level')
                # Activity type is determined by the current_sport
                activity_type = 'running' if current_sport == 'running' else 'walking'
                
                # Set pace target level
                if activity_type == 'running':
                    profile.pace_target_level = pace_level
                profile.save()
                
                # Create pace entry
                today = timezone.now().date()
                PaceEntry.objects.update_or_create(
                    user=request.user,
                    activity_type=activity_type,
                    recorded_date=today,
                    source='manual',
                    defaults={'level': pace_level, 'is_active': True}
                )
                
                # Check if user wants to add backdated entries
                if form.cleaned_data.get('add_backdated'):
                    wizard.stage_data['add_backdated_pace'] = activity_type
                    wizard.save()
                    return _redirect_with_params('wizard_stage_4_backdated_pace', sport_index=current_sport_index)
                else:
                    # Move to next sport
                    next_sport_index = current_sport_index + 1
                    if next_sport_index >= len(selected_sports):
                        # All sports done
                        wizard.mark_stage_complete(4)
                        wizard.current_stage = 5
                        wizard.save()
                        messages.success(request, f'Pace level saved: Level {pace_level}')
                        return redirect('wizard_stage_5')
                    else:
                        messages.success(request, f'Pace level saved: Level {pace_level}')
                        return _redirect_with_params('wizard_stage_4', sport_index=next_sport_index)
    else:
        form = None
        if current_sport == 'cycling':
            initial_data = {'current_ftp': profile.ftp_score or 200}
            form = WizardStage4FTPForm(initial=initial_data)
        else:
            initial_data = {'pace_level': 5}
            form = WizardStage4PaceForm(initial=initial_data)
    
    context = {
        'form': form,
        'stage': 4,
        'total_stages': 6,
        'wizard': wizard,
        'current_sport': current_sport.title(),
        'sport_index': current_sport_index,
        'total_sports': len(selected_sports),
    }
    return render(request, 'accounts/wizard/stage4.html', context)


@login_required
def wizard_stage_4_backdated_ftp(request):
    """Add backdated FTP entries"""
    wizard, _ = OnboardingWizard.objects.get_or_create(user=request.user)
    sport_index = request.GET.get('sport_index', 0)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_entry':
            form = WizardStage4BackdatedFTPForm(request.POST)
            if form.is_valid():
                entry = form.save(commit=False)
                entry.user = request.user
                entry.source = 'manual'
                entry.save()
                messages.success(request, f'FTP entry added: {entry.ftp_value}W on {entry.recorded_date}')
                return _redirect_with_params('wizard_stage_4_backdated_ftp', sport_index=sport_index)
        
        elif action == 'done':
            # Move to next sport or stage 5
            selected_sports = wizard.stage_data.get('selected_sports', [])
            try:
                next_sport_index = int(sport_index) + 1
            except (ValueError, TypeError):
                next_sport_index = 1
            
            if next_sport_index >= len(selected_sports):
                wizard.mark_stage_complete(4)
                wizard.current_stage = 5
                wizard.save()
                messages.success(request, 'FTP entries saved!')
                return redirect('wizard_stage_5')
            else:
                return _redirect_with_params('wizard_stage_4', sport_index=next_sport_index)
    else:
        form = WizardStage4BackdatedFTPForm()
    
    # Get FTP entries
    ftp_entries = request.user.ftp_entries.all().order_by('-recorded_date')
    
    context = {
        'form': form,
        'ftp_entries': ftp_entries,
        'wizard': wizard,
        'sport_index': sport_index,
    }
    return render(request, 'accounts/wizard/stage4_backdated_ftp.html', context)


@login_required
def wizard_stage_4_backdated_pace(request):
    """Add backdated pace entries"""
    wizard, _ = OnboardingWizard.objects.get_or_create(user=request.user)
    sport_index = request.GET.get('sport_index', 0)
    activity_type = wizard.stage_data.get('add_backdated_pace', 'running')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_entry':
            form = WizardStage4BackdatedPaceForm(request.POST)
            if form.is_valid():
                entry = form.save(commit=False)
                entry.user = request.user
                entry.activity_type = activity_type
                entry.source = 'manual'
                entry.save()
                messages.success(request, f'Pace entry added: Level {entry.level} on {entry.recorded_date}')
                return _redirect_with_params('wizard_stage_4_backdated_pace', sport_index=sport_index)
        
        elif action == 'done':
            # Move to next sport or stage 5
            selected_sports = wizard.stage_data.get('selected_sports', [])
            try:
                next_sport_index = int(sport_index) + 1
            except (ValueError, TypeError):
                next_sport_index = 1
            
            if next_sport_index >= len(selected_sports):
                wizard.mark_stage_complete(4)
                wizard.current_stage = 5
                wizard.save()
                messages.success(request, 'Pace entries saved!')
                return redirect('wizard_stage_5')
            else:
                return _redirect_with_params('wizard_stage_4', sport_index=next_sport_index)
    else:
        form = WizardStage4BackdatedPaceForm()
    
    # Get pace entries for this activity type
    pace_entries = request.user.pace_entries.filter(activity_type=activity_type).order_by('-recorded_date')
    
    context = {
        'form': form,
        'pace_entries': pace_entries,
        'activity_type': activity_type.title(),
        'wizard': wizard,
        'sport_index': sport_index,
    }
    return render(request, 'accounts/wizard/stage4_backdated_pace.html', context)


@login_required
def wizard_stage_5(request):
    """Stage 5: Weight History"""
    wizard, _ = OnboardingWizard.objects.get_or_create(user=request.user)
    selected_sports = wizard.stage_data.get('selected_sports', [])
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'skip':
            wizard.mark_stage_complete(5)
            wizard.current_stage = 6
            wizard.save()
            messages.info(request, 'You can add weight entries later in your profile settings.')
            return redirect('wizard_stage_6')
        
        elif action == 'add_weight':
            form = WizardStage5Form(request.POST)
            if form.is_valid():
                current_weight = form.cleaned_data.get('current_weight')
                
                if current_weight:
                    # Create weight entry for today
                    today = timezone.now().date()
                    WeightEntry.objects.update_or_create(
                        user=request.user,
                        recorded_date=today,
                        defaults={'weight': current_weight}
                    )
                
                # Check if user wants to add backdated entries
                if form.cleaned_data.get('add_backdated'):
                    return redirect('wizard_stage_5_backdated')
                else:
                    wizard.mark_stage_complete(5)
                    wizard.current_stage = 6
                    wizard.save()
                    messages.success(request, 'Weight entry saved!')
                    return redirect('wizard_stage_6')
    else:
        form = WizardStage5Form()
    
    context = {
        'form': form,
        'stage': 5,
        'total_stages': 6,
        'wizard': wizard,
        'total_sports': len(selected_sports) if selected_sports else 1,
    }
    return render(request, 'accounts/wizard/stage5.html', context)


@login_required
def wizard_stage_5_backdated(request):
    """Add backdated weight entries"""
    wizard, _ = OnboardingWizard.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_entry':
            form = WizardStage5BackdatedForm(request.POST)
            if form.is_valid():
                entry = form.save(commit=False)
                entry.user = request.user
                entry.save()
                messages.success(request, f'Weight entry added: {entry.weight} lbs on {entry.recorded_date}')
                return redirect('wizard_stage_5_backdated')
        
        elif action == 'done':
            wizard.mark_stage_complete(5)
            wizard.current_stage = 6
            wizard.save()
            messages.success(request, 'Weight entries saved!')
            return redirect('wizard_stage_6')
    else:
        form = WizardStage5BackdatedForm()
    
    # Get weight entries
    weight_entries = request.user.weight_entries.all().order_by('-recorded_date')
    
    context = {
        'form': form,
        'weight_entries': weight_entries,
        'wizard': wizard,
    }
    return render(request, 'accounts/wizard/stage5_backdated.html', context)


@login_required
def wizard_stage_6(request):
    """Stage 6: Activation Status"""
    wizard, _ = OnboardingWizard.objects.get_or_create(user=request.user)
    site_settings = SiteSettings.get_settings()
    peloton_connected = (
        hasattr(request.user, 'peloton_api_connection')
        and request.user.peloton_api_connection
        and request.user.peloton_api_connection.is_active
    )
    
    if request.method == 'POST':
        # Complete the wizard
        wizard.mark_stage_complete(6)
        wizard.save()
        
        messages.success(request, 'Congratulations! Your account setup is complete. Welcome to Chase The Zones!')
        return redirect('core:dashboard')
    
    context = {
        'stage': 6,
        'total_stages': 6,
        'wizard': wizard,
        'user': request.user,
        'site_settings': site_settings,
        'require_activation': site_settings.require_user_activation,
        'peloton_connected': peloton_connected,
    }
    return render(request, 'accounts/wizard/stage6.html', context)
