from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from projects.models import Project
from channel_partners.models import ChannelPartner

User = get_user_model()


class GlobalConfiguration(models.Model):
    """Global Configuration Types - Not project-specific"""
    CONFIGURATION_CHOICES = [
        ('1BHK', '1BHK'),
        ('2BHK', '2BHK'),
        ('3BHK', '3BHK'),
        ('4BHK', '4BHK'),
        ('5BHK', '5BHK'),
        ('PentHouse', 'PentHouse'),
        ('Villa', 'Villa'),
        ('Plot', 'Plot'),
    ]
    
    name = models.CharField(max_length=50, choices=CONFIGURATION_CHOICES, unique=True)
    display_name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text="Display order")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'global_configurations'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.display_name
    
    def save(self, *args, **kwargs):
        if not self.display_name:
            self.display_name = self.get_name_display()
        super().save(*args, **kwargs)


class Lead(models.Model):
    """Lead Entity - Master data, not tied to a single project"""
    
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    
    RESIDENCE_CHOICES = [
        ('own', 'Own'),
        ('rent', 'Rent'),
    ]
    
    OCCUPATION_CHOICES = [
        ('self_emp', 'Self Employed'),
        ('service', 'Service'),
        ('homemaker', 'Homemaker'),
        ('business', 'Business'),
        ('retired', 'Retired'),
        ('other', 'Other'),
    ]
    
    PURPOSE_CHOICES = [
        ('investment', 'Investment'),
        ('first_home', 'First Home'),
        ('second_home', 'Second Home'),
        ('retirement_home', 'Retirement Home'),
    ]
    
    VISIT_TYPE_CHOICES = [
        ('family', 'Family'),
        ('alone', 'Alone'),
    ]
    
    VISIT_SOURCE_CHOICES = [
        ('call', 'Call Generated'),
        ('cp', 'Channel Partner'),
        ('walkin', 'Direct Walk-in'),
    ]
    
    # Client Information (Master Data)
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=15, db_index=True, unique=True, help_text="Unique phone number - used for deduplication")
    email = models.EmailField(blank=True)
    age = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(18), MaxValueValidator(100)])
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    locality = models.CharField(max_length=200, blank=True)
    current_residence = models.CharField(max_length=10, choices=RESIDENCE_CHOICES, blank=True)
    occupation = models.CharField(max_length=20, choices=OCCUPATION_CHOICES, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    designation = models.CharField(max_length=200, blank=True)
    
    # Requirement Details (Global preferences - can be overridden per project)
    configurations = models.ManyToManyField(
        GlobalConfiguration,
        related_name='leads',
        blank=True,
        help_text="Preferred configurations (multiple selection)"
    )
    # Legacy fields - kept for backward compatibility during migration
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='legacy_leads',
        help_text="DEPRECATED: Use project_associations instead"
    )
    budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Overall budget preference")
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, blank=True)
    visit_type = models.CharField(max_length=10, choices=VISIT_TYPE_CHOICES, blank=True)
    is_first_visit = models.BooleanField(default=True)
    how_did_you_hear = models.CharField(max_length=200, blank=True)
    visit_source = models.CharField(
        max_length=20,
        choices=VISIT_SOURCE_CHOICES,
        blank=True,
        null=True,
        help_text="How was this visit generated? (Call, CP, or Walk-in)"
    )
    
    # CP Information (Optional for New Visit, Mandatory for Pretag)
    channel_partner = models.ForeignKey(
        ChannelPartner,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leads'
    )
    cp_firm_name = models.CharField(max_length=200, blank=True)  # Fallback if CP not in master
    cp_name = models.CharField(max_length=200, blank=True)
    cp_phone = models.CharField(max_length=15, blank=True)
    cp_rera_number = models.CharField(max_length=50, blank=True)
    
    # Notes - Critical for lead management
    notes = models.TextField(blank=True, help_text="General notes about the lead, conversations, preferences, etc.")
    
    # System Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_leads'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)
    
    # Legacy field - kept for backward compatibility (will be removed in future migration)
    is_pretagged = models.BooleanField(default=False, help_text="DEPRECATED: Use LeadProjectAssociation.is_pretagged instead")
    
    class Meta:
        db_table = 'leads'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['is_archived', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.phone}"
    
    @property
    def primary_project(self):
        """Get the primary project (first active association)"""
        association = self.project_associations.filter(is_archived=False).first()
        return association.project if association else None
    
    @property
    def all_projects(self):
        """Get all projects this lead is associated with"""
        return Project.objects.filter(
            lead_associations__lead=self,
            lead_associations__is_archived=False
        ).distinct()


