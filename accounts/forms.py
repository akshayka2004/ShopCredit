"""
==============================================================================
ACCOUNTS APP - FORMS
==============================================================================
Forms for user authentication and profile management.

Forms:
    - LoginForm: User login with username/password
    - RegistrationForm: New user registration with role selection
    - ProfileForm: Edit user profile information

Author: ShopCredit Development Team
==============================================================================
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import CustomUser, Profile


class LoginForm(AuthenticationForm):
    """
    Custom login form with Bootstrap styling.
    
    Extends Django's AuthenticationForm to add custom styling
    and placeholder text.
    """
    
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username',
            'autofocus': True,
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
        })
    )
    
    # Remember me checkbox
    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )


class RegistrationForm(UserCreationForm):
    """
    Custom registration form for new users.
    
    Includes:
    - Username, email, password fields
    - Role selection (Shop Owner or Wholesaler)
    - Phone number
    - Business information
    
    Note: Admin users can only be created via Django admin.
    """
    
    # Role choices - exclude admin for public registration
    ROLE_CHOICES = [
        ('shop_owner', 'Shop Owner - I want to order products on credit'),
        ('wholesaler', 'Wholesaler - I want to sell products on credit'),
    ]
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@example.com',
        })
    )
    
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input',
        }),
        initial='shop_owner',
    )
    
    phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+91-9876543210',
        })
    )
    
    # Business information
    business_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your Business Name',
        })
    )
    
    business_address = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your complete business address',
            'rows': 3,
        })
    )
    
    # Terms and conditions checkbox
    agree_terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
        error_messages={
            'required': 'You must agree to the terms and conditions to register.'
        }
    )
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2', 'role', 'phone']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes to default fields
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Choose a username',
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Create a password (min 8 characters)',
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your password',
        })
    
    def clean_email(self):
        """Validate that email is unique."""
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError('This email address is already registered.')
        return email
    
    def save(self, commit=True):
        """
        Save user and create associated profile with business info.
        """
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.role = self.cleaned_data['role']
        user.phone = self.cleaned_data.get('phone', '')
        
        if commit:
            user.save()
            
            # Update the profile (created by signal)
            user.profile.business_name = self.cleaned_data['business_name']
            user.profile.business_address = self.cleaned_data['business_address']
            
            # Set initial credit limit based on role
            if user.role == 'shop_owner':
                user.profile.credit_limit = 10000.00  # Default ₹10,000 for shop owners
            
            user.profile.save()
        
        return user


class ProfileForm(forms.ModelForm):
    """
    Form for editing user profile information.
    
    Allows users to update their business details.
    Credit limit can only be changed by admin/wholesaler.
    """
    
    class Meta:
        model = Profile
        fields = ['business_name', 'business_address', 'gst_number', 'profile_picture']
        widgets = {
            'business_name': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'business_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
            'gst_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '15-character GST number',
                'maxlength': 15,
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
        }
    
    def clean_gst_number(self):
        """Validate GST number format if provided."""
        gst = self.cleaned_data.get('gst_number')
        if gst:
            # Remove spaces and convert to uppercase
            gst = gst.strip().upper()
            
            # GST should be 15 characters
            if len(gst) != 15:
                raise ValidationError('GST number must be exactly 15 characters.')
            
            # Basic format validation: 2 digits, 10 alphanumeric, 1 digit, Z, 1 alphanumeric
            # Example: 22AAAAA0000A1Z5
            import re
            pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
            if not re.match(pattern, gst):
                raise ValidationError('Invalid GST number format.')
        
        return gst


class UserUpdateForm(forms.ModelForm):
    """
    Form for updating basic user information.
    
    Separate from Profile form for cleaner UI.
    """
    
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+91-9876543210',
            }),
        }


class CreditLimitForm(forms.ModelForm):
    """
    Form for updating credit limit (Admin/Wholesaler only).
    
    Used when approving ML-suggested credit limits.
    """
    
    class Meta:
        model = Profile
        fields = ['credit_limit']
        widgets = {
            'credit_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 100,
            }),
        }
