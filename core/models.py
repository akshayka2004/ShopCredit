"""
==============================================================================
CORE APP - MODELS
==============================================================================
This module defines the core business models for the ShopCredit Udhaar system.

Key Models:
    - Product: Catalog of items available for purchase
    - Order: Credit-based orders placed by shop owners
    - OrderItem: Individual products within an order
    - CreditTransaction: Record of all credit/debit operations
    - EMISchedule: 30-day EMI payment schedule for orders
    - DailySales: Daily aggregated sales data for analytics

The Udhaar (Credit) Flow:
    1. Shop Owner browses Product catalog
    2. Shop Owner places an Order on credit
    3. System creates EMISchedule with 30-day payment plan
    4. As payments are made, CreditTransactions are recorded
    5. DailySales tracks aggregate data for ML features

Author: ShopCredit Development Team
==============================================================================
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from datetime import date, timedelta
from accounts.models import CustomUser


class Category(models.Model):
    """
    Product category for organizing the catalog.
    
    Examples: Groceries, Electronics, FMCG, Dairy, etc.
    
    Attributes:
        name (str): Category name
        description (str): Brief description of the category
        is_active (bool): Whether category is currently active
    """
    
    name = models.CharField(
        max_length=100, 
        unique=True,
        help_text="Category name (e.g., Groceries, Electronics)"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Brief description of this category"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive categories won't show in product listings"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Product catalog for items available in the system.
    
    Products are managed by Wholesalers and can be ordered on credit
    by Shop Owners.
    
    Attributes:
        name (str): Product name
        sku (str): Stock Keeping Unit - unique product identifier
        category (FK): Product category
        description (str): Detailed product description
        unit_price (Decimal): Price per unit in INR
        stock_quantity (int): Available quantity
        wholesaler (FK): The wholesaler who provides this product
        is_active (bool): Whether product is available for ordering
    """
    
    # Basic product information
    name = models.CharField(
        max_length=200,
        help_text="Product name as displayed to customers"
    )
    
    sku = models.CharField(
        max_length=50, 
        unique=True,
        help_text="Stock Keeping Unit - unique identifier (e.g., PROD-001)"
    )
    
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='products',
        help_text="Product category"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Detailed product description"
    )
    
    # Pricing and stock
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Price per unit in INR"
    )
    
    stock_quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Available quantity in stock"
    )
    
    # Minimum order quantity (useful for wholesale)
    min_order_quantity = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Minimum quantity that can be ordered"
    )
    
    # Product image (uploaded file)
    image = models.ImageField(
        upload_to='products/', 
        blank=True, 
        null=True,
        help_text="Product image for catalog display (upload)"
    )
    
    # Product image URL (external link)
    image_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="External image URL (if not uploading)"
    )
    
    def get_image_url(self):
        """
        Get the product image URL.
        Priority: image_url (external) > image (uploaded) > None
        """
        if self.image_url:
            return self.image_url
        elif self.image:
            return self.image.url
        return None
    
    # Wholesaler who provides this product
    wholesaler = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE,
        related_name='products',
        limit_choices_to={'role': 'wholesaler'},
        help_text="Wholesaler managing this product"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive products won't appear in catalog"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} (₹{self.unit_price})"
    
    def is_in_stock(self):
        """Check if product has available stock."""
        return self.stock_quantity > 0


