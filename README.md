HEAD
# ShopCredit: Intelligent Digital Udhaar System
## Setup Guide

### Prerequisites
1. **Python 3.10+** installed
2. **WAMP Server** running with MySQL active
3. MySQL database created (see below)

---

### Step 1: Create MySQL Database

Open phpMyAdmin (http://localhost/phpmyadmin) or MySQL command line and run:

```sql
CREATE DATABASE shopcredit_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Or in phpMyAdmin:
1. Click "New" in the left sidebar
2. Enter database name: `shopcredit_db`
3. Select collation: `utf8mb4_unicode_ci`
4. Click "Create"

---

### Step 2: Install Dependencies

```bash
cd d:\Projects\Master-Architect
pip install -r requirements.txt
```

---

### Step 3: Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

---

### Step 4: Create Superuser (Admin Account)

```bash
python manage.py createsuperuser
```

Enter:
- Username: `admin`
- Email: `admin@shopcredit.local`
- Password: (your choice)

---

### Step 5: Run Development Server

```bash
python manage.py runserver
```

Access the application at: http://localhost:8000

---

### URLs

| URL | Description |
|-----|-------------|
| http://localhost:8000/ | Home (redirects to login) |
| http://localhost:8000/admin/ | Django Admin Panel |
| http://localhost:8000/accounts/login/ | User Login |
| http://localhost:8000/accounts/dashboard/ | User Dashboard |
| http://localhost:8000/analytics/ | Analytics Dashboard |

---

### Project Structure

```
Master-Architect/
├── shopcredit/          # Main Django project settings
│   ├── settings.py      # Database, apps, static files config
│   ├── urls.py          # Root URL configuration
│   └── wsgi.py          # WSGI entry point
├── accounts/            # User management app
│   ├── models.py        # CustomUser, Profile
│   ├── views.py         # Login, register, dashboard
│   └── admin.py         # Admin configuration
├── core/                # Core business logic
│   ├── models.py        # Product, Order, EMI, Transaction
│   ├── views.py         # Order creation, EMI payments
│   └── admin.py         # Admin configuration
├── analytics/           # ML & Analytics
│   ├── models.py        # RiskPrediction, CreditLimit, Segment
│   ├── views.py         # ML predictions, chart APIs
│   └── admin.py         # Admin configuration
├── reports/             # PDF generation
│   └── views.py         # Invoice, reports (ReportLab)
├── ml_models/           # Trained ML model files (.pkl)
├── static/              # Local CSS, JS (Bootstrap, Chart.js)
├── templates/           # HTML templates
├── manage.py            # Django management script
└── requirements.txt     # Python dependencies
```

---

### Database Credentials (settings.py)

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'shopcredit_db',
        'USER': 'root',
        'PASSWORD': 'root1234',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

---

### Next Steps (Module-by-Module)

| Step | Focus | What to implement |
|------|-------|-------------------|
| 2 | Core Logic | Views for credit orders, 30-day EMI calculation |
| 3 | Machine Learning | train_models.py, Random Forest, Linear Regression, K-Means |
| 4 | Dashboard UI | Bootstrap 5 templates, Chart.js visualizations |
| 5 | PDF Generation | ReportLab invoice and report generation |
| 6 | Seed Data | Sample data for demo |
=======
# ShopCredit
ShopCredit is an intelligent digital credit management system designed to modernize the traditional "Udhaar" (credit) system used in Indian wholesale-retail business relationships. The system enables shop owners to purchase goods on credit from wholesalers, with built-in EMI payment schedules and AI-powered risk assessment.
c35316cbecdd825326405c6fd5c4bf524e7acbf6
