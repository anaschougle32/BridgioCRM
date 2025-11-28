from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from projects.models import Project, ProjectConfiguration
from channel_partners.models import ChannelPartner

User = get_user_model()


class Lead(models.Model):
    """Lead Entity - New Visit + Pretagging"""
    
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
    
    # Client Information
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=15, db_index=True)
    email = models.EmailField(blank=True)
    age = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(18), MaxValueValidator(100)])
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    locality = models.CharField(max_length=200, blank=True)
    current_residence = models.CharField(max_length=10, choices=RESIDENCE_CHOICES, blank=True)
    occupation = models.CharField(max_length=20, choices=OCCUPATION_CHOICES, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    designation = models.CharField(max_length=200, blank=True)
    
    # Requirement Details
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='leads')
    configuration = models.ForeignKey(
        ProjectConfiguration,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leads'
    )
    budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, blank=True)
    visit_type = models.CharField(max_length=10, choices=VISIT_TYPE_CHOICES, blank=True)
    is_first_visit = models.BooleanField(default=True)
    how_did_you_hear = models.CharField(max_length=200, blank=True)
    
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
    
    # Pretagging Flags
    is_pretagged = models.BooleanField(default=False)
    pretag_status = models.CharField(
        max_length=20,
        choices=PRETAG_STATUS_CHOICES,
        default='pending_verification',
        blank=True
    )
    phone_verified = models.BooleanField(default=False)
    
    # Lead Status
    status = models.CharField(max_length=20, choices=LEAD_STATUS_CHOICES, default='new', db_index=True)
    
    # Assignment
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_leads',
        limit_choices_to={'role__in': ['closing_manager', 'telecaller', 'sourcing_manager']}
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lead_assignments',
        limit_choices_to={'role__in': ['super_admin', 'mandate_owner', 'site_head']}
    )
    
    # System Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_leads')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'leads'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone', 'status']),
            models.Index(fields=['project', 'status']),
            models.Index(fields=['is_pretagged', 'pretag_status']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.phone} - {self.project.name}"


class OtpLog(models.Model):
    """OTP Verification Logs"""
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='otp_logs')
    otp_hash = models.CharField(max_length=64)  # SHA256 hash
    otp_code = models.CharField(max_length=6)  # For display purposes only (should be hashed in production)
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'otp_logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"OTP for {self.lead.name} - {self.otp_code}"


class CallLog(models.Model):
    """Call Logs for Leads"""
    
    OUTCOME_CHOICES = [
        ('connected', 'Connected'),
        ('not_reachable', 'Not Reachable'),
        ('switched_off', 'Switched Off'),
        ('wrong_number', 'Wrong Number'),
        ('busy', 'Busy'),
    ]
    
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='call_logs')
    called_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES)
    notes = models.TextField(blank=True)
    call_duration = models.IntegerField(null=True, blank=True)  # in seconds
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'call_logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Call to {self.lead.name} by {self.called_by}"


class FollowUpReminder(models.Model):
    """Follow-up Reminders for Leads"""
    
    REMINDER_TYPE_CHOICES = [
        ('callback', 'Callback'),
        ('payment_followup', 'Payment Follow-up'),
        ('visit_reminder', 'Visit Reminder'),
    ]
    
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='reminders')
    reminder_date = models.DateTimeField()
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPE_CHOICES, default='callback')
    notes = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'follow_up_reminders'
        ordering = ['reminder_date']
    
    def __str__(self):
        return f"Reminder for {self.lead.name} - {self.reminder_date}"


class DailyAssignmentQuota(models.Model):
    """Daily assignment quotas for employees per project"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='assignment_quotas')
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_quotas',
                                 limit_choices_to={'role__in': ['closing_manager', 'telecaller', 'sourcing_manager']})
    daily_quota = models.IntegerField(default=0, help_text="Number of leads to assign daily")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_quotas',
                                   limit_choices_to={'role__in': ['super_admin', 'site_head']})
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'daily_assignment_quotas'
        unique_together = ['project', 'employee']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.employee.username} - {self.project.name} - {self.daily_quota} leads/day"
