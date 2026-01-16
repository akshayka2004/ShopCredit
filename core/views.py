"""
==============================================================================
CORE APP - VIEWS
==============================================================================
Views for core business functionality including products, orders, and EMI.

Views:
    - Products: List, detail, add, edit
    - Orders: Create, list, detail, approve, cancel
    - EMI: List, pay
    - Transactions: History

The Order Create view implements the full credit ordering workflow:
    1. Shop owner selects products
    2. System validates credit limit
    3. Order is created in 'pending' status
    4. Wholesaler approves → EMI schedule is created
    5. Outstanding balance is updated

Author: ShopCredit Development Team
==============================================================================
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import json

from .models import (
    Category, Product, Order, OrderItem, 
    EMISchedule, CreditTransaction, DailySales
)
from .forms import (
    ProductForm, OrderCreateForm, EMIPaymentForm,
    create_emi_schedule, validate_credit_limit, update_outstanding_balance
)
from accounts.models import CustomUser


# =============================================================================
# HELPER DECORATORS
# =============================================================================

def wholesaler_required(view_func):
    """Decorator to require wholesaler role."""
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'wholesaler':
            messages.error(request, 'Access denied. Wholesalers only.')
            return redirect('accounts:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def shop_owner_required(view_func):
    """Decorator to require shop owner role."""
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'shop_owner':
            messages.error(request, 'Access denied. Shop owners only.')
            return redirect('accounts:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


# =============================================================================
# PRODUCT VIEWS
# =============================================================================

@login_required
def product_list(request):
    """
    Display product catalog.
    
    - Shop owners see all active products
    - Wholesalers see their own products
    - Admins see all products
    """
    user = request.user
    
    if user.role == 'wholesaler':
        # Wholesaler sees their products
        products = Product.objects.filter(wholesaler=user).order_by('-created_at')
        title = 'My Products'
    else:
        # Shop owners and admins see all active products
        products = Product.objects.filter(is_active=True).order_by('name')
        title = 'Product Catalog'
    
    # Filter by category if provided
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Search functionality
    search = request.GET.get('search')
    if search:
        products = products.filter(
            Q(name__icontains=search) | 
            Q(sku__icontains=search) |
            Q(description__icontains=search)
        )
    
    categories = Category.objects.filter(is_active=True)
    
    context = {
        'title': title,
        'products': products,
        'categories': categories,
        'selected_category': category_id,
        'search_query': search or '',
    }
    
    return render(request, 'core/product_list.html', context)


@login_required
def product_detail(request, pk):
    """Display product details."""
    product = get_object_or_404(Product, pk=pk)
    
    context = {
        'title': product.name,
        'product': product,
    }
    
    return render(request, 'core/product_detail.html', context)


@login_required
@wholesaler_required
def product_add(request):
    """
    Add new product (Wholesalers only).
    """
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        
        if form.is_valid():
            product = form.save(commit=False)
            product.wholesaler = request.user
            product.save()
            
            messages.success(request, f'Product "{product.name}" added successfully!')
            return redirect('core:product_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProductForm()
    
    context = {
        'title': 'Add Product',
        'form': form,
        'action': 'Add',
    }
    
    return render(request, 'core/product_form.html', context)


@login_required
@wholesaler_required
def product_edit(request, pk):
    """
    Edit existing product (Wholesalers only, own products).
    """
    product = get_object_or_404(Product, pk=pk, wholesaler=request.user)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        
        if form.is_valid():
            form.save()
            messages.success(request, f'Product "{product.name}" updated!')
            return redirect('core:product_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProductForm(instance=product)
    
    context = {
        'title': f'Edit {product.name}',
        'form': form,
        'product': product,
        'action': 'Update',
    }
    
    return render(request, 'core/product_form.html', context)


# =============================================================================
# ORDER VIEWS
# =============================================================================

@login_required
def order_list(request):
    """
    Display orders list.
    
    - Shop owners see their orders
    - Wholesalers see orders to them
    - Admins see all orders
    """
    user = request.user
    
    if user.role == 'shop_owner':
        orders = Order.objects.filter(shop_owner=user)
        title = 'My Orders'
    elif user.role == 'wholesaler':
        orders = Order.objects.filter(wholesaler=user)
        title = 'Customer Orders'
    else:
        orders = Order.objects.all()
        title = 'All Orders'
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)
    
    orders = orders.order_by('-created_at')
    
    context = {
        'title': title,
        'orders': orders,
        'selected_status': status,
    }
    
    return render(request, 'core/order_list.html', context)


@login_required
@shop_owner_required
def order_create(request):
    """
    Create new credit order.
    
    This is the main Udhaar functionality:
    1. Shop owner selects products and quantities
    2. System calculates total
    3. Credit limit is validated
    4. Order is created in 'pending' status
    5. Wholesaler must approve before EMI schedule is created
    """
    if request.method == 'POST':
        # Get form data
        wholesaler_id = request.POST.get('wholesaler')
        emi_count = int(request.POST.get('emi_count', 4))
        notes = request.POST.get('notes', '')
        
        # Get product items from JSON
        items_json = request.POST.get('items', '[]')
        try:
            items = json.loads(items_json)
        except json.JSONDecodeError:
            messages.error(request, 'Invalid order data.')
            return redirect('core:order_create')
        
        if not items:
            messages.error(request, 'Please add at least one product to your order.')
            return redirect('core:order_create')
        
        # Get wholesaler
        wholesaler = get_object_or_404(CustomUser, pk=wholesaler_id, role='wholesaler')
        
        # Calculate total
        total_amount = Decimal('0.00')
        order_items_data = []
        
        for item in items:
            product = get_object_or_404(Product, pk=item['product_id'])
            quantity = int(item['quantity'])
            item_total = product.unit_price * quantity
            total_amount += item_total
            
            order_items_data.append({
                'product': product,
                'quantity': quantity,
                'unit_price': product.unit_price,
                'total_price': item_total,
            })
        
        # Validate credit limit
        is_valid, message = validate_credit_limit(request.user, total_amount)
        
        if not is_valid:
            messages.error(request, message)
            return redirect('core:order_create')
        
        # Create order
        order = Order.objects.create(
            shop_owner=request.user,
            wholesaler=wholesaler,
            total_amount=total_amount,
            emi_count=emi_count,
            status='pending',
            notes=notes
        )
        
        # Create order items
        for item_data in order_items_data:
            OrderItem.objects.create(
                order=order,
                product=item_data['product'],
                product_name=item_data['product'].name,
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price'],
                total_price=item_data['total_price']
            )
            
            # Update stock
            item_data['product'].stock_quantity -= item_data['quantity']
            item_data['product'].save()
        
        messages.success(
            request, 
            f'Order {order.order_number} placed successfully! '
            'Awaiting wholesaler approval.'
        )
        return redirect('core:order_detail', pk=order.pk)
    
    # GET request - show order form
    wholesalers = CustomUser.objects.filter(role='wholesaler', is_verified=True)
    
    # Get user's available credit
    profile = request.user.profile
    
    context = {
        'title': 'Create New Order',
        'wholesalers': wholesalers,
        'available_credit': profile.available_credit(),
        'credit_limit': profile.credit_limit,
    }
    
    return render(request, 'core/order_create.html', context)


@login_required
def order_detail(request, pk):
    """
    Display order details including EMI schedule.
    """
    order = get_object_or_404(Order, pk=pk)
    
    # Access control
    user = request.user
    if user.role == 'shop_owner' and order.shop_owner != user:
        messages.error(request, 'Access denied.')
        return redirect('core:order_list')
    if user.role == 'wholesaler' and order.wholesaler != user:
        messages.error(request, 'Access denied.')
        return redirect('core:order_list')
    
    # Get order items and EMI schedule
    items = order.items.all()
    emis = order.emi_schedules.all().order_by('installment_number')
    
    context = {
        'title': f'Order {order.order_number}',
        'order': order,
        'items': items,
        'emis': emis,
        'paid_amount': order.paid_amount(),
        'pending_amount': order.pending_amount(),
    }
    
    return render(request, 'core/order_detail.html', context)


@login_required
@wholesaler_required
def order_approve(request, pk):
    """
    Approve a pending order (Wholesalers only).
    
    On approval:
    1. Status changes to 'approved'
    2. EMI schedule is created
    3. Shop owner's outstanding balance is updated
    4. Credit transaction is recorded
    """
    order = get_object_or_404(Order, pk=pk, wholesaler=request.user, status='pending')
    
    if request.method == 'POST':
        # Approve the order
        order.status = 'approved'
        order.approval_date = date.today()
        order.save()
        
        # Create EMI schedule
        create_emi_schedule(order)
        
        # Update shop owner's outstanding balance
        update_outstanding_balance(order.shop_owner, order.total_amount, 'credit')
        
        # Record transaction
        CreditTransaction.objects.create(
            user=order.shop_owner,
            transaction_type='credit',
            amount=order.total_amount,
            order=order,
            description=f'Credit order {order.order_number} approved',
            balance_after=order.shop_owner.profile.current_outstanding
        )
        
        messages.success(request, f'Order {order.order_number} approved!')
        return redirect('core:order_detail', pk=order.pk)
    
    context = {
        'title': f'Approve Order {order.order_number}',
        'order': order,
    }
    
    return render(request, 'core/order_approve.html', context)


@login_required
def order_cancel(request, pk):
    """
    Cancel an order.
    
    Only pending orders can be cancelled.
    If approved, only admin can cancel (with balance adjustment).
    """
    order = get_object_or_404(Order, pk=pk)
    
    # Access control
    user = request.user
    if user.role == 'shop_owner' and order.shop_owner != user:
        messages.error(request, 'Access denied.')
        return redirect('core:order_list')
    
    # Only pending orders can be cancelled by shop owner
    if order.status != 'pending' and user.role != 'admin':
        messages.error(request, 'Only pending orders can be cancelled.')
        return redirect('core:order_detail', pk=order.pk)
    
    if request.method == 'POST':
        # Restore stock
        for item in order.items.all():
            if item.product:
                item.product.stock_quantity += item.quantity
                item.product.save()
        
        # If order was approved, adjust balance
        if order.status == 'approved':
            update_outstanding_balance(order.shop_owner, order.total_amount, 'debit')
            
            CreditTransaction.objects.create(
                user=order.shop_owner,
                transaction_type='debit',
                amount=order.total_amount,
                order=order,
                description=f'Order {order.order_number} cancelled - balance restored',
                balance_after=order.shop_owner.profile.current_outstanding
            )
        
        order.status = 'cancelled'
        order.save()
        
        messages.success(request, f'Order {order.order_number} cancelled.')
        return redirect('core:order_list')
    
    context = {
        'title': f'Cancel Order {order.order_number}',
        'order': order,
    }
    
    return render(request, 'core/order_cancel.html', context)


# =============================================================================
# EMI VIEWS
# =============================================================================

@login_required
def emi_list(request):
    """
    Display EMI payment schedule.
    
    - Shop owners see their EMIs
    - Wholesalers see EMIs from their orders
    """
    user = request.user
    
    if user.role == 'shop_owner':
        emis = EMISchedule.objects.filter(order__shop_owner=user)
        title = 'My EMI Payments'
    elif user.role == 'wholesaler':
        emis = EMISchedule.objects.filter(order__wholesaler=user)
        title = 'Customer EMI Payments'
    else:
        emis = EMISchedule.objects.all()
        title = 'All EMI Payments'
    
    # Filter options
    status = request.GET.get('status')
    if status == 'pending':
        emis = emis.filter(is_paid=False)
    elif status == 'paid':
        emis = emis.filter(is_paid=True)
    elif status == 'overdue':
        emis = emis.filter(is_paid=False, due_date__lt=date.today())
    
    emis = emis.order_by('due_date')
    
    context = {
        'title': title,
        'emis': emis,
        'selected_status': status,
        'today': date.today(),
    }
    
    return render(request, 'core/emi_list_v2.html', context)


@login_required
def emi_pay(request, pk):
    """
    Process EMI payment.
    
    On payment:
    1. EMI is marked as paid
    2. Shop owner's outstanding balance decreases
    3. Credit transaction is recorded
    4. Check if order is complete
    """
    emi = get_object_or_404(EMISchedule, pk=pk)
    order = emi.order
    
    # Access control - shop owner or wholesaler can record payment
    user = request.user
    if user.role == 'shop_owner' and order.shop_owner != user:
        messages.error(request, 'Access denied.')
        return redirect('core:emi_list')
    
    if emi.is_paid:
        messages.warning(request, 'This EMI has already been paid.')
        return redirect('core:order_detail', pk=order.pk)
    
    if request.method == 'POST':
        form = EMIPaymentForm(request.POST, emi=emi)
        
        if form.is_valid():
            amount = form.cleaned_data['amount']
            reference = form.cleaned_data['payment_reference']
            
            # Mark EMI as paid
            emi.mark_as_paid(amount, reference)
            
            # Update outstanding balance
            update_outstanding_balance(order.shop_owner, amount, 'debit')
            
            # Record transaction
            CreditTransaction.objects.create(
                user=order.shop_owner,
                transaction_type='debit',
                amount=amount,
                order=order,
                emi=emi,
                description=f'EMI {emi.installment_number} payment for {order.order_number}',
                balance_after=order.shop_owner.profile.current_outstanding
            )
            
            # Check if all EMIs paid → complete order
            if not order.emi_schedules.filter(is_paid=False).exists():
                order.status = 'completed'
                order.save()
                messages.success(
                    request, 
                    f'🎉 All EMIs paid! Order {order.order_number} is now complete.'
                )
            else:
                messages.success(
                    request, 
                    f'EMI {emi.installment_number} paid successfully!'
                )
            
            return redirect('core:order_detail', pk=order.pk)
    else:
        form = EMIPaymentForm(emi=emi)
    
    context = {
        'title': f'Pay EMI #{emi.installment_number}',
        'emi': emi,
        'order': order,
        'form': form,
    }
    
    return render(request, 'core/emi_pay.html', context)


# =============================================================================
# TRANSACTION VIEWS
# =============================================================================

@login_required
def transaction_list(request):
    """
    Display credit transaction history.
    """
    user = request.user
    
    if user.role == 'shop_owner':
        transactions = CreditTransaction.objects.filter(user=user)
        title = 'My Transactions'
    elif user.role == 'wholesaler':
        transactions = CreditTransaction.objects.filter(order__wholesaler=user)
        title = 'Customer Transactions'
    else:
        transactions = CreditTransaction.objects.all()
        title = 'All Transactions'
    
    transactions = transactions.order_by('-created_at')
    
    context = {
        'title': title,
        'transactions': transactions,
    }
    
    return render(request, 'core/transaction_list.html', context)


# =============================================================================
# CATEGORY VIEWS
# =============================================================================

@login_required
def category_list(request):
    """Display list of product categories."""
    categories = Category.objects.all().order_by('name')
    
    context = {
        'title': 'Categories',
        'categories': categories,
    }
    
    return render(request, 'core/category_list.html', context)


# =============================================================================
# API VIEWS (for AJAX requests)
# =============================================================================

@login_required
def get_products_by_wholesaler(request, wholesaler_id):
    """
    API endpoint to get products by wholesaler.
    
    Used in order creation form for dynamic product loading.
    """
    products = Product.objects.filter(
        wholesaler_id=wholesaler_id,
        is_active=True,
        stock_quantity__gt=0
    ).values('id', 'name', 'sku', 'unit_price', 'stock_quantity')
    
    return JsonResponse({'products': list(products)})