class LeadProjectAssociation(models.Model):
    """Association between Lead and Project - stores project-specific data"""
    
    PRETAG_STATUS_CHOICES = [
        ('pending_verification', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    
    LEAD_STATUS_CHOICES = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('visit_scheduled', 'Visit Scheduled'),
        ('visit_completed', 'Visit Completed'),
        ('discussion', 'Discussion'),
        ('hot', 'Hot'),
        ('ready_to_book', 'Ready to Book'),
        ('booked', 'Booked'),
        ('lost', 'Lost'),
    ]
    
    # Core Association
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='project_associations')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='lead_associations')
    
    # Project-Specific Status
    status = models.CharField(max_length=20, choices=LEAD_STATUS_CHOICES, default='new', db_index=True)
    
    # Pretagging Flags (project-specific)
    is_pretagged = models.BooleanField(default=False)
    pretag_status = models.CharField(
        max_length=20,
        choices=PRETAG_STATUS_CHOICES,
        default='pending_verification',
        blank=True
    )
    phone_verified = models.BooleanField(default=False)
    
    # Assignment (project-specific)
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_lead_associations',
        limit_choices_to={'role__in': ['closing_manager', 'telecaller', 'sourcing_manager']}
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lead_association_assignments',
        limit_choices_to={'role__in': ['super_admin', 'mandate_owner', 'site_head']}
    )
    
    # Project-Specific Notes
    notes = models.TextField(blank=True, help_text="Project-specific notes")
    
    # System Metadata
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_lead_associations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'lead_project_associations'
        unique_together = ['lead', 'project']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'status', 'is_archived']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['is_pretagged', 'pretag_status']),
        ]
    
    def __str__(self):
        return f"{self.lead.name} - {self.project.name} ({self.status})"


class OtpLog(models.Model):
    """OTP Verification Logs"""
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='otp_logs')
    otp_hash = models.CharField(max_length=128)  # HMAC-SHA256 hash
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    gateway_response = models.TextField(blank=True, help_text='SMS gateway response (JSON)')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'otp_logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"OTP for {self.lead.name} - {'Verified' if self.is_verified else 'Pending'}"


class CallLog(models.Model):
    """Call logs for telecallers"""
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='call_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='call_logs')
    call_date = models.DateTimeField()
    duration_minutes = models.IntegerField(null=True, blank=True)
    outcome = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'call_logs'
        ordering = ['-call_date']
    
    def __str__(self):
        return f"Call - {self.lead.name} - {self.call_date}"


class FollowUpReminder(models.Model):
    """Follow-up reminders for leads"""
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='reminders')
    reminder_date = models.DateTimeField()
    notes = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'follow_up_reminders'
        ordering = ['reminder_date']
    
    def __str__(self):
        return f"Reminder - {self.lead.name} - {self.reminder_date}"


class DailyAssignmentQuota(models.Model):
    """Daily lead assignment quotas per employee per project"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='assignment_quotas')
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignment_quotas')
    daily_quota = models.IntegerField(default=5)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'daily_assignment_quotas'
        unique_together = ['project', 'employee']
    
    def __str__(self):
        return f"{self.employee.username} - {self.project.name} - {self.daily_quota}/day"
