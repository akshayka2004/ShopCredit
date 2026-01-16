"""
==============================================================================
ANALYTICS APP - MODELS
==============================================================================
This module defines ML-related models for the ShopCredit intelligent system.

Key Models:
    - RiskPrediction: Stores default probability predictions (Random Forest)
    - CreditLimitSuggestion: ML-suggested credit limits (Linear Regression)
    - ShopSegment: K-Means clustering results for shop segmentation
    - MLModelMetadata: Tracks trained model versions and performance

Why These ML Algorithms?
    
    1. Random Forest for Default Prediction:
       - Handles non-linear relationships between features
       - Robust to outliers and missing values
       - Provides feature importance for explainability
       - Works well with imbalanced datasets (defaults are rare)
    
    2. Linear Regression for Credit Limit:
       - Clear, interpretable relationship between features and limit
       - Easy to explain to business stakeholders
       - Fast prediction for real-time use
       - Good baseline for this regression problem
    
    3. K-Means for Shop Segmentation:
       - Unsupervised - doesn't need labeled data
       - Groups shops by behavior patterns
       - Useful for targeted marketing and risk tiers
       - Easy to visualize and understand

Author: ShopCredit Development Team
==============================================================================
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from accounts.models import CustomUser


class RiskPrediction(models.Model):
    """
    Stores default probability predictions for shop owners.
    
    The Random Forest model analyzes various features to predict the
    probability that a shop owner will default on their credit.
    
    Features Used (from shop owner's history):
        - Payment history (on-time vs late payments)
        - Credit utilization percentage
        - Order frequency
        - Average order value
        - Account age
        - Previous defaults (if any)
    
    Attributes:
        user (FK): Shop owner being assessed
        default_probability (float): Probability of default (0.0 to 1.0)
        risk_category (str): Derived category (low/medium/high)
        feature_data (JSON): Snapshot of features used for prediction
        model_version (str): Version of ML model used
        confidence_score (float): Model's confidence in prediction
    """
    
    RISK_CHOICES = [
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
    ]
    
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE,
        related_name='risk_predictions',
        help_text="Shop owner being assessed"
    )
    
    # Core prediction output
    default_probability = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Probability of default (0.0 = no risk, 1.0 = certain default)"
    )
    
    risk_category = models.CharField(
        max_length=10, 
        choices=RISK_CHOICES,
        help_text="Risk category derived from probability"
    )
    
    # Feature snapshot for explainability and auditing
    # Stored as JSON for flexibility
    feature_data = models.JSONField(
        default=dict,
        help_text="Snapshot of features used for this prediction"
    )
    
    # Model metadata
    model_version = models.CharField(
        max_length=50,
        help_text="Version of the ML model used (e.g., rf_v1.0)"
    )
    
    confidence_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        default=0.8,
        help_text="Model's confidence in this prediction"
    )
    
    # Timestamps
    prediction_date = models.DateTimeField(auto_now_add=True)
    
    # Is this the current/active prediction for this user?
    is_current = models.BooleanField(
        default=True,
        help_text="True if this is the latest prediction for this user"
    )
    
    class Meta:
        verbose_name = 'Risk Prediction'
        verbose_name_plural = 'Risk Predictions'
        ordering = ['-prediction_date']
    
    def __str__(self):
        return f"{self.user.username} - {self.risk_category} ({self.default_probability:.2%})"
    
    def save(self, *args, **kwargs):
        """
        Derive risk category from probability and mark previous predictions as non-current.
        """
        # Derive risk category
        if self.default_probability < 0.2:
            self.risk_category = 'low'
        elif self.default_probability < 0.5:
            self.risk_category = 'medium'
        else:
            self.risk_category = 'high'
        
        # Mark previous predictions as non-current
        if self.is_current:
            RiskPrediction.objects.filter(
                user=self.user, 
                is_current=True
            ).update(is_current=False)
        
        super().save(*args, **kwargs)
    
    def get_risk_color(self):
        """
        Return Bootstrap color class for risk level.
        
        Returns:
            str: Bootstrap color class (success/warning/danger)
        """
        color_map = {
            'low': 'success',
            'medium': 'warning',
            'high': 'danger'
        }
        return color_map.get(self.risk_category, 'secondary')


class CreditLimitSuggestion(models.Model):
    """
    ML-suggested credit limits using Linear Regression.
    
    The model analyzes shop owner's profile and history to suggest
    an appropriate credit limit.
    
    Features Used:
        - Business type and size
        - Monthly revenue (estimated)
        - Payment history score
        - Account age
        - Current credit utilization
        - Risk score
    
    Why Linear Regression?
        - Credit limit has a roughly linear relationship with income/revenue
        - Interpretable: "For every ₹10,000 in monthly sales, add ₹5,000 to limit"
        - Fast to compute for real-time suggestions
        - Easy to explain coefficients to business stakeholders
    
    Attributes:
        user (FK): Shop owner being assessed
        suggested_limit (Decimal): ML-suggested credit limit
        current_limit (Decimal): Current assigned limit
        feature_data (JSON): Features used for suggestion
        model_version (str): Version of ML model
        is_approved (bool): Whether wholesaler approved this suggestion
    """
    
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE,
        related_name='credit_suggestions',
        help_text="Shop owner being assessed"
    )
    
    # Suggestion output
    suggested_limit = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="ML-suggested credit limit in INR"
    )
    
    # Current limit for comparison
    current_limit = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Current assigned credit limit"
    )
    
    # Difference for easy display
    limit_difference = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Difference: suggested - current"
    )
    
    # Feature snapshot
    feature_data = models.JSONField(
        default=dict,
        help_text="Features used for this suggestion"
    )
    
    # Model metadata
    model_version = models.CharField(
        max_length=50,
        help_text="Version of the ML model used"
    )
    
    confidence_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        default=0.8,
        help_text="Model's confidence in this suggestion"
    )
    
    # Approval workflow
    is_approved = models.BooleanField(
        default=False,
        help_text="Whether this suggestion was approved"
    )
    
    approved_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='approved_suggestions',
        help_text="Wholesaler who approved this suggestion"
    )
    
    approved_limit = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        null=True, 
        blank=True,
        help_text="Actual approved limit (may differ from suggestion)"
    )
    
    # Timestamps
    suggestion_date = models.DateTimeField(auto_now_add=True)
    approval_date = models.DateTimeField(null=True, blank=True)
    
    is_current = models.BooleanField(
        default=True,
        help_text="True if this is the latest suggestion"
    )
    
    class Meta:
        verbose_name = 'Credit Limit Suggestion'
        verbose_name_plural = 'Credit Limit Suggestions'
        ordering = ['-suggestion_date']
    
    def __str__(self):
        status = "✓ Approved" if self.is_approved else "⏳ Pending"
        return f"{self.user.username} - ₹{self.suggested_limit} ({status})"
    
    def save(self, *args, **kwargs):
        """Calculate limit difference before saving."""
        self.limit_difference = self.suggested_limit - self.current_limit
        
        # Mark previous suggestions as non-current
        if self.is_current:
            CreditLimitSuggestion.objects.filter(
                user=self.user, 
                is_current=True
            ).update(is_current=False)
        
        super().save(*args, **kwargs)
    
    def get_recommendation(self):
        """
        Get a text recommendation based on limit difference.
        
        Returns:
            str: Recommendation text
        """
        if self.limit_difference > 0:
            return f"Increase limit by ₹{self.limit_difference:,.2f}"
        elif self.limit_difference < 0:
            return f"Decrease limit by ₹{abs(self.limit_difference):,.2f}"
        else:
            return "Current limit is appropriate"


class ShopSegment(models.Model):
    """
    K-Means clustering results for shop segmentation.
    
    Shops are grouped into segments based on their behavior patterns.
    This helps in:
        - Targeted marketing campaigns
        - Risk-based pricing
        - Personalized credit offers
        - Churn prediction
    
    Typical Segments:
        1. "High Value Regular" - High order value, consistent payments
        2. "Growing Business" - Increasing order frequency
        3. "At Risk" - Declining payments, irregular orders
        4. "New Customer" - Limited history
        5. "Dormant" - Low recent activity
    
    Features Used for Clustering:
        - Average order value
        - Order frequency
        - Payment consistency score
        - Credit utilization
        - Account age
        - Growth rate
    
    Why K-Means?
        - Unsupervised learning - no labeled data needed
        - Creates natural groupings based on behavior
        - Easy to interpret cluster centers
        - Efficient for medium-sized datasets
    """
    
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE,
        related_name='shop_segments',
        help_text="Shop owner being segmented"
    )
    
    # Cluster assignment
    cluster_id = models.IntegerField(
        help_text="Cluster number (0, 1, 2, ...)"
    )
    
    cluster_name = models.CharField(
        max_length=100,
        help_text="Human-readable segment name"
    )
    
    cluster_description = models.TextField(
        blank=True,
        help_text="Description of this segment's characteristics"
    )
    
    # Distance from cluster center (lower = more representative)
    distance_to_center = models.FloatField(
        validators=[MinValueValidator(0.0)],
        help_text="Distance from cluster center (lower = better fit)"
    )
    
    # Feature snapshot
    feature_data = models.JSONField(
        default=dict,
        help_text="Features used for clustering"
    )
    
    # Cluster characteristics (center values)
    cluster_center = models.JSONField(
        default=dict,
        help_text="Cluster center values (mean of all features)"
    )
    
    # Model metadata
    model_version = models.CharField(
        max_length=50,
        help_text="Version of the K-Means model"
    )
    
    # Timestamps
    segmentation_date = models.DateTimeField(auto_now_add=True)
    
    is_current = models.BooleanField(
        default=True,
        help_text="True if this is the latest segmentation"
    )
    
    class Meta:
        verbose_name = 'Shop Segment'
        verbose_name_plural = 'Shop Segments'
        ordering = ['-segmentation_date']
    
    def __str__(self):
        return f"{self.user.username} - {self.cluster_name}"
    
    def save(self, *args, **kwargs):
        """Mark previous segmentations as non-current."""
        if self.is_current:
            ShopSegment.objects.filter(
                user=self.user, 
                is_current=True
            ).update(is_current=False)
        
        super().save(*args, **kwargs)
    
    def get_segment_color(self):
        """
        Return a color for this segment (for visualization).
        
        Returns:
            str: Hex color code
        """
        # Define colors for up to 6 clusters
        colors = [
            '#1a237e',  # Deep Navy
            '#00897b',  # Teal
            '#f57c00',  # Orange
            '#7b1fa2',  # Purple
            '#c62828',  # Red
            '#558b2f',  # Green
        ]
        return colors[self.cluster_id % len(colors)]


class MLModelMetadata(models.Model):
    """
    Tracks trained ML model versions and their performance.
    
    Every time models are retrained, a new record is created here.
    This helps in:
        - Version control for models
        - Performance tracking over time
        - Rollback capability if new model performs poorly
        - Audit trail for compliance
    
    Attributes:
        model_type (str): Type of model (risk/credit_limit/segmentation)
        version (str): Model version identifier
        file_path (str): Path to the .pkl file
        training_date (datetime): When model was trained
        training_samples (int): Number of samples used for training
        accuracy_score (float): Model's accuracy/performance metric
        is_active (bool): Whether this is the currently active model
    """
    
    MODEL_TYPES = [
        ('risk', 'Default Risk (Random Forest)'),
        ('credit_limit', 'Credit Limit (Linear Regression)'),
        ('segmentation', 'Shop Segmentation (K-Means)'),
    ]
    
    model_type = models.CharField(
        max_length=20, 
        choices=MODEL_TYPES,
        help_text="Type of ML model"
    )
    
    version = models.CharField(
        max_length=50,
        help_text="Model version (e.g., v1.0.0)"
    )
    
    file_path = models.CharField(
        max_length=255,
        help_text="Path to the saved .pkl file"
    )
    
    # Training details
    training_date = models.DateTimeField(auto_now_add=True)
    
    training_samples = models.IntegerField(
        help_text="Number of samples used for training"
    )
    
    # Performance metrics (interpretation depends on model type)
    # - Risk: ROC-AUC score
    # - Credit Limit: R² score
    # - Segmentation: Silhouette score
    accuracy_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Performance metric (depends on model type)"
    )
    
    # Additional metrics stored as JSON
    metrics = models.JSONField(
        default=dict,
        help_text="Additional performance metrics"
    )
    
    # Feature list used for training
    features_used = models.JSONField(
        default=list,
        help_text="List of features used for training"
    )
    
    # Hyperparameters
    hyperparameters = models.JSONField(
        default=dict,
        help_text="Model hyperparameters"
    )
    
    # Active status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this is the currently active model"
    )
    
    # Notes about this version
    notes = models.TextField(
        blank=True,
        help_text="Notes about this model version"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'ML Model Metadata'
        verbose_name_plural = 'ML Model Metadata'
        ordering = ['-training_date']
        unique_together = ['model_type', 'version']
    
    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.get_model_type_display()} - {self.version} ({status})"
    
    def save(self, *args, **kwargs):
        """Deactivate other models of the same type when this one is activated."""
        if self.is_active:
            MLModelMetadata.objects.filter(
                model_type=self.model_type, 
                is_active=True
            ).update(is_active=False)
        
        super().save(*args, **kwargs)
