"""
==============================================================================
REPORTS APP - URL CONFIGURATION
==============================================================================
URL patterns for PDF report generation.

Author: ShopCredit Development Team
==============================================================================
"""

from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Invoice
    path('invoice/<int:order_id>/', views.generate_invoice, name='invoice'),
    
    # Risk Reports
    path('risk-summary/', views.risk_summary, name='risk_summary'),
    path('risk/<int:user_id>/', views.risk_user_report, name='risk_user_report'),
    
    # Credit Reports  
    path('credit-history/', views.credit_history, name='credit_history'),
    path('credit/<int:user_id>/', views.credit_user_report, name='credit_user_report'),
    
    # Daily Summary
    path('daily-summary/', views.daily_summary, name='daily_summary'),
]