class Order(models.Model):
    """
    Credit-based order placed by a Shop Owner.
    
    Orders in ShopCredit are always on credit (Udhaar). Each order generates
    an EMI schedule for repayment over 30 days.
    
    Order Flow:
        1. PENDING: Order placed, awaiting wholesaler approval
        2. APPROVED: Wholesaler approved, EMI schedule created
        3. DISPATCHED: Products shipped to shop owner
        4. DELIVERED: Products received by shop owner
        5. COMPLETED: All EMIs paid, order closed
        6. CANCELLED: Order was cancelled
        7. DEFAULTED: Payment not received within grace period
    
    Attributes:
        order_number (str): Unique order identifier (auto-generated)
        shop_owner (FK): Shop owner who placed the order
        wholesaler (FK): Wholesaler fulfilling the order
        total_amount (Decimal): Total order value in INR
        status (str): Current order status
        emi_count (int): Number of EMI installments (default: 4 for 30 days)
        due_date (date): Final payment due date
    """
    
    # Order status choices
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('dispatched', 'Dispatched'),
        ('delivered', 'Delivered'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('defaulted', 'Defaulted'),
    ]
    
    # Unique order number - auto-generated
    order_number = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False,
        help_text="System-generated unique order number"
    )
    
    # Parties involved in the transaction
    shop_owner = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE,
        related_name='orders_placed',
        limit_choices_to={'role': 'shop_owner'},
        help_text="Shop owner who placed this order"
    )
    
    wholesaler = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE,
        related_name='orders_received',
        limit_choices_to={'role': 'wholesaler'},
        help_text="Wholesaler fulfilling this order"
    )
    
    # Financial details
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total order value in INR"
    )
    
    # EMI Configuration
    # Default: 4 installments over 30 days (weekly payments)
    emi_count = models.IntegerField(
        default=4,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Number of EMI installments (1-12)"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=15, 
        choices=STATUS_CHOICES, 
        default='pending',
        help_text="Current order status"
    )
    
    # Important dates
    order_date = models.DateField(
        auto_now_add=True,
        help_text="Date when order was placed"
    )
    
    due_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Final payment due date (order_date + 30 days)"
    )
    
    approval_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Date when wholesaler approved the order"
    )
    
    delivery_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Date when order was delivered"
    )
    
    # Notes and remarks
    notes = models.TextField(
        blank=True,
        help_text="Any special instructions or notes"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order {self.order_number} - ₹{self.total_amount}"
    
    def save(self, *args, **kwargs):
        """
        Custom save to auto-generate order number and due date.
        
        Order number format: ORD-YYYYMMDD-XXXX (e.g., ORD-20260108-0001)
        Due date: order_date + 30 days
        """
        if not self.order_number:
            # Generate order number
            today = date.today()
            prefix = f"ORD-{today.strftime('%Y%m%d')}-"
            
            # Get the last order number for today
            last_order = Order.objects.filter(
                order_number__startswith=prefix
            ).order_by('-order_number').first()
            
            if last_order:
                # Extract the sequence number and increment
                last_seq = int(last_order.order_number.split('-')[-1])
                new_seq = last_seq + 1
            else:
                new_seq = 1
            
            self.order_number = f"{prefix}{new_seq:04d}"
        
        # Set due date to 30 days from order date
        if not self.due_date and self.order_date:
            self.due_date = self.order_date + timedelta(days=30)
        elif not self.due_date:
            self.due_date = date.today() + timedelta(days=30)
        
        super().save(*args, **kwargs)
    
    def calculate_emi_amount(self):
        """
        Calculate the EMI amount for each installment.
        
        Returns:
            Decimal: Amount to be paid per EMI
        """
        if self.emi_count == 0:
            return self.total_amount
        return self.total_amount / self.emi_count
    
    def paid_amount(self):
        """
        Calculate total amount paid so far.
        
        Returns:
            Decimal: Sum of all completed EMI payments
        """
        return sum(
            emi.amount_paid for emi in self.emi_schedules.filter(is_paid=True)
        )
    
    def pending_amount(self):
        """
        Calculate remaining amount to be paid.
        
        Returns:
            Decimal: Total amount minus paid amount
        """
        return self.total_amount - self.paid_amount()
    
    def is_overdue(self):
        """
        Check if the order has overdue payments.
        
        Returns:
            bool: True if any EMI is overdue
        """
        today = date.today()
        return self.emi_schedules.filter(
            is_paid=False, 
            due_date__lt=today
        ).exists()


class OrderItem(models.Model):
    """
    Individual product within an order.
    
    Represents a line item in an order with quantity and pricing.
    
    Attributes:
        order (FK): Parent order
        product (FK): Product being ordered
        quantity (int): Number of units ordered
        unit_price (Decimal): Price per unit at time of order
        total_price (Decimal): quantity * unit_price
    """
    
    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE,
        related_name='items',
        help_text="The order this item belongs to"
    )
    
    product = models.ForeignKey(
        Product, 
        on_delete=models.SET_NULL,
        null=True,
        related_name='order_items',
        help_text="Product being ordered"
    )
    
    # Store product name separately in case product is deleted
    product_name = models.CharField(
        max_length=200,
        help_text="Product name (stored for historical reference)"
    )
    
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Number of units ordered"
    )
    
    # Store unit price at time of order (prices may change later)
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Price per unit at time of order"
    )
    
    total_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total price for this line item"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
    
    def save(self, *args, **kwargs):
        """Calculate total price before saving."""
        self.total_price = self.unit_price * self.quantity
        
        # Store product name if product exists
        if self.product and not self.product_name:
            self.product_name = self.product.name
        
        super().save(*args, **kwargs)
        
        # Update parent order total
        total = sum(item.total_price for item in self.order.items.all())
        self.order.total_amount = total
        self.order.save(update_fields=['total_amount'])


