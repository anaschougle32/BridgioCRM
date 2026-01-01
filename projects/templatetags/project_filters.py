from django import template

register = template.Library()


@register.filter
def floor_display_name(floor_num):
    """
    Convert floor number to display name.
    Floor 0 = Ground Floor (G)
    Floor 1 = 1st Floor
    Floor 2 = 2nd Floor
    Floor 3 = 3rd Floor
    etc.
    """
    if floor_num == 0:
        return "Ground Floor (G)"
    elif floor_num == 1:
        return "1st Floor"
    elif floor_num == 2:
        return "2nd Floor"
    elif floor_num == 3:
        return "3rd Floor"
    elif floor_num == 4:
        return "4th Floor"
    else:
        return f"{floor_num}th Floor"

