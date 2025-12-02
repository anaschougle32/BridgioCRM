from django.contrib import admin
from .models import Project, ProjectConfiguration, PaymentMilestone, ConfigurationAreaType, ConfigurationFloorMapping, UnitConfiguration


class ConfigurationAreaTypeInline(admin.TabularInline):
    model = ConfigurationAreaType
    extra = 1
    fields = ('carpet_area', 'buildup_area', 'rera_area', 'description')


class ProjectConfigurationInline(admin.TabularInline):
    model = ProjectConfiguration
    extra = 1
    fields = ('name', 'description', 'price_per_sqft', 'stamp_duty_percent', 'gst_percent', 'registration_charges', 'legal_charges', 'development_charges')
    inlines = [ConfigurationAreaTypeInline]


class ConfigurationFloorMappingInline(admin.TabularInline):
    model = ConfigurationFloorMapping
    extra = 1
    fields = ('configuration', 'floor_number', 'units_per_floor', 'unit_number_start')


class PaymentMilestoneInline(admin.TabularInline):
    model = PaymentMilestone
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'builder_name', 'project_type', 'mandate_owner', 'site_head', 'is_active']
    list_filter = ['project_type', 'is_active', 'created_at']
    search_fields = ['name', 'builder_name', 'location', 'rera_id']
    inlines = [ProjectConfigurationInline, PaymentMilestoneInline, ConfigurationFloorMappingInline]
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
    list_display = ['name', 'project', 'price_per_sqft', 'stamp_duty_percent', 'gst_percent']
    list_filter = ['project']
    search_fields = ['name', 'project__name']
    inlines = [ConfigurationAreaTypeInline]


@admin.register(ConfigurationAreaType)
class ConfigurationAreaTypeAdmin(admin.ModelAdmin):
    list_display = ['configuration', 'carpet_area', 'buildup_area', 'rera_area', 'description']
    list_filter = ['configuration__project']
    search_fields = ['configuration__name', 'description']


@admin.register(ConfigurationFloorMapping)
class ConfigurationFloorMappingAdmin(admin.ModelAdmin):
    list_display = ['project', 'configuration', 'floor_number', 'units_per_floor', 'unit_number_start']
    list_filter = ['project', 'floor_number']
    search_fields = ['project__name', 'configuration__name']


@admin.register(PaymentMilestone)
class PaymentMilestoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'order', 'percentage']
    list_filter = ['project']
    search_fields = ['name', 'project__name']


@admin.register(UnitConfiguration)
class UnitConfigurationAdmin(admin.ModelAdmin):
    list_display = ['project', 'tower_number', 'floor_number', 'unit_number', 'area_type', 'is_excluded']
    list_filter = ['project', 'tower_number', 'floor_number', 'is_excluded']
    search_fields = ['project__name', 'unit_number']
    ordering = ['project', 'tower_number', 'floor_number', 'unit_number']
