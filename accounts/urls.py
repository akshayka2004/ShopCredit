"""
==============================================================================
ACCOUNTS APP - URL CONFIGURATION
==============================================================================
URL patterns for user authentication and account management.

URL Patterns:
    - /login/           : User login
    - /logout/          : User logout
    - /register/        : New user registration
    - /dashboard/       : Role-based dashboard redirect
    - /profile/         : User profile view/edit

Author: ShopCredit Development Team
==============================================================================
"""

from django.urls import path
from . import views

# App namespace for URL reversing (e.g., 'accounts:login')
app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.register, name='register'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Profile
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
]
