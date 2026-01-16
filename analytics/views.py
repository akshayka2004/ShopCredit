"""
==============================================================================
ANALYTICS APP - VIEWS
==============================================================================
Views for ML analytics dashboard, risk predictions, credit suggestions,
and shop segmentation.

Features:
    - Interactive analytics dashboard
    - Real-time risk predictions
    - Credit limit suggestions with approval workflow
    - Customer segmentation visualization
    - Chart.js data API endpoints

Author: ShopCredit Development Team
==============================================================================
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

from .models import RiskPrediction, CreditLimitSuggestion, ShopSegment, MLModelMetadata
from .ml_utils import (
    predict_default_risk, 
    suggest_credit_limit, 
    get_customer_segment,
    update_all_predictions
)
from accounts.models import CustomUser, Profile
from core.models import Order, EMISchedule, CreditTransaction


# =============================================================================
# DASHBOARD VIEW
# =============================================================================

@login_required
def analytics_dashboard(request):
    """
    Main analytics dashboard with overview charts.
    
    Shows:
    - Risk distribution (pie chart)
    - Repayment trends (line chart)
    - Credit utilization (bar chart)
    - Segment distribution (doughnut chart)
    """
    user = request.user
    
    # Get aggregate statistics
    if user.role == 'admin':
        profiles = Profile.objects.all()
        orders = Order.objects.all()
    elif user.role == 'wholesaler':
        profiles = Profile.objects.filter(user__orders_placed__wholesaler=user).distinct()
        orders = Order.objects.filter(wholesaler=user)
    else:
        profiles = Profile.objects.filter(user=user)
        orders = Order.objects.filter(shop_owner=user)
    
    # Risk distribution
    risk_counts = {
        'low': profiles.filter(risk_category='low').count(),
        'medium': profiles.filter(risk_category='medium').count(),
        'high': profiles.filter(risk_category='high').count(),
    }
    
    # Credit utilization stats
    credit_stats = profiles.aggregate(
        total_limit=Sum('credit_limit'),
        total_outstanding=Sum('current_outstanding'),
        avg_score=Avg('credit_score')
    )
    
    # Order stats
    order_stats = {
        'total': orders.count(),
        'pending': orders.filter(status='pending').count(),
        'approved': orders.filter(status='approved').count(),
        'completed': orders.filter(status='completed').count(),
    }
    
    # EMI stats
    if user.role == 'shop_owner':
        emis = EMISchedule.objects.filter(order__shop_owner=user)
    elif user.role == 'wholesaler':
        emis = EMISchedule.objects.filter(order__wholesaler=user)
    else:
        emis = EMISchedule.objects.all()
    
    emi_stats = {
        'total': emis.count(),
        'paid': emis.filter(is_paid=True).count(),
        'pending': emis.filter(is_paid=False).count(),
        'overdue': emis.filter(is_paid=False, due_date__lt=date.today()).count(),
    }
    
    # ML Model status
    models_status = {}
    for model_type in ['risk_prediction', 'credit_limit', 'shop_segment']:
        latest = MLModelMetadata.objects.filter(
            model_type=model_type, is_active=True
        ).first()
        models_status[model_type] = latest
    
    context = {
        'title': 'Analytics Dashboard',
        'risk_counts': risk_counts,
        'credit_stats': credit_stats,
        'order_stats': order_stats,
        'emi_stats': emi_stats,
        'models_status': models_status,
    }
    
    return render(request, 'analytics/dashboard.html', context)


# =============================================================================
# RISK PREDICTION VIEWS
# =============================================================================

@login_required
def risk_overview(request):
    """
    Overview of all risk predictions.
    
    Shows list of users with their risk categories and default probabilities.
    """
    user = request.user
    
    if user.role == 'shop_owner':
        # Shop owners only see their own risk
        return redirect('analytics:risk_detail', pk=user.pk)
    
    # Get all shop owners with their predictions
    if user.role == 'wholesaler':
        shop_owners = CustomUser.objects.filter(
            role='shop_owner',
            orders_placed__wholesaler=user
        ).distinct()
    else:
        shop_owners = CustomUser.objects.filter(role='shop_owner')
    
    # Get latest predictions
    predictions = []
    for owner in shop_owners:
        pred = RiskPrediction.objects.filter(user=owner, is_current=True).first()
        predictions.append({
            'user': owner,
            'prediction': pred,
        })
    
    # Sort by risk category (high first)
    risk_order = {'high': 0, 'medium': 1, 'low': 2}
    predictions.sort(key=lambda x: risk_order.get(x['user'].profile.risk_category, 3))
    
    context = {
        'title': 'Risk Assessment',
        'predictions': predictions,
    }
    
    return render(request, 'analytics/risk_overview.html', context)


@login_required
def risk_detail(request, pk):
    """
    Detailed risk analysis for a specific user.
    """
    target_user = get_object_or_404(CustomUser, pk=pk)
    
    # Access control
    user = request.user
    if user.role == 'shop_owner' and target_user != user:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')
    
    # Get or create prediction
    result = predict_default_risk(target_user)
    
    # Get prediction history
    history = RiskPrediction.objects.filter(user=target_user).order_by('-prediction_date')[:10]
    
    context = {
        'title': f'Risk Analysis - {target_user.username}',
        'target_user': target_user,
        'prediction': result,
        'history': history,
    }
    
    return render(request, 'analytics/risk_detail.html', context)


@login_required
def risk_predict(request, pk):
    """
    Run a fresh risk prediction for a user.
    """
    target_user = get_object_or_404(CustomUser, pk=pk)
    
    if request.user.role not in ['admin', 'wholesaler']:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')
    
    # Run prediction
    result = predict_default_risk(target_user)
    
    # Save to database
    RiskPrediction.objects.filter(user=target_user, is_current=True).update(is_current=False)
    RiskPrediction.objects.create(
        user=target_user,
        default_probability=Decimal(str(result['probability'])),
        risk_category=result['risk_category'],
        feature_data=result['features'],
        confidence_score=Decimal(str(result['confidence'])),
        is_current=True
    )
    
    # Update profile
    target_user.profile.risk_category = result['risk_category']
    target_user.profile.save()
    
    messages.success(request, f'Risk prediction updated for {target_user.username}')
    return redirect('analytics:risk_detail', pk=pk)


# =============================================================================
# CREDIT LIMIT VIEWS
# =============================================================================

@login_required
def credit_overview(request):
    """
    Overview of credit limit suggestions.
    """
    user = request.user
    
    if user.role == 'shop_owner':
        return redirect('analytics:credit_detail', pk=user.pk)
    
    # Get pending suggestions
    if user.role == 'wholesaler':
        suggestions = CreditLimitSuggestion.objects.filter(
            user__orders_placed__wholesaler=user,
            is_approved=False
        ).distinct().order_by('-suggestion_date')
    else:
        suggestions = CreditLimitSuggestion.objects.filter(
            is_approved=False
        ).order_by('-suggestion_date')
    
    context = {
        'title': 'Credit Limit Suggestions',
        'suggestions': suggestions[:20],
    }
    
    return render(request, 'analytics/credit_overview.html', context)


@login_required  
def credit_detail(request, pk):
    """
    Detailed credit analysis for a specific user.
    """
    target_user = get_object_or_404(CustomUser, pk=pk)
    
    user = request.user
    if user.role == 'shop_owner' and target_user != user:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')
    
    # Get suggestion
    result = suggest_credit_limit(target_user)
    
    # Get suggestion history
    history = CreditLimitSuggestion.objects.filter(user=target_user).order_by('-suggestion_date')[:10]
    
    context = {
        'title': f'Credit Analysis - {target_user.username}',
        'target_user': target_user,
        'suggestion': result,
        'history': history,
    }
    
    return render(request, 'analytics/credit_detail.html', context)


@login_required
def credit_suggest(request, pk):
    """
    Generate a new credit limit suggestion.
    """
    target_user = get_object_or_404(CustomUser, pk=pk)
    
    if request.user.role not in ['admin', 'wholesaler']:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')
    
    result = suggest_credit_limit(target_user)
    
    CreditLimitSuggestion.objects.create(
        user=target_user,
        suggested_limit=result['suggested_limit'],
        current_limit=result['current_limit'],
        limit_difference=result['difference'],
        feature_data=result['factors'],
    )
    
    messages.success(request, f'Credit limit suggestion created for {target_user.username}')
    return redirect('analytics:credit_detail', pk=pk)


@login_required
def credit_approve(request, suggestion_id):
    """
    Approve a credit limit suggestion.
    """
    suggestion = get_object_or_404(CreditLimitSuggestion, pk=suggestion_id)
    
    if request.user.role not in ['admin', 'wholesaler']:
        messages.error(request, 'Access denied.')
        return redirect('analytics:credit_overview')
    
    if request.method == 'POST':
        # Apply the new credit limit
        suggestion.user.profile.credit_limit = suggestion.suggested_limit
        suggestion.user.profile.save()
        
        suggestion.is_approved = True
        suggestion.approved_by = request.user
        suggestion.save()
        
        messages.success(
            request, 
            f'Credit limit updated to ₹{suggestion.suggested_limit} for {suggestion.user.username}'
        )
    
    return redirect('analytics:credit_overview')


# =============================================================================
# SEGMENTATION VIEWS
# =============================================================================

@login_required
def segment_overview(request):
    """
    Overview of customer segments.
    """
    user = request.user
    
    if user.role == 'shop_owner':
        return redirect('analytics:segment_detail', pk=user.pk)
    
    # Get segment distribution
    if user.role == 'wholesaler':
        segments = ShopSegment.objects.filter(
            user__orders_placed__wholesaler=user,
            is_current=True
        ).distinct()
    else:
        segments = ShopSegment.objects.filter(is_current=True)
    
    # Group by cluster
    segment_counts = {}
    for seg in segments:
        name = seg.cluster_name
        if name not in segment_counts:
            segment_counts[name] = {'count': 0, 'users': []}
        segment_counts[name]['count'] += 1
        segment_counts[name]['users'].append(seg)
    
    context = {
        'title': 'Customer Segmentation',
        'segment_counts': segment_counts,
        'total_customers': segments.count(),
    }
    
    return render(request, 'analytics/segment_overview.html', context)


@login_required
def segment_detail(request, pk):
    """
    Segment details for a specific user.
    """
    target_user = get_object_or_404(CustomUser, pk=pk)
    
    user = request.user
    if user.role == 'shop_owner' and target_user != user:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')
    
    result = get_customer_segment(target_user)
    
    context = {
        'title': f'Segment Analysis - {target_user.username}',
        'target_user': target_user,
        'segment': result,
    }
    
    return render(request, 'analytics/segment_detail.html', context)


# =============================================================================
# CHART DATA API ENDPOINTS
# =============================================================================

@login_required
def chart_repayment_trends(request):
    """
    API endpoint for repayment trends chart data.
    
    Returns daily payment amounts for the last 30 days.
    """
    user = request.user
    today = date.today()
    days = 30
    
    # Get EMI payments
    if user.role == 'shop_owner':
        emis = EMISchedule.objects.filter(order__shop_owner=user, is_paid=True)
    elif user.role == 'wholesaler':
        emis = EMISchedule.objects.filter(order__wholesaler=user, is_paid=True)
    else:
        emis = EMISchedule.objects.filter(is_paid=True)
    
    # Aggregate by date
    data = []
    labels = []
    
    for i in range(days, -1, -1):
        day = today - timedelta(days=i)
        paid = emis.filter(paid_date=day).aggregate(Sum('amount'))['amount__sum'] or 0
        labels.append(day.strftime('%d %b'))
        data.append(float(paid))
    
    return JsonResponse({
        'labels': labels,
        'datasets': [{
            'label': 'Payments Received',
            'data': data,
            'borderColor': '#00897b',
            'backgroundColor': 'rgba(0, 137, 123, 0.1)',
            'fill': True,
        }]
    })


@login_required
def chart_risk_levels(request):
    """
    API endpoint for risk distribution chart data.
    """
    user = request.user
    
    if user.role == 'admin':
        profiles = Profile.objects.all()
    elif user.role == 'wholesaler':
        profiles = Profile.objects.filter(user__orders_placed__wholesaler=user).distinct()
    else:
        profiles = Profile.objects.filter(user=user)
    
    data = {
        'labels': ['Low Risk', 'Medium Risk', 'High Risk'],
        'datasets': [{
            'data': [
                profiles.filter(risk_category='low').count(),
                profiles.filter(risk_category='medium').count(),
                profiles.filter(risk_category='high').count(),
            ],
            'backgroundColor': ['#00897b', '#f57c00', '#c62828'],
        }]
    }
    
    return JsonResponse(data)


@login_required
def chart_sales_trends(request):
    """
    API endpoint for sales trends chart data.
    """
    user = request.user
    today = date.today()
    days = 30
    
    if user.role == 'shop_owner':
        orders = Order.objects.filter(shop_owner=user)
    elif user.role == 'wholesaler':
        orders = Order.objects.filter(wholesaler=user)
    else:
        orders = Order.objects.all()
    
    data = []
    labels = []
    
    for i in range(days, -1, -1):
        day = today - timedelta(days=i)
        sales = orders.filter(
            order_date=day,
            status__in=['approved', 'delivered', 'completed']
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        labels.append(day.strftime('%d %b'))
        data.append(float(sales))
    
    return JsonResponse({
        'labels': labels,
        'datasets': [{
            'label': 'Daily Sales',
            'data': data,
            'borderColor': '#1a237e',
            'backgroundColor': 'rgba(26, 35, 126, 0.1)',
            'fill': True,
        }]
    })


@login_required
def chart_segments(request):
    """
    API endpoint for segment distribution chart data.
    """
    user = request.user
    
    if user.role == 'admin':
        segments = ShopSegment.objects.filter(is_current=True)
    elif user.role == 'wholesaler':
        segments = ShopSegment.objects.filter(
            user__orders_placed__wholesaler=user,
            is_current=True
        ).distinct()
    else:
        segments = ShopSegment.objects.filter(user=user, is_current=True)
    
    segment_names = ['Low Activity', 'Regular', 'High Value', 'At Risk']
    counts = [segments.filter(cluster_name=name).count() for name in segment_names]
    
    return JsonResponse({
        'labels': segment_names,
        'datasets': [{
            'data': counts,
            'backgroundColor': ['#9e9e9e', '#1a237e', '#00897b', '#c62828'],
        }]
    })
