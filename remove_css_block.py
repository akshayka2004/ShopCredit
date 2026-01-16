"""Remove the duplicate ENHANCED STAT CARDS section effectively."""
import re

with open('static/css/style.css', 'r', encoding='utf-8') as f:
    content = f.read()

# Define the start and end markers for the section to remove
start_marker = "/* ============================================\n   ENHANCED STAT CARDS"
end_marker = "/* ============================================\n   EMI TIMELINE"

# Find start index
start_idx = content.find(start_marker)
if start_idx == -1:
    print("Could not find start marker!")
else:
    # Find end index (start of EMI timeline)
    end_idx = content.find(end_marker, start_idx)
    if end_idx == -1:
        print("Could not find end marker!")
    else:
        # Remove the section (keep the end marker)
        new_content = content[:start_idx] + content[end_idx:]
        
        with open('static/css/style.css', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Successfully removed ENHANCED STAT CARDS section!")
