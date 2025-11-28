from django.contrib import admin
from .models import ChannelPartner


@admin.register(ChannelPartner)
class ChannelPartnerAdmin(admin.ModelAdmin):
    list_display = ['firm_name', 'cp_name', 'phone', 'cp_type', 'is_active', 'created_at']
    list_filter = ['cp_type', 'is_active', 'created_at']
    search_fields = ['firm_name', 'cp_name', 'phone', 'email', 'rera_id']
    filter_horizontal = ['linked_projects']
