from django.contrib import admin
from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['user', 'project', 'check_in_time', 'check_out_time', 'is_within_radius', 'is_valid']
    list_filter = ['is_within_radius', 'is_valid', 'check_in_time', 'project']
    search_fields = ['user__username', 'project__name']
    readonly_fields = ['check_in_time', 'user_agent', 'ip_address']
