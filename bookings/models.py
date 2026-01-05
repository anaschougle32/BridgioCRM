from django.db import models
from django.db.models import Sum
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from projects.models import Project
from leads.models import Lead
from channel_partners.models import ChannelPartner

User = get_user_model()


class Booking(models.Model):
    """Booking Entity - One lead can have multiple bookings (e.g., investor booking multiple units)"""
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='bookings')
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
    
    def calculate_and_create_commissions(self):
        """Automatically calculate and create commissions for CP and employees"""
        from django.utils import timezone
        
        # CP Commission
        if self.channel_partner and self.cp_commission_percent > 0:
            cp_commission = Commission.objects.filter(
                booking=self,
                commission_type='cp',
                channel_partner=self.channel_partner
            ).first()
            
            if not cp_commission:
                cp_commission = Commission(
                    booking=self,
                    commission_type='cp',
                    channel_partner=self.channel_partner,
                    commission_percent=self.cp_commission_percent,
                    calculation_basis='booking_amount'
                )
            
            cp_commission.calculate_commission()
            cp_commission.save()
        
        # Employee Commissions
        employee_commissions = [
            ('closing_manager', self.credited_to_closing_manager, self.project.default_commission_percent),
            ('sourcing_manager', self.credited_to_sourcing_manager, 1.0),  # Default 1% for sourcing
            ('telecaller', self.credited_to_telecaller, 0.5),  # Default 0.5% for telecaller
        ]
        
        for role, employee, default_percent in employee_commissions:
            if employee:
                # Get commission percent from project or use default
                commission_percent = default_percent
                if role == 'closing_manager':
                    commission_percent = self.project.default_commission_percent
                
                emp_commission = Commission.objects.filter(
                    booking=self,
                    commission_type='employee',
                    employee=employee
                ).first()
                
                if not emp_commission:
                    emp_commission = Commission(
                        booking=self,
                        commission_type='employee',
                        employee=employee,
                        commission_percent=commission_percent,
                        calculation_basis='booking_amount'
                    )
                
                emp_commission.calculate_commission()
                emp_commission.save()
    
    @property
    def total_commission_amount(self):
        """Total commission amount for this booking"""
        return self.commissions.aggregate(total=Sum('commission_amount'))['total'] or 0
    
    @property
    def pending_commissions(self):
        """Get pending commissions for this booking"""
        return self.commissions.filter(status='pending')
    
    @property
    def approved_commissions(self):
        """Get approved commissions for this booking"""
        return self.commissions.filter(status='approved')
    
    @property
    def paid_commissions(self):
        """Get paid commissions for this booking"""
        return self.commissions.filter(status='paid')


class Commission(models.Model):
    """Commission tracking for Channel Partners and Employees"""
    
    COMMISSION_TYPE_CHOICES = [
        ('cp', 'Channel Partner'),
        ('employee', 'Employee'),
        ('referral', 'Referral'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='commissions')
    commission_type = models.CharField(max_length=20, choices=COMMISSION_TYPE_CHOICES)
    
    # Recipient
    channel_partner = models.ForeignKey(
        ChannelPartner,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commissions'
    )
    employee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commissions_received',
        limit_choices_to={'role__in': ['closing_manager', 'sourcing_manager', 'telecaller']}
    )
    
    # Commission details
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    commission_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    base_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)  # Booking amount or payment amount
    
    # Calculation basis
    calculation_basis = models.CharField(
        max_length=20,
        choices=[
            ('booking_amount', 'Booking Amount'),
            ('payment_received', 'Payment Received'),
            ('token_amount', 'Token Amount'),
        ],
        default='booking_amount'
    )
    
    # Status and tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commissions_approved'
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    paid_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commissions_paid'
    )
    
    # Notes
    notes = models.TextField(blank=True, help_text="Commission calculation notes or payment details")
    
    # System
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'commissions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['booking', 'commission_type']),
            models.Index(fields=['status', 'commission_type']),
            models.Index(fields=['channel_partner', 'status']),
            models.Index(fields=['employee', 'status']),
        ]
    
    def __str__(self):
        if self.channel_partner:
            return f"CP Commission - {self.channel_partner.cp_name} - ₹{self.commission_amount}"
        elif self.employee:
            return f"Employee Commission - {self.employee.username} - ₹{self.commission_amount}"
        return f"Commission - ₹{self.commission_amount}"
    
    def calculate_commission(self):
        """Calculate commission amount based on basis and percentage"""
        if self.calculation_basis == 'booking_amount':
            self.base_amount = self.booking.final_negotiated_price
        elif self.calculation_basis == 'payment_received':
            self.base_amount = self.booking.total_paid
        elif self.calculation_basis == 'token_amount':
            self.base_amount = self.booking.token_amount
        
        self.commission_amount = (self.base_amount * self.commission_percent) / 100
        return self.commission_amount
    
    def approve(self, approved_by):
        """Approve commission"""
        from django.utils import timezone
        self.status = 'approved'
        self.approved_at = timezone.now()
        self.approved_by = approved_by
        self.save()
    
    def mark_paid(self, paid_by):
        """Mark commission as paid"""
        from django.utils import timezone
        self.status = 'paid'
        self.paid_at = timezone.now()
        self.paid_by = paid_by
        self.save()


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
