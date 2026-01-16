"""
Custom template filters for analytics app.
"""
from django import template

register = template.Library()


@register.filter
def humanize_name(value):
    """
    Convert snake_case or underscore-separated names to Title Case.
    Example: 'raju_super' -> 'Raju Super'
    """
    if not value:
        return value
    return value.replace('_', ' ').title()


@register.filter
def cap_percentage(value, max_val=100):
    """
    Cap a percentage value for display purposes.
    Returns the capped value for use in progress bar width.
    Example: 297 -> 100 (for progress bar width)
    """
    try:
        num = float(value)
        return min(num, float(max_val))
    except (ValueError, TypeError):
        return 0


@register.filter
def format_percentage(value):
    """
    Format a percentage value with one decimal place.
    Handles both decimal (0.297) and percentage (29.7) formats.
    """
    try:
        num = float(value)
        # If value seems to be a decimal ratio (less than 2), convert to percentage
        if num < 2 and num > 0:
            num = num * 100
        return f"{num:.1f}%"
    except (ValueError, TypeError):
        return "0%"
