"""
Script to reset all user passwords to a common password.
Run with: python manage.py shell < reset_passwords.py
"""
from django.contrib.auth import get_user_model

User = get_user_model()
COMMON_PASSWORD = "password123"

users = User.objects.all()
count = 0

print(f"Resetting passwords for {users.count()} users...")

for user in users:
    user.set_password(COMMON_PASSWORD)
    user.save()
    count += 1
    print(f"Reset password for: {user.username}")

print(f"\nSuccessfully reset {count} passwords to '{COMMON_PASSWORD}'")
