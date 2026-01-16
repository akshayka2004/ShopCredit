"""
==============================================================================
ACCOUNTS APP - MODELS
==============================================================================
This module defines the custom User model and Profile for the ShopCredit system.

Key Models:
    - CustomUser: Extended Django user with role-based access (Shop Owner, Wholesaler, Admin)
    - Profile: Business profile with credit-related information

Why Custom User Model?
    Django's default User model doesn't support roles. We extend AbstractUser
    to add a 'role' field that determines what features each user can access.

Author: ShopCredit Development Team
==============================================================================
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class CustomUser(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    
    This model adds role-based access control to differentiate between:
    - Shop Owner: Small business owners who take credit from wholesalers
    - Wholesaler: Distributors who provide credit to shop owners
    - Admin: System administrators with full access
    
    Attributes:
        role (str): User's role in the system (shop_owner/wholesaler/admin)
        phone (str): Contact phone number for communication
        is_verified (bool): Whether the user has been verified by admin
        created_at (datetime): When the account was created
        updated_at (datetime): When the account was last modified
    """
    
    # Role choices - these determine what features each user can access
    ROLE_CHOICES = [
        ('shop_owner', 'Shop Owner'),      # Takes credit, makes purchases
        ('wholesaler', 'Wholesaler'),       # Provides credit, manages inventory
        ('admin', 'Administrator'),         # Full system access
    ]
    
    # Additional fields beyond AbstractUser (username, email, password already included)
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='shop_owner',
        help_text="User's role determines their permissions in the system"
    )
    
    phone = models.CharField(
        max_length=15, 
        blank=True, 
        null=True,
        help_text="Contact phone number (e.g., +91-9876543210)"
    )
    
    is_verified = models.BooleanField(
        default=False,
        help_text="Set to True after admin verifies the user's identity"
    )
    
    # Timestamps for tracking account lifecycle
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']  # Most recent users first
    
    def __str__(self):
        """Return username with role for easy identification in admin."""
        return f"{self.username} ({self.get_role_display()})"
    
    def is_shop_owner(self):
        """Check if user is a shop owner."""
        return self.role == 'shop_owner'
    
    def is_wholesaler(self):
        """Check if user is a wholesaler."""
        return self.role == 'wholesaler'
    
    def is_admin_user(self):
        """Check if user is an administrator."""
        return self.role == 'admin'


class Profile(models.Model):
    """
    Extended profile for business-related information.
    
    This model stores additional details required for credit operations:
    - Business information (name, address, GST)
    - Credit metrics (limit, score, outstanding balance)
    - Risk assessment data
    
    The Profile is automatically created when a CustomUser is registered.
    
    Attributes:
        user (OneToOne): Link to the CustomUser
        business_name (str): Name of the business/shop
        business_address (str): Physical location of the business
        gst_number (str): GST registration number (if applicable)
        credit_limit (Decimal): Maximum credit amount allowed
        current_outstanding (Decimal): Current unpaid credit amount
        credit_score (int): Internal credit score (0-1000)
        risk_category (str): Risk classification (low/medium/high)
        created_by (ForeignKey): Admin/Wholesaler who created this profile
    """
    
    # Risk category choices based on ML predictions
    RISK_CHOICES = [
        ('low', 'Low Risk'),           # < 20% default probability
        ('medium', 'Medium Risk'),      # 20-50% default probability
        ('high', 'High Risk'),          # > 50% default probability
    ]
    
    # One-to-one relationship with CustomUser
    # When user is deleted, profile is also deleted (CASCADE)
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='profile',
        help_text="The user this profile belongs to"
    )
    
    # Business Information
    business_name = models.CharField(
        max_length=200, 
        blank=True,
        help_text="Registered name of the business"
    )
    
    business_address = models.TextField(
        blank=True,
        help_text="Complete physical address of the business"
    )
    
    gst_number = models.CharField(
        max_length=15, 
        blank=True, 
        null=True,
        help_text="GST registration number (15 characters)"
    )
    
    # Credit-related fields - these are crucial for the Udhaar system
    credit_limit = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Maximum credit amount this user can take (in INR)"
    )
    
    current_outstanding = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Current unpaid credit balance (in INR)"
    )
    
    # Credit score: Internal scoring system (0-1000, higher is better)
    credit_score = models.IntegerField(
        default=500,
        validators=[MinValueValidator(0), MaxValueValidator(1000)],
        help_text="Internal credit score (0-1000). 500 is average."
    )
    
    risk_category = models.CharField(
        max_length=10, 
        choices=RISK_CHOICES, 
        default='medium',
        help_text="Risk classification based on ML predictions"
    )
    
    # Who created/manages this profile (useful for wholesaler tracking)
    created_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_profiles',
        help_text="Admin or Wholesaler who created this profile"
    )
    
    # Profile picture (optional)
    profile_picture = models.ImageField(
        upload_to='profile_pics/', 
        blank=True, 
        null=True,
        help_text="Profile photo for identification"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Profile'
        verbose_name_plural = 'Profiles'
        ordering = ['-created_at']
    
    def __str__(self):
        """Return business name or username."""
        return self.business_name if self.business_name else self.user.username
    
    def available_credit(self):
        """
        Calculate remaining available credit.
        
        Returns:
            Decimal: Credit limit minus current outstanding balance
        """
        return self.credit_limit - self.current_outstanding
    
    def credit_utilization_percentage(self):
        """
        Calculate credit utilization as a percentage.
        
        Used for ML features and dashboard displays.
        
        Returns:
            float: Percentage of credit limit currently used (0-100)
        """
        if self.credit_limit == 0:
            return 0.0
        return float((self.current_outstanding / self.credit_limit) * 100)
    
    def update_risk_category(self, default_probability):
        """
        Update risk category based on ML-predicted default probability.
        
        Args:
            default_probability (float): Probability of default (0.0 to 1.0)
        """
        if default_probability < 0.2:
            self.risk_category = 'low'
        elif default_probability < 0.5:
            self.risk_category = 'medium'
        else:
            self.risk_category = 'high'
        self.save()


# =============================================================================
# Django Signals for automatic Profile creation
# =============================================================================
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create a Profile when a new CustomUser is created.
    
    This signal ensures every user has an associated profile without
    requiring manual creation.
    """
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    """
    Automatically save the Profile when the CustomUser is saved.
    
    This ensures profile data stays in sync with user data.
    """
    # Only save if profile exists (prevents errors during initial migration)
    if hasattr(instance, 'profile'):
        instance.profile.save()
