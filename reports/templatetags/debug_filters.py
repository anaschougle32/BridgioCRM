from django import template

register = template.Library()

@register.filter
def debug_type(value):
    """Debug filter to show the type of a value"""
    return f"{value} (type: {type(value).__name__})"

@register.filter
def debug_iterable(value):
    """Debug filter to show if value is iterable and its contents"""
    try:
        if hasattr(value, '__iter__') and not isinstance(value, (str, bytes)):
            return f"Iterable: [{', '.join(str(item) for item in value)}]"
        else:
            return f"Not iterable: {value}"
    except:
        return f"Error checking: {value}"
