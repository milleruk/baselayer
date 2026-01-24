from django import forms
from django.contrib import messages
from .models import PelotonConnection


class PelotonConnectionForm(forms.ModelForm):
    """Form for connecting Peloton account"""
    username = forms.CharField(
        max_length=255,
        required=True,
        help_text="Your Peloton username or email"
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=True,
        help_text="Your Peloton password"
    )
    
    class Meta:
        model = PelotonConnection
        fields = []  # We handle username/password manually
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Pre-populate if connection exists
        if self.instance and self.instance.pk:
            self.fields['username'].initial = self.instance.username
    
    def save(self, commit=True):
        """Save the connection with encrypted credentials"""
        connection = super().save(commit=False)
        connection.user = self.user
        
        # Set encrypted credentials
        connection.username = self.cleaned_data['username']
        connection.password = self.cleaned_data['password']
        
        if commit:
            connection.save()
        return connection
