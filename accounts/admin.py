"""
==============================================================================
ACCOUNTS APP - ADMIN CONFIGURATION
==============================================================================
Register Custom User and Profile models with Django Admin interface.

This provides a user-friendly interface for managing users through the
admin panel at /admin/.

Author: ShopCredit Development Team
==============================================================================
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Profile


class ProfileInline(admin.StackedInline):
    """
    Display Profile information inline when editing a User.
    
    This allows admins to edit user and profile data on the same page.
    """
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    
    # Fields to display
    fieldsets = (
        ('Business Information', {
            'fields': ('business_name', 'business_address', 'gst_number')
        }),
        ('Credit Information', {
            'fields': ('credit_limit', 'current_outstanding', 'credit_score', 'risk_category')
        }),
        ('Profile Picture', {
            'fields': ('profile_picture',),
            'classes': ('collapse',)  # Collapsible section
        }),
    )


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Custom admin configuration for CustomUser model.
    
    Extends Django's built-in UserAdmin to include our custom fields.
    """
    
    # Fields to display in the list view
    list_display = ('username', 'email', 'role', 'phone', 'is_verified', 
                    'is_active', 'date_joined')
    
    # Fields that can be clicked to edit
    list_display_links = ('username', 'email')
    
    # Filters in the right sidebar
    list_filter = ('role', 'is_verified', 'is_active', 'is_staff', 'date_joined')
    
    # Fields that can be searched
    search_fields = ('username', 'email', 'phone', 'first_name', 'last_name')
    
    # Default ordering
    ordering = ('-date_joined',)
    
    # Include Profile inline
    inlines = [ProfileInline]
    
    # Organize fields into logical sections
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        ('Role & Verification', {
            'fields': ('role', 'is_verified'),
            'description': 'Role determines what features the user can access.'
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)  # Collapsible section
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    # Fields shown when adding a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role', 'phone')
        }),
    )
    
    # Actions available in list view
    actions = ['verify_users', 'unverify_users']
    
    @admin.action(description='Verify selected users')
    def verify_users(self, request, queryset):
        """Bulk action to verify multiple users at once."""
        count = queryset.update(is_verified=True)
        self.message_user(request, f'{count} users have been verified.')
    
    @admin.action(description='Unverify selected users')
    def unverify_users(self, request, queryset):
        """Bulk action to unverify multiple users."""
        count = queryset.update(is_verified=False)
        self.message_user(request, f'{count} users have been unverified.')


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """
    Admin configuration for Profile model.
    
    Provides a separate view for managing profiles if needed.
    """
    
    list_display = ('user', 'business_name', 'credit_limit', 'current_outstanding', 
                    'credit_score', 'risk_category', 'created_at')
    
    list_filter = ('risk_category', 'created_at')
    
    search_fields = ('user__username', 'business_name', 'gst_number')
    
    ordering = ('-created_at',)
    
    # Read-only fields that shouldn't be edited directly
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Business Information', {
            'fields': ('business_name', 'business_address', 'gst_number', 'profile_picture')
        }),
        ('Credit Information', {
            'fields': ('credit_limit', 'current_outstanding', 'credit_score', 'risk_category')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
