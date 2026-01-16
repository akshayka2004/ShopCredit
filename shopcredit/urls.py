"""
==============================================================================
SHOPCREDIT - ROOT URL CONFIGURATION
==============================================================================
Main URL configuration for the ShopCredit project.

This file routes requests to the appropriate app URL configurations:
    - /             : Home page (redirects to dashboard or login)
    - /admin/       : Django admin interface
    - /accounts/    : User authentication & profiles
    - /core/        : Products, orders, EMI, transactions
    - /analytics/   : ML analytics & dashboard
    - /reports/     : PDF report generation

Author: ShopCredit Development Team
==============================================================================
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect


def home_redirect(request):
    """
    Redirect home page based on authentication status.
    
    - Authenticated users -> Dashboard
    - Anonymous users -> Login page
    """
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    return redirect('accounts:login')


# =============================================================================
# URL PATTERNS
# =============================================================================
urlpatterns = [
    # Home page - redirect to appropriate location
    path('', home_redirect, name='home'),
    
    # Django Admin Interface
    # Access at: http://localhost:8000/admin/
    path('admin/', admin.site.urls),
    
    # ==========================================================================
    # APP URL INCLUDES
    # ==========================================================================
    
    # Accounts App - User authentication, profiles, dashboards
    # Example URLs: /accounts/login/, /accounts/register/
    path('accounts/', include('accounts.urls')),
    
    # Core App - Products, orders, EMI, transactions
    # Example URLs: /core/products/, /core/orders/
    path('core/', include('core.urls')),
    
    # Analytics App - ML predictions, charts, analytics dashboard
    # Example URLs: /analytics/, /analytics/risk/
    path('analytics/', include('analytics.urls')),
    
    # Reports App - PDF generation
    # Example URLs: /reports/invoice/1/, /reports/risk-summary/
    path('reports/', include('reports.urls')),
]

# =============================================================================
# STATIC & MEDIA FILES IN DEVELOPMENT
# =============================================================================
# Only serve static files this way in development (DEBUG=True)
# In production, these should be served by a web server like Nginx

if settings.DEBUG:
    # Serve static files (CSS, JS, images)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Serve media files (user uploads)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# =============================================================================
# CUSTOMIZE ADMIN INTERFACE
# =============================================================================
admin.site.site_header = "ShopCredit Admin"
admin.site.site_title = "ShopCredit Admin Portal"
admin.site.index_title = "Welcome to ShopCredit Administration"
