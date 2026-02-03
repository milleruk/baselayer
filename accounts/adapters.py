from allauth.account.adapter import DefaultAccountAdapter
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from core.models import SiteSettings


class AccountAdapter(DefaultAccountAdapter):
    """
    Custom allauth adapter to integrate with site settings.
    Handles user activation requirements and onboarding flow.
    """
    
    def save_user(self, request, user, form, commit=True):
        """
        Save newly registered user with proper activation status.
        New users are set as inactive but can complete the onboarding wizard.
        They'll be activated upon wizard completion or by admin.
        """
        user = super().save_user(request, user, form, commit=False)
        
        # Always set new users as inactive initially
        # They can still complete the wizard (backends allow this)
        # Full activation happens after wizard completion or admin approval
        user.is_active = False
        
        if commit:
            user.save()
        
        return user
    
    def is_open_for_signup(self, request):
        """
        Allow signups - activation control is handled via is_active flag.
        """
        return True
    
    def get_signup_redirect_url(self, request):
        """
        After signup, inactive users will see the activation pending page.
        The middleware will redirect active users with incomplete onboarding to the wizard.
        """
        return super().get_signup_redirect_url(request)
    
    def get_client_ip(self, request):
        """
        Override to handle cases where IP cannot be determined.
        Return a default value instead of raising PermissionDenied.
        """
        try:
            return super().get_client_ip(request)
        except (PermissionDenied, ValueError):
            # If IP cannot be determined, use a generic identifier
            # This prevents rate limiting from failing in development/proxy environments
            return "0.0.0.0"

