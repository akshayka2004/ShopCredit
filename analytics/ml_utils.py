"""
==============================================================================
ANALYTICS APP - ML UTILITIES
==============================================================================
Machine Learning utility functions for ShopCredit.

This module provides:
    1. Data preparation functions
    2. Feature engineering
    3. Model training and saving
    4. Prediction functions

Models:
    - Default Probability: Random Forest Classifier
    - Credit Limit Suggestion: Linear Regression
    - Shop Segmentation: K-Means Clustering

All models are saved as .pkl files in the ml_models/ directory.

Author: ShopCredit Development Team
==============================================================================
"""

import os
import joblib
import pandas as pd
import numpy as np
from datetime import date, timedelta
from decimal import Decimal
from django.conf import settings
from django.db.models import Sum, Count, Avg, F, Q

# Sklearn imports
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_squared_error, silhouette_score


# =============================================================================
# CONSTANTS
# =============================================================================

# Directory for saved models
MODELS_DIR = settings.BASE_DIR / 'ml_models'

# Model filenames
RISK_MODEL_FILE = 'risk_prediction_model.pkl'
CREDIT_MODEL_FILE = 'credit_limit_model.pkl'
SEGMENT_MODEL_FILE = 'shop_segment_model.pkl'
SCALER_FILE = 'feature_scaler.pkl'

# Feature names for consistency
RISK_FEATURES = [
    'credit_utilization',     # Current outstanding / Credit limit
    'payment_delay_avg',      # Average days of payment delay
    'late_payment_ratio',     # Percentage of late payments
    'order_frequency',        # Orders per month
    'total_credit_used',      # Total credit used in lifetime
    'account_age_days',       # Days since registration
    'monthly_revenue',        # Average monthly order value
]

CREDIT_FEATURES = [
    'monthly_revenue',        # Average monthly sales
    'payment_delay_avg',      # Payment behavior
    'account_age_days',       # Length of relationship
    'order_frequency',        # Ordering pattern
    'current_credit_score',   # Existing credit score
]

SEGMENT_FEATURES = [
    'total_orders',           # Total order count
    'total_spent',            # Total amount spent
    'avg_order_value',        # Average order value
    'payment_delay_avg',      # Payment behavior
    'credit_utilization',     # Credit usage pattern
]


# =============================================================================
# DATA PREPARATION FUNCTIONS
# =============================================================================

