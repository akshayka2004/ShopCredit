"""
==============================================================================
SHOPCREDIT - DJANGO SETTINGS
==============================================================================
Django settings for the ShopCredit: Intelligent Digital Udhaar System.

Configuration Overview:
    - Database: MySQL via WAMP (localhost)
    - Static Files: Local Bootstrap 5, Chart.js (NO CDN)
    - Auth: Custom User Model (accounts.CustomUser)
    - Apps: accounts, core, analytics, reports

IMPORTANT FOR VIVA:
    - We use MySQL instead of SQLite for better performance with large datasets
    - Custom User Model allows role-based access (Shop Owner, Wholesaler, Admin)
    - Static files are served locally for offline operation

Author: ShopCredit Development Team
==============================================================================
"""

from pathlib import Path
import os

# ==============================================================================
# PATH CONFIGURATION
# ==============================================================================
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ==============================================================================
# SECURITY SETTINGS
# ==============================================================================
# SECURITY WARNING: keep the secret key used in production secret!
# In a real production environment, this should be stored in environment variables
SECRET_KEY = 'django-insecure-shopcredit-bca-project-2026-change-in-production'

# SECURITY WARNING: don't run with debug turned on in production!
# Debug mode shows detailed error pages - useful for development
DEBUG = True

# Hosts that are allowed to serve this site
# For localhost development, we add common local addresses
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']


# ==============================================================================
# APPLICATION DEFINITION
# ==============================================================================
# All Django apps installed in this project
INSTALLED_APPS = [
    # Django built-in apps (order matters for admin styling)
    'django.contrib.admin',          # Admin panel
    'django.contrib.auth',           # Authentication framework
    'django.contrib.contenttypes',   # Content type framework
    'django.contrib.sessions',       # Session framework
    'django.contrib.messages',       # Messaging framework
    'django.contrib.staticfiles',    # Static files handling
    
    # ==========================================================================
    # SHOPCREDIT CUSTOM APPS
    # ==========================================================================
    'accounts.apps.AccountsConfig',   # User management & authentication
    'core.apps.CoreConfig',           # Core business logic (orders, products)
    'analytics.apps.AnalyticsConfig', # ML analytics & predictions
    'reports.apps.ReportsConfig',     # PDF report generation
]

# Middleware - runs on every request/response cycle
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',           # CSRF protection
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Root URL configuration
ROOT_URLCONF = 'shopcredit.urls'

# Template configuration
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Global templates directory (for base.html, shared components)
        'DIRS': [BASE_DIR / 'templates'],
        # Also look for templates in each app's 'templates' folder
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',  # Required for admin
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# WSGI configuration for deployment
WSGI_APPLICATION = 'shopcredit.wsgi.application'


# ==============================================================================
# DATABASE CONFIGURATION
# ==============================================================================
# MySQL Database via WAMP
# Make sure WAMP is running and MySQL service is active before starting Django
#
# To create the database in MySQL:
#   1. Open phpMyAdmin (http://localhost/phpmyadmin)
#   2. Create new database: shopcredit_db
#   3. Or run: CREATE DATABASE shopcredit_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

DATABASES = {
    'default': {
        # MySQL database engine
        'ENGINE': 'django.db.backends.mysql',
        
        # Database name - create this in phpMyAdmin first!
        'NAME': 'shopcredit_db',
        
        # MySQL credentials (change these to match your WAMP setup)
        'USER': 'root',              # Default WAMP MySQL user
        'PASSWORD': 'root1234',      # Your MySQL password
        
        # Connection settings
        'HOST': 'localhost',         # WAMP runs on localhost
        'PORT': '3306',              # Default MySQL port
        
        # Additional options for better compatibility
        'OPTIONS': {
            'charset': 'utf8mb4',    # Support for emojis and special characters
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}


# ==============================================================================
# CUSTOM USER MODEL
# ==============================================================================
# Tell Django to use our CustomUser model instead of the default User
# This MUST be set before running the first migration!
AUTH_USER_MODEL = 'accounts.CustomUser'


# ==============================================================================
# PASSWORD VALIDATION
# ==============================================================================
# Password validators to ensure strong passwords
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,  # Minimum 8 characters
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# ==============================================================================
# AUTHENTICATION SETTINGS
# ==============================================================================
# URL to redirect to for login
LOGIN_URL = 'accounts:login'

# URL to redirect to after successful login (if no 'next' parameter)
LOGIN_REDIRECT_URL = 'accounts:dashboard'

# URL to redirect to after logout
LOGOUT_REDIRECT_URL = 'accounts:login'


# ==============================================================================
# INTERNATIONALIZATION
# ==============================================================================
# Language and timezone settings
LANGUAGE_CODE = 'en-us'

# Set timezone to India Standard Time (for accurate timestamps)
TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True      # Enable internationalization
USE_TZ = True        # Use timezone-aware datetimes


# ==============================================================================
# STATIC FILES CONFIGURATION
# ==============================================================================
# Static files are CSS, JavaScript, and images that don't change per-user
# We're using LOCAL static files (no CDN) for offline operation

# URL prefix for static files
STATIC_URL = '/static/'

# Additional directories to look for static files
STATICFILES_DIRS = [
    BASE_DIR / 'static',  # Project-level static folder
]

# Directory where 'collectstatic' will gather all static files for production
STATIC_ROOT = BASE_DIR / 'staticfiles'


# ==============================================================================
# MEDIA FILES CONFIGURATION
# ==============================================================================
# Media files are user-uploaded content (profile pictures, product images)

# URL prefix for media files
MEDIA_URL = '/media/'

# Directory where uploaded files are stored
MEDIA_ROOT = BASE_DIR / 'media'


# ==============================================================================
# ML MODELS CONFIGURATION
# ==============================================================================
# Directory for storing trained .pkl model files
ML_MODELS_DIR = BASE_DIR / 'ml_models'


# ==============================================================================
# DEFAULT PRIMARY KEY FIELD TYPE
# ==============================================================================
# Default auto-generated primary key field type for models
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ==============================================================================
# EMAIL CONFIGURATION (Optional - for password reset)
# ==============================================================================
# For a localhost project, we'll use console backend (prints emails to terminal)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# ==============================================================================
# SESSION CONFIGURATION
# ==============================================================================
# Session age in seconds (30 minutes of inactivity = logout)
SESSION_COOKIE_AGE = 1800

# Save session data on every request (keep session alive while user is active)
SESSION_SAVE_EVERY_REQUEST = True


# ==============================================================================
# LOGGING CONFIGURATION
# ==============================================================================
# Configure logging for debugging and monitoring
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'shopcredit': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
