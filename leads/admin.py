from django.contrib import admin
from .models import Lead, OtpLog, CallLog, FollowUpReminder, DailyAssignmentQuota


@admin.register(DailyAssignmentQuota)
class DailyAssignmentQuotaAdmin(admin.ModelAdmin):
    list_display = ['employee', 'project', 'daily_quota', 'is_active', 'created_by', 'created_at']
    list_filter = ['is_active', 'project', 'created_at']
    search_fields = ['employee__username', 'project__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'project', 'status', 'is_pretagged', 'pretag_status', 'assigned_to', 'created_at']
    list_filter = ['status', 'is_pretagged', 'pretag_status', 'project', 'created_at']
    search_fields = ['name', 'phone', 'email', 'project__name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Client Information', {
            'fields': ('name', 'phone', 'email', 'age', 'gender', 'locality', 'current_residence', 
                      'occupation', 'company_name', 'designation')
        }),
        ('Requirement Details', {
            'fields': ('project', 'configuration', 'budget', 'purpose', 'visit_type', 
                      'is_first_visit', 'how_did_you_hear')
        }),
        ('Channel Partner', {
            'fields': ('channel_partner', 'cp_firm_name', 'cp_name', 'cp_phone', 'cp_rera_number')
        }),
        ('Pretagging', {
            'fields': ('is_pretagged', 'pretag_status', 'phone_verified')
        }),
        ('Assignment', {
            'fields': ('status', 'assigned_to', 'assigned_at', 'assigned_by')
        }),
        ('System', {
            'fields': ('created_by', 'created_at', 'updated_at', 'is_archived')
        }),
    )


@admin.register(OtpLog)
class OtpLogAdmin(admin.ModelAdmin):
    list_display = ['lead', 'is_verified', 'attempts', 'expires_at', 'created_at', 'sent_by']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['lead__name', 'lead__phone']
    readonly_fields = ['created_at', 'otp_hash']  # Never show OTP hash in admin, but make it readonly if shown
    exclude = ['otp_hash']  # Don't show OTP hash in admin forms for security


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display = ['lead', 'called_by', 'outcome', 'call_duration', 'created_at']
    list_filter = ['outcome', 'created_at']
    search_fields = ['lead__name', 'lead__phone', 'called_by__username']


@admin.register(FollowUpReminder)
class FollowUpReminderAdmin(admin.ModelAdmin):
    list_display = ['lead', 'reminder_date', 'is_completed', 'created_by', 'created_at']
    list_filter = ['is_completed', 'reminder_date']
    search_fields = ['lead__name', 'lead__phone']