def get_user_features(user):
    """
    Extract features for a single user.
    
    Args:
        user: CustomUser object (shop_owner)
    
    Returns:
        dict: Dictionary of feature values
    """
    from accounts.models import Profile
    from core.models import Order, EMISchedule, CreditTransaction
    
    profile = user.profile
    today = date.today()
    account_age = (today - user.date_joined.date()).days
    
    # Get all orders for this user
    orders = Order.objects.filter(shop_owner=user)
    total_orders = orders.count()
    
    # Calculate total spent
    total_spent = orders.filter(
        status__in=['completed', 'delivered', 'approved']
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
    
    # Calculate average order value
    avg_order_value = float(total_spent) / max(total_orders, 1)
    
    # Get EMI payment history
    emis = EMISchedule.objects.filter(order__shop_owner=user, is_paid=True)
    total_emis = emis.count()
    late_emis = emis.filter(is_late=True).count()
    
    # Late payment ratio
    late_payment_ratio = late_emis / max(total_emis, 1)
    
    # Average payment delay
    delayed_emis = emis.filter(paid_date__gt=F('due_date'))
    if delayed_emis.exists():
        delays = []
        for emi in delayed_emis:
            if emi.paid_date and emi.due_date:
                delay = (emi.paid_date - emi.due_date).days
                delays.append(max(0, delay))
        payment_delay_avg = sum(delays) / max(len(delays), 1) if delays else 0
    else:
        payment_delay_avg = 0
    
    # Credit utilization
    if profile.credit_limit > 0:
        credit_utilization = float(profile.current_outstanding) / float(profile.credit_limit)
    else:
        credit_utilization = 0
    
    # Order frequency (orders per 30 days)
    recent_orders = orders.filter(
        order_date__gte=today - timedelta(days=30)
    ).count()
    order_frequency = recent_orders
    
    # Monthly revenue (average of last 6 months)
    six_months_ago = today - timedelta(days=180)
    recent_revenue = orders.filter(
        order_date__gte=six_months_ago,
        status__in=['completed', 'delivered', 'approved']
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
    monthly_revenue = float(recent_revenue) / 6
    
    return {
        'user_id': user.id,
        'username': user.username,
        'credit_utilization': credit_utilization,
        'payment_delay_avg': payment_delay_avg,
        'late_payment_ratio': late_payment_ratio,
        'order_frequency': order_frequency,
        'total_credit_used': float(total_spent),
        'account_age_days': account_age,
        'monthly_revenue': monthly_revenue,
        'current_credit_score': profile.credit_score,
        'total_orders': total_orders,
        'total_spent': float(total_spent),
        'avg_order_value': avg_order_value,
    }


def prepare_training_data():
    """
    Prepare training dataset from all shop owners.
    
    Returns:
        pd.DataFrame: DataFrame with all features and labels
    """
    from accounts.models import CustomUser
    
    shop_owners = CustomUser.objects.filter(role='shop_owner')
    
    data = []
    for user in shop_owners:
        features = get_user_features(user)
        
        # Add target variable (is_high_risk) based on current risk category
        features['is_high_risk'] = 1 if user.profile.risk_category == 'high' else 0
        features['is_defaulted'] = 1 if has_defaulted(user) else 0
        
        data.append(features)
    
    return pd.DataFrame(data)


def has_defaulted(user):
    """
    Check if user has any seriously overdue payments (>30 days).
    """
    from core.models import EMISchedule
    
    overdue_emis = EMISchedule.objects.filter(
        order__shop_owner=user,
        is_paid=False,
        due_date__lt=date.today() - timedelta(days=30)
    )
    
    return overdue_emis.exists()


# =============================================================================
# MODEL TRAINING FUNCTIONS
# =============================================================================

def train_risk_model(data=None):
    """
    Train the Default Probability model using Random Forest.
    
    Random Forest is chosen because:
    - Handles non-linear relationships well
    - Robust to outliers
    - Provides feature importance
    - Works well with limited data
    
    Args:
        data: Optional DataFrame, if None will prepare from database
    
    Returns:
        tuple: (model, accuracy, feature_importance)
    """
    if data is None:
        data = prepare_training_data()
    
    if len(data) < 10:
        print("Warning: Not enough data for training. Using synthetic data.")
        data = generate_synthetic_data(100)
    
    # Prepare features and target
    X = data[RISK_FEATURES].fillna(0)
    y = data['is_defaulted']
    
    # Split data
    if len(data) > 20:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
    else:
        X_train, X_test, y_train, y_test = X, X, y, y
    
    # Train Random Forest
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=5,
        min_samples_split=5,
        random_state=42
    )
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    # Feature importance
    feature_importance = dict(zip(RISK_FEATURES, model.feature_importances_))
    
    # Save model
    os.makedirs(MODELS_DIR, exist_ok=True)
    model_path = MODELS_DIR / RISK_MODEL_FILE
    joblib.dump(model, model_path)
    
    print(f"Risk model trained with accuracy: {accuracy:.2%}")
    print(f"Model saved to: {model_path}")
    
    return model, accuracy, feature_importance


def train_credit_model(data=None):
    """
    Train the Credit Limit Suggestion model using Linear Regression.
    
    Linear Regression is chosen because:
    - Highly interpretable (important for financial decisions)
    - Shows clear relationship between features and credit limit
    - Easy to explain to stakeholders
    
    Args:
        data: Optional DataFrame
    
    Returns:
        tuple: (model, mse, coefficients)
    """
    if data is None:
        data = prepare_training_data()
    
    if len(data) < 10:
        print("Warning: Not enough data for training. Using synthetic data.")
        data = generate_synthetic_data(100)
    
    # Target: suggested credit limit based on monthly revenue and behavior
    # A simple heuristic: credit_limit = monthly_revenue * 3 * (1 - late_ratio)
    data['suggested_limit'] = (
        data['monthly_revenue'] * 3 * 
        (1 - data['late_payment_ratio'] * 0.5)
    ).clip(lower=5000)
    
    # Prepare features
    X = data[CREDIT_FEATURES].fillna(0)
    y = data['suggested_limit']
    
    # Split data
    if len(data) > 20:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
    else:
        X_train, X_test, y_train, y_test = X, X, y, y
    
    # Train Linear Regression
    model = LinearRegression()
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    
    # Coefficients
    coefficients = dict(zip(CREDIT_FEATURES, model.coef_))
    
    # Save model
    os.makedirs(MODELS_DIR, exist_ok=True)
    model_path = MODELS_DIR / CREDIT_MODEL_FILE
    joblib.dump(model, model_path)
    
    print(f"Credit model trained with MSE: {mse:.2f}")
    print(f"Model saved to: {model_path}")
    
    return model, mse, coefficients


def train_segment_model(data=None, n_clusters=4):
    """
    Train the Shop Segmentation model using K-Means Clustering.
    
    K-Means is chosen because:
    - Unsupervised: discovers natural customer segments
    - Easy to visualize and interpret
    - Scalable to large datasets
    
    Typical segments:
    - Cluster 0: "Low Activity" - Few orders, low spending
    - Cluster 1: "Regular" - Moderate activity, good payment
    - Cluster 2: "High Value" - High spending, good behavior
    - Cluster 3: "At Risk" - High activity but payment issues
    
    Args:
        data: Optional DataFrame
        n_clusters: Number of segments
    
    Returns:
        tuple: (model, scaler, silhouette, cluster_centers)
    """
    if data is None:
        data = prepare_training_data()
    
    if len(data) < 10:
        print("Warning: Not enough data for training. Using synthetic data.")
        data = generate_synthetic_data(100)
    
    # Prepare features
    X = data[SEGMENT_FEATURES].fillna(0)
    
    # Standardize features (important for K-Means)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Train K-Means
    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    model.fit(X_scaled)
    
    # Evaluate
    if len(data) >= n_clusters:
        silhouette = silhouette_score(X_scaled, model.labels_)
    else:
        silhouette = 0
    
    # Cluster centers (inverse transform for interpretation)
    centers = scaler.inverse_transform(model.cluster_centers_)
    cluster_centers = pd.DataFrame(centers, columns=SEGMENT_FEATURES)
    
    # Save model and scaler
    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump(model, MODELS_DIR / SEGMENT_MODEL_FILE)
    joblib.dump(scaler, MODELS_DIR / SCALER_FILE)
    
    print(f"Segment model trained with silhouette score: {silhouette:.3f}")
    print(f"Model saved to: {MODELS_DIR / SEGMENT_MODEL_FILE}")
    
    return model, scaler, silhouette, cluster_centers


def generate_synthetic_data(n_samples=100):
    """
    Generate synthetic training data when real data is insufficient.
    
    This is useful for:
    - Initial model training
    - Testing the ML pipeline
    - Demo purposes
    
    Args:
        n_samples: Number of synthetic samples
    
    Returns:
        pd.DataFrame: Synthetic dataset
    """
    np.random.seed(42)
    
    data = pd.DataFrame({
        'user_id': range(1, n_samples + 1),
        'credit_utilization': np.random.uniform(0, 1, n_samples),
        'payment_delay_avg': np.random.exponential(5, n_samples),
        'late_payment_ratio': np.random.uniform(0, 0.5, n_samples),
        'order_frequency': np.random.poisson(3, n_samples),
        'total_credit_used': np.random.uniform(10000, 500000, n_samples),
        'account_age_days': np.random.randint(30, 730, n_samples),
        'monthly_revenue': np.random.uniform(5000, 100000, n_samples),
        'current_credit_score': np.random.randint(300, 900, n_samples),
        'total_orders': np.random.poisson(10, n_samples),
        'total_spent': np.random.uniform(10000, 500000, n_samples),
        'avg_order_value': np.random.uniform(500, 10000, n_samples),
    })
    
    # Generate is_defaulted based on features (logical rules)
    data['is_defaulted'] = (
        (data['late_payment_ratio'] > 0.3) & 
        (data['payment_delay_avg'] > 10)
    ).astype(int)
    
    data['is_high_risk'] = (
        (data['credit_utilization'] > 0.8) |
        (data['late_payment_ratio'] > 0.25)
    ).astype(int)
    
    return data


# =============================================================================
# PREDICTION FUNCTIONS
# =============================================================================

def predict_default_risk(user):
    """
    Predict default probability for a user.
    
    Args:
        user: CustomUser object
    
    Returns:
        dict: {
            'probability': float (0-1),
            'risk_category': str ('low', 'medium', 'high'),
            'confidence': float (0-1),
            'features': dict
        }
    """
    model_path = MODELS_DIR / RISK_MODEL_FILE
    
    if not os.path.exists(model_path):
        # Return heuristic-based prediction if model not trained
        return predict_default_risk_heuristic(user)
    
    model = joblib.load(model_path)
    
    # Get user features
    features = get_user_features(user)
    X = pd.DataFrame([{k: features[k] for k in RISK_FEATURES}])
    X = X.fillna(0)
    
    # Predict
    probability = model.predict_proba(X)[0][1]  # Probability of class 1 (default)
    
    # Determine risk category
    if probability < 0.2:
        risk_category = 'low'
    elif probability < 0.5:
        risk_category = 'medium'
    else:
        risk_category = 'high'
    
    # Confidence is based on the max probability
    confidence = max(model.predict_proba(X)[0])
    
    return {
        'probability': float(probability),
        'risk_category': risk_category,
        'confidence': float(confidence),
        'features': features,
    }


def predict_default_risk_heuristic(user):
    """
    Heuristic-based risk prediction when ML model is not available.
    """
    features = get_user_features(user)
    
    # Simple scoring logic
    risk_score = 0
    
    if features['credit_utilization'] > 0.8:
        risk_score += 30
    elif features['credit_utilization'] > 0.5:
        risk_score += 15
    
    if features['late_payment_ratio'] > 0.3:
        risk_score += 35
    elif features['late_payment_ratio'] > 0.1:
        risk_score += 15
    
    if features['payment_delay_avg'] > 15:
        risk_score += 25
    elif features['payment_delay_avg'] > 7:
        risk_score += 10
    
    probability = min(risk_score / 100, 1.0)
    
    if probability < 0.2:
        risk_category = 'low'
    elif probability < 0.5:
        risk_category = 'medium'
    else:
        risk_category = 'high'
    
    return {
        'probability': probability,
        'risk_category': risk_category,
        'confidence': 0.7,  # Lower confidence for heuristic
        'features': features,
    }


def suggest_credit_limit(user):
    """
    Suggest credit limit for a user.
    
    Args:
        user: CustomUser object
    
    Returns:
        dict: {
            'suggested_limit': Decimal,
            'current_limit': Decimal,
            'difference': Decimal,
            'factors': dict
        }
    """
    model_path = MODELS_DIR / CREDIT_MODEL_FILE
    
    features = get_user_features(user)
    current_limit = user.profile.credit_limit
    
    if not os.path.exists(model_path):
        # Heuristic-based suggestion
        suggested = max(
            features['monthly_revenue'] * 2 * (1 - features['late_payment_ratio']),
            5000
        )
    else:
        model = joblib.load(model_path)
        X = pd.DataFrame([{k: features[k] for k in CREDIT_FEATURES}])
        X = X.fillna(0)
        suggested = max(model.predict(X)[0], 5000)
    
    suggested_limit = Decimal(str(round(suggested, -2)))  # Round to nearest 100
    
    return {
        'suggested_limit': suggested_limit,
        'current_limit': current_limit,
        'difference': suggested_limit - current_limit,
        'factors': {
            'monthly_revenue': features['monthly_revenue'],
            'payment_behavior': 1 - features['late_payment_ratio'],
            'account_age': features['account_age_days'],
        }
    }


def get_customer_segment(user):
    """
    Get the customer segment for a user.
    
    Args:
        user: CustomUser object
    
    Returns:
        dict: {
            'cluster_id': int,
            'cluster_name': str,
            'distance_to_center': float,
            'segment_description': str
        }
    """
    model_path = MODELS_DIR / SEGMENT_MODEL_FILE
    scaler_path = MODELS_DIR / SCALER_FILE
    
    features = get_user_features(user)
    
    # Default segment names
    SEGMENT_NAMES = {
        0: 'Low Activity',
        1: 'Regular',
        2: 'High Value',
        3: 'At Risk'
    }
    
    SEGMENT_DESCRIPTIONS = {
        0: 'New or inactive customers with few orders',
        1: 'Regular customers with steady ordering pattern',
        2: 'High-value customers with large orders and good payment history',
        3: 'Active customers with potential payment issues'
    }
    
    if not os.path.exists(model_path):
        # Heuristic-based segmentation
        if features['total_orders'] < 3:
            cluster_id = 0
        elif features['late_payment_ratio'] > 0.2:
            cluster_id = 3
        elif features['avg_order_value'] > 5000:
            cluster_id = 2
        else:
            cluster_id = 1
        
        return {
            'cluster_id': cluster_id,
            'cluster_name': SEGMENT_NAMES.get(cluster_id, f'Segment {cluster_id}'),
            'distance_to_center': 0,
            'segment_description': SEGMENT_DESCRIPTIONS.get(cluster_id, ''),
        }
    
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    
    X = pd.DataFrame([{k: features[k] for k in SEGMENT_FEATURES}])
    X = X.fillna(0)
    X_scaled = scaler.transform(X)
    
    cluster_id = model.predict(X_scaled)[0]
    
    # Calculate distance to cluster center
    center = model.cluster_centers_[cluster_id]
    distance = np.linalg.norm(X_scaled[0] - center)
    
    return {
        'cluster_id': int(cluster_id),
        'cluster_name': SEGMENT_NAMES.get(cluster_id, f'Segment {cluster_id}'),
        'distance_to_center': float(distance),
        'segment_description': SEGMENT_DESCRIPTIONS.get(cluster_id, ''),
    }


# =============================================================================
# DATABASE UPDATE FUNCTIONS
# =============================================================================

def update_all_predictions():
    """
    Update predictions for all shop owners and save to database.
    
    This should be run periodically (e.g., daily) to keep predictions fresh.
    """
    from accounts.models import CustomUser, Profile
    from analytics.models import RiskPrediction, CreditLimitSuggestion, ShopSegment
    
    shop_owners = CustomUser.objects.filter(role='shop_owner')
    
    for user in shop_owners:
        # Risk Prediction
        risk_result = predict_default_risk(user)
        RiskPrediction.objects.update_or_create(
            user=user,
            is_current=True,
            defaults={
                'default_probability': Decimal(str(risk_result['probability'])),
                'risk_category': risk_result['risk_category'],
                'feature_data': risk_result['features'],
                'confidence_score': Decimal(str(risk_result['confidence'])),
            }
        )
        
        # Update profile risk category
        user.profile.risk_category = risk_result['risk_category']
        user.profile.save()
        
        # Credit Limit Suggestion
        credit_result = suggest_credit_limit(user)
        CreditLimitSuggestion.objects.create(
            user=user,
            suggested_limit=credit_result['suggested_limit'],
            current_limit=credit_result['current_limit'],
            limit_difference=credit_result['difference'],
            feature_data=credit_result['factors'],
        )
        
        # Shop Segment
        segment_result = get_customer_segment(user)
        ShopSegment.objects.update_or_create(
            user=user,
            is_current=True,
            defaults={
                'cluster_id': segment_result['cluster_id'],
                'cluster_name': segment_result['cluster_name'],
                'distance_to_center': Decimal(str(segment_result['distance_to_center'])),
            }
        )
    
    print(f"Updated predictions for {shop_owners.count()} shop owners")
