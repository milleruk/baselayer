from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from challenges.models import ChallengeInstance
from .models import Profile, WeightEntry, FTPEntry, PaceEntry, PaceLevel, PaceBand
from .forms import ProfileForm, EmailChangeForm, CustomPasswordChangeForm, WeightForm, FTPForm, PaceForm, EmailUserCreationForm, EmailAuthenticationForm
from .pace_converter import DEFAULT_RUNNING_PACE_LEVELS, ZONE_COLORS
from .walking_pace_levels_data import DEFAULT_WALKING_PACE_LEVELS, WALKING_ZONE_COLORS

def register(request):
    if request.method == "POST":
        form = EmailUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # New users are inactive by default - don't auto-login
            # Show message that account needs activation
            messages.info(request, 'Your account has been created successfully! However, your account is currently inactive and requires administrator approval before you can log in. You will be notified once your account has been activated.')
            return redirect("login")
    else:
        form = EmailUserCreationForm()
    return render(request, "accounts/register.html", {"form": form})


class CustomLoginView(LoginView):
    """Custom login view that uses email authentication"""
    form_class = EmailAuthenticationForm
    template_name = 'accounts/login.html'
    
    def form_invalid(self, form):
        """Handle invalid form submission - check if account is inactive"""
        # Check if the error is due to inactive account
        if 'username' in form.errors:
            for error in form.errors['username']:
                if error.code == 'inactive':
                    # Redirect to inactive account page
                    return redirect('account_inactive')
        
        # Also check if user exists and is inactive (fallback)
        email = form.cleaned_data.get('username') or form.cleaned_data.get('email')
        if email:
            from .models import User
            try:
                user = User.objects.get(email=email)
                if not user.is_active:
                    # Redirect to inactive account page
                    return redirect('account_inactive')
            except User.DoesNotExist:
                pass  # User doesn't exist, let default error handling work
        
        return super().form_invalid(form)


def account_inactive(request):
    """Display page for inactive accounts"""
    return render(request, 'accounts/inactive.html')

