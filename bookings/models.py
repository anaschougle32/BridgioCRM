from django.db import models
from django.db.models import Sum
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from projects.models import Project
from leads.models import Lead
from channel_partners.models import ChannelPartner

User = get_user_model()


class Booking(models.Model):
    """Booking Entity"""
    lead = models.OneToOneField(Lead, on_delete=models.CASCADE, related_name='booking')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='bookings')
    
    # Unit Details
    tower_wing = models.CharField(max_length=100, blank=True)
    unit_number = models.CharField(max_length=50)
    carpet_area = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    floor = models.IntegerField(null=True, blank=True)
    
    # Pricing
    final_negotiated_price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    token_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)]
    )
    token_receipt_proof = models.FileField(upload_to='bookings/receipts/', blank=True, null=True)
    
    # CP Details
    channel_partner = models.ForeignKey(
        ChannelPartner,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings'
    )
    cp_commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Credit Tracking (for performance metrics)
    credited_to_closing_manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='credited_bookings_closing',
        limit_choices_to={'role': 'closing_manager'},
        help_text="Closing manager who gets credit for this booking"
    )
    credited_to_sourcing_manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='credited_bookings_sourcing',
        limit_choices_to={'role': 'sourcing_manager'},
        help_text="Sourcing manager who gets credit for this booking (if CP lead)"
    )
    credited_to_telecaller = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='credited_bookings_telecaller',
        limit_choices_to={'role': 'telecaller'},
        help_text="Telecaller who gets credit for this booking (if telecaller-generated lead)"
    )
    
    # System
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_archived = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'bookings'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Booking - {self.lead.name} - {self.unit_number}"
    
    @property
    def total_paid(self):
        return self.payments.aggregate(total=Sum('amount'))['total'] or 0
    
    @property
    def remaining_balance(self):
        return self.final_negotiated_price - self.total_paid


class Payment(models.Model):
    """Payment Entries"""
    
    PAYMENT_MODE_CHOICES = [
        ('upi', 'UPI'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('rtgs', 'RTGS'),
        ('neft', 'NEFT'),
        ('card', 'Card'),
    ]
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODE_CHOICES)
    payment_date = models.DateField()
    milestone = models.ForeignKey(
        'projects.PaymentMilestone',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )
    reference_number = models.CharField(max_length=100, blank=True)
    receipt_proof = models.FileField(upload_to='payments/receipts/', blank=True, null=True)
    notes = models.TextField(blank=True)
    
    # System
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-payment_date', '-created_at']
    
    def __str__(self):
        return f"Payment - {self.booking.lead.name} - ₹{self.amount}"
