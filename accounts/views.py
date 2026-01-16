"""
==============================================================================
ACCOUNTS APP - VIEWS
==============================================================================
Views for user authentication and account management.

Views:
    - user_login: Handle user login
    - user_logout: Handle user logout
    - register: New user registration
    - dashboard: Role-based dashboard
    - profile: View user profile
    - profile_edit: Edit user profile

Author: ShopCredit Development Team
==============================================================================
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta

from .forms import LoginForm, RegistrationForm, ProfileForm, UserUpdateForm
from .models import CustomUser, Profile
from core.models import Order, EMISchedule, CreditTransaction, DailySales


def user_login(request):
    """
    Handle user login.
    
    GET: Display login form
    POST: Process login credentials and redirect to dashboard
    
    Uses Django's built-in authentication with custom form styling.
    """
    # Redirect if already logged in
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            remember_me = form.cleaned_data.get('remember_me', True)
            
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # Set session expiry based on "Remember Me"
                if not remember_me:
                    request.session.set_expiry(0)  # Session ends when browser closes
                
                messages.success(request, f'Welcome back, {user.username}!')
                
                # Redirect to 'next' URL if provided, else dashboard
                next_url = request.GET.get('next', 'accounts:dashboard')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {
        'form': form,
        'title': 'Login',
    })


def user_logout(request):
    """
    Handle user logout.
    
    Logs out the current user and redirects to login page.
    """
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('accounts:login')


def register(request):
    """
    Handle new user registration.
    
    GET: Display registration form
    POST: Process registration data, create user and profile
    
    New users are created as 'unverified' by default.
    They need admin/wholesaler approval to get a credit limit.
    """
    # Redirect if already logged in
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        
        if form.is_valid():
            user = form.save()
            
            # Log the user in automatically
            login(request, user)
            
            messages.success(
                request, 
                f'Welcome to ShopCredit, {user.username}! '
                'Your account has been created. An admin will verify your account soon.'
            )
            
            return redirect('accounts:dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RegistrationForm()
    
    return render(request, 'accounts/register.html', {
        'form': form,
        'title': 'Register',
    })


@login_required
def dashboard(request):
    """
    Role-based dashboard with key metrics.
    
    Shows different data based on user role:
    - Shop Owner: Orders, EMIs, outstanding balance
    - Wholesaler: Products, incoming orders, revenue
    - Admin: System-wide statistics
    """
    user = request.user
    context = {
        'title': 'Dashboard',
        'user': user,
    }
    
    # Get current date for calculations
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    
    if user.role == 'shop_owner':
        # Shop Owner Dashboard Data
        # -------------------------
        
        # Credit Summary
        profile = user.profile
        context['credit_limit'] = profile.credit_limit
        context['current_outstanding'] = profile.current_outstanding
        context['available_credit'] = profile.available_credit()
        context['credit_utilization'] = profile.credit_utilization_percentage()
        context['credit_score'] = profile.credit_score
        
        # Order Statistics
        orders = Order.objects.filter(shop_owner=user)
        context['total_orders'] = orders.count()
        context['pending_orders'] = orders.filter(status='pending').count()
        context['active_orders'] = orders.filter(
            status__in=['approved', 'dispatched', 'delivered']
        ).count()
        
        # EMI Summary
        emis = EMISchedule.objects.filter(order__shop_owner=user)
        context['pending_emis'] = emis.filter(is_paid=False).count()
        context['overdue_emis'] = emis.filter(
            is_paid=False, 
            due_date__lt=today
        ).count()
        
        # Get upcoming EMIs (next 7 days)
        next_week = today + timedelta(days=7)
        context['upcoming_emis'] = emis.filter(
            is_paid=False,
            due_date__gte=today,
            due_date__lte=next_week
        ).order_by('due_date')[:5]
        
        # Recent orders
        context['recent_orders'] = orders.order_by('-created_at')[:5]
        
        template = 'accounts/dashboard_shop_owner.html'
    
    elif user.role == 'wholesaler':
        # Wholesaler Dashboard Data
        # --------------------------
        
        # Product Statistics
        from core.models import Product
        products = Product.objects.filter(wholesaler=user)
        context['total_products'] = products.count()
        context['active_products'] = products.filter(is_active=True).count()
        context['low_stock'] = products.filter(stock_quantity__lt=10).count()
        
        # Order Statistics
        orders = Order.objects.filter(wholesaler=user)
        context['total_orders'] = orders.count()
        context['pending_orders'] = orders.filter(status='pending').count()
        context['pending_approval'] = orders.filter(status='pending')[:5]
        
        # Revenue (last 30 days)
        recent_orders = orders.filter(
            order_date__gte=thirty_days_ago,
            status__in=['completed', 'delivered']
        )
        context['monthly_revenue'] = recent_orders.aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        # Customer count (unique shop owners)
        context['customer_count'] = orders.values('shop_owner').distinct().count()
        
        # High risk customers
        high_risk = Profile.objects.filter(
            user__orders_placed__wholesaler=user,
            risk_category='high'
        ).distinct()[:5]
        context['high_risk_customers'] = high_risk
        
        # Recent transactions
        transactions = CreditTransaction.objects.filter(
            order__wholesaler=user
        ).order_by('-created_at')[:10]
        context['recent_transactions'] = transactions
        
        template = 'accounts/dashboard_wholesaler.html'
    
    else:  # admin
        # Admin Dashboard Data
        # ---------------------
        
        # System Statistics
        context['total_users'] = CustomUser.objects.count()
        context['shop_owners'] = CustomUser.objects.filter(role='shop_owner').count()
        context['wholesalers'] = CustomUser.objects.filter(role='wholesaler').count()
        context['unverified_users'] = CustomUser.objects.filter(is_verified=False).count()
        
        # Order Statistics
        context['total_orders'] = Order.objects.count()
        context['pending_orders'] = Order.objects.filter(status='pending').count()
        
        # Financial Overview
        total_outstanding = Profile.objects.aggregate(
            total=Sum('current_outstanding')
        )['total'] or 0
        context['total_outstanding'] = total_outstanding
        
        # Risk Distribution
        context['low_risk'] = Profile.objects.filter(risk_category='low').count()
        context['medium_risk'] = Profile.objects.filter(risk_category='medium').count()
        context['high_risk'] = Profile.objects.filter(risk_category='high').count()
        
        # Recent activities
        context['recent_orders'] = Order.objects.order_by('-created_at')[:10]
        context['recent_users'] = CustomUser.objects.order_by('-date_joined')[:5]
        
        template = 'accounts/dashboard_admin.html'
    
    return render(request, template, context)


@login_required
def profile(request):
    """
    Display user profile with credit information.
    """
    user = request.user
    profile = user.profile
    
    # Get credit history
    transactions = CreditTransaction.objects.filter(user=user).order_by('-created_at')[:10]
    
    # Get EMI payment history
    if user.role == 'shop_owner':
        emi_history = EMISchedule.objects.filter(
            order__shop_owner=user,
            is_paid=True
        ).order_by('-paid_date')[:10]
    else:
        emi_history = []
    
    context = {
        'title': 'My Profile',
        'user': user,
        'profile': profile,
        'transactions': transactions,
        'emi_history': emi_history,
    }
    
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit(request):
    """
    Edit user profile information.
    
    Uses two forms: UserUpdateForm and ProfileForm
    """
    user = request.user
    profile = user.profile
    
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = ProfileForm(instance=profile)
    
    context = {
        'title': 'Edit Profile',
        'user_form': user_form,
        'profile_form': profile_form,
    }
    
    return render(request, 'accounts/profile_edit.html', context)
