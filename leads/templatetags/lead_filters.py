from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    if dictionary is None:
        return {}
    return dictionary.get(key, {})

@register.filter
def first(queryset):
    """Get first item from queryset"""
    if queryset is None:
        return None
    try:
        if hasattr(queryset, 'first'):
            return queryset.first()
        elif hasattr(queryset, '__iter__'):
            return next(iter(queryset), None)
        return None
    except (StopIteration, TypeError):
        return None

