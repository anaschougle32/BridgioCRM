from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def format_price(value):
    """Format price: if >= 100L, show in Cr with decimals, otherwise show in L"""
    if value is None:
        return "—"
    
    try:
        if isinstance(value, Decimal):
            value = float(value)
        else:
            value = float(value)
    except (ValueError, TypeError):
        return "—"
    
    # Convert to Lakhs
    lakhs = value / 100000
    
    if lakhs >= 100:
        # Show in Crores with 2 decimal places
        crores = lakhs / 100
        return f"₹{crores:.2f} Cr"
    else:
        # Show in Lakhs with 2 decimal places
        return f"₹{lakhs:.2f} L"

@register.filter
def format_price_simple(value):
    """Format price: if >= 100L, show in Cr, otherwise show in L (no decimals)"""
    if value is None:
        return "—"
    
    try:
        if isinstance(value, Decimal):
            value = float(value)
        else:
            value = float(value)
    except (ValueError, TypeError):
        return "—"
    
    # Convert to Lakhs
    lakhs = value / 100000
    
    if lakhs >= 100:
        # Show in Crores
        crores = lakhs / 100
        return f"₹{int(crores)} Cr" if crores == int(crores) else f"₹{crores:.1f} Cr"
    else:
        # Show in Lakhs
        return f"₹{int(lakhs)} L" if lakhs == int(lakhs) else f"₹{lakhs:.1f} L"

@register.filter
def mul(value, arg):
    """Multiply value by arg"""
    try:
        if isinstance(value, Decimal):
            value = float(value)
        if isinstance(arg, Decimal):
            arg = float(arg)
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