@login_required
def profile(request):
    # Get or create user profile
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    # Get all challenge instances for this user (both completed and in progress)
    all_challenge_instances = ChallengeInstance.objects.filter(
        user=request.user
    ).select_related('challenge').prefetch_related('weekly_plans').order_by('-started_at')
    
    # Group by challenge and count attempts
    from collections import defaultdict
    challenge_groups = defaultdict(list)
    
    for ci in all_challenge_instances:
        challenge_groups[ci.challenge.id].append(ci)
    
    # Separate into fully completed and partially completed, showing only latest attempt per challenge
    fully_completed_challenges = []
    partially_completed_challenges = []
    
    for challenge_id, instances in challenge_groups.items():
        # Sort by started_at descending to get the latest attempt
        latest_instance = max(instances, key=lambda x: x.started_at)
        attempt_count = len(instances)
        
        # Get first completion date (for badge/award date)
        first_completed = None
        completed_instances = [ci for ci in instances if ci.completed_at]
        if completed_instances:
            first_completed = min(completed_instances, key=lambda x: x.completed_at)
        
        # Add attempt count and first completion info to the instance
        latest_instance.attempt_count = attempt_count
        latest_instance.first_completion_date = first_completed.completed_at if first_completed else None
        latest_instance.first_completion_instance = first_completed
        
        if latest_instance.all_weeks_completed:
            fully_completed_challenges.append(latest_instance)
        elif latest_instance.weekly_plans.exists() and latest_instance.completion_rate > 0:
            # Has some progress but not all weeks completed
            partially_completed_challenges.append(latest_instance)
    
    # Get weight entries
    weight_entries = WeightEntry.objects.filter(user=request.user).order_by('-recorded_date', '-created_at')
    
    # Get FTP entries
    ftp_entries = FTPEntry.objects.filter(user=request.user).order_by('-recorded_date', '-created_at')
    current_ftp = profile.get_current_ftp()
    
    # Get Pace entries
    running_pace_entries = PaceEntry.objects.filter(user=request.user, activity_type='running').order_by('-recorded_date', '-created_at')
    walking_pace_entries = PaceEntry.objects.filter(user=request.user, activity_type='walking').order_by('-recorded_date', '-created_at')
    current_running_pace = profile.get_current_pace('running')
    current_walking_pace = profile.get_current_pace('walking')
    
    # Get Pace Levels (both running and walking)
    running_pace_levels = PaceLevel.objects.filter(user=request.user, activity_type='running').prefetch_related('bands').order_by('-recorded_date', '-level')
    walking_pace_levels = PaceLevel.objects.filter(user=request.user, activity_type='walking').prefetch_related('bands').order_by('-recorded_date', '-level')
    
    # Get current active pace level objects for metrics display
    current_running_pace_level = None
    current_walking_pace_level = None
    if current_running_pace:
        # Get the most recent pace level definition for the current level
        current_running_pace_level = PaceLevel.objects.filter(
            user=request.user, 
            activity_type='running', 
            level=current_running_pace
        ).prefetch_related('bands').order_by('-recorded_date').first()
        
        # If no custom pace level exists but we have default data, create a display object
        if not current_running_pace_level and current_running_pace in DEFAULT_RUNNING_PACE_LEVELS:
            from datetime import date
            from decimal import Decimal
            
            class DefaultPaceLevel:
                def __init__(self, level, default_data):
                    self.level = level
                    self.recorded_date = date.today()
                    self._default_data = default_data
                
                @property
                def bands(self):
                    class DefaultBands:
                        def __init__(self, default_data):
                            self._default_data = default_data
                        
                        def all(self):
                            class DefaultBand:
                                def __init__(self, zone, data):
                                    self.zone = zone
                                    self.min_mph = Decimal(str(data[0]))
                                    self.max_mph = Decimal(str(data[1]))
                                    self.min_pace = Decimal(str(data[2]))
                                    self.max_pace = Decimal(str(data[3]))
                                    self.description = data[4]
                                
                                def get_zone_display(self):
                                    zone_map = {
                                        'recovery': 'Recovery',
                                        'easy': 'Easy',
                                        'moderate': 'Moderate',
                                        'challenging': 'Challenging',
                                        'hard': 'Hard',
                                        'very_hard': 'Very Hard',
                                        'max': 'Max',
                                    }
                                    return zone_map.get(self.zone, self.zone.title())
                            
                            return [DefaultBand(zone, data) for zone, data in self._default_data.items()]
                    
                    return DefaultBands(self._default_data)
            
            current_running_pace_level = DefaultPaceLevel(current_running_pace, DEFAULT_RUNNING_PACE_LEVELS[current_running_pace])
    if current_walking_pace:
        # Get the most recent pace level definition for the current level
        current_walking_pace_level = PaceLevel.objects.filter(
            user=request.user, 
            activity_type='walking', 
            level=current_walking_pace
        ).prefetch_related('bands').order_by('-recorded_date').first()
        
        # If no custom pace level exists but we have default data, create a display object
        if not current_walking_pace_level and current_walking_pace in DEFAULT_WALKING_PACE_LEVELS:
            from datetime import date
            from decimal import Decimal
            
            class DefaultPaceLevel:
                def __init__(self, level, default_data):
                    self.level = level
                    self.recorded_date = date.today()
                    self._default_data = default_data
                
                @property
                def bands(self):
                    class DefaultBands:
                        def __init__(self, default_data):
                            self._default_data = default_data
                        
                        def all(self):
                            class DefaultBand:
                                def __init__(self, zone, data):
                                    self.zone = zone
                                    self.min_mph = Decimal(str(data[0]))
                                    self.max_mph = Decimal(str(data[1]))
                                    self.min_pace = Decimal(str(data[2]))
                                    self.max_pace = Decimal(str(data[3]))
                                    self.description = data[4]
                                
                                def get_zone_display(self):
                                    zone_map = {
                                        'recovery': 'Recovery',
                                        'easy': 'Easy',
                                        'brisk': 'Brisk',
                                        'power': 'Power',
                                        'max': 'Max',
                                    }
                                    return zone_map.get(self.zone, self.zone.title())
                            
                            return [DefaultBand(zone, data) for zone, data in self._default_data.items()]
                    
                    return DefaultBands(self._default_data)
            
            current_walking_pace_level = DefaultPaceLevel(current_walking_pace, DEFAULT_WALKING_PACE_LEVELS[current_walking_pace])
    
    # Check if user is in an active challenge
    from datetime import date
    today = date.today()
    active_challenge_instance = ChallengeInstance.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('challenge').first()
    
    is_in_active_challenge = False
    if active_challenge_instance:
        challenge = active_challenge_instance.challenge
        # Check if challenge is currently running (started but not ended)
        if challenge.start_date <= today <= challenge.end_date:
            is_in_active_challenge = True
    
    # Handle form submissions
    profile_form = ProfileForm(instance=profile)
    email_form = EmailChangeForm(user=request.user)
    password_form = CustomPasswordChangeForm(user=request.user)
    weight_form = WeightForm()
    ftp_form = FTPForm()
    pace_form = PaceForm()
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'profile':
            profile_form = ProfileForm(request.POST, instance=profile)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Profile updated successfully!')
                return HttpResponseRedirect(reverse('profile') + '#tab-profile')
        
        elif form_type == 'email':
            email_form = EmailChangeForm(user=request.user, data=request.POST)
            if email_form.is_valid():
                request.user.email = email_form.cleaned_data['new_email']
                request.user.save()
                messages.success(request, 'Email address updated successfully!')
                return HttpResponseRedirect(reverse('profile') + '#tab-security')
        
        elif form_type == 'password':
            password_form = CustomPasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, password_form.user)
                messages.success(request, 'Password changed successfully!')
                return HttpResponseRedirect(reverse('profile') + '#tab-security')
        
        elif form_type == 'weight':
            weight_form = WeightForm(request.POST)
            if weight_form.is_valid():
                weight_entry = weight_form.save(commit=False)
                weight_entry.user = request.user
                weight_entry.save()
                messages.success(request, 'Weight entry added successfully!')
                return HttpResponseRedirect(reverse('profile') + '#tab-weight')
        
        elif form_type == 'ftp':
            ftp_form = FTPForm(request.POST)
            if ftp_form.is_valid():
                ftp_entry = ftp_form.save(commit=False)
                ftp_entry.user = request.user
                ftp_entry.is_active = True  # New FTP entries are active by default
                ftp_entry.save()
                messages.success(request, 'FTP entry added successfully!')
                return HttpResponseRedirect(reverse('profile') + '#tab-ftp-pace')
        
        elif form_type == 'pace':
            pace_form = PaceForm(request.POST)
            if pace_form.is_valid():
                pace_entry = pace_form.save(commit=False)
                pace_entry.user = request.user
                pace_entry.is_active = True  # New pace entries are active by default
                pace_entry.save()
                messages.success(request, 'Pace entry added successfully!')
                return HttpResponseRedirect(reverse('profile') + '#tab-ftp-pace')
    
    return render(request, "accounts/profile.html", {
        "user": request.user,
        "profile": profile,
        "profile_form": profile_form,
        "email_form": email_form,
        "password_form": password_form,
        "weight_form": weight_form,
        "weight_entries": weight_entries,
        "ftp_form": ftp_form,
        "ftp_entries": ftp_entries,
        "current_ftp": current_ftp,
        "pace_form": pace_form,
        "running_pace_entries": running_pace_entries,
        "walking_pace_entries": walking_pace_entries,
        "current_running_pace": current_running_pace,
        "current_walking_pace": current_walking_pace,
        "running_pace_levels": running_pace_levels,
        "walking_pace_levels": walking_pace_levels,
        "current_running_pace_level": current_running_pace_level,
        "current_walking_pace_level": current_walking_pace_level,
        "default_running_pace_levels": DEFAULT_RUNNING_PACE_LEVELS,
        "default_walking_pace_levels": DEFAULT_WALKING_PACE_LEVELS,
        "zone_colors": ZONE_COLORS,
        "walking_zone_colors": WALKING_ZONE_COLORS,
        "is_in_active_challenge": is_in_active_challenge,
        "fully_completed_challenges": fully_completed_challenges,
        "partially_completed_challenges": partially_completed_challenges,
    })


