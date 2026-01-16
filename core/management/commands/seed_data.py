"""
==============================================================================
SEED DATA - Django Management Command
==============================================================================
Generate sample data for demo/testing purposes.

Creates:
    - Admin user
    - Wholesaler users with products
    - Shop owner users with orders
    - EMI payments and transactions

Usage:
    python manage.py seed_data              # Create all seed data
    python manage.py seed_data --clear      # Clear existing data first

Author: ShopCredit Development Team
==============================================================================
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Sum
from datetime import date, timedelta
from decimal import Decimal
import random

CustomUser = get_user_model()


class Command(BaseCommand):
    help = 'Generate sample data for ShopCredit demo'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('='*60))
        self.stdout.write(self.style.NOTICE('ShopCredit Seed Data Generator'))
        self.stdout.write(self.style.NOTICE('='*60))
        
        if options['clear']:
            self.clear_data()
        
        self.create_users()
        self.create_categories()
        self.create_products()
        self.create_orders()
        self.train_ml_models()
        
        self.stdout.write(self.style.SUCCESS('\n✅ Seed data created successfully!'))
        self.stdout.write(self.style.NOTICE('\nDemo Accounts:'))
        self.stdout.write('  Admin:      admin / admin123')
        self.stdout.write('  Wholesaler: wholesaler1 / demo1234')
        self.stdout.write('  Shop Owner: shopowner1 / demo1234')
    
    def clear_data(self):
        """Clear existing data."""
        from core.models import Order, Product, Category, CreditTransaction, EMISchedule
        from analytics.models import RiskPrediction, CreditLimitSuggestion, ShopSegment
        
        self.stdout.write('Clearing existing data...')
        
        CreditTransaction.objects.all().delete()
        EMISchedule.objects.all().delete()
        Order.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        RiskPrediction.objects.all().delete()
        CreditLimitSuggestion.objects.all().delete()
        ShopSegment.objects.all().delete()
        
        # Keep admin, delete demo users
        CustomUser.objects.filter(username__startswith='wholesaler').delete()
        CustomUser.objects.filter(username__startswith='shopowner').delete()
        CustomUser.objects.filter(username__in=['sharma_shop', 'gupta_prov', 'khan_stores', 'metro_trade', 'laxmi_whole']).delete()
        
        self.stdout.write(self.style.SUCCESS('  ✓ Data cleared'))
    
    def create_users(self):
        """Create demo users."""
        self.stdout.write('\nCreating users...')
        
        # Admin
        if not CustomUser.objects.filter(username='admin').exists():
            admin = CustomUser.objects.create_superuser(
                username='admin',
                email='admin@shopcredit.local',
                password='admin123',
                role='admin'
            )
            admin.is_verified = True
            admin.save()
            self.stdout.write(self.style.SUCCESS('  ✓ Admin user created'))
        
        # Wholesalers (Realistic Names)
        wholesaler_data = [
            {'username': 'metro_trade', 'business': 'Metro Trading Corp', 'city': 'Bangalore', 'phone': '9876543210'},
            {'username': 'laxmi_whole', 'business': 'Laxmi Wholesale', 'city': 'Mumbai', 'phone': '9876543211'},
            {'username': 'delhi_dist', 'business': 'Delhi Distributors', 'city': 'New Delhi', 'phone': '9876543212'},
        ]
        
        self.wholesalers = []
        for data in wholesaler_data:
            user, created = CustomUser.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': f'{data["username"]}@shopcredit.local',
                    'role': 'wholesaler',
                    'is_verified': True,
                    'phone': f'+91-{data["phone"]}',
                }
            )
            if created:
                user.set_password('demo1234')
                user.save()
                user.profile.business_name = data['business']
                user.profile.business_address = f'{data["city"]}, India'
                user.profile.save()
            self.wholesalers.append(user)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(self.wholesalers)} wholesalers created'))
        
        # Shop Owners (Realistic Names)
        shop_data = [
            {'username': 'sharma_shop', 'business': 'Sharma General Store', 'limit': 75000, 'risk': 'low', 'phone': '9876511111'},
            {'username': 'gupta_prov', 'business': 'Gupta Provisions', 'limit': 50000, 'risk': 'low', 'phone': '9876522222'},
            {'username': 'khan_stores', 'business': 'Khan Daily Needs', 'limit': 35000, 'risk': 'medium', 'phone': '9876533333'},
            {'username': 'amma_kirana', 'business': 'Amma Kirana', 'limit': 60000, 'risk': 'medium', 'phone': '9876544444'},
            {'username': 'raju_super', 'business': 'Raju Supermarket', 'limit': 20000, 'risk': 'high', 'phone': '9876555555'},
            {'username': 'patel_mart', 'business': 'Patel Mini Mart', 'limit': 90000, 'risk': 'low', 'phone': '9876566666'},
            {'username': 'singh_bros', 'business': 'Singh Brothers', 'limit': 45000, 'risk': 'medium', 'phone': '9876577777'},
        ]
        
        self.shop_owners = []
        for data in shop_data:
            user, created = CustomUser.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': f'{data["username"]}@shopcredit.local',
                    'role': 'shop_owner',
                    'is_verified': True,
                    'phone': f'+91-{data["phone"]}',
                }
            )
            if created:
                user.set_password('demo1234')
                user.save()
                user.profile.business_name = data['business']
                user.profile.business_address = 'Local Market, India'
                user.profile.credit_limit = Decimal(str(data['limit']))
                user.profile.credit_score = random.randint(500, 850)
                user.profile.risk_category = data['risk']
                user.profile.save()
            self.shop_owners.append(user)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(self.shop_owners)} shop owners created'))
    
    def create_categories(self):
        """Create product categories."""
        from core.models import Category
        
        self.stdout.write('\nCreating categories...')
        
        categories = [
            'Groceries', 'Dairy', 'Beverages', 
            'Snacks', 'Personal Care', 'Household'
        ]
        
        self.categories = []
        for name in categories:
            cat, created = Category.objects.get_or_create(
                name=name,
                defaults={'is_active': True}
            )
            self.categories.append(cat)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(self.categories)} categories created'))
    
    def create_products(self):
        """Create sample products with realistic brands."""
        from core.models import Product
        
        self.stdout.write('\nCreating products...')
        
        # Format: (Name, SKU, Price, CategoryIndex)
        products = [
            ('India Gate Basmati Rice (5kg)', 'RICE-IG-5', 650, 0),
            ('Aashirvaad Atta (10kg)', 'ATTA-ASH-10', 420, 0),
            ('Tata Salt (1kg)', 'SALT-TATA-1', 25, 0),
            ('Toor Dal (1kg)', 'DAL-TOOR-1', 140, 0),
            ('Sugar (1kg)', 'SUGAR-1', 45, 0),
            ('Fortune Sunlite Oil (1L)', 'OIL-FORT-1', 135, 0),
            
            ('Amul Taaza Milk (1L)', 'MILK-AMUL-1', 72, 1),
            ('Amul Butter (500g)', 'BUTR-AMUL-500', 275, 1),
            ('Paneer (200g)', 'PNR-200', 95, 1),
            ('Mother Dairy Curd (400g)', 'CURD-MD-400', 35, 1),
            
            ('Coca Cola (2L)', 'COLA-2L', 95, 2),
            ('Real Fruit Juice (1L)', 'JUICE-REAL-1', 110, 2),
            ('Nescafe Classic (50g)', 'COF-NES-50', 160, 2),
            ('Red Label Tea (500g)', 'TEA-RL-500', 280, 2),
            
            ('Lay\'s Classic Salted', 'CHIP-LAY-L', 20, 3),
            ('Parle-G Biscuits', 'BISC-PG', 10, 3),
            ('Britannia Good Day', 'BISC-GD', 30, 3),
            ('Maggi Noodles (Pack of 4)', 'NOD-MAG-4', 56, 3),
            ('Haldiram Bhujia (400g)', 'SNK-HAL-400', 110, 3),
            
            ('Lux Soap (Pack of 3)', 'SOAP-LUX-3', 140, 4),
            ('Dove Shampoo (180ml)', 'SHMP-DOVE-180', 195, 4),
            ('Colgate Toothpaste (200g)', 'TP-COL-200', 112, 4),
            ('Dettol Handwash (200ml)', 'HW-DET-200', 99, 4),
            
            ('Surf Excel Easy Wash (1kg)', 'DTGT-SURF-1', 130, 5),
            ('Lizol Floor Cleaner (500ml)', 'CLN-LIZ-500', 109, 5),
            ('Vim Dishwash Gel (250ml)', 'DW-VIM-250', 55, 5),
            ('Harpic Toilet Cleaner', 'CLN-HARP-500', 98, 5),
        ]
        
        self.products = []
        for idx, (name, sku, price, cat_idx) in enumerate(products):
            wholesaler = random.choice(self.wholesalers)
            product, created = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    'name': name,
                    'category': self.categories[cat_idx],
                    'wholesaler': wholesaler,
                    'unit_price': Decimal(str(price)),
                    'stock_quantity': random.randint(20, 500),
                    'is_active': True,
                }
            )
            # Update price if exists
            if not created:
                 product.unit_price = Decimal(str(price))
                 product.save()
            self.products.append(product)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ {len(self.products)} products created'))
    
    def create_orders(self):
        """Create sample orders with EMI schedules."""
        from core.models import Order, OrderItem, EMISchedule, CreditTransaction
        
        self.stdout.write('\nCreating orders...')
        
        order_count = 0
        today = date.today()
        
        for shop_owner in self.shop_owners:
            # Create 3-5 orders per shop owner
            num_orders = random.randint(3, 5)
            
            # Reset outstanding for clean calculation
            shop_owner.profile.current_outstanding = Decimal('0')
            shop_owner.profile.save()
            
            for i in range(num_orders):
                wholesaler = random.choice(self.wholesalers)
                # Spread orders over last 3 months
                days_ago = random.randint(1, 90)
                order_date = today - timedelta(days=days_ago)
                
                # Random realistic products
                num_items = random.randint(3, 8)
                selected_products = random.sample(self.products, min(num_items, len(self.products)))
                
                # Calculate total
                total = Decimal('0')
                items_data = []
                for product in selected_products:
                    # Realistic retailer quantities
                    qty = random.randint(5, 50) 
                    item_total = product.unit_price * qty
                    total += item_total
                    items_data.append({
                        'product': product,
                        'quantity': qty,
                        'unit_price': product.unit_price,
                        'total_price': item_total,
                    })
                
                # Create order
                order = Order.objects.create(
                    shop_owner=shop_owner,
                    wholesaler=wholesaler,
                    total_amount=total,
                    emi_count=4,
                    status='approved',
                    approval_date=order_date,
                    order_number=f"ORD-{order_date.strftime('%Y%m%d')}-{random.randint(1000,9999)}"
                )
                # Manually set order_date since it is auto_now_add
                order.order_date = order_date
                order.save()
                
                # Create order items
                for item_data in items_data:
                    OrderItem.objects.create(
                        order=order,
                        product=item_data['product'],
                        product_name=item_data['product'].name,
                        quantity=item_data['quantity'],
                        unit_price=item_data['unit_price'],
                        total_price=item_data['total_price'],
                    )
                
                # Create EMI schedule (Weekly)
                emi_amount = total / 4
                for emi_num in range(1, 5):
                    due_date = order_date + timedelta(days=7 * emi_num)
                    
                    # Simulated payment status based on user risk profile
                    risk_factor = 0.9 if shop_owner.profile.risk_category == 'low' else (0.6 if shop_owner.profile.risk_category == 'medium' else 0.4)
                    
                    if due_date < today:
                         is_paid = random.random() < risk_factor
                         paid_date = due_date if is_paid else None
                         is_late = is_paid and random.random() > 0.8
                    else:
                        is_paid = False
                        paid_date = None
                        is_late = False
                    
                    EMISchedule.objects.create(
                        order=order,
                        installment_number=emi_num,
                        amount=emi_amount,
                        due_date=due_date,
                        is_paid=is_paid,
                        paid_date=paid_date,
                        is_late=is_late,
                    )
                
                # Update outstanding
                paid_emis = order.emi_schedules.filter(is_paid=True)
                paid_amount = paid_emis.aggregate(total=Sum('amount'))['total'] or Decimal('0')
                shop_owner.profile.current_outstanding += (total - paid_amount)
                
                # Record transaction
                ct = CreditTransaction.objects.create(
                    user=shop_owner,
                    transaction_type='credit',
                    amount=total,
                    order=order,
                    description=f'Credit order {order.order_number}',
                    balance_after=shop_owner.profile.current_outstanding,
                )
                ct.transaction_date = order_date
                ct.save()
                
                order_count += 1
            
            # Final save of consolidated outstanding
            shop_owner.profile.save()
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ {order_count} orders created with EMI schedules'))
    
    def train_ml_models(self):
        """Train ML models with the seed data."""
        from django.core.management import call_command
        
        self.stdout.write('\nTraining ML models...')
        
        try:
            call_command('train_models', '--synthetic', verbosity=0)
            self.stdout.write(self.style.SUCCESS('  ✓ ML models trained'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ⚠ ML training skipped: {str(e)}'))