class EMISchedule(models.Model):
    """
    EMI (Equated Monthly Installment) payment schedule for an order.
    
    Each order is split into multiple EMIs for easier repayment.
    Default: 4 installments over 30 days (weekly payments).
    
    EMI Calculation:
        - Total Amount: ₹10,000
        - EMI Count: 4
        - EMI Amount: ₹2,500 per week
    
    Attributes:
        order (FK): Parent order
        installment_number (int): Which installment this is (1, 2, 3, 4)
        amount (Decimal): Amount to be paid in this installment
        due_date (date): When this installment is due
        is_paid (bool): Whether this installment has been paid
        paid_date (date): When payment was received
        amount_paid (Decimal): Actual amount received (may differ from amount)
    """
    
    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE,
        related_name='emi_schedules',
        help_text="The order this EMI belongs to"
    )
    
    installment_number = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Installment number (1, 2, 3, ...)"
    )
    
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Amount to be paid in this installment"
    )
    
    due_date = models.DateField(
        help_text="Due date for this installment"
    )
    
    is_paid = models.BooleanField(
        default=False,
        help_text="Whether this installment has been paid"
    )
    
    paid_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Date when payment was received"
    )
    
    amount_paid = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Actual amount received"
    )
    
    # Late payment tracking
    is_late = models.BooleanField(
        default=False,
        help_text="True if payment was made after due date"
    )
    
    # Payment reference (transaction ID, cheque number, etc.)
    payment_reference = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Payment reference (UPI ID, cheque number, etc.)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'EMI Schedule'
        verbose_name_plural = 'EMI Schedules'
        ordering = ['order', 'installment_number']
        # Ensure unique installment per order
        unique_together = ['order', 'installment_number']
    
    def __str__(self):
        status = "✓ Paid" if self.is_paid else "⏳ Pending"
        return f"EMI {self.installment_number} - ₹{self.amount} ({status})"
    
    def mark_as_paid(self, amount_paid, payment_reference=''):
        """
        Mark this EMI as paid.
        
        Args:
            amount_paid (Decimal): Actual amount received
            payment_reference (str): Transaction reference
        """
        self.is_paid = True
        self.paid_date = date.today()
        self.amount_paid = amount_paid
        self.payment_reference = payment_reference
        
        # Check if payment is late
        if self.paid_date > self.due_date:
            self.is_late = True
        
        self.save()
    
    @property
    def is_overdue(self):
        """Check if EMI is overdue."""
        return not self.is_paid and self.due_date < date.today()

    @property
    def days_until_due(self):
        """Calculate days until due date."""
        if self.is_paid:
            return 999  # Return high number if paid so it's not "due soon"
        return (self.due_date - date.today()).days

    def days_overdue(self):
        """
        Calculate how many days this EMI is overdue.
        
        Returns:
            int: Number of days overdue (0 if not overdue)
        """
        if self.is_paid or date.today() <= self.due_date:
            return 0
        return (date.today() - self.due_date).days


