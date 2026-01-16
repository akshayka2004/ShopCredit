"""
==============================================================================
ANALYTICS APP - ADMIN CONFIGURATION
==============================================================================
Register ML-related models with Django Admin interface.

Models registered:
    - RiskPrediction: Default probability predictions
    - CreditLimitSuggestion: ML-suggested credit limits
    - ShopSegment: K-Means clustering results
    - MLModelMetadata: Model version tracking

Author: ShopCredit Development Team
==============================================================================
"""

from django.contrib import admin
from .models import (
    RiskPrediction, CreditLimitSuggestion, 
    ShopSegment, MLModelMetadata
)


@admin.register(RiskPrediction)
class RiskPredictionAdmin(admin.ModelAdmin):
    """Admin configuration for Risk Prediction model."""
    
    list_display = ('user', 'default_probability', 'risk_category', 
                    'confidence_score', 'model_version', 'is_current', 
                    'prediction_date')
    list_filter = ('risk_category', 'is_current', 'model_version', 'prediction_date')
    search_fields = ('user__username',)
    ordering = ('-prediction_date',)
    readonly_fields = ('prediction_date',)
    
    fieldsets = (
        ('Prediction', {
            'fields': ('user', 'default_probability', 'risk_category', 'confidence_score')
        }),
        ('Model Details', {
            'fields': ('model_version', 'feature_data', 'is_current')
        }),
        ('Metadata', {
            'fields': ('prediction_date',),
            'classes': ('collapse',)
        }),
    )


@admin.register(CreditLimitSuggestion)
class CreditLimitSuggestionAdmin(admin.ModelAdmin):
    """Admin configuration for Credit Limit Suggestion model."""
    
    list_display = ('user', 'suggested_limit', 'current_limit', 'limit_difference',
                    'is_approved', 'approved_by', 'suggestion_date')
    list_filter = ('is_approved', 'is_current', 'model_version', 'suggestion_date')
    search_fields = ('user__username',)
    ordering = ('-suggestion_date',)
    readonly_fields = ('suggestion_date', 'limit_difference')
    
    actions = ['approve_suggestions']
    
    @admin.action(description='Approve selected suggestions')
    def approve_suggestions(self, request, queryset):
        from django.utils import timezone
        for suggestion in queryset.filter(is_approved=False):
            suggestion.is_approved = True
            suggestion.approved_by = request.user
            suggestion.approved_limit = suggestion.suggested_limit
            suggestion.approval_date = timezone.now()
            suggestion.save()
            
            # Update user's credit limit
            suggestion.user.profile.credit_limit = suggestion.suggested_limit
            suggestion.user.profile.save()
        
        self.message_user(request, 'Selected suggestions have been approved.')


@admin.register(ShopSegment)
class ShopSegmentAdmin(admin.ModelAdmin):
    """Admin configuration for Shop Segment model."""
    
    list_display = ('user', 'cluster_id', 'cluster_name', 'distance_to_center',
                    'model_version', 'is_current', 'segmentation_date')
    list_filter = ('cluster_id', 'cluster_name', 'is_current', 'model_version')
    search_fields = ('user__username', 'cluster_name')
    ordering = ('-segmentation_date',)
    readonly_fields = ('segmentation_date',)


@admin.register(MLModelMetadata)
class MLModelMetadataAdmin(admin.ModelAdmin):
    """Admin configuration for ML Model Metadata."""
    
    list_display = ('model_type', 'version', 'accuracy_score', 'training_samples',
                    'is_active', 'training_date')
    list_filter = ('model_type', 'is_active', 'training_date')
    search_fields = ('version', 'notes')
    ordering = ('-training_date',)
    readonly_fields = ('training_date', 'created_at')
    
    fieldsets = (
        ('Model Information', {
            'fields': ('model_type', 'version', 'file_path', 'is_active')
        }),
        ('Performance', {
            'fields': ('accuracy_score', 'training_samples', 'metrics')
        }),
        ('Configuration', {
            'fields': ('features_used', 'hyperparameters'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_models']
    
    @admin.action(description='Activate selected models')
    def activate_models(self, request, queryset):
        """Activate selected models (deactivates others of same type)."""
        for model in queryset:
            model.is_active = True
            model.save()  # save() handles deactivating other models of same type
        self.message_user(request, 'Selected models have been activated.')
