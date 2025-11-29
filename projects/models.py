from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Project(models.Model):
    """Project/Mandate Entity"""
    
    PROJECT_TYPE_CHOICES = [
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('mixed', 'Mixed'),
    ]
    
    name = models.CharField(max_length=200)
    builder_name = models.CharField(max_length=200)
    location = models.TextField()
    rera_id = models.CharField(max_length=50, blank=True)
    project_type = models.CharField(max_length=20, choices=PROJECT_TYPE_CHOICES, default='residential')
    starting_price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    inventory_summary = models.TextField(blank=True)
    
    # Project Image
    image = models.ImageField(upload_to='projects/', blank=True, null=True, help_text="Cover image for project cards and detail page")
    
    # Tower and Unit Structure (for BookMyShow-style UI)
    number_of_towers = models.IntegerField(default=1, help_text="Total number of towers")
    floors_per_tower = models.IntegerField(default=1, help_text="Number of floors in each tower")
    units_per_floor = models.IntegerField(default=1, help_text="Number of residential units per floor")
    has_commercial = models.BooleanField(default=False, help_text="Does this project have commercial units?")
    commercial_floors = models.IntegerField(default=0, help_text="Number of floors with commercial units")
    commercial_units_per_floor = models.IntegerField(default=0, help_text="Number of commercial units per floor")
    
    # Geo coordinates for attendance
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Settings
    default_commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    auto_assignment_strategy = models.CharField(
        max_length=20,
        choices=[('round_robin', 'Round Robin'), ('manual', 'Manual')],
        default='manual'
    )
    
    # Relationships
    mandate_owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='projects',
        limit_choices_to={'role': 'mandate_owner'}
    )
    site_head = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_projects',
        limit_choices_to={'role': 'site_head'}
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'projects'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    @property
    def total_residential_units(self):
        """Calculate total residential units"""
        return self.number_of_towers * self.floors_per_tower * self.units_per_floor
    
    @property
    def total_commercial_units(self):
        """Calculate total commercial units"""
        if self.has_commercial:
            return self.commercial_floors * self.commercial_units_per_floor
        return 0
    
    @property
    def total_units(self):
        """Calculate total units (residential + commercial)"""
        return self.total_residential_units + self.total_commercial_units


class ProjectConfiguration(models.Model):
    """Project Configuration Types (1BHK, 2BHK, etc.)"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='configurations')
    name = models.CharField(max_length=50)  # e.g., "1BHK", "2BHK", "3BHK"
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'project_configurations'
        unique_together = ['project', 'name']
    
    def __str__(self):
        return f"{self.project.name} - {self.name}"


class PaymentMilestone(models.Model):
    """Payment Milestone Templates for Projects"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='payment_milestones')
    name = models.CharField(max_length=100)  # e.g., "Demand 1", "Demand 2", "On Booking"
    order = models.IntegerField(default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    class Meta:
        db_table = 'payment_milestones'
        ordering = ['order']
        unique_together = ['project', 'name']
    
    def __str__(self):
        return f"{self.project.name} - {self.name}"
