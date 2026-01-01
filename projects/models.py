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
    starting_price_unit = models.CharField(max_length=10, choices=[('lakhs', 'Lakhs'), ('crores', 'Crores')], default='lakhs', blank=True)
    ending_price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    ending_price_unit = models.CharField(max_length=10, choices=[('lakhs', 'Lakhs'), ('crores', 'Crores')], default='lakhs', blank=True)
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
        """Calculate total residential units - use TowerFloorConfig if available"""
        tower_configs = self.tower_floor_configs.all()
        if tower_configs.exists():
            # Use flexible tower structure
            return sum(tc.floors_count * tc.units_per_floor for tc in tower_configs if not tc.is_commercial)
        # Fallback to legacy calculation
        return self.number_of_towers * self.floors_per_tower * self.units_per_floor
    
    @property
    def total_commercial_units(self):
        """Calculate total commercial units - use TowerFloorConfig if available"""
        tower_configs = self.tower_floor_configs.filter(is_commercial=True)
        if tower_configs.exists():
            # Use flexible tower structure
            return sum(tc.floors_count * tc.units_per_floor for tc in tower_configs)
        # Fallback to legacy calculation
        if self.has_commercial:
            return self.commercial_floors * self.commercial_units_per_floor
        return 0
    
    @property
    def total_units(self):
        """Calculate total units (residential + commercial)"""
        return self.total_residential_units + self.total_commercial_units


class ProjectConfiguration(models.Model):
    """Project Configuration Types (1BHK, 2BHK, etc.) with detailed pricing and area information"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='configurations')
    name = models.CharField(max_length=50)  # e.g., "1BHK", "2BHK", "3BHK"
    description = models.TextField(blank=True)
    
    # Pricing (per sqft)
    price_per_sqft = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Price per square foot")
    
    # Charges (percentages and flat amounts)
    stamp_duty_percent = models.DecimalField(max_digits=5, decimal_places=2, default=5.00, help_text="Stamp duty percentage (default 5%)")
    gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=5.00, help_text="GST percentage (default 5%)")
    registration_charges = models.DecimalField(max_digits=10, decimal_places=2, default=30000.00, help_text="Registration charges (default ₹30,000)")
    legal_charges = models.DecimalField(max_digits=10, decimal_places=2, default=30000.00, help_text="Legal charges (default ₹30,000)")
    development_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Development charges (flat amount in ₹)")
    
    class Meta:
        db_table = 'project_configurations'
        unique_together = ['project', 'name']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.project.name} - {self.name}"
    
    def calculate_agreement_value(self, carpet_area=None, buildup_area=None):
        """Calculate agreement value based on area and price per sqft
        Formula: Agreement Value = price_per_sqft * buildup_area
        """
        if not self.price_per_sqft:
            return None
        
        # Use buildup area (as per requirement: price per sqft * buildup area)
        if not buildup_area:
            return None
        
        return self.price_per_sqft * buildup_area
    
    def calculate_total_cost(self, carpet_area=None, buildup_area=None):
        """Calculate total cost including all charges"""
        agreement_value = self.calculate_agreement_value(carpet_area, buildup_area)
        if not agreement_value:
            return None
        
        stamp_duty = agreement_value * (self.stamp_duty_percent / 100)
        gst = agreement_value * (self.gst_percent / 100)
        
        total = agreement_value + stamp_duty + gst + self.registration_charges + self.legal_charges + self.development_charges
        return {
            'agreement_value': agreement_value,
            'stamp_duty': stamp_duty,
            'gst': gst,
            'registration_charges': self.registration_charges,
            'legal_charges': self.legal_charges,
            'development_charges': self.development_charges,
            'total': total
        }


class ConfigurationAreaType(models.Model):
    """Different carpet area options for the same configuration (e.g., 1BHK can have 500 sqft or 600 sqft)"""
    configuration = models.ForeignKey(ProjectConfiguration, on_delete=models.CASCADE, related_name='area_types')
    carpet_area = models.DecimalField(max_digits=10, decimal_places=2, help_text="Carpet area in sqft")
    buildup_area = models.DecimalField(max_digits=10, decimal_places=2, help_text="Buildup area in sqft")
    rera_area = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="RERA area in sqft")
    description = models.CharField(max_length=200, blank=True, help_text="Optional description (e.g., 'Compact', 'Spacious')")
    
    class Meta:
        db_table = 'configuration_area_types'
        unique_together = ['configuration', 'carpet_area', 'buildup_area']
        ordering = ['carpet_area']
    
    def __str__(self):
        return f"{self.configuration.name} - {self.carpet_area} sqft (Carpet) / {self.buildup_area} sqft (Buildup)"
    
    def calculate_agreement_value(self):
        """Calculate agreement value for this area type"""
        return self.configuration.calculate_agreement_value(
            carpet_area=self.carpet_area,
            buildup_area=self.buildup_area
        )
    
    def calculate_total_cost(self):
        """Calculate total cost for this area type"""
        return self.configuration.calculate_total_cost(
            carpet_area=self.carpet_area,
            buildup_area=self.buildup_area
        )
    
    def get_display_name(self):
        """Get display name for dropdowns: e.g., '1BHK-379sqft'"""
        return f"{self.configuration.name}-{int(self.carpet_area)}sqft"


class ConfigurationFloorMapping(models.Model):
    """Map which configurations are available on which floors and how many units per floor"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='floor_configurations')
    configuration = models.ForeignKey(ProjectConfiguration, on_delete=models.CASCADE, related_name='floor_mappings')
    floor_number = models.IntegerField(help_text="Floor number (1 = Ground floor, 2 = First floor, etc.)")
    units_per_floor = models.IntegerField(default=1, help_text="Number of units of this configuration on this floor")
    unit_number_start = models.IntegerField(default=1, help_text="Starting unit number for this floor (e.g., 201 for floor 2, unit 1)")
    
    class Meta:
        db_table = 'configuration_floor_mappings'
        unique_together = ['project', 'configuration', 'floor_number']
        ordering = ['floor_number', 'configuration__name']
    
    def __str__(self):
        return f"{self.project.name} - Floor {self.floor_number} - {self.configuration.name} ({self.units_per_floor} units, starting from {self.unit_number_start})"
    
    def get_unit_numbers(self):
        """Get list of unit numbers for this floor mapping (e.g., [201, 202, 203])"""
        return [self.unit_number_start + i for i in range(self.units_per_floor)]


