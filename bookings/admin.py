from django.contrib import admin
from .models import Booking, Payment


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['lead', 'project', 'unit_number', 'final_negotiated_price', 'token_amount', 'created_at']
    list_filter = ['project', 'created_at']
    search_fields = ['lead__name', 'lead__phone', 'unit_number', 'project__name']
    readonly_fields = ['created_at', 'updated_at', 'total_paid', 'remaining_balance']
    fieldsets = (
        ('Lead & Project', {
            'fields': ('lead', 'project')
        }),
        ('Unit Details', {
            'fields': ('tower_wing', 'unit_number', 'carpet_area', 'floor')
        }),
        ('Pricing', {
            'fields': ('final_negotiated_price', 'token_amount', 'token_receipt_proof')
        }),
        ('Channel Partner', {
            'fields': ('channel_partner', 'cp_commission_percent')
        }),
        ('System', {
            'fields': ('created_by', 'created_at', 'updated_at', 'is_archived', 'total_paid', 'remaining_balance')
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['booking', 'amount', 'payment_mode', 'payment_date', 'milestone', 'created_at']
    list_filter = ['payment_mode', 'payment_date', 'created_at']
    search_fields = ['booking__lead__name', 'booking__lead__phone', 'reference_number']
    readonly_fields = ['created_at', 'updated_at']
