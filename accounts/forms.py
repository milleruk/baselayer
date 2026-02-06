from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import Profile, WeightEntry, FTPEntry, PaceEntry

User = get_user_model()

# Tailwind CSS classes for form inputs
INPUT_CLASS = 'dark:bg-dark-900 h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 shadow-theme-xs placeholder:text-gray-400 focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:placeholder:text-white/30 dark:focus:border-brand-800'
SELECT_CLASS = 'dark:bg-dark-900 h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800'



class EmailAuthenticationForm(AuthenticationForm):
    """Custom authentication form that uses email instead of username"""
    username = forms.EmailField(
        label='Email address',
        widget=forms.EmailInput(attrs={
            'autofocus': True,
            'placeholder': 'info@gmail.com',
            'class': 'dark:bg-dark-900 h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 shadow-theme-xs placeholder:text-gray-400 focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:placeholder:text-white/30 dark:focus:border-brand-800'
        })
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your password',
            'class': 'dark:bg-dark-900 h-11 w-full rounded-lg border border-gray-300 bg-transparent py-2.5 pl-4 pr-11 text-sm text-gray-800 shadow-theme-xs placeholder:text-gray-400 focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:placeholder:text-white/30 dark:focus:border-brand-800'
        })
    )
    remember_me = forms.BooleanField(
        label='Keep me logged in',
        required=False,
        initial=False,
        widget=forms.CheckboxInput()
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Email address'
    
    def clean_username(self):
        email = self.cleaned_data.get('username')
        if email:
            email = email.lower().strip()
        return email


class EmailUserCreationForm(forms.ModelForm):
    """Custom user creation form that uses email instead of username"""
    email = forms.EmailField(
        label='Email',
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your email',
            'class': 'dark:bg-dark-900 h-11 w-full rounded-lg border border-gray-300 bg-transparent px-4 py-2.5 text-sm text-gray-800 shadow-theme-xs placeholder:text-gray-400 focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:placeholder:text-white/30 dark:focus:border-brand-800',
            'autocomplete': 'email'
        })
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your password',
            'class': 'dark:bg-dark-900 h-11 w-full rounded-lg border border-gray-300 bg-transparent py-2.5 pl-4 pr-11 text-sm text-gray-800 shadow-theme-xs placeholder:text-gray-400 focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:placeholder:text-white/30 dark:focus:border-brand-800',
            'autocomplete': 'new-password'
        }),
        help_text="Your password must contain at least 8 characters."
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm your password',
            'class': 'dark:bg-dark-900 h-11 w-full rounded-lg border border-gray-300 bg-transparent py-2.5 pl-4 pr-11 text-sm text-gray-800 shadow-theme-xs placeholder:text-gray-400 focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:placeholder:text-white/30 dark:focus:border-brand-800',
            'autocomplete': 'new-password'
        }),
        help_text="Enter the same password as before, for verification."
    )
    
    class Meta:
        model = User
        fields = ('email',)
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower().strip()
            if User.objects.filter(email=email).exists():
                raise ValidationError("A user with this email already exists.")
        return email
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError("The two password fields didn't match.")
        return password2
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


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


class FTPForm(forms.ModelForm):
    """Form for adding FTP entries"""
    class Meta:
        model = FTPEntry
        fields = ['ftp_value', 'recorded_date', 'source']
        widgets = {
            'ftp_value': forms.NumberInput(attrs={
                'style': 'width: 100%; background: var(--dark-light); border: 1px solid var(--border); border-radius: 0; color: var(--text); padding: 0.75rem 1rem; font-size: 1rem; font-family: inherit;',
                'placeholder': 'Enter FTP value in watts',
                'step': '1',
                'min': '0'
            }),
            'recorded_date': forms.DateInput(attrs={
                'type': 'date',
                'style': 'width: 100%; background: var(--dark-light); border: 1px solid var(--border); border-radius: 0; color: var(--text); padding: 0.75rem 1rem; font-size: 1rem; font-family: inherit;'
            }),
            'source': forms.Select(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary'
            })
        }


# ========== WIZARD FORMS ==========