@login_required
def delete_weight_entry(request, entry_id):
    """Delete a weight entry"""
    weight_entry = get_object_or_404(WeightEntry, id=entry_id, user=request.user)
    weight_entry.delete()
    messages.success(request, 'Weight entry deleted successfully!')
    return HttpResponseRedirect(reverse('profile') + '#tab-weight')


@login_required
def delete_ftp_entry(request, entry_id):
    """Delete an FTP entry"""
    ftp_entry = get_object_or_404(FTPEntry, id=entry_id, user=request.user)
    ftp_entry.delete()
    messages.success(request, 'FTP entry deleted successfully!')
    return HttpResponseRedirect(reverse('profile') + '#tab-ftp-pace')


@login_required
def toggle_ftp_active(request, entry_id):
    """Toggle the active status of an FTP entry"""
    ftp_entry = get_object_or_404(FTPEntry, id=entry_id, user=request.user)
    ftp_entry.is_active = not ftp_entry.is_active
    ftp_entry.save()
    
    if ftp_entry.is_active:
        messages.success(request, 'FTP entry activated successfully!')
    else:
        messages.success(request, 'FTP entry deactivated successfully!')
    
    return HttpResponseRedirect(reverse('profile') + '#tab-ftp-pace')


@login_required
def delete_pace_entry(request, entry_id):
    """Delete a pace entry"""
    pace_entry = get_object_or_404(PaceEntry, id=entry_id, user=request.user)
    pace_entry.delete()
    messages.success(request, 'Pace entry deleted successfully!')
    return HttpResponseRedirect(reverse('profile') + '#tab-ftp-pace')


