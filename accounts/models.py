from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom User Model with Role-Based Access Control"""
    
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('mandate_owner', 'Mandate Owner'),
        ('site_head', 'Site Head'),
        ('closing_manager', 'Closing Manager'),
        ('sourcing_manager', 'Sourcing Manager'),
        ('telecaller', 'Telecaller'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='telecaller')
    phone = models.CharField(max_length=15, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Relationships
    mandate_owner = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
        limit_choices_to={'role': 'mandate_owner'}
    )
    assigned_projects = models.ManyToManyField(
        'projects.Project',
        blank=True,
        related_name='assigned_telecallers',
        help_text='Projects assigned to this telecaller (for telecallers only)'
    )
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def save(self, *args, **kwargs):
        # Automatically set role to 'super_admin' if user is a superuser
        if self.is_superuser and self.role != 'super_admin':
            self.role = 'super_admin'
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def is_super_admin(self):
        return self.role == 'super_admin'
    
    def is_mandate_owner(self):
        return self.role == 'mandate_owner'
    
    def is_site_head(self):
        return self.role == 'site_head'
    
    def is_closing_manager(self):
        return self.role == 'closing_manager'
    
    def is_sourcing_manager(self):
        return self.role == 'sourcing_manager'
    
    def is_telecaller(self):
        return self.role == 'telecaller'


class AuditLog(models.Model):
    """System-wide audit logging"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    changes = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.model_name}"