class CreditTransaction(models.Model):
    """
    Record of all credit and debit transactions.
    
    This model tracks every financial movement in the system:
    - CREDIT: When a shop owner takes credit (increases outstanding)
    - DEBIT: When a payment is made (decreases outstanding)
    
    Used for:
    - Audit trail
    - ML feature extraction
    - Financial reporting
    
    Attributes:
        user (FK): User whose credit is affected
        transaction_type (str): CREDIT or DEBIT
        amount (Decimal): Transaction amount
        order (FK): Related order (if applicable)
        description (str): Transaction description
        balance_after (Decimal): Outstanding balance after transaction
    """
    
    TRANSACTION_TYPES = [
        ('credit', 'Credit (Debit to Account)'),   # Shop owner takes credit
        ('debit', 'Debit (Payment Received)'),      # Payment made
    ]
    
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE,
        related_name='credit_transactions',
        help_text="User whose credit is affected"
    )
    
    transaction_type = models.CharField(
        max_length=10, 
        choices=TRANSACTION_TYPES,
        help_text="Type of transaction"
    )
    
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Transaction amount in INR"
    )
    
    # Link to order (optional - direct payments may not have an order)
    order = models.ForeignKey(
        Order, 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='transactions',
        help_text="Related order (if applicable)"
    )
    
    # Link to EMI (for EMI payments)
    emi = models.ForeignKey(
        EMISchedule, 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='transactions',
        help_text="Related EMI schedule (if applicable)"
    )
    
    description = models.CharField(
        max_length=255,
        help_text="Transaction description"
    )
    
    # Balance after this transaction
    balance_after = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Outstanding balance after this transaction"
    )
    
    # Transaction metadata
    transaction_date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Credit Transaction'
        verbose_name_plural = 'Credit Transactions'
        ordering = ['-created_at']
    
    def __str__(self):
        arrow = "↑" if self.transaction_type == 'credit' else "↓"
        return f"{arrow} ₹{self.amount} - {self.description}"


class DailySales(models.Model):
    """
    Daily aggregated sales data for analytics and ML.
    
    This model stores daily summaries for each shop owner, used for:
    - Dashboard visualizations
    - ML feature extraction (sales trends, seasonality)
    - Business intelligence
    
    Data is aggregated at end of each day by a scheduled task.
    
    Attributes:
        user (FK): Shop owner
        date (date): Date of the record
        total_orders (int): Number of orders placed
        total_sales (Decimal): Total sales value
        total_payments (Decimal): Payments received
        new_credit (Decimal): New credit taken
        outstanding_balance (Decimal): Outstanding at end of day
    """
    
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE,
        related_name='daily_sales',
        help_text="Shop owner this data belongs to"
    )
    
    date = models.DateField(
        help_text="Date of this daily record"
    )
    
    # Sales metrics
    total_orders = models.IntegerField(
        default=0,
        help_text="Number of orders placed on this day"
    )
    
    total_sales = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total sales value for the day"
    )
    
    # Payment metrics
    total_payments = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total payments received on this day"
    )
    
    # Credit metrics
    new_credit = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="New credit taken on this day"
    )
    
    outstanding_balance = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Outstanding balance at end of day"
    )
    
    # Additional metrics for ML
    on_time_payments = models.IntegerField(
        default=0,
        help_text="Number of on-time payments"
    )
    
    late_payments = models.IntegerField(
        default=0,
        help_text="Number of late payments"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Daily Sales'
        verbose_name_plural = 'Daily Sales'
        ordering = ['-date']
        # One record per user per day
        unique_together = ['user', 'date']
    
    def __str__(self):
        return f"{self.user.username} - {self.date} - ₹{self.total_sales}"
    
    def payment_ratio(self):
        """
        Calculate payment-to-sales ratio (good for ML).
        
        Returns:
            float: Ratio of payments to sales (0.0 to 1.0+)
        """
        if self.total_sales == 0:
            return 1.0 if self.total_payments > 0 else 0.0
        return float(self.total_payments / self.total_sales)
