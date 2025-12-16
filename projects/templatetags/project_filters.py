from django import template

register = template.Library()


@register.filter
def floor_display_name(floor_num):
    """
    Convert floor number to display name.
    Floor 1 = Ground (G)
    Floor 2 = 1st Floor
    Floor 3 = 2nd Floor
    etc.
    """
    if floor_num == 1:
        return "Ground (G)"
    elif floor_num == 2:
        return "1st Floor"
    elif floor_num == 3:
        return "2nd Floor"
    elif floor_num == 4:
        return "3rd Floor"
    else:
        return f"{floor_num - 1}th Floor"