class WizardStage1Form(forms.Form):
    """Stage 1: User Details (Name + DOB)"""
    first_name = forms.CharField(
        label='First Name',
        required=True,
        max_length=150,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your first name',
            'class': INPUT_CLASS,
            'autocomplete': 'given-name'
        })
    )
    last_name = forms.CharField(
        label='Last Name',
        required=True,
        max_length=150,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your last name',
            'class': INPUT_CLASS,
            'autocomplete': 'family-name'
        })
    )
    date_of_birth = forms.DateField(
        label='Date of Birth',
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': INPUT_CLASS
        })
    )


class WizardStage3Form(forms.Form):
    """Stage 3: Sport Selection"""
    SPORT_CHOICES = [
        ('cycling', 'Cycling'),
        ('running', 'Running'),
        ('walking', 'Walking'),
    ]
    
    sports = forms.MultipleChoiceField(
        label='What sports do you participate in?',
        choices=SPORT_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'w-4 h-4 rounded'
        }),
        required=True,
        help_text='Select one, two, or all three'
    )


class WizardStage4FTPForm(forms.Form):
    """Stage 4: FTP Entries for Cycling"""
    current_ftp = forms.IntegerField(
        label='Current FTP (Watts)',
        required=True,
        widget=forms.NumberInput(attrs={
            'placeholder': 'e.g., 250',
            'class': INPUT_CLASS,
            'min': '50',
            'max': '500'
        }),
        help_text='Your current Functional Threshold Power in watts'
    )
    add_backdated = forms.BooleanField(
        label='Add historical FTP entries?',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded'
        })
    )


class WizardStage4PaceForm(forms.Form):
    """Stage 4: Pace Level for Running/Walking (activity-specific)"""
    pace_level = forms.ChoiceField(
        label='Pace Level (1-10)',
        required=True,
        choices=[(i, f'Level {i}') for i in range(1, 11)],
        widget=forms.Select(attrs={
            'class': SELECT_CLASS
        }),
        help_text='1 = Slow/Recovery, 10 = Maximum Effort'
    )
    
    add_backdated = forms.BooleanField(
        label='Add historical pace entries?',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded'
        })
    )


class WizardStage4BackdatedFTPForm(forms.ModelForm):
    """Form for adding multiple FTP entries"""
    class Meta:
        model = FTPEntry
        fields = ['ftp_value', 'recorded_date']
        widgets = {
            'ftp_value': forms.NumberInput(attrs={
                'placeholder': 'FTP in watts',
                'class': INPUT_CLASS,
                'min': '50',
                'max': '500'
            }),
            'recorded_date': forms.DateInput(attrs={
                'type': 'date',
                'class': INPUT_CLASS
            })
        }


class WizardStage4BackdatedPaceForm(forms.ModelForm):
    """Form for adding multiple pace entries"""
    class Meta:
        model = PaceEntry
        fields = ['level', 'recorded_date']
        widgets = {
            'level': forms.Select(attrs={
                'class': SELECT_CLASS
            }, choices=[(i, f'Level {i}') for i in range(1, 11)]),
            'recorded_date': forms.DateInput(attrs={
                'type': 'date',
                'class': INPUT_CLASS
            })
        }


class WizardStage5Form(forms.Form):
    """Stage 5: Weight Entry"""
    current_weight = forms.DecimalField(
        label='Current Weight (lbs)',
        required=False,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'placeholder': 'e.g., 165.50',
            'class': INPUT_CLASS,
            'step': '0.01',
            'min': '50'
        })
    )
    add_backdated = forms.BooleanField(
        label='Add historical weight entries?',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded'
        })
    )


class WizardStage5BackdatedForm(forms.ModelForm):
    """Form for adding multiple weight entries"""
    class Meta:
        model = WeightEntry
        fields = ['weight', 'recorded_date']
        widgets = {
            'weight': forms.NumberInput(attrs={
                'placeholder': 'Weight in lbs',
                'class': INPUT_CLASS,
                'step': '0.01',
                'min': '50'
            }),
            'recorded_date': forms.DateInput(attrs={
                'type': 'date',
                'class': INPUT_CLASS
            })
        }

class PaceForm(forms.ModelForm):
    """Form for adding pace entries"""
    class Meta:
        model = PaceEntry
        fields = ['level', 'activity_type', 'recorded_date', 'source']
        widgets = {
            'level': forms.Select(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary'
            }, choices=[(i, f'Level {i}') for i in range(1, 11)]),
            'activity_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary'
            }),
            'recorded_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary'
            }),
            'source': forms.Select(attrs={
                'class': 'w-full px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary'
            })
        }
