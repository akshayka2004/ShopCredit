"""
==============================================================================
CORE APP - URL CONFIGURATION
==============================================================================
URL patterns for core business functionality.

URL Patterns:
    - Products: Catalog listing, detail, add, edit
    - Orders: Create, list, detail, manage
    - EMI: Payment processing, schedule view
    - Transactions: Credit/debit history

Author: ShopCredit Development Team
==============================================================================
"""

from django.urls import path
from . import views

# App namespace for URL reversing (e.g., 'core:product_list')
app_name = 'core'

urlpatterns = [
    # ==========================================================================
    # PRODUCT URLS
    # ==========================================================================
    path('products/', views.product_list, name='product_list'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    
    # ==========================================================================
    # ORDER URLS
    # ==========================================================================
    path('orders/', views.order_list, name='order_list'),
    path('orders/create/', views.order_create, name='order_create'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/approve/', views.order_approve, name='order_approve'),
    path('orders/<int:pk>/cancel/', views.order_cancel, name='order_cancel'),
    
    # ==========================================================================
    # EMI URLS
    # ==========================================================================
    path('emi/', views.emi_list, name='emi_list'),
    path('emi/<int:pk>/pay/', views.emi_pay, name='emi_pay'),
    
    # ==========================================================================
    # TRANSACTION URLS
    # ==========================================================================
    path('transactions/', views.transaction_list, name='transaction_list'),
    
    # ==========================================================================
    # CATEGORY URLS
    # ==========================================================================
    path('categories/', views.category_list, name='category_list'),
    
    # ==========================================================================
    # API URLS
    # ==========================================================================
    path('api/products/<int:wholesaler_id>/', views.get_products_by_wholesaler, name='api_products_by_wholesaler'),
]
