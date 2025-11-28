from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, AuditLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'role', 'phone', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'is_staff', 'is_superuser']
    search_fields = ['username', 'email', 'phone']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Bridgio CRM Fields', {
            'fields': ('role', 'phone', 'mandate_owner')
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Bridgio CRM Fields', {
            'fields': ('role', 'phone', 'mandate_owner')
        }),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'model_name', 'object_id', 'created_at']
    list_filter = ['action', 'model_name', 'created_at']
    search_fields = ['user__username', 'action', 'model_name']
    readonly_fields = ['user', 'action', 'model_name', 'object_id', 'changes', 'ip_address', 'user_agent', 'created_at']
