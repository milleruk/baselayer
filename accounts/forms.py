from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
from .models import Profile, WeightEntry

User = get_user_model()


class ProfileForm(forms.ModelForm):
    """Form for editing profile information"""
    class Meta:
        model = Profile
        fields = ['full_name', 'date_of_birth']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'style': 'width: 100%; background: var(--dark-light); border: 1px solid var(--border); border-radius: 0; color: var(--text); padding: 0.75rem 1rem; font-size: 1rem; font-family: inherit;',
                'placeholder': 'Enter your full name'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'type': 'date',
                'style': 'width: 100%; background: var(--dark-light); border: 1px solid var(--border); border-radius: 0; color: var(--text); padding: 0.75rem 1rem; font-size: 1rem; font-family: inherit;'
            })
        }


class EmailChangeForm(forms.Form):
    """Form for changing email address"""
    new_email = forms.EmailField(
        label='New Email',
        widget=forms.EmailInput(attrs={
            'style': 'width: 100%; background: var(--dark-light); border: 1px solid var(--border); border-radius: 0; color: var(--text); padding: 0.75rem 1rem; font-size: 1rem; font-family: inherit;',
            'placeholder': 'Enter new email address'
        })
    )
    confirm_email = forms.EmailField(
        label='Confirm Email',
        widget=forms.EmailInput(attrs={
            'style': 'width: 100%; background: var(--dark-light); border: 1px solid var(--border); border-radius: 0; color: var(--text); padding: 0.75rem 1rem; font-size: 1rem; font-family: inherit;',
            'placeholder': 'Confirm new email address'
        })
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        new_email = cleaned_data.get('new_email')
        confirm_email = cleaned_data.get('confirm_email')
        
        if new_email and confirm_email:
            if new_email != confirm_email:
                raise ValidationError("Email addresses do not match.")
            
            # Check if email is already in use by another user
            if User.objects.filter(email=new_email).exclude(pk=self.user.pk).exists():
                raise ValidationError("This email address is already in use.")
        
        return cleaned_data


class CustomPasswordChangeForm(PasswordChangeForm):
    """Custom password change form with better styling"""
    old_password = forms.CharField(
        label='Current Password',
        widget=forms.PasswordInput(attrs={
            'style': 'width: 100%; background: var(--dark-light); border: 1px solid var(--border); border-radius: 0; color: var(--text); padding: 0.75rem 1rem; font-size: 1rem; font-family: inherit;',
            'placeholder': 'Enter current password'
        })
    )
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'style': 'width: 100%; background: var(--dark-light); border: 1px solid var(--border); border-radius: 0; color: var(--text); padding: 0.75rem 1rem; font-size: 1rem; font-family: inherit;',
            'placeholder': 'Enter new password'
        })
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'style': 'width: 100%; background: var(--dark-light); border: 1px solid var(--border); border-radius: 0; color: var(--text); padding: 0.75rem 1rem; font-size: 1rem; font-family: inherit;',
            'placeholder': 'Confirm new password'
        })
    )


class WeightForm(forms.ModelForm):
    """Form for adding weight entries"""
    class Meta:
        model = WeightEntry
        fields = ['weight', 'recorded_date']
        widgets = {
            'weight': forms.NumberInput(attrs={
                'style': 'width: 100%; background: var(--dark-light); border: 1px solid var(--border); border-radius: 0; color: var(--text); padding: 0.75rem 1rem; font-size: 1rem; font-family: inherit;',
                'placeholder': 'Enter weight in pounds',
                'step': '0.01',
                'min': '0'
            }),
            'recorded_date': forms.DateInput(attrs={
                'type': 'date',
                'style': 'width: 100%; background: var(--dark-light); border: 1px solid var(--border); border-radius: 0; color: var(--text); padding: 0.75rem 1rem; font-size: 1rem; font-family: inherit;'
            })
        }
