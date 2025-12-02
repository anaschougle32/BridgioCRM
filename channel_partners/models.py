from django.db import models
from projects.models import Project
import random
import string


def generate_cp_id(cp_name):
    """Generate unique 5-character CP ID: 2 letters (first letter of first name + first letter of last name) + 3 random numbers"""
    name_parts = cp_name.strip().split()
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
    
    return cp_id


class ChannelPartner(models.Model):
    """Channel Partner Master Data"""
    
    CP_TYPE_CHOICES = [
        ('broker', 'Broker'),
        ('agency', 'Agency'),
        ('individual', 'Individual'),
    ]
    
    firm_name = models.CharField(max_length=200)
    cp_name = models.CharField(max_length=200)
    cp_unique_id = models.CharField(max_length=5, unique=True, blank=True, null=True, db_index=True)
    phone = models.CharField(max_length=15, unique=True)
    phone2 = models.CharField(max_length=15, blank=True, help_text="Secondary phone number")
    email = models.EmailField(blank=True)
    locality = models.CharField(max_length=200, blank=True, help_text="Locality/Area")
    team_size = models.IntegerField(null=True, blank=True, help_text="Number of team members")
    owner_name = models.CharField(max_length=200, blank=True, help_text="Owner/Proprietor name")
    owner_number = models.CharField(max_length=15, blank=True, help_text="Owner contact number")
    rera_id = models.CharField(max_length=50, blank=True)
    cp_type = models.CharField(max_length=20, choices=CP_TYPE_CHOICES, default='broker')
    working_area = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=[('active', 'Active'), ('inactive', 'Inactive')],
        default='active',
        db_index=True
    )
    
    # Relationships
    linked_projects = models.ManyToManyField(Project, related_name='channel_partners', blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'channel_partners'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.cp_unique_id:
            self.cp_unique_id = generate_cp_id(self.cp_name)
        super().save(*args, **kwargs)
    
    def get_formatted_phone(self):
        """Return phone number without decimal point if it's a float string"""
        if not self.phone:
            return ''
        # Remove .0 if present (from Excel float conversion)
        phone = str(self.phone)
        if phone.endswith('.0'):
            phone = phone[:-2]
        return phone
    
    def __str__(self):
        return f"{self.firm_name} - {self.cp_name} ({self.cp_unique_id})"
