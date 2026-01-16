"""
==============================================================================
CORE APP - FORMS
==============================================================================
Forms for order management, products, and EMI payments.

Forms:
    - ProductForm: Add/edit product (Wholesalers)
    - OrderForm: Create new credit order
    - OrderItemFormSet: Products in an order
    - EMIPaymentForm: Process EMI payment

The Order Form implements the 30-day EMI logic:
    - Orders are split into 4 weekly EMIs
    - Due dates are calculated from order date
    - Credit limit is validated before order approval

Author: ShopCredit Development Team
==============================================================================
"""

from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from decimal import Decimal
from datetime import date, timedelta

from .models import Product, Order, OrderItem, EMISchedule, Category
from accounts.models import CustomUser


class CategoryForm(forms.ModelForm):
    """Form for creating/editing product categories."""
    
    class Meta:
        model = Category
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ProductForm(forms.ModelForm):
    """
    Form for adding/editing products (Wholesalers only).
    
    Includes all product details necessary for the catalog.
    """
    
    class Meta:
        model = Product
        fields = [
            'name', 'sku', 'category', 'description',
            'unit_price', 'stock_quantity', 'min_order_quantity',
            'image', 'image_url', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Product Name',
            }),
            'sku': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'SKU-001',
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Product description...',
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0.01',
                'step': '0.01',
            }),
            'stock_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
            }),
            'min_order_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'image_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com/image.jpg',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
    
    def clean_sku(self):
        """Ensure SKU is unique (case-insensitive)."""
        sku = self.cleaned_data.get('sku', '').upper()
        
        # Check if editing existing product
        existing = Product.objects.filter(sku__iexact=sku)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        
        if existing.exists():
            raise ValidationError('This SKU is already in use.')
        
        return sku


class OrderItemForm(forms.Form):
    """
    Form for a single order item.
    
    Used in the order creation process to select products and quantities.
    """
    
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            'class': 'form-select product-select',
        })
    )
    
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control quantity-input',
            'min': '1',
        })
    )
    
    def __init__(self, *args, wholesaler=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter products by wholesaler if provided
        if wholesaler:
            self.fields['product'].queryset = Product.objects.filter(
                wholesaler=wholesaler,
                is_active=True,
                stock_quantity__gt=0
            )


class OrderCreateForm(forms.Form):
    """
    Form for creating a new credit order.
    
    Features:
    - Select wholesaler
    - Choose EMI count (1-4 installments)
    - Add notes
    
    The 30-day EMI logic:
    - Default: 4 EMIs (weekly payments over 30 days)
    - EMI amount = Total / EMI count
    - Due dates: Day 7, 14, 21, 28 from order date
    """
    
    EMI_CHOICES = [
        (1, '1 Payment (Full amount in 7 days)'),
        (2, '2 Payments (Every 15 days)'),
        (4, '4 Payments (Weekly for 30 days) - Recommended'),
    ]
    
    wholesaler = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(role='wholesaler', is_verified=True),
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
        help_text='Select the wholesaler to order from'
    )
    
    emi_count = forms.ChoiceField(
        choices=EMI_CHOICES,
        initial=4,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input',
        }),
        help_text='Choose how you want to pay'
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Any special instructions...',
        })
    )
    
    def __init__(self, *args, shop_owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.shop_owner = shop_owner
    
    def clean(self):
        """
        Validate order against credit limit.
        
        This method should be called after calculating total_amount
        from the order items.
        """
        cleaned_data = super().clean()
        
        # Credit limit validation will be done in the view
        # after calculating total from order items
        
        return cleaned_data


class EMIPaymentForm(forms.Form):
    """
    Form for processing EMI payments.
    
    Allows recording of payment with amount and reference.
    Supports partial payments if needed.
    """
    
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
        })
    )
    
    payment_reference = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'UPI ID, Cheque No., etc.',
        })
    )
    
    def __init__(self, *args, emi=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.emi = emi
        
        if emi:
            # Pre-fill with EMI amount
            self.fields['amount'].initial = emi.amount
            self.fields['amount'].help_text = f'EMI amount: ₹{emi.amount}'
    
    def clean_amount(self):
        """Validate payment amount."""
        amount = self.cleaned_data['amount']
        
        if self.emi and amount < self.emi.amount:
            # Allow partial payment but warn
            pass  # Could add warning for partial payment
        
        return amount


def create_emi_schedule(order):
    """
    Create EMI schedule for an order.
    
    This is the core 30-day EMI logic:
    - Split total amount into equal EMIs
    - Set due dates based on EMI count
    - Create EMISchedule objects
    
    Args:
        order: Order object with total_amount and emi_count set
    
    Returns:
        list: List of created EMISchedule objects
    
    Example (4 EMIs for ₹10,000 order placed on Jan 1):
        EMI 1: ₹2,500 due Jan 8
        EMI 2: ₹2,500 due Jan 15
        EMI 3: ₹2,500 due Jan 22
        EMI 4: ₹2,500 due Jan 29
    """
    if not order.order_date:
        order.order_date = date.today()
    
    emi_count = order.emi_count
    total_amount = order.total_amount
    
    # Calculate EMI amount (handle rounding)
    emi_amount = total_amount / emi_count
    
    # Calculate days between EMIs
    # For 30-day period:
    # 1 EMI: due in 7 days
    # 2 EMIs: due in 15 days each
    # 4 EMIs: due in ~7 days each (weekly)
    
    if emi_count == 1:
        days_between = 7
    elif emi_count == 2:
        days_between = 15
    else:  # 4 EMIs
        days_between = 7
    
    emi_schedules = []
    
    for i in range(1, emi_count + 1):
        due_date = order.order_date + timedelta(days=days_between * i)
        
        # For the last EMI, adjust amount to account for rounding
        if i == emi_count:
            # Sum of previous EMIs
            previous_total = emi_amount * (emi_count - 1)
            current_amount = total_amount - previous_total
        else:
            current_amount = emi_amount
        
        emi = EMISchedule.objects.create(
            order=order,
            installment_number=i,
            amount=current_amount,
            due_date=due_date
        )
        emi_schedules.append(emi)
    
    return emi_schedules


def validate_credit_limit(shop_owner, order_amount):
    """
    Validate if shop owner has sufficient credit limit.
    
    Args:
        shop_owner: CustomUser object (shop owner)
        order_amount: Decimal amount of the order
    
    Returns:
        tuple: (is_valid: bool, message: str)
    
    Checks:
    1. User is verified
    2. Available credit >= order amount
    """
    profile = shop_owner.profile
    
    # Check verification status
    if not shop_owner.is_verified:
        return False, 'Your account is not verified. Please contact an admin.'
    
    # Check available credit
    available = profile.available_credit()
    
    if order_amount > available:
        return False, (
            f'Insufficient credit. Available: ₹{available:.2f}, '
            f'Required: ₹{order_amount:.2f}'
        )
    
    return True, 'Credit check passed.'


def update_outstanding_balance(user, amount, transaction_type='credit'):
    """
    Update user's outstanding balance after transaction.
    
    Args:
        user: CustomUser object
        amount: Decimal amount
        transaction_type: 'credit' (increase) or 'debit' (decrease)
    
    This is called after:
    - Order is approved (credit - increases outstanding)
    - EMI is paid (debit - decreases outstanding)
    """
    profile = user.profile
    
    if transaction_type == 'credit':
        profile.current_outstanding += amount
    else:  # debit
        profile.current_outstanding -= amount
        # Ensure outstanding doesn't go negative
        if profile.current_outstanding < 0:
            profile.current_outstanding = Decimal('0.00')
    
    profile.save()
