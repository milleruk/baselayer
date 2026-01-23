from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from tracker.models import ChallengeInstance
from .models import Profile, WeightEntry
from .forms import ProfileForm, EmailChangeForm, CustomPasswordChangeForm, WeightForm

def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("plans:dashboard")
    else:
        form = UserCreationForm()
    return render(request, "accounts/register.html", {"form": form})

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
        
        # Add attempt count to the instance
        latest_instance.attempt_count = attempt_count
        
        if latest_instance.all_weeks_completed:
            fully_completed_challenges.append(latest_instance)
        elif latest_instance.weekly_plans.exists() and latest_instance.completion_rate > 0:
            # Has some progress but not all weeks completed
            partially_completed_challenges.append(latest_instance)
    
    # Get weight entries
    weight_entries = WeightEntry.objects.filter(user=request.user).order_by('-recorded_date', '-created_at')
    
    # Handle form submissions
    profile_form = ProfileForm(instance=profile)
    email_form = EmailChangeForm(user=request.user)
    password_form = CustomPasswordChangeForm(user=request.user)
    weight_form = WeightForm()
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'profile':
            profile_form = ProfileForm(request.POST, instance=profile)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('profile')
        
        elif form_type == 'email':
            email_form = EmailChangeForm(user=request.user, data=request.POST)
            if email_form.is_valid():
                request.user.email = email_form.cleaned_data['new_email']
                request.user.save()
                messages.success(request, 'Email address updated successfully!')
                return redirect('profile')
        
        elif form_type == 'password':
            password_form = CustomPasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, password_form.user)
                messages.success(request, 'Password changed successfully!')
                return redirect('profile')
        
        elif form_type == 'weight':
            weight_form = WeightForm(request.POST)
            if weight_form.is_valid():
                weight_entry = weight_form.save(commit=False)
                weight_entry.user = request.user
                weight_entry.save()
                messages.success(request, 'Weight entry added successfully!')
                return redirect('profile')
    
    return render(request, "accounts/profile.html", {
        "user": request.user,
        "profile": profile,
        "profile_form": profile_form,
        "email_form": email_form,
        "password_form": password_form,
        "weight_form": weight_form,
        "weight_entries": weight_entries,
    })


@login_required
def delete_weight_entry(request, entry_id):
    """Delete a weight entry"""
    weight_entry = get_object_or_404(WeightEntry, id=entry_id, user=request.user)
    weight_entry.delete()
    messages.success(request, 'Weight entry deleted successfully!')
    return redirect('profile')
