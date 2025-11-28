"""
Script to generate CP unique IDs for existing Channel Partners
Run: python manage.py shell < generate_cp_ids.py
Or: python manage.py shell
Then: exec(open('generate_cp_ids.py').read())
"""
from channel_partners.models import ChannelPartner
import random

cps = ChannelPartner.objects.filter(cp_unique_id__isnull=True) | ChannelPartner.objects.filter(cp_unique_id='')
count = 0

for cp in cps:
    # Generate CP ID
    name_parts = cp.cp_name.strip().split()
    if len(name_parts) >= 2:
        first_letter = name_parts[0][0].upper() if name_parts[0] else 'X'
        last_letter = name_parts[-1][0].upper() if name_parts[-1] else 'X'
    elif len(name_parts) == 1:
        first_letter = name_parts[0][0].upper() if len(name_parts[0]) > 0 else 'X'
        last_letter = name_parts[0][1].upper() if len(name_parts[0]) > 1 else 'X'
    else:
        first_letter = 'X'
        last_letter = 'X'
    
    # Generate 3 random numbers
    numbers = ''.join([str(random.randint(0, 9)) for _ in range(3)])
    cp_id = f"{first_letter}{last_letter}{numbers}"
    
    # Ensure uniqueness
    while ChannelPartner.objects.filter(cp_unique_id=cp_id).exists():
        numbers = ''.join([str(random.randint(0, 9)) for _ in range(3)])
        cp_id = f"{first_letter}{last_letter}{numbers}"
    
    cp.cp_unique_id = cp_id
    cp.save()
    count += 1
    print(f"[OK] Generated CP ID {cp_id} for {cp.cp_name}")

print(f"\n[OK] Generated {count} CP IDs")