@login_required
def toggle_pace_active(request, entry_id):
    """Toggle the active status of a pace entry"""
    pace_entry = get_object_or_404(PaceEntry, id=entry_id, user=request.user)
    pace_entry.is_active = not pace_entry.is_active
    pace_entry.save()
    
    if pace_entry.is_active:
        messages.success(request, 'Pace entry activated successfully!')
    else:
        messages.success(request, 'Pace entry deactivated successfully!')
    
    return HttpResponseRedirect(reverse('profile') + '#tab-ftp-pace')


@login_required
def create_pace_level(request):
    """Create a new pace level from default data"""
    if request.method == 'POST':
        level = int(request.POST.get('level'))
        activity_type = request.POST.get('activity_type', 'running')
        recorded_date = request.POST.get('recorded_date')
        notes = request.POST.get('notes', '')
        
        from datetime import datetime
        recorded_date = datetime.strptime(recorded_date, '%Y-%m-%d').date()
        
        # Get the appropriate default data
        if activity_type == 'running':
            default_levels = DEFAULT_RUNNING_PACE_LEVELS
        else:
            default_levels = DEFAULT_WALKING_PACE_LEVELS
        
        if level in default_levels:
            # Check if this level/date/activity combination already exists
            existing = PaceLevel.objects.filter(
                user=request.user,
                activity_type=activity_type,
                level=level,
                recorded_date=recorded_date
            ).first()
            
            if existing:
                messages.error(request, f'Pace Level {level} ({activity_type}) for {recorded_date} already exists.')
                return HttpResponseRedirect(reverse('profile') + '#tab-ftp-pace')
            
            # Create pace level
            pace_level = PaceLevel.objects.create(
                user=request.user,
                activity_type=activity_type,
                level=level,
                recorded_date=recorded_date,
                notes=notes
            )
            
            # Create pace bands
            level_data = default_levels[level]
            for zone, (min_mph, max_mph, min_pace, max_pace, description) in level_data.items():
                PaceBand.objects.create(
                    pace_level=pace_level,
                    zone=zone,
                    min_mph=min_mph,
                    max_mph=max_mph,
                    min_pace=min_pace,
                    max_pace=max_pace,
                    description=description
                )
            
            messages.success(request, f'Pace Level {level} ({activity_type}) created successfully!')
        else:
            messages.error(request, 'Invalid pace level.')
    
    return HttpResponseRedirect(reverse('profile') + '#tab-ftp-pace')


@login_required
def delete_pace_level(request, level_id):
    """Delete a pace level"""
    pace_level = get_object_or_404(PaceLevel, id=level_id, user=request.user)
    pace_level.delete()
    messages.success(request, 'Pace level deleted successfully!')
    return HttpResponseRedirect(reverse('profile') + '#tab-ftp-pace')
