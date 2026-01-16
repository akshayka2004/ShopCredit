"""Fix profile.html template variable that's split across lines."""
import re

with open('accounts/templates/accounts/profile.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the split template variable on lines 26-27
# Match the pattern with newline and whitespace
pattern = r'<span class="badge bg-primary mb-3" style="font-size: 0.85rem; padding: 8px 16px;">\s*\{\{\s*user\.get_role_display\s*\}\}\s*</span>'
replacement = '<span class="badge bg-primary mb-3" style="font-size: 0.85rem; padding: 8px 16px;">{{ user.get_role_display }}</span>'

new_content = re.sub(pattern, replacement, content)

with open('accounts/templates/accounts/profile.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Fixed profile.html template variable')
