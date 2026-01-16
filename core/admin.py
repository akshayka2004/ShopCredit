"""
==============================================================================
CORE APP - ADMIN CONFIGURATION
==============================================================================
Register core business models with Django Admin interface.

Models registered:
    - Category: Product categories
    - Product: Product catalog
    - Order: Credit orders
    - OrderItem: Order line items
    - EMISchedule: Payment schedules
    - CreditTransaction: Transaction history
    - DailySales: Daily aggregated sales

Author: ShopCredit Development Team
==============================================================================
"""

from django.contrib import admin
from .models import (
    Category, Product, Order, OrderItem, 
    EMISchedule, CreditTransaction, DailySales
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin configuration for Category model."""
    
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    ordering = ('name',)


class OrderItemInline(admin.TabularInline):
    """
    Display Order Items inline when editing an Order.
    """
    model = OrderItem
    extra = 1  # Show 1 empty form by default
    readonly_fields = ('total_price',)


class EMIScheduleInline(admin.TabularInline):
    """
    Display EMI Schedule inline when editing an Order.
    """
    model = EMISchedule
    extra = 0  # Don't show empty forms
    readonly_fields = ('is_late',)
    ordering = ('installment_number',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin configuration for Product model."""
    
    list_display = ('name', 'sku', 'category', 'unit_price', 'stock_quantity', 
                    'wholesaler', 'is_active')
    list_filter = ('category', 'is_active', 'wholesaler')
    search_fields = ('name', 'sku', 'description')
    ordering = ('name',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'sku', 'category', 'description', 'image')
        }),
        ('Pricing & Stock', {
            'fields': ('unit_price', 'stock_quantity', 'min_order_quantity')
        }),
        ('Ownership', {
            'fields': ('wholesaler', 'is_active')
        }),
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin configuration for Order model."""
    
    list_display = ('order_number', 'shop_owner', 'wholesaler', 'total_amount', 
                    'status', 'emi_count', 'order_date', 'due_date')
    list_filter = ('status', 'order_date', 'wholesaler')
    search_fields = ('order_number', 'shop_owner__username', 'wholesaler__username')
    ordering = ('-created_at',)
    readonly_fields = ('order_number', 'order_date', 'created_at', 'updated_at')
    
    inlines = [OrderItemInline, EMIScheduleInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'shop_owner', 'wholesaler', 'status')
        }),
        ('Financial Details', {
            'fields': ('total_amount', 'emi_count')
        }),
        ('Dates', {
            'fields': ('order_date', 'due_date', 'approval_date', 'delivery_date')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_orders', 'mark_delivered', 'mark_completed']
    
    @admin.action(description='Approve selected orders')
    def approve_orders(self, request, queryset):
        from datetime import date
        count = queryset.filter(status='pending').update(
            status='approved', 
            approval_date=date.today()
        )
        self.message_user(request, f'{count} orders have been approved.')
    
    @admin.action(description='Mark as delivered')
    def mark_delivered(self, request, queryset):
        from datetime import date
        count = queryset.filter(status__in=['approved', 'dispatched']).update(
            status='delivered',
            delivery_date=date.today()
        )
        self.message_user(request, f'{count} orders marked as delivered.')
    
    @admin.action(description='Mark as completed')
    def mark_completed(self, request, queryset):
        count = queryset.filter(status='delivered').update(status='completed')
        self.message_user(request, f'{count} orders marked as completed.')


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Admin configuration for OrderItem model."""
    
    list_display = ('order', 'product_name', 'quantity', 'unit_price', 'total_price')
    list_filter = ('order__status',)
    search_fields = ('order__order_number', 'product_name')


@admin.register(EMISchedule)
class EMIScheduleAdmin(admin.ModelAdmin):
    """Admin configuration for EMI Schedule model."""
    
    list_display = ('order', 'installment_number', 'amount', 'due_date', 
                    'is_paid', 'paid_date', 'is_late')
    list_filter = ('is_paid', 'is_late', 'due_date')
    search_fields = ('order__order_number',)
    ordering = ('order', 'installment_number')
    
    actions = ['mark_as_paid']
    
    @admin.action(description='Mark as paid (today)')
    def mark_as_paid(self, request, queryset):
        from datetime import date
        for emi in queryset.filter(is_paid=False):
            emi.mark_as_paid(emi.amount)
        self.message_user(request, 'Selected EMIs have been marked as paid.')


@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    """Admin configuration for Credit Transaction model."""
    
    list_display = ('user', 'transaction_type', 'amount', 'balance_after', 
                    'description', 'transaction_date')
    list_filter = ('transaction_type', 'transaction_date')
    search_fields = ('user__username', 'description', 'order__order_number')
    ordering = ('-created_at',)
    readonly_fields = ('transaction_date', 'created_at')


@admin.register(DailySales)
class DailySalesAdmin(admin.ModelAdmin):
    """Admin configuration for Daily Sales model."""
    
    list_display = ('user', 'date', 'total_orders', 'total_sales', 
                    'total_payments', 'outstanding_balance')
    list_filter = ('date', 'user')
    search_fields = ('user__username',)
    ordering = ('-date',)
    readonly_fields = ('created_at', 'updated_at')
