from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from projects.models import Project

User = get_user_model()


class Attendance(models.Model):
    """Attendance with Geo-location and Selfie"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendances')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='attendances', null=True, blank=True)
    
    # Geo-location
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy_radius = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )  # in meters
    
    # Selfie
    selfie_photo = models.ImageField(upload_to='attendance/selfies/')
    
    # Metadata
    check_in_time = models.DateTimeField(auto_now_add=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Validation
    is_within_radius = models.BooleanField(default=False)  # Must be within 20m
    is_valid = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'attendances'
        ordering = ['-check_in_time']
        indexes = [
            models.Index(fields=['user', 'check_in_time']),
            models.Index(fields=['project', 'check_in_time']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.check_in_time.date()} - {self.project.name if self.project else 'Office'}"
