from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "accounts"
    
    def ready(self):
        """Set up custom admin site with email authentication"""
        from django.contrib import admin
        from django.contrib.admin import AdminSite
        from django.contrib.auth.views import LoginView
        from django.urls import path
        from .forms import EmailAuthenticationForm
        
        # Store the existing registry before replacing
        old_registry = dict(admin.site._registry)
        old_site_header = admin.site.site_header
        old_site_title = admin.site.site_title
        old_index_title = admin.site.index_title
        
        class EmailAdminSite(AdminSite):
            """Custom admin site that uses email-based authentication"""
            login_form = EmailAuthenticationForm
            
            def get_urls(self):
                urls = super().get_urls()
                # Replace the default login view with our custom one
                custom_urls = [
                    path('login/', LoginView.as_view(
                        authentication_form=EmailAuthenticationForm,
                        template_name='admin/login.html',
                        extra_context={'site_header': self.site_header, 'site_title': self.site_title}
                    ), name='login'),
                ]
                return custom_urls + urls
        
        # Create new admin site and copy over the registry
        new_site = EmailAdminSite(name='admin')
        new_site.site_header = old_site_header
        new_site.site_title = old_site_title
        new_site.index_title = old_index_title
        
        # Copy all registered models from old site to new site (preserve admin instances)
        new_site._registry = old_registry.copy()
        
        # Update admin_site reference in all admin instances
        for admin_instance in new_site._registry.values():
            admin_instance.admin_site = new_site
        
        # Replace the default admin site
        admin.site = new_site