class UnitConfiguration(models.Model):
    """Map each individual unit to a specific configuration area type"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='unit_configurations')
    tower_number = models.IntegerField(default=1, help_text="Tower number (1, 2, 3, etc.)")
    floor_number = models.IntegerField(help_text="Floor number (1 = Ground floor, 2 = First floor, etc.)")
    unit_number = models.IntegerField(help_text="Unit number (e.g., 101, 102, 201, 202) - same numbers can exist in different towers")
    area_type = models.ForeignKey(ConfigurationAreaType, on_delete=models.SET_NULL, null=True, blank=True, 
                                  related_name='unit_configurations', 
                                  help_text="Configuration variant assigned to this unit (e.g., 1BHK-379sqft)")
    is_excluded = models.BooleanField(default=False, help_text="Exclude this unit (e.g., for commercial floors)")
    is_commercial = models.BooleanField(default=False, help_text="Is this unit on a commercial floor?")
    
    class Meta:
        db_table = 'unit_configurations'
        unique_together = ['project', 'tower_number', 'floor_number', 'unit_number']
        ordering = ['tower_number', 'floor_number', 'unit_number']
    
    def __str__(self):
        if self.is_excluded:
            return f"{self.project.name} - Tower {self.tower_number} - Floor {self.floor_number} - Unit {self.unit_number} (Excluded)"
        if self.area_type:
            return f"{self.project.name} - Tower {self.tower_number} - Floor {self.floor_number} - Unit {self.unit_number} - {self.area_type.configuration.name}-{self.area_type.carpet_area}sqft"
        return f"{self.project.name} - Tower {self.tower_number} - Floor {self.floor_number} - Unit {self.unit_number} (Unassigned)"


class TowerFloorConfig(models.Model):
    """Flexible tower/floor configuration - allows different floors per tower and units per floor"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tower_floor_configs')
    tower_number = models.IntegerField(help_text="Tower number (1, 2, 3, etc.)")
    floors_count = models.IntegerField(default=1, help_text="Number of floors in this tower")
    units_per_floor = models.IntegerField(default=1, help_text="Number of units per floor in this tower")
    is_commercial = models.BooleanField(default=False, help_text="Is this tower commercial?")
    
    class Meta:
        db_table = 'tower_floor_configs'
        unique_together = ['project', 'tower_number']
        ordering = ['tower_number']
    
    def __str__(self):
        return f"{self.project.name} - Tower {self.tower_number} ({self.floors_count} floors, {self.units_per_floor} units/floor)"


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


