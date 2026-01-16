
import os

print("--- emi_list_v2.html ---")
try:
    with open(r'd:\Projects\Master-Architect\core\templates\core\emi_list_v2.html', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if 'selected_status' in line:
                print(f"{i+1}: {line.strip()}")
except Exception as e:
    print(f"Error reading template: {e}")

print("\n--- core/views.py ---")
try:
    with open(r'd:\Projects\Master-Architect\core\views.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if 'emi_list_v2.html' in line:
                print(f"{i+1}: {line.strip()}")
except Exception as e:
    print(f"Error reading view: {e}")
