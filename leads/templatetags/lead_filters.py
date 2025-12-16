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

@register.filter
def split_by_timestamp(notes_text):
    """Split notes by timestamp markers and return list of note objects"""
    if not notes_text:
        return []
    import re
    # Split by timestamp pattern: --- YYYY-MM-DD HH:MM:SS (User) ---
    pattern = r'\n\n--- (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \((.+?)\) ---\n'
    parts = re.split(pattern, notes_text)
    
    notes = []
    # First part might be initial content without timestamp
    if parts[0].strip():
        notes.append({'timestamp': None, 'user': None, 'content': parts[0].strip()})
    
    # Process pairs of (timestamp, user, content)
    for i in range(1, len(parts), 3):
        if i + 2 < len(parts):
            timestamp = parts[i]
            user = parts[i + 1]
            content = parts[i + 2].strip() if i + 2 < len(parts) else ''
            if content:
                notes.append({'timestamp': timestamp, 'user': user, 'content': content})
        elif i + 1 < len(parts):
            # Last part without timestamp
            content = parts[i].strip()
            if content:
                notes.append({'timestamp': None, 'user': None, 'content': content})
    
    return notes if notes else [{'timestamp': None, 'user': None, 'content': notes_text}]

