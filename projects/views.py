from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.http import JsonResponse
from .models import Project, ProjectConfiguration, PaymentMilestone, UnitConfiguration, ConfigurationAreaType
from accounts.models import User
from leads.models import Lead
from bookings.models import Booking, Payment
from decimal import Decimal


@login_required
def project_list(request):
    """List all projects - Super Admin and Mandate Owners see all, others see their projects"""
    if request.user.is_super_admin():
        projects = Project.objects.all()
    elif request.user.is_mandate_owner():
        # Mandate owners can see all projects
        projects = Project.objects.all()
    elif request.user.is_site_head():
        projects = Project.objects.filter(site_head=request.user)
    else:
        messages.error(request, 'You do not have permission to view projects.')
        return redirect('dashboard')
    
    # Annotate with stats
    projects = projects.annotate(
        lead_count=Count('leads', filter=~Q(leads__is_archived=True)),
        booking_count=Count('bookings', filter=~Q(bookings__is_archived=True)),
        revenue=Sum('bookings__payments__amount')
    ).order_by('-created_at')
    
    context = {
        'projects': projects,
    }
    return render(request, 'projects/list.html', context)


@login_required
def project_create(request):
    """Create new project - Super Admin and Mandate Owners"""
    if not (request.user.is_super_admin() or request.user.is_mandate_owner()):
        messages.error(request, 'You do not have permission to create projects.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        builder_name = request.POST.get('builder_name')
        location = request.POST.get('location')
        rera_id = request.POST.get('rera_id', '')
        project_type = request.POST.get('project_type')
        starting_price = request.POST.get('starting_price') or None
        starting_price_unit = request.POST.get('starting_price_unit', 'lakhs')
        ending_price = request.POST.get('ending_price') or None
        ending_price_unit = request.POST.get('ending_price_unit', 'lakhs')
        inventory_summary = request.POST.get('inventory_summary', '')
        
        # Convert price to actual decimal value based on unit
        if starting_price:
            starting_price = float(starting_price)
            if starting_price_unit == 'crores':
                starting_price = starting_price * 10000000
            else:  # lakhs
                starting_price = starting_price * 100000
        
        if ending_price:
            ending_price = float(ending_price)
            if ending_price_unit == 'crores':
                ending_price = ending_price * 10000000
            else:  # lakhs
                ending_price = ending_price * 100000
        latitude = request.POST.get('latitude') or None
        longitude = request.POST.get('longitude') or None
        default_commission_percent = request.POST.get('default_commission_percent') or 0
        auto_assignment_strategy = request.POST.get('auto_assignment_strategy', 'manual')
        site_head_id = request.POST.get('site_head') or None
        
        # Tower and Unit Structure
        number_of_towers = int(request.POST.get('number_of_towers', 1))
        floors_per_tower = int(request.POST.get('floors_per_tower', 1))
        units_per_floor = int(request.POST.get('units_per_floor', 1))
        has_commercial = request.POST.get('has_commercial') == 'on'
        commercial_floors = int(request.POST.get('commercial_floors', 0)) if has_commercial else 0
        commercial_units_per_floor = int(request.POST.get('commercial_units_per_floor', 0)) if has_commercial else 0
        
        project = Project.objects.create(
            name=name,
            builder_name=builder_name,
            location=location,
            rera_id=rera_id,
            project_type=project_type,
            starting_price=Decimal(str(starting_price)) if starting_price else None,
            starting_price_unit=starting_price_unit,
            ending_price=Decimal(str(ending_price)) if ending_price else None,
            ending_price_unit=ending_price_unit,
            inventory_summary=inventory_summary,
            latitude=Decimal(str(latitude)) if latitude else None,
            longitude=Decimal(str(longitude)) if longitude else None,
            default_commission_percent=Decimal(str(default_commission_percent)),
            auto_assignment_strategy=auto_assignment_strategy,
            mandate_owner=request.user,
            site_head_id=site_head_id,
            number_of_towers=number_of_towers,
            floors_per_tower=floors_per_tower,
            units_per_floor=units_per_floor,
            has_commercial=has_commercial,
            commercial_floors=commercial_floors,
            commercial_units_per_floor=commercial_units_per_floor,
            is_active=True
        )
        
        # Handle image upload
        if 'image' in request.FILES:
            project.image = request.FILES['image']
            project.save()
        
        # Handle configurations
        from projects.models import ProjectConfiguration, ConfigurationAreaType
        from decimal import Decimal
        
        # Map to store area type IDs: "config_0_area_0" -> actual_area_type_id
        area_type_map = {}
        
        # Process configurations
        config_count = 0
        while True:
            config_name = request.POST.get(f'config_name_{config_count}')
            if not config_name:
                break
            
            config_description = request.POST.get(f'config_description_{config_count}', '')
            price_per_sqft = request.POST.get(f'config_price_per_sqft_{config_count}')
            stamp_duty = request.POST.get(f'config_stamp_duty_{config_count}', '5.00')
            gst = request.POST.get(f'config_gst_{config_count}', '5.00')
            registration = request.POST.get(f'config_registration_{config_count}', '30000.00')
            legal = request.POST.get(f'config_legal_{config_count}', '15000.00')
            development = request.POST.get(f'config_development_{config_count}', '0.00')
            
            config = ProjectConfiguration.objects.create(
                project=project,
                name=config_name,
                description=config_description,
                price_per_sqft=Decimal(price_per_sqft) if price_per_sqft else None,
                stamp_duty_percent=Decimal(stamp_duty),
                gst_percent=Decimal(gst),
                registration_charges=Decimal(registration),
                legal_charges=Decimal(legal),
                development_charges=Decimal(development),
            )
            
            # Process area types for this configuration
            # Check all possible area indices (up to 50 to handle multiple area types)
            area_count = 0
            found_any = False
            while area_count < 50:  # Reasonable limit
                carpet_area = request.POST.get(f'config_{config_count}_area_carpet_{area_count}')
                buildup_area = request.POST.get(f'config_{config_count}_area_buildup_{area_count}')
                
                # Only process if both carpet and buildup are provided
                if carpet_area and buildup_area:
                    found_any = True
                    rera_area = request.POST.get(f'config_{config_count}_area_rera_{area_count}')
                    area_description = request.POST.get(f'config_{config_count}_area_desc_{area_count}', '')
                    
                    area_type = ConfigurationAreaType.objects.create(
                        configuration=config,
                        carpet_area=Decimal(carpet_area),
                        buildup_area=Decimal(buildup_area),
                        rera_area=Decimal(rera_area) if rera_area else None,
                        description=area_description,
                    )
                    # Map the form identifier to the actual area type ID
                    area_type_map[f'config_{config_count}_area_{area_count}'] = area_type.id
                elif not found_any and area_count > 10:
                    # If we haven't found any and checked 10 indices, stop
                    break
                
                area_count += 1
            
            config_count += 1
        
        # Handle unit configurations (floor mapping) - separate from configuration creation
        from projects.models import UnitConfiguration
        # Delete existing unit configurations
        project.unit_configurations.all().delete()
        
        # Process unit configurations for each tower, floor and unit
        floors_per_tower = project.floors_per_tower
        units_per_floor = project.units_per_floor
        number_of_towers = project.number_of_towers
        
        for tower_num in range(1, number_of_towers + 1):
            for floor_num in range(1, floors_per_tower + 1):
                # Check if floor is excluded (commercial)
                floor_excluded = request.POST.get(f'tower_{tower_num}_floor_{floor_num}_excluded') == 'on'
                
                for unit_idx in range(1, units_per_floor + 1):
                    # Unit number format: Floor-Unit (e.g., Floor 1, Unit 1 = 101, Floor 2, Unit 1 = 201)
                    # Same unit numbers can exist in different towers
                    unit_number = floor_num * 100 + unit_idx
                    
                    # Check if this specific unit is excluded
                    unit_excluded = request.POST.get(f'tower_{tower_num}_floor_{floor_num}_unit_{unit_idx}_excluded') == 'on'
                    area_type_key = request.POST.get(f'tower_{tower_num}_floor_{floor_num}_unit_{unit_idx}_area_type')
                    # Map the form key to actual area type ID
                    area_type_id = area_type_map.get(area_type_key) if area_type_key else None
                    
                    UnitConfiguration.objects.create(
                        project=project,
                        tower_number=tower_num,
                        floor_number=floor_num,
                        unit_number=unit_number,
                        area_type_id=area_type_id if area_type_id and not (floor_excluded or unit_excluded) else None,
                        is_excluded=(floor_excluded or unit_excluded),
                    )
        
        messages.success(request, f'Project "{project.name}" created successfully!')
        return redirect('projects:detail', pk=project.pk)
    
    # GET request - show form
    mandate_owners = User.objects.filter(role='mandate_owner')
    site_heads = User.objects.filter(role='site_head')
    
    context = {
        'mandate_owners': mandate_owners,
        'site_heads': site_heads,
    }
    return render(request, 'projects/create.html', context)


@login_required
def project_detail(request, pk):
    """Project detail view"""
    project = get_object_or_404(Project, pk=pk)
    
    # Permission check
    if request.user.is_super_admin():
        pass  # Super admin can see all
    elif request.user.is_mandate_owner() and project.mandate_owner != request.user:
        messages.error(request, 'You do not have permission to view this project.')
        return redirect('projects:list')
    elif request.user.is_site_head() and project.site_head != request.user:
        messages.error(request, 'You do not have permission to view this project.')
        return redirect('projects:list')
    elif not (request.user.is_super_admin() or request.user.is_mandate_owner() or request.user.is_site_head()):
        messages.error(request, 'You do not have permission to view projects.')
        return redirect('dashboard')
    
    # Get stats
    leads = Lead.objects.filter(project=project, is_archived=False)
    bookings = Booking.objects.filter(project=project, is_archived=False)
    
    from django.utils import timezone
    today = timezone.now().date()
    
    stats = {
        'total_leads': leads.count(),
        'new_visits_today': leads.filter(created_at__date=today).count(),
        'total_bookings': bookings.count(),
        'pending_otp': leads.filter(is_pretagged=True, pretag_status='pending_verification').count(),
        'revenue': Payment.objects.filter(booking__project=project).aggregate(total=Sum('amount'))['total'] or 0,
    }
    
    # Get configurations with area types and pricing details
    configurations = project.configurations.all().prefetch_related('area_types')
    
    # Get payment milestones
    milestones = project.payment_milestones.all().order_by('order')
    
    # Get unit configurations for inventory overview
    from projects.models import UnitConfiguration
    unit_configs = UnitConfiguration.objects.filter(project=project).select_related('area_type', 'area_type__configuration')
    
    # Calculate unit statistics
    total_units = project.total_units
    assigned_units = unit_configs.filter(area_type__isnull=False, is_excluded=False).count()
    excluded_units = unit_configs.filter(is_excluded=True).count()
    available_units = total_units - assigned_units - excluded_units
    
    # Get unit distribution by configuration
    unit_distribution = {}
    for unit_config in unit_configs.filter(is_excluded=False, area_type__isnull=False):
        config_name = unit_config.area_type.configuration.name if unit_config.area_type else 'Unassigned'
        if config_name not in unit_distribution:
            unit_distribution[config_name] = {
                'count': 0,
                'towers': set(),
                'floors': set()
            }
        unit_distribution[config_name]['count'] += 1
        unit_distribution[config_name]['towers'].add(unit_config.tower_number)
        unit_distribution[config_name]['floors'].add(unit_config.floor_number)
    
    # Convert sets to sorted lists for display
    for config_name in unit_distribution:
        unit_distribution[config_name]['towers'] = sorted(unit_distribution[config_name]['towers'])
        unit_distribution[config_name]['floors'] = sorted(unit_distribution[config_name]['floors'])
    
    context = {
        'project': project,
        'stats': stats,
        'configurations': configurations,
        'milestones': milestones,
        'total_units': total_units,
        'assigned_units': assigned_units,
        'excluded_units': excluded_units,
        'available_units': available_units,
        'unit_distribution': unit_distribution,
    }
    return render(request, 'projects/detail.html', context)


@login_required
def project_edit(request, pk):
    """Edit project - Super Admin and Mandate Owners"""
    project = get_object_or_404(Project, pk=pk)
    if not (request.user.is_super_admin() or request.user.is_mandate_owner()):
        messages.error(request, 'You do not have permission to edit projects.')
        return redirect('projects:detail', pk=project.pk)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        builder_name = request.POST.get('builder_name')
        location = request.POST.get('location')
        rera_id = request.POST.get('rera_id', '')
        project_type = request.POST.get('project_type')
        starting_price = request.POST.get('starting_price') or None
        starting_price_unit = request.POST.get('starting_price_unit', 'lakhs')
        ending_price = request.POST.get('ending_price') or None
        ending_price_unit = request.POST.get('ending_price_unit', 'lakhs')
        inventory_summary = request.POST.get('inventory_summary', '')
        
        # Convert price to actual decimal value based on unit
        if starting_price:
            starting_price = float(starting_price)
            if starting_price_unit == 'crores':
                starting_price = starting_price * 10000000
            else:  # lakhs
                starting_price = starting_price * 100000
        
        if ending_price:
            ending_price = float(ending_price)
            if ending_price_unit == 'crores':
                ending_price = ending_price * 10000000
            else:  # lakhs
                ending_price = ending_price * 100000
        latitude = request.POST.get('latitude') or None
        longitude = request.POST.get('longitude') or None
        default_commission_percent = request.POST.get('default_commission_percent') or 0
        auto_assignment_strategy = request.POST.get('auto_assignment_strategy', 'manual')
        site_head_id = request.POST.get('site_head') or None
        
        # Tower and Unit Structure
        number_of_towers = int(request.POST.get('number_of_towers', 1))
        floors_per_tower = int(request.POST.get('floors_per_tower', 1))
        units_per_floor = int(request.POST.get('units_per_floor', 1))
        has_commercial = request.POST.get('has_commercial') == 'on'
        commercial_floors = int(request.POST.get('commercial_floors', 0)) if has_commercial else 0
        commercial_units_per_floor = int(request.POST.get('commercial_units_per_floor', 0)) if has_commercial else 0
        
        project.name = name
        project.builder_name = builder_name
        project.location = location
        project.rera_id = rera_id
        project.project_type = project_type
        project.starting_price = Decimal(str(starting_price)) if starting_price else None
        project.starting_price_unit = starting_price_unit
        project.ending_price = Decimal(str(ending_price)) if ending_price else None
        project.ending_price_unit = ending_price_unit
        project.inventory_summary = inventory_summary
        project.latitude = Decimal(str(latitude)) if latitude else None
        project.longitude = Decimal(str(longitude)) if longitude else None
        project.default_commission_percent = Decimal(str(default_commission_percent))
        project.auto_assignment_strategy = auto_assignment_strategy
        project.site_head_id = site_head_id
        project.number_of_towers = number_of_towers
        project.floors_per_tower = floors_per_tower
        project.units_per_floor = units_per_floor
        project.has_commercial = has_commercial
        project.commercial_floors = commercial_floors
        project.commercial_units_per_floor = commercial_units_per_floor
        
        if 'image' in request.FILES:
            project.image = request.FILES['image']
        
        project.save()
        
        # Handle configurations - update or create
        from projects.models import ProjectConfiguration, ConfigurationAreaType, ConfigurationFloorMapping
        from decimal import Decimal
        
        # Get all existing config names to track what to keep
        submitted_config_names = set()
        
        # Process configurations
        config_count = 0
        while True:
            config_name = request.POST.get(f'config_name_{config_count}')
            if not config_name:
                break
            
            submitted_config_names.add(config_name)
            config_description = request.POST.get(f'config_description_{config_count}', '')
            price_per_sqft = request.POST.get(f'config_price_per_sqft_{config_count}')
            stamp_duty = request.POST.get(f'config_stamp_duty_{config_count}', '5.00')
            gst = request.POST.get(f'config_gst_{config_count}', '5.00')
            registration = request.POST.get(f'config_registration_{config_count}', '30000.00')
            legal = request.POST.get(f'config_legal_{config_count}', '15000.00')
            development = request.POST.get(f'config_development_{config_count}', '0.00')
            
            # Use get_or_create to avoid IntegrityError
            config, created = ProjectConfiguration.objects.get_or_create(
                project=project,
                name=config_name,
                defaults={
                    'description': config_description,
                    'price_per_sqft': Decimal(price_per_sqft) if price_per_sqft else None,
                    'stamp_duty_percent': Decimal(stamp_duty),
                    'gst_percent': Decimal(gst),
                    'registration_charges': Decimal(registration),
                    'legal_charges': Decimal(legal),
                    'development_charges': Decimal(development),
                }
            )
            
            # Update if it already exists
            if not created:
                config.description = config_description
                config.price_per_sqft = Decimal(price_per_sqft) if price_per_sqft else None
                config.stamp_duty_percent = Decimal(stamp_duty)
                config.gst_percent = Decimal(gst)
                config.registration_charges = Decimal(registration)
                config.legal_charges = Decimal(legal)
                config.development_charges = Decimal(development)
                config.save()
                
                # Delete existing area types and floor mappings for this config
                config.area_types.all().delete()
                config.floor_mappings.all().delete()
            
            # Process area types for this configuration
            # Check all possible area indices (up to 50 to handle multiple area types)
            area_count = 0
            found_any = False
            while area_count < 50:  # Reasonable limit
                carpet_area = request.POST.get(f'config_{config_count}_area_carpet_{area_count}')
                buildup_area = request.POST.get(f'config_{config_count}_area_buildup_{area_count}')
                
                # Only process if both carpet and buildup are provided
                if carpet_area and buildup_area:
                    found_any = True
                    rera_area = request.POST.get(f'config_{config_count}_area_rera_{area_count}')
                    area_description = request.POST.get(f'config_{config_count}_area_desc_{area_count}', '')
                    
                    area_type = ConfigurationAreaType.objects.create(
                        configuration=config,
                        carpet_area=Decimal(carpet_area),
                        buildup_area=Decimal(buildup_area),
                        rera_area=Decimal(rera_area) if rera_area else None,
                        description=area_description,
                    )
                elif not found_any and area_count > 10:
                    # If we haven't found any and checked 10 indices, stop
                    break
                
                area_count += 1
            
            config_count += 1
        
        # Handle unit configurations (floor mapping) - separate from configuration creation
        from projects.models import UnitConfiguration
        # Delete existing unit configurations
        project.unit_configurations.all().delete()
        
        # Process unit configurations for each tower, floor and unit
        floors_per_tower = project.floors_per_tower
        units_per_floor = project.units_per_floor
        number_of_towers = project.number_of_towers
        
        for tower_num in range(1, number_of_towers + 1):
            for floor_num in range(1, floors_per_tower + 1):
                # Check if floor is excluded (commercial)
                floor_excluded = request.POST.get(f'tower_{tower_num}_floor_{floor_num}_excluded') == 'on'
                
                for unit_idx in range(1, units_per_floor + 1):
                    # Unit number format: Floor-Unit (e.g., Floor 1, Unit 1 = 101, Floor 2, Unit 1 = 201)
                    # Same unit numbers can exist in different towers
                    unit_number = floor_num * 100 + unit_idx
                    
                    # Check if this specific unit is excluded
                    unit_excluded = request.POST.get(f'tower_{tower_num}_floor_{floor_num}_unit_{unit_idx}_excluded') == 'on'
                    area_type_key = request.POST.get(f'tower_{tower_num}_floor_{floor_num}_unit_{unit_idx}_area_type')
                    
                    # For edit: area_type_key can be either form key (config_X_area_Y) or actual ID
                    # Try to find matching area type
                    area_type_id = None
                    if area_type_key:
                        # If it's a numeric ID, use it directly
                        if area_type_key.isdigit():
                            area_type_id = int(area_type_key)
                        else:
                            # Otherwise, it's a form key - find matching area type
                            # This is complex, so for edit we'll use IDs directly
                            # The template should populate with actual IDs
                            try:
                                area_type_id = int(area_type_key)
                            except:
                                pass
                    
                    UnitConfiguration.objects.create(
                        project=project,
                        tower_number=tower_num,
                        floor_number=floor_num,
                        unit_number=unit_number,
                        area_type_id=area_type_id if area_type_id and not (floor_excluded or unit_excluded) else None,
                        is_excluded=(floor_excluded or unit_excluded),
                    )
        
        messages.success(request, f'Project "{project.name}" updated successfully!')
        return redirect('projects:detail', pk=project.pk)
    
    # GET request - show form with existing data
    mandate_owners = User.objects.filter(role='mandate_owner')
    site_heads = User.objects.filter(role='site_head')
    
    # Get existing configurations
    configurations = project.configurations.all()
    
    # Get all area types for dropdown population
    from projects.models import ConfigurationAreaType
    all_area_types = ConfigurationAreaType.objects.filter(configuration__project=project).select_related('configuration')
    
    # Get existing unit configurations
    from projects.models import UnitConfiguration
    # Create a key-based lookup: "tower_floor_unit" -> unit_config
    unit_configurations = {}
    for uc in project.unit_configurations.all().select_related('area_type'):
        key = f"{uc.tower_number}_{uc.floor_number}_{uc.unit_number}"
        unit_configurations[key] = uc
    
    context = {
        'project': project,
        'mandate_owners': mandate_owners,
        'site_heads': site_heads,
        'configurations': configurations,
        'all_area_types': all_area_types,
        'unit_configurations': unit_configurations,
    }
    return render(request, 'projects/edit.html', context)


@login_required
def unit_selection(request, pk):
    """Interactive unit selection page (BookMyShow-style UI)"""
    project = get_object_or_404(Project, pk=pk)
    
    # Permission check - all user types can view units
    if request.user.is_super_admin():
        pass  # Super admin can see all
    elif request.user.is_mandate_owner() and project.mandate_owner != request.user:
        messages.error(request, 'You do not have permission to view this project.')
        return redirect('projects:list')
    elif request.user.is_site_head() and project.site_head != request.user:
        messages.error(request, 'You do not have permission to view this project.')
        return redirect('projects:list')
    
    # Get all unit configurations with related data
    unit_configs = UnitConfiguration.objects.filter(project=project).select_related(
        'area_type', 
        'area_type__configuration'
    ).order_by('tower_number', 'floor_number', 'unit_number')
    
    # Get all configurations with area types for filtering
    configurations = project.configurations.all().prefetch_related('area_types')
    
    # Get bookings to show which units are booked
    from bookings.models import Booking
    booked_units = {}
    for booking in Booking.objects.filter(project=project, is_archived=False).select_related('lead', 'project', 'channel_partner'):
        # Match booking to unit by tower, floor, and unit number
        # Booking has: tower_wing, unit_number, floor
        # UnitConfiguration has: tower_number, floor_number, unit_number
        try:
            # Try to parse unit_number from booking (could be "101", "201", etc.)
            booking_unit_num = int(booking.unit_number) if booking.unit_number.isdigit() else None
            booking_floor = booking.floor
            
            if booking_unit_num and booking_floor:
                # Unit number format: floor * 100 + unit_index
                # So we can extract tower info if needed, but for now match by floor and unit
                key = f"{booking_floor}_{booking_unit_num}"
                booked_units[key] = booking
        except (ValueError, AttributeError):
            # If we can't parse, skip this booking
            pass
    
    # Organize units by tower and floor
    units_by_tower = {}
    for unit_config in unit_configs:
        tower_key = unit_config.tower_number
        if tower_key not in units_by_tower:
            units_by_tower[tower_key] = {}
        
        floor_key = unit_config.floor_number
        if floor_key not in units_by_tower[tower_key]:
            units_by_tower[tower_key][floor_key] = []
        
        # Calculate pricing if area type exists
        pricing_info = None
        if unit_config.area_type and unit_config.area_type.configuration:
            config = unit_config.area_type.configuration
            area_type = unit_config.area_type
            
            # Calculate agreement value
            agreement_value = config.calculate_agreement_value(
                carpet_area=area_type.carpet_area,
                buildup_area=area_type.buildup_area
            )
            
            # Calculate total cost breakdown
            # Formula: Agreement Value = price_per_sqft * buildup_area
            # Total = Agreement Value + (Stamp Duty % of Agreement Value) + (GST % of Agreement Value) + Registration + Legal + Development Charges
            cost_breakdown = config.calculate_total_cost(
                carpet_area=area_type.carpet_area,
                buildup_area=area_type.buildup_area
            ) if agreement_value else None
            
            pricing_info = {
                'agreement_value': agreement_value,
                'total_cost': cost_breakdown['total'] if cost_breakdown else None,
                'cost_breakdown': cost_breakdown,
                'price_per_sqft': config.price_per_sqft,
                'stamp_duty_percent': config.stamp_duty_percent,
                'gst_percent': config.gst_percent,
                'carpet_area': area_type.carpet_area,
                'buildup_area': area_type.buildup_area,
                'rera_area': area_type.rera_area,
                'configuration_name': config.name,
                'area_display': area_type.get_display_name(),
            }
        
        # Check if unit is booked
        # Match by floor and unit number (since Booking doesn't store tower explicitly in a separate field)
        booking_key = f"{unit_config.floor_number}_{unit_config.unit_number}"
        is_booked = booking_key in booked_units
        
        units_by_tower[tower_key][floor_key].append({
            'unit_config': unit_config,
            'pricing_info': pricing_info,
            'is_booked': is_booked,
            'booking': booked_units.get(booking_key),
        })
    
    context = {
        'project': project,
        'units_by_tower': units_by_tower,
        'configurations': configurations,
        'booked_units': booked_units,
    }
    return render(request, 'projects/unit_selection.html', context)


@login_required
def migrate_leads(request, pk):
    """Migrate leads from one project to another - Mandate Owners only"""
    project = get_object_or_404(Project, pk=pk)
    if not request.user.is_mandate_owner():
        messages.error(request, 'You do not have permission to migrate leads.')
        return redirect('projects:detail', pk=project.pk)
    
    if request.method == 'POST':
        target_project_id = request.POST.get('target_project')
        if not target_project_id:
            messages.error(request, 'Please select a target project.')
            return redirect('projects:migrate_leads', pk=project.pk)
        
        target_project = get_object_or_404(Project, pk=target_project_id)
        
        # Migrate leads
        leads_to_migrate = Lead.objects.filter(project=project, is_archived=False)
        count = leads_to_migrate.count()
        leads_to_migrate.update(project=target_project)
        
        messages.success(request, f'Successfully migrated {count} lead(s) to {target_project.name}.')
        return redirect('projects:detail', pk=project.pk)
    
    # GET request - show form
    # Get all projects owned by the same mandate owner
    target_projects = Project.objects.filter(
        mandate_owner=project.mandate_owner
    ).exclude(pk=project.pk).order_by('name')
    
    context = {
        'project': project,
        'target_projects': target_projects,
    }
    return render(request, 'projects/migrate_leads.html', context)