class HighrisePricing(models.Model):
    """Highrise Pricing Configuration - Optional feature for projects with floor-based pricing"""
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='highrise_pricing')
    
    # Enable/Disable highrise pricing
    is_enabled = models.BooleanField(default=False, help_text="Enable highrise pricing for this project")
    
    # Floor threshold - pricing changes after this floor
    floor_threshold = models.IntegerField(default=10, help_text="Floor number where pricing starts to change (e.g., 10 = floors 1-10 have base price, 11+ have increased price)")
    
    # Base price per sqft (used for floors up to threshold)
    base_price_per_sqft = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Base price per sqft for floors up to threshold")
    
    # Pricing type for floors above threshold
    PRICING_TYPE_CHOICES = [
        ('fixed_total', 'Fixed Total Price Addition'),
        ('fixed_sqft', 'Fixed Per Sqft Addition'),
        ('per_sqft', 'Per Sqft Addition'),
    ]
    pricing_type = models.CharField(max_length=20, choices=PRICING_TYPE_CHOICES, default='per_sqft', help_text="How price increases for floors above threshold")
    
    # Fixed total price increment (if pricing_type = 'fixed_total')
    fixed_price_increment = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Fixed total amount to add per range (if pricing_type = 'fixed_total') OR fixed per sqft amount (if pricing_type = 'fixed_sqft')")
    
    # Per sqft increment (if pricing_type = 'per_sqft')
    per_sqft_increment = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Amount to add per sqft per floor above threshold (e.g., 20 = ₹20/sqft per floor)")
    
    # Development charges type
    DEV_CHARGES_TYPE_CHOICES = [
        ('fixed', 'Fixed Amount'),
        ('per_sqft', 'Per Sqft'),
    ]
    development_charges_type = models.CharField(max_length=20, choices=DEV_CHARGES_TYPE_CHOICES, default='fixed', help_text="How development charges are calculated")
    
    # Development charges - fixed
    development_charges_fixed = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Fixed development charges amount (if development_charges_type = 'fixed')")
    
    # Development charges - per sqft
    development_charges_per_sqft = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Development charges per sqft (if development_charges_type = 'per_sqft')")
    
    # Parking
    parking_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Parking price")
    parking_negotiable = models.BooleanField(default=False, help_text="Is parking price negotiable?")
    include_parking_in_calculation = models.BooleanField(default=True, help_text="Include parking in total calculation")
    
    class Meta:
        db_table = 'highrise_pricing'
    
    def __str__(self):
        return f"{self.project.name} - Highrise Pricing ({'Enabled' if self.is_enabled else 'Disabled'})"
    
    def calculate_price_per_sqft(self, floor_number, base_price_per_sqft=None):
        """Calculate price per sqft for a given floor number
        
        Range-based pricing: Increment is added for every threshold range.
        Example: If threshold=4, increment=100, base=6500
        - Floors 0-4: ₹6500 (base price)
        - Floors 5-8: ₹6600 (base + 100, 1st range above threshold)
        - Floors 9-12: ₹6700 (base + 200, 2nd range above threshold)
        - Floors 13-16: ₹6800 (base + 300, 3rd range above threshold)
        
        Note: For 'fixed_total' pricing type, this returns the base price per sqft only.
        Use calculate_total_price_increment() to get the fixed total increment.
        """
        if not self.is_enabled:
            return base_price_per_sqft or 0
        
        # Use provided base_price_per_sqft or fallback to model's base_price_per_sqft
        base_price = base_price_per_sqft or self.base_price_per_sqft or 0
        
        if floor_number <= self.floor_threshold:
            return base_price
        
        # Calculate which range the floor falls into
        # Floors above threshold are divided into ranges of threshold size
        floors_above_threshold = floor_number - self.floor_threshold
        range_number = ((floors_above_threshold - 1) // self.floor_threshold) + 1
        
        if self.pricing_type == 'fixed_total':
            # For fixed total, return base price per sqft (increment is added to total separately)
            return base_price
        elif self.pricing_type == 'fixed_sqft':
            # Fixed per sqft addition per range
            return base_price + (self.fixed_price_increment * range_number)
        else:
            # Per sqft addition per range
            return base_price + (self.per_sqft_increment * range_number)
    
    def calculate_total_price_increment(self, floor_number):
        """Calculate fixed total price increment for a given floor number
        
        Only applicable when pricing_type = 'fixed_total'.
        Returns the fixed amount to add to the total unit price.
        
        Example: If threshold=4, fixed_increment=100000
        - Floors 0-4: ₹0 (no increment)
        - Floors 5-8: ₹100,000 (1st range above threshold)
        - Floors 9-12: ₹200,000 (2nd range above threshold)
        """
        if not self.is_enabled or self.pricing_type != 'fixed_total':
            return 0
        
        if floor_number <= self.floor_threshold:
            return 0
        
        # Calculate which range the floor falls into
        floors_above_threshold = floor_number - self.floor_threshold
        range_number = ((floors_above_threshold - 1) // self.floor_threshold) + 1
        
        return self.fixed_price_increment * range_number
    
    def calculate_development_charges(self, buildup_area=None):
        """Calculate development charges based on type"""
        if not self.is_enabled:
            return 0
        
        if self.development_charges_type == 'fixed':
            return self.development_charges_fixed
        else:
            if not buildup_area:
                return 0
            return self.development_charges_per_sqft * buildup_area
    
    def get_parking_price(self):
        """Get parking price (returns 0 if not included in calculation)"""
        if not self.include_parking_in_calculation:
            return 0
        return self.parking_price
