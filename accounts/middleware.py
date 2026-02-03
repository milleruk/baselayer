from django.conf import settings
from django.shortcuts import redirect
from django.urls import Resolver404, resolve, reverse

from .models import OnboardingWizard


class OnboardingRedirectMiddleware:
    """
    Redirect authenticated users with incomplete onboarding to the wizard,
    except for configured URL exceptions.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Always pass through if not authenticated
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Bypass onboarding for superusers
        if request.user.is_superuser:
            return self.get_response(request)

        # Check if this URL is exempt from onboarding redirect
        if self._is_exempt(request):
            return self.get_response(request)

        # Get or create wizard for this user
        wizard, _ = OnboardingWizard.objects.get_or_create(user=request.user)
        
        # If wizard is complete, let them through
        if wizard.is_complete():
            return self.get_response(request)

        # Calculate where they should be in the wizard
        redirect_url = self._get_wizard_url(wizard)
        
        # If they're already on the correct wizard page, let them through
        if request.get_full_path() == redirect_url:
            return self.get_response(request)

        # Redirect to the appropriate wizard stage
        return redirect(redirect_url)

    def _is_exempt(self, request):
        path = request.path
        for prefix in getattr(settings, "ONBOARDING_EXEMPT_PATH_PREFIXES", []):
            if prefix and path.startswith(prefix):
                return True

        try:
            match = resolve(path)
        except Resolver404:
            return False

        url_name = match.url_name
        if not url_name:
            return False

        return url_name in getattr(settings, "ONBOARDING_EXEMPT_URLNAMES", set())

    def _get_wizard_url(self, wizard):
        stage = wizard.current_stage or 1
        stage_map = {
            1: "wizard_stage_1",
            2: "wizard_stage_2",
            3: "wizard_stage_3",
            4: "wizard_stage_4",
            5: "wizard_stage_5",
            6: "wizard_stage_6",
        }
        url_name = stage_map.get(stage, "wizard_stage_1")
        url = reverse(url_name)
        if stage == 4:
            return f"{url}?sport_index=0"
        return url