"""Remove the duplicate ENHANCED STAT CARDS section that overrides our new vibrant styles."""
import re

with open('static/css/style.css', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the ENHANCED STAT CARDS section (lines 1331-1379)
# This section overrides our new vibrant gradient styles
pattern = r'/\* =+\s*\n\s*ENHANCED STAT CARDS\s*\n\s*=+ \*/.*?\.stat-card:hover \.stat-icon \{[^}]+\}'

new_content = re.sub(pattern, '/* ENHANCED STAT CARDS - Removed to use vibrant gradient styles */', content, flags=re.DOTALL)

with open('static/css/style.css', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Removed duplicate ENHANCED STAT CARDS section!')
