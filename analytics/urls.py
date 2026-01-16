"""
==============================================================================
ANALYTICS APP - URL CONFIGURATION
==============================================================================
URL patterns for ML analytics and dashboard visualizations.

URL Patterns:
    - Dashboard: Analytics overview
    - Risk: Risk predictions and assessment
    - Credit: Credit limit suggestions
    - Segments: Shop segmentation
    - Charts: JSON data endpoints for Chart.js

Author: ShopCredit Development Team
==============================================================================
"""

from django.urls import path
from . import views

# App namespace for URL reversing (e.g., 'analytics:dashboard')
app_name = 'analytics'

urlpatterns = [
    # ==========================================================================
    # DASHBOARD
    # ==========================================================================
    path('', views.analytics_dashboard, name='dashboard'),
    
    # ==========================================================================
    # RISK PREDICTION
    # ==========================================================================
    path('risk/', views.risk_overview, name='risk_overview'),
    path('risk/<int:pk>/', views.risk_detail, name='risk_detail'),
    path('risk/predict/<int:pk>/', views.risk_predict, name='risk_predict'),
    
    # ==========================================================================
    # CREDIT LIMIT
    # ==========================================================================
    path('credit/', views.credit_overview, name='credit_overview'),
    path('credit/<int:pk>/', views.credit_detail, name='credit_detail'),
    path('credit/suggest/<int:pk>/', views.credit_suggest, name='credit_suggest'),
    path('credit/approve/<int:suggestion_id>/', views.credit_approve, name='credit_approve'),
    
    # ==========================================================================
    # SHOP SEGMENTATION
    # ==========================================================================
    path('segments/', views.segment_overview, name='segment_overview'),
    path('segments/<int:pk>/', views.segment_detail, name='segment_detail'),
    
    # ==========================================================================
    # CHART DATA ENDPOINTS (JSON for Chart.js)
    # ==========================================================================
    path('api/repayment-trends/', views.chart_repayment_trends, name='chart_repayment'),
    path('api/risk-levels/', views.chart_risk_levels, name='chart_risk'),
    path('api/sales-trends/', views.chart_sales_trends, name='chart_sales'),
    path('api/segment-distribution/', views.chart_segments, name='chart_segments'),
]
