from django.contrib import admin
from .models import Project, ProjectConfiguration, PaymentMilestone


class ProjectConfigurationInline(admin.TabularInline):
    model = ProjectConfiguration
    extra = 1


class PaymentMilestoneInline(admin.TabularInline):
    model = PaymentMilestone
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'builder_name', 'project_type', 'mandate_owner', 'site_head', 'is_active']
    list_filter = ['project_type', 'is_active', 'created_at']
    search_fields = ['name', 'builder_name', 'location', 'rera_id']
    inlines = [ProjectConfigurationInline, PaymentMilestoneInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'builder_name', 'location', 'rera_id', 'project_type')
        }),
        ('Pricing & Inventory', {
            'fields': ('starting_price', 'inventory_summary')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude')
        }),
        ('Settings', {
            'fields': ('default_commission_percent', 'auto_assignment_strategy')
        }),
        ('Relationships', {
            'fields': ('mandate_owner', 'site_head')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(ProjectConfiguration)
class ProjectConfigurationAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'description']
    list_filter = ['project']
    search_fields = ['name', 'project__name']


@admin.register(PaymentMilestone)
class PaymentMilestoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'order', 'percentage']
    list_filter = ['project']
    search_fields = ['name', 'project__name']
