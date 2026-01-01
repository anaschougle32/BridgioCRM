from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from .models import Project, ProjectConfiguration, PaymentMilestone, UnitConfiguration, ConfigurationAreaType
from accounts.models import User
from leads.models import Lead
from bookings.models import Booking, Payment
from decimal import Decimal
from leads.models import DailyAssignmentQuota


def get_floor_display_name(floor_num):
    """
    Convert floor number to display name.
    Floor 0 = Ground Floor (G)
    Floor 1 = 1st Floor
    Floor 2 = 2nd Floor
    Floor 3 = 3rd Floor
    etc.
    """
    if floor_num == 0:
        return "Ground Floor (G)"
    elif floor_num == 1:
        return "1st Floor"
    elif floor_num == 2:
        return "2nd Floor"
    elif floor_num == 3:
        return "3rd Floor"
    elif floor_num == 4:
        return "4th Floor"
    else:
        return f"{floor_num}th Floor"


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
    elif request.user.is_closing_manager() or request.user.is_sourcing_manager():
        # Closing and Sourcing managers see projects they're assigned to
        projects = request.user.assigned_projects.filter(is_active=True)
    else:
        messages.error(request, 'You do not have permission to view projects.')
        return redirect('dashboard')
    
    # Annotate with stats - use lead_associations instead of leads
    projects = projects.annotate(
        lead_count=Count('lead_associations', filter=~Q(lead_associations__is_archived=True), distinct=True),
        booking_count=Count('bookings', filter=~Q(bookings__is_archived=True), distinct=True),
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
        step = request.POST.get('step', '1')
        
        if step == '1':
            # Step 1: Basic Information - Store in session
            request.session['new_project_data'] = {
                'name': request.POST.get('name'),
                'builder_name': request.POST.get('builder_name'),
                'location': request.POST.get('location'),
                'rera_id': request.POST.get('rera_id', ''),
                'project_type': request.POST.get('project_type'),
                'starting_price': request.POST.get('starting_price'),
                'starting_price_unit': request.POST.get('starting_price_unit', 'lakhs'),
                'ending_price': request.POST.get('ending_price'),
                'ending_price_unit': request.POST.get('ending_price_unit', 'lakhs'),
                'inventory_summary': request.POST.get('inventory_summary', ''),
                'latitude': request.POST.get('latitude'),
                'longitude': request.POST.get('longitude'),
            }
            # Store image in session if uploaded
            if 'image' in request.FILES:
                # For now, we'll handle image in final step
                pass
            request.session.modified = True
            return JsonResponse({'success': True, 'step': 2})
        
        elif step == '2':
            # Step 2: Tower/Unit Structure - Store in session
            # Collect tower configurations (flexible structure)
            tower_configs = []
            commercial_floors = {}  # Store which floors are commercial per tower
            tower_count = 0
            while True:
                tower_num = request.POST.get(f'tower_{tower_count}_number')
                if not tower_num:
                    break
                tower_num_int = int(tower_num)
                floors_count = int(request.POST.get(f'tower_{tower_count}_floors', '1'))
                
                # Collect commercial floors and their unit counts for this tower
                tower_commercial_floors = {}
                # Check if ground floor (0) is commercial
                ground_is_commercial = request.POST.get(f'tower_{tower_count}_floor_0_commercial') == 'on'
                
                # If ground is commercial, total = floors_count + 1 (G + N floors)
                # If ground is NOT commercial, total = floors_count (just 1-N floors, no ground)
                if ground_is_commercial:
                    total_floors = floors_count + 1
                    for floor_num in range(0, total_floors):  # Floor 0 (Ground) through N floors
                        if request.POST.get(f'tower_{tower_count}_floor_{floor_num}_commercial') == 'on':
                            commercial_units = request.POST.get(f'tower_{tower_count}_floor_{floor_num}_commercial_units', '0')
                            tower_commercial_floors[floor_num] = int(commercial_units) if commercial_units else 0
                else:
                    total_floors = floors_count
                    for floor_num in range(1, total_floors + 1):  # Floor 1 through N floors (no ground)
                        if request.POST.get(f'tower_{tower_count}_floor_{floor_num}_commercial') == 'on':
                            commercial_units = request.POST.get(f'tower_{tower_count}_floor_{floor_num}_commercial_units', '0')
                            tower_commercial_floors[floor_num] = int(commercial_units) if commercial_units else 0
                
                tower_configs.append({
                    'tower_number': tower_num_int,
                    'floors_count': total_floors,  # Store total floors (G + N)
                    'units_per_floor': int(request.POST.get(f'tower_{tower_count}_units_per_floor', '1')),
                    'is_commercial': request.POST.get(f'tower_{tower_count}_is_commercial') == 'on',
                })
                commercial_floors[tower_num_int] = tower_commercial_floors
                tower_count += 1
                if tower_count > 100:  # Safety limit
                    break
            
            # Also store legacy fields for backward compatibility
            request.session['new_project_data'].update({
                'number_of_towers': request.POST.get('number_of_towers', str(len(tower_configs))),
                'floors_per_tower': request.POST.get('floors_per_tower', '1'),
                'units_per_floor': request.POST.get('units_per_floor', '1'),
                'has_commercial': request.POST.get('has_commercial') == 'on',
                'commercial_floors': request.POST.get('commercial_floors', '0'),
                'commercial_units_per_floor': request.POST.get('commercial_units_per_floor', '0'),
                'tower_configs': tower_configs,  # New flexible structure
                'commercial_floors': commercial_floors,  # Which floors are commercial per tower
            })
            request.session.modified = True
            return JsonResponse({'success': True, 'step': 3})
        
        elif step == '3':
            # Step 3: Configurations & Pricing - Store in session
            # Collect all configuration data
            configs_data = []
            config_count = 0
            while True:
                config_name = request.POST.get(f'config_name_{config_count}', '').strip()
                if not config_name:
                    break
                
                config_data = {
                    'name': config_name,
                    'description': request.POST.get(f'config_description_{config_count}', ''),
                    'price_per_sqft': request.POST.get(f'config_price_per_sqft_{config_count}'),
                    'stamp_duty': request.POST.get(f'config_stamp_duty_{config_count}', '5.00'),
                    'gst': request.POST.get(f'config_gst_{config_count}', '5.00'),
                    'registration': request.POST.get(f'config_registration_{config_count}', '30000.00'),
                    'legal': request.POST.get(f'config_legal_{config_count}', '15000.00'),
                    'development': request.POST.get(f'config_development_{config_count}', '0.00'),
                    'config_id': request.POST.get(f'config_id_{config_count}', '').strip(),
                    'area_types': []
                }
                
                # Collect area types
                area_count = 0
                while area_count < 50:
                    carpet_area = request.POST.get(f'config_{config_count}_area_carpet_{area_count}')
                    buildup_area = request.POST.get(f'config_{config_count}_area_buildup_{area_count}')
                    if carpet_area and buildup_area:
                        config_data['area_types'].append({
                            'carpet_area': carpet_area,
                            'buildup_area': buildup_area,
                            'rera_area': request.POST.get(f'config_{config_count}_area_rera_{area_count}'),
                            'description': request.POST.get(f'config_{config_count}_area_desc_{area_count}', ''),
                        })
                        area_count += 1
                    elif area_count > 10:
                        break
                    else:
                        area_count += 1
                
                configs_data.append(config_data)
                config_count += 1
            
            request.session['new_project_data']['configurations'] = configs_data
            request.session.modified = True
            return JsonResponse({'success': True, 'step': 4})
        
        elif step == '4':
            # Step 4: Floor Mapping - Store in session
            floor_mapping_data = {}
            for key in request.POST.keys():
                if key.startswith('tower_'):
                    floor_mapping_data[key] = request.POST.get(key)
            request.session['new_project_data']['floor_mapping'] = floor_mapping_data
            request.session.modified = True
            return JsonResponse({'success': True, 'step': 5})
        
        elif step == '5':
            # Step 5: Settings & Assignment - Final submission
            project_data = request.session.get('new_project_data', {})
            
            # Get all data
            name = project_data.get('name')
            builder_name = project_data.get('builder_name')
            location = project_data.get('location')
            rera_id = project_data.get('rera_id', '')
            project_type = project_data.get('project_type')
            starting_price = project_data.get('starting_price')
            starting_price_unit = project_data.get('starting_price_unit', 'lakhs')
            ending_price = project_data.get('ending_price')
            ending_price_unit = project_data.get('ending_price_unit', 'lakhs')
            inventory_summary = project_data.get('inventory_summary', '')
            latitude = project_data.get('latitude')
            longitude = project_data.get('longitude')
            default_commission_percent = request.POST.get('default_commission_percent') or 0
            auto_assignment_strategy = request.POST.get('auto_assignment_strategy', 'manual')
            site_head_id = request.POST.get('site_head') or None
            
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
            
            # Tower and Unit Structure
            number_of_towers = int(project_data.get('number_of_towers', 1))
            floors_per_tower = int(project_data.get('floors_per_tower', 1))
            units_per_floor = int(project_data.get('units_per_floor', 1))
            has_commercial = project_data.get('has_commercial', False)
            commercial_floors = int(project_data.get('commercial_floors', 0)) if has_commercial else 0
            commercial_units_per_floor = int(project_data.get('commercial_units_per_floor', 0)) if has_commercial else 0
            
            # Create project
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
            
            # Create/Update Highrise Pricing
            from projects.models import HighrisePricing
            highrise_enabled = request.POST.get('highrise_enabled') == 'on'
            if highrise_enabled:
                highrise_pricing, created = HighrisePricing.objects.get_or_create(
                    project=project,
                    defaults={
                        'is_enabled': True,
                        'floor_threshold': int(request.POST.get('highrise_floor_threshold', 10)),
                        'base_price_per_sqft': Decimal(request.POST.get('highrise_base_price_per_sqft', 0)) if request.POST.get('highrise_base_price_per_sqft') else None,
                        'pricing_type': request.POST.get('highrise_pricing_type', 'per_sqft'),
                        'fixed_price_increment': Decimal(request.POST.get('highrise_fixed_price_increment', 0)) if request.POST.get('highrise_fixed_price_increment') else Decimal('0'),
                        'per_sqft_increment': Decimal(request.POST.get('highrise_per_sqft_increment', 20)) if request.POST.get('highrise_per_sqft_increment') else Decimal('20'),
                        'development_charges_type': request.POST.get('highrise_dev_charges_type', 'fixed'),
                        'development_charges_fixed': Decimal(request.POST.get('highrise_dev_charges_fixed', 0)) if request.POST.get('highrise_dev_charges_fixed') else Decimal('0'),
                        'development_charges_per_sqft': Decimal(request.POST.get('highrise_dev_charges_per_sqft', 0)) if request.POST.get('highrise_dev_charges_per_sqft') else Decimal('0'),
                        'parking_price': Decimal(request.POST.get('highrise_parking_price', 0)) if request.POST.get('highrise_parking_price') else Decimal('0'),
                        'parking_negotiable': request.POST.get('highrise_parking_negotiable') == 'on',
                        'include_parking_in_calculation': request.POST.get('highrise_include_parking') == 'on',
                    }
                )
                if not created:
                    # Update existing
                    highrise_pricing.is_enabled = True
                    highrise_pricing.floor_threshold = int(request.POST.get('highrise_floor_threshold', 10))
                    highrise_pricing.base_price_per_sqft = Decimal(request.POST.get('highrise_base_price_per_sqft', 0)) if request.POST.get('highrise_base_price_per_sqft') else None
                    highrise_pricing.pricing_type = request.POST.get('highrise_pricing_type', 'per_sqft')
                    highrise_pricing.fixed_price_increment = Decimal(request.POST.get('highrise_fixed_price_increment', 0)) if request.POST.get('highrise_fixed_price_increment') else Decimal('0')
                    highrise_pricing.per_sqft_increment = Decimal(request.POST.get('highrise_per_sqft_increment', 20)) if request.POST.get('highrise_per_sqft_increment') else Decimal('20')
                    highrise_pricing.development_charges_type = request.POST.get('highrise_dev_charges_type', 'fixed')
                    highrise_pricing.development_charges_fixed = Decimal(request.POST.get('highrise_dev_charges_fixed', 0)) if request.POST.get('highrise_dev_charges_fixed') else Decimal('0')
                    highrise_pricing.development_charges_per_sqft = Decimal(request.POST.get('highrise_dev_charges_per_sqft', 0)) if request.POST.get('highrise_dev_charges_per_sqft') else Decimal('0')
                    highrise_pricing.parking_price = Decimal(request.POST.get('highrise_parking_price', 0)) if request.POST.get('highrise_parking_price') else Decimal('0')
                    highrise_pricing.parking_negotiable = request.POST.get('highrise_parking_negotiable') == 'on'
                    highrise_pricing.include_parking_in_calculation = request.POST.get('highrise_include_parking') == 'on'
                    highrise_pricing.save()
            else:
                # Disable highrise pricing if checkbox is unchecked
                HighrisePricing.objects.filter(project=project).update(is_enabled=False)
            
            # Create flexible tower/floor configurations
            from projects.models import TowerFloorConfig
            tower_configs = project_data.get('tower_configs', [])
            if tower_configs:
                for tower_config in tower_configs:
                    TowerFloorConfig.objects.create(
                        project=project,
                        tower_number=tower_config['tower_number'],
                        floors_count=tower_config['floors_count'],
                        units_per_floor=tower_config['units_per_floor'],
                        is_commercial=tower_config.get('is_commercial', False),
                    )
            else:
                # Create default configs for backward compatibility
                for tower_num in range(1, number_of_towers + 1):
                    TowerFloorConfig.objects.create(
                        project=project,
                        tower_number=tower_num,
                        floors_count=floors_per_tower,
                        units_per_floor=units_per_floor,
                        is_commercial=has_commercial,
                    )
            
            # Process configurations
            from projects.models import ProjectConfiguration, ConfigurationAreaType
            area_type_map = {}
            configs_data = project_data.get('configurations', [])
            
            for config_data in configs_data:
                config = ProjectConfiguration.objects.create(
                    project=project,
                    name=config_data['name'],
                    description=config_data.get('description', ''),
                    price_per_sqft=Decimal(config_data['price_per_sqft']) if config_data.get('price_per_sqft') else None,
                    stamp_duty_percent=Decimal(config_data.get('stamp_duty', '5.00')),
                    gst_percent=Decimal(config_data.get('gst', '5.00')),
                    registration_charges=Decimal(config_data.get('registration', '30000.00')),
                    legal_charges=Decimal(config_data.get('legal', '15000.00')),
                    development_charges=Decimal(config_data.get('development', '0.00')),
                )
                
                # Process area types
                for idx, area_data in enumerate(config_data.get('area_types', [])):
                    area_type = ConfigurationAreaType.objects.create(
                        configuration=config,
                        carpet_area=Decimal(area_data['carpet_area']),
                        buildup_area=Decimal(area_data['buildup_area']),
                        rera_area=Decimal(area_data['rera_area']) if area_data.get('rera_area') else None,
                        description=area_data.get('description', ''),
                    )
                    # Map for floor mapping
                    area_type_map[f'config_{len(area_type_map)}_area_{idx}'] = area_type.id
            
            # Handle floor mapping
            from projects.models import UnitConfiguration, TowerFloorConfig
            floor_mapping_data = project_data.get('floor_mapping', {})
            tower_configs_list = list(TowerFloorConfig.objects.filter(project=project).order_by('tower_number'))
            
            if floor_mapping_data:
                if tower_configs_list:
                    # Use flexible structure
                    for tower_config in tower_configs_list:
                        tower_num = tower_config.tower_number
                        floors_count = tower_config.floors_count
                        units_per_floor_tower = tower_config.units_per_floor
                        
                        # Get commercial floors and their unit counts from tower structure step
                        commercial_floors_data = project_data.get('commercial_floors', {})
                        tower_commercial_floors = commercial_floors_data.get(tower_num, {})  # Dict: {floor_num: units_count}
                        
                        # Check if ground floor (0) is commercial for this tower
                        ground_is_commercial = 0 in tower_commercial_floors
                        
                        # Determine floor range based on whether ground floor exists
                        if ground_is_commercial:
                            # Ground is commercial: iterate from 0 to floors_count-1 (G + 1-N)
                            floor_range = range(0, floors_count)
                        else:
                            # Ground is NOT commercial: iterate from 1 to floors_count (1-N only)
                            floor_range = range(1, floors_count + 1)
                        
                        for floor_num in floor_range:
                            floor_excluded = floor_mapping_data.get(f'tower_{tower_num}_floor_{floor_num}_excluded') == 'on'
                            # Check if this floor is commercial from tower structure step
                            floor_is_commercial = floor_num in tower_commercial_floors
                            
                            # Get units per floor for commercial floors, otherwise use default
                            if floor_is_commercial:
                                units_per_floor_this = tower_commercial_floors.get(floor_num, units_per_floor_tower)
                            else:
                                units_per_floor_this = units_per_floor_tower
                            for unit_idx in range(1, units_per_floor_this + 1):
                                # Floor 0 (Ground): 001, 002, 003... Floor 1: 101, 102, 103... Floor 7: 701, 702, 703...
                                unit_number = floor_num * 100 + unit_idx if floor_num > 0 else unit_idx
                                unit_excluded = floor_mapping_data.get(f'tower_{tower_num}_floor_{floor_num}_unit_{unit_idx}_excluded') == 'on'
                                area_type_key = floor_mapping_data.get(f'tower_{tower_num}_floor_{floor_num}_unit_{unit_idx}_area_type')
                                area_type_id = area_type_map.get(area_type_key) if area_type_key else None
                                
                                # Get the actual area_type object if ID exists
                                area_type_obj = None
                                if area_type_id and not (floor_excluded or unit_excluded):
                                    try:
                                        area_type_obj = ConfigurationAreaType.objects.get(id=area_type_id)
                                    except ConfigurationAreaType.DoesNotExist:
                                        pass
                                
                                UnitConfiguration.objects.create(
                                    project=project,
                                    tower_number=tower_num,
                                    floor_number=floor_num,
                                    unit_number=unit_number,
                                    area_type=area_type_obj,
                                    is_excluded=(floor_excluded or unit_excluded),
                                    is_commercial=floor_is_commercial,
                                )
                else:
                    # Fallback to legacy structure (no ground floor in legacy, start from floor 1)
                    for tower_num in range(1, number_of_towers + 1):
                        for floor_num in range(1, floors_per_tower + 1):
                            floor_excluded = floor_mapping_data.get(f'tower_{tower_num}_floor_{floor_num}_excluded') == 'on'
                            
                            for unit_idx in range(1, units_per_floor + 1):
                                # Floor 0 (Ground): 001, 002, 003... Floor 1: 101, 102, 103... Floor 2: 201, 202, 203...
                                unit_number = floor_num * 100 + unit_idx if floor_num > 0 else unit_idx
                                unit_excluded = floor_mapping_data.get(f'tower_{tower_num}_floor_{floor_num}_unit_{unit_idx}_excluded') == 'on'
                                area_type_key = floor_mapping_data.get(f'tower_{tower_num}_floor_{floor_num}_unit_{unit_idx}_area_type')
                                area_type_id = area_type_map.get(area_type_key) if area_type_key else None
                                
                                # Get the actual area_type object if ID exists
                                area_type_obj = None
                                if area_type_id and not (floor_excluded or unit_excluded):
                                    try:
                                        area_type_obj = ConfigurationAreaType.objects.get(id=area_type_id)
                                    except ConfigurationAreaType.DoesNotExist:
                                        pass
                                
                                UnitConfiguration.objects.create(
                                    project=project,
                                    tower_number=tower_num,
                                    floor_number=floor_num,
                                    unit_number=unit_number,
                                    area_type=area_type_obj,
                                    is_excluded=(floor_excluded or unit_excluded),
                                )
            
            # Clear session
            if 'new_project_data' in request.session:
                del request.session['new_project_data']
            request.session.modified = True
            
            messages.success(request, f'Project "{project.name}" created successfully!')
            return JsonResponse({
                'success': True,
                'redirect_url': reverse('projects:detail', kwargs={'pk': project.pk})
            })
    
    # GET request - show form
    mandate_owners = User.objects.filter(role='mandate_owner')
    site_heads = User.objects.filter(role='site_head')
    
    # Get project type choices for dropdown
    project_type_choices = Project.PROJECT_TYPE_CHOICES
    
    context = {
        'mandate_owners': mandate_owners,
        'site_heads': site_heads,
        'project_type_choices': project_type_choices,
    }
    return render(request, 'projects/create.html', context)


@login_required
def project_detail(request, pk):
    """Project detail view"""
    project = get_object_or_404(Project, pk=pk)
    
    # Permission check - Mandate Owner has same permissions as Super Admin
    # Site Heads can view projects they manage
    # Closing and Sourcing managers can view projects they're assigned to
    if request.user.is_super_admin() or request.user.is_mandate_owner():
        pass  # Super admin and Mandate Owner can see all
    elif request.user.is_site_head():
        # Site Head can view projects they manage
        if project.site_head != request.user:
            messages.error(request, 'You do not have permission to view this project.')
            return redirect('projects:list')
    elif request.user.is_closing_manager() or request.user.is_sourcing_manager():
        # Check if user is assigned to this project
        if project not in request.user.assigned_projects.all():
            messages.error(request, 'You do not have permission to view this project.')
            return redirect('projects:list')
    elif request.user.is_telecaller():
        # Telecallers can view projects they're assigned to
        if project not in request.user.assigned_projects.all():
            messages.error(request, 'You do not have permission to view this project.')
            return redirect('projects:list')
    else:
        messages.error(request, 'You do not have permission to view projects.')
        return redirect('dashboard')
    
    # Get stats from associations
    from leads.models import LeadProjectAssociation
    associations = LeadProjectAssociation.objects.filter(project=project, is_archived=False)
    bookings = Booking.objects.filter(project=project, is_archived=False)
    
    from django.utils import timezone
    today = timezone.now().date()
    
    # Count visits properly - all associations with visit_completed status or pretagged leads
    total_visits = associations.filter(
        Q(status='visit_completed') | Q(is_pretagged=True)
    ).count()
    
    # Count CP visits (associations with channel partner)
    cp_visits = associations.filter(
        Q(status='visit_completed') | Q(is_pretagged=True),
        lead__channel_partner__isnull=False
    ).count()
    
    # Get unique leads count
    unique_leads = associations.values_list('lead_id', flat=True).distinct().count()
    
    stats = {
        'total_leads': unique_leads,
        'new_visits_today': associations.filter(created_at__date=today).count(),
        'total_visits': total_visits,
        'cp_visits': cp_visits,
        'total_bookings': bookings.count(),
        'pending_otp': associations.filter(is_pretagged=True, pretag_status='pending_verification').count(),
        'revenue': Payment.objects.filter(booking__project=project).aggregate(total=Sum('amount'))['total'] or 0,
    }
    
    # Get configurations with area types and pricing details
    configurations = project.configurations.all().prefetch_related('area_types')
    
    # Get payment milestones
    milestones = project.payment_milestones.all().order_by('order')
    
    # Get unit configurations for inventory overview
    from projects.models import UnitConfiguration, TowerFloorConfig
    unit_configs = UnitConfiguration.objects.filter(project=project).select_related('area_type', 'area_type__configuration')
    
    # Calculate total units - use TowerFloorConfig if available, otherwise use legacy calculation
    tower_configs = TowerFloorConfig.objects.filter(project=project)
    if tower_configs.exists():
        # Use flexible tower structure
        total_units = sum(tc.floors_count * tc.units_per_floor for tc in tower_configs)
    else:
        # Fallback to legacy calculation
        total_units = project.total_units
    
    # Count booked units
    booked_units = Booking.objects.filter(project=project, is_archived=False).count()
    
    # Calculate remaining/available units (total - booked - excluded)
    excluded_units = unit_configs.filter(is_excluded=True).count()
    available_units = total_units - booked_units - excluded_units
    
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
        'booked_units': booked_units,
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
        step = request.POST.get('step', '1')
        
        if step == '1':
            # Step 1: Basic Information - Update project
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
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            
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
            
            if 'image' in request.FILES:
                project.image = request.FILES['image']
            
            project.save()
            return JsonResponse({'success': True, 'step': 2})
        
        elif step == '2':
            # Step 2: Tower/Unit Structure - Update project with flexible structure
            from projects.models import TowerFloorConfig
            
            number_of_towers = int(request.POST.get('number_of_towers', 1))
            
            # Update legacy fields for backward compatibility
            floors_per_tower = int(request.POST.get('floors_per_tower', 1))
            units_per_floor = int(request.POST.get('units_per_floor', 1))
            has_commercial = request.POST.get('has_commercial') == 'on'
            commercial_floors = int(request.POST.get('commercial_floors', 0)) if has_commercial else 0
            commercial_units_per_floor = int(request.POST.get('commercial_units_per_floor', 0)) if has_commercial else 0
            
            project.number_of_towers = number_of_towers
            project.floors_per_tower = floors_per_tower
            project.units_per_floor = units_per_floor
            project.has_commercial = has_commercial
            project.commercial_floors = commercial_floors
            project.commercial_units_per_floor = commercial_units_per_floor
            project.save()
            
            # Delete existing tower configs and recreate from form data
            TowerFloorConfig.objects.filter(project=project).delete()
            
            # Collect tower configurations (flexible structure)
            tower_count = 0
            while tower_count < number_of_towers:
                tower_num = request.POST.get(f'tower_{tower_count}_number')
                if not tower_num:
                    break
                tower_num = int(tower_num)
                floors_count = int(request.POST.get(f'tower_{tower_count}_floors', '1'))
                units_per_floor_tower = int(request.POST.get(f'tower_{tower_count}_units_per_floor', '1'))
                is_commercial = request.POST.get(f'tower_{tower_count}_is_commercial') == 'on'
                
                # Store commercial floors and their unit counts in session for floor mapping step
                tower_commercial_floors = {}
                # Check if ground floor (0) is commercial
                ground_is_commercial = request.POST.get(f'tower_{tower_count}_floor_0_commercial') == 'on'
                
                # If ground is commercial, total = floors_count + 1 (G + N floors)
                # If ground is NOT commercial, total = floors_count (just 1-N floors, no ground)
                if ground_is_commercial:
                    total_floors = floors_count + 1
                    for floor_num in range(0, total_floors):  # Floor 0 (Ground) through N floors
                        if request.POST.get(f'tower_{tower_count}_floor_{floor_num}_commercial') == 'on':
                            commercial_units = request.POST.get(f'tower_{tower_count}_floor_{floor_num}_commercial_units', '0')
                            tower_commercial_floors[floor_num] = int(commercial_units) if commercial_units else 0
                else:
                    total_floors = floors_count
                    for floor_num in range(1, total_floors + 1):  # Floor 1 through N floors (no ground)
                        if request.POST.get(f'tower_{tower_count}_floor_{floor_num}_commercial') == 'on':
                            commercial_units = request.POST.get(f'tower_{tower_count}_floor_{floor_num}_commercial_units', '0')
                            tower_commercial_floors[floor_num] = int(commercial_units) if commercial_units else 0
                
                if 'edit_project_data' not in request.session:
                    request.session['edit_project_data'] = {}
                if 'commercial_floors' not in request.session['edit_project_data']:
                    request.session['edit_project_data']['commercial_floors'] = {}
                request.session['edit_project_data']['commercial_floors'][tower_num] = tower_commercial_floors
                request.session.modified = True
                
                TowerFloorConfig.objects.create(
                    project=project,
                    tower_number=tower_num,
                    floors_count=total_floors,  # Store total floors (G + N)
                    units_per_floor=units_per_floor_tower,
                    is_commercial=is_commercial,
                )
                tower_count += 1
            
            return JsonResponse({'success': True, 'step': 3})
        
        elif step == '3':
            # Step 3: Configurations & Pricing - Update configurations
            try:
                from django.db import transaction
                from projects.models import ProjectConfiguration, ConfigurationAreaType
                
                with transaction.atomic():
                    submitted_config_ids = set()
                    all_config_ids_in_form = set()
                    for key in request.POST.keys():
                        if key.startswith('config_id_'):
                            config_id = request.POST.get(key, '').strip()
                            if config_id and config_id.isdigit():
                                all_config_ids_in_form.add(int(config_id))
                    
                    # Find all config indices that exist in the form
                    config_indices = set()
                    for key in request.POST.keys():
                        if key.startswith('config_name_'):
                            idx = key.replace('config_name_', '')
                            if idx.isdigit():
                                config_indices.add(int(idx))
                    
                    config_count = 0
                    processed_configs = 0
                    max_configs = max(config_indices) if config_indices else 0
                    
                    while config_count <= max(max_configs, 100):
                        config_name = request.POST.get(f'config_name_{config_count}', '').strip()
                        if not config_name:
                            config_id = request.POST.get(f'config_id_{config_count}', '').strip()
                            if config_id and config_id.isdigit():
                                submitted_config_ids.add(int(config_id))
                            config_count += 1
                            continue
                        
                        config_id = request.POST.get(f'config_id_{config_count}', '').strip()
                        config_description = request.POST.get(f'config_description_{config_count}', '')
                        price_per_sqft = request.POST.get(f'config_price_per_sqft_{config_count}')
                        stamp_duty = request.POST.get(f'config_stamp_duty_{config_count}', '5.00')
                        gst = request.POST.get(f'config_gst_{config_count}', '5.00')
                        registration = request.POST.get(f'config_registration_{config_count}', '30000.00')
                        legal = request.POST.get(f'config_legal_{config_count}', '15000.00')
                        development = request.POST.get(f'config_development_{config_count}', '0.00')
                        
                        if config_id and config_id.isdigit():
                            # Existing configuration - update it
                            try:
                                config = ProjectConfiguration.objects.get(id=int(config_id), project=project)
                                if config.name != config_name:
                                    config.name = config_name
                                config.description = config_description
                                config.price_per_sqft = Decimal(price_per_sqft) if price_per_sqft else None
                                config.stamp_duty_percent = Decimal(stamp_duty)
                                config.gst_percent = Decimal(gst)
                                config.registration_charges = Decimal(registration)
                                config.legal_charges = Decimal(legal)
                                config.development_charges = Decimal(development)
                                config.save()
                                created = False
                                # Add to submitted IDs to prevent deletion
                                submitted_config_ids.add(config.id)
                            except ProjectConfiguration.DoesNotExist:
                                # ID doesn't exist, create new
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
                                created = True
                                # Add new config ID to prevent deletion
                                submitted_config_ids.add(config.id)
                        else:
                            # New configuration - create it
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
                            if not created:
                                # Config with same name exists, update it
                                config.description = config_description
                                config.price_per_sqft = Decimal(price_per_sqft) if price_per_sqft else None
                                config.stamp_duty_percent = Decimal(stamp_duty)
                                config.gst_percent = Decimal(gst)
                                config.registration_charges = Decimal(registration)
                                config.legal_charges = Decimal(legal)
                                config.development_charges = Decimal(development)
                                config.save()
                            # Add config ID to prevent deletion (whether created or updated)
                            submitted_config_ids.add(config.id)
                        
                        has_area_types = any(key.startswith(f'config_{config_count}_area_') for key in request.POST.keys())
                        if has_area_types:
                            # Collect area type IDs from form to track which ones to keep
                            area_type_ids_in_form = set()
                            
                            # First, update or create area types
                            area_count = 0
                            while area_count < 50:
                                carpet_area = request.POST.get(f'config_{config_count}_area_carpet_{area_count}')
                                buildup_area = request.POST.get(f'config_{config_count}_area_buildup_{area_count}')
                                area_type_id = request.POST.get(f'config_{config_count}_area_id_{area_count}', '').strip()
                                
                                if carpet_area and buildup_area:
                                    try:
                                        rera_area = request.POST.get(f'config_{config_count}_area_rera_{area_count}')
                                        area_description = request.POST.get(f'config_{config_count}_area_desc_{area_count}', '')
                                        
                                        carpet_decimal = Decimal(carpet_area)
                                        buildup_decimal = Decimal(buildup_area)
                                        rera_decimal = Decimal(rera_area) if rera_area else None
                                        
                                        # If we have an area_type_id, try to update existing
                                        if area_type_id and area_type_id.isdigit():
                                            try:
                                                area_type = ConfigurationAreaType.objects.get(
                                                    id=int(area_type_id),
                                                    configuration=config
                                                )
                                                # Check if carpet_area or buildup_area changed (unique constraint fields)
                                                carpet_changed = area_type.carpet_area != carpet_decimal
                                                buildup_changed = area_type.buildup_area != buildup_decimal
                                                
                                                if carpet_changed or buildup_changed:
                                                    # If unique fields changed, we need to handle the unique constraint
                                                    # First, check if a record with new values already exists
                                                    try:
                                                        existing = ConfigurationAreaType.objects.get(
                                                            configuration=config,
                                                            carpet_area=carpet_decimal,
                                                            buildup_area=buildup_decimal
                                                        )
                                                        # If it exists and it's not the same record, update it and delete old
                                                        if existing.id != area_type.id:
                                                            existing.rera_area = rera_decimal
                                                            existing.description = area_description
                                                            existing.save()
                                                            area_type.delete()
                                                            area_type = existing
                                                            area_type_ids_in_form.add(area_type.id)
                                                        else:
                                                            # Same record, just update
                                                            area_type.carpet_area = carpet_decimal
                                                            area_type.buildup_area = buildup_decimal
                                                            area_type.rera_area = rera_decimal
                                                            area_type.description = area_description
                                                            area_type.save()
                                                            area_type_ids_in_form.add(area_type.id)
                                                    except ConfigurationAreaType.DoesNotExist:
                                                        # No conflict, delete old and create new
                                                        old_id = area_type.id
                                                        area_type.delete()
                                                        area_type = ConfigurationAreaType.objects.create(
                                                            configuration=config,
                                                            carpet_area=carpet_decimal,
                                                            buildup_area=buildup_decimal,
                                                            rera_area=rera_decimal,
                                                            description=area_description,
                                                        )
                                                        area_type_ids_in_form.add(area_type.id)
                                                else:
                                                    # Only non-unique fields changed, update in place
                                                    area_type.rera_area = rera_decimal
                                                    area_type.description = area_description
                                                    area_type.save()
                                                    area_type_ids_in_form.add(area_type.id)
                                            except ConfigurationAreaType.DoesNotExist:
                                                # ID doesn't exist, create new
                                                area_type = ConfigurationAreaType.objects.create(
                                                    configuration=config,
                                                    carpet_area=carpet_decimal,
                                                    buildup_area=buildup_decimal,
                                                    rera_area=rera_decimal,
                                                    description=area_description,
                                                )
                                                area_type_ids_in_form.add(area_type.id)
                                        else:
                                            # No ID provided, check if area type already exists or create new
                                            area_type, created = ConfigurationAreaType.objects.get_or_create(
                                                configuration=config,
                                                carpet_area=carpet_decimal,
                                                buildup_area=buildup_decimal,
                                                defaults={
                                                    'rera_area': rera_decimal,
                                                    'description': area_description,
                                                }
                                            )
                                            # If it already existed, update the non-unique fields
                                            if not created:
                                                area_type.rera_area = rera_decimal
                                                area_type.description = area_description
                                                area_type.save()
                                            area_type_ids_in_form.add(area_type.id)
                                    except Exception as e:
                                        import traceback
                                        return JsonResponse({
                                            'success': False,
                                            'error': f'Error saving area type: {str(e)}'
                                        }, status=400)
                                elif area_count > 10:
                                    break
                                area_count += 1
                            
                            # Delete area types that are no longer in the form
                            if area_type_ids_in_form:
                                # Get area types to delete before deleting them
                                area_types_to_delete = list(config.area_types.exclude(id__in=area_type_ids_in_form).values_list('id', flat=True))
                                if area_types_to_delete:
                                    # Delete floor mappings that reference these area types
                                    config.floor_mappings.filter(area_type_id__in=area_types_to_delete).delete()
                                    # Now delete the area types
                                    config.area_types.filter(id__in=area_types_to_delete).delete()
                            else:
                                # If no area types in form, delete all
                                config.floor_mappings.all().delete()
                                config.area_types.all().delete()
                        
                        config_count += 1
                        processed_configs += 1
                        
                        # Safety check to prevent infinite loops
                        if processed_configs > 100:
                            break
                
                # Delete removed configurations
                existing_configs = ProjectConfiguration.objects.filter(project=project)
                if submitted_config_ids or all_config_ids_in_form:
                    ids_to_keep = submitted_config_ids | all_config_ids_in_form
                    configs_to_delete = existing_configs.exclude(id__in=ids_to_keep)
                    for config in configs_to_delete:
                        config.area_types.all().delete()
                        config.floor_mappings.all().delete()
                    configs_to_delete.delete()
                
                return JsonResponse({'success': True, 'step': 4})
            except Exception as e:
                import traceback
                return JsonResponse({
                    'success': False,
                    'error': f'Error updating configurations: {str(e)}'
                }, status=400)
        
        elif step == '4':
            # Step 4: Floor Mapping - Update unit configurations
            from projects.models import UnitConfiguration, TowerFloorConfig, ConfigurationAreaType
            
            has_floor_mapping_data = any(key.startswith('tower_') for key in request.POST.keys())
            if has_floor_mapping_data:
                project.unit_configurations.all().delete()
                
                # Build area type map from configurations
                area_type_map = {}
                for config in project.configurations.all():
                    for idx, area_type in enumerate(config.area_types.all()):
                        # Support both old format (config_{config.id}_area_{idx}) and new format (config_{index}_area_{idx})
                        area_type_map[f'config_{config.id}_area_{idx}'] = area_type.id
                        # Also map by index for compatibility
                        config_index = list(project.configurations.all()).index(config) if config in list(project.configurations.all()) else config.id
                        area_type_map[f'config_{config_index}_area_{idx}'] = area_type.id
                
                # Check if using flexible tower structure
                tower_configs_list = list(TowerFloorConfig.objects.filter(project=project).order_by('tower_number'))
                
                if tower_configs_list:
                    # Use flexible structure
                    for tower_config in tower_configs_list:
                        tower_num = tower_config.tower_number
                        floors_count = tower_config.floors_count
                        units_per_floor_tower = tower_config.units_per_floor
                        
                        # Get commercial floors and their unit counts from tower structure step (stored in session)
                        commercial_floors_data = request.session.get('edit_project_data', {}).get('commercial_floors', {})
                        tower_commercial_floors = commercial_floors_data.get(tower_num, {})  # Dict: {floor_num: units_count}
                        
                        # Check if ground floor (0) is commercial for this tower
                        ground_is_commercial = 0 in tower_commercial_floors
                        
                        # Determine floor range based on whether ground floor exists
                        if ground_is_commercial:
                            # Ground is commercial: iterate from 0 to floors_count-1 (G + 1-N)
                            floor_range = range(0, floors_count)
                        else:
                            # Ground is NOT commercial: iterate from 1 to floors_count (1-N only)
                            floor_range = range(1, floors_count + 1)
                        
                        for floor_num in floor_range:
                            floor_excluded = request.POST.get(f'tower_{tower_num}_floor_{floor_num}_excluded') == 'on'
                            # Check if this floor is commercial from tower structure step
                            floor_is_commercial = floor_num in tower_commercial_floors
                            
                            # Get units per floor
                            # For commercial floors, use the specified unit count, otherwise use default
                            if floor_is_commercial and floor_num in tower_commercial_floors:
                                units_per_floor_this = tower_commercial_floors.get(floor_num, units_per_floor_tower)
                            else:
                                units_per_floor_this = units_per_floor_tower
                            
                            for unit_idx in range(1, units_per_floor_this + 1):
                                # Floor 0 (Ground): 001, 002, 003... Floor 1: 101, 102, 103... Floor 7: 701, 702, 703...
                                unit_number = floor_num * 100 + unit_idx if floor_num > 0 else unit_idx
                                unit_excluded = request.POST.get(f'tower_{tower_num}_floor_{floor_num}_unit_{unit_idx}_excluded') == 'on'
                                area_type_key = request.POST.get(f'tower_{tower_num}_floor_{floor_num}_unit_{unit_idx}_area_type')
                                area_type_id = area_type_map.get(area_type_key) if area_type_key else None
                                
                                # Get the actual area_type object if ID exists
                                area_type_obj = None
                                if area_type_id and not (floor_excluded or unit_excluded):
                                    try:
                                        area_type_obj = ConfigurationAreaType.objects.get(id=area_type_id)
                                    except ConfigurationAreaType.DoesNotExist:
                                        pass
                                
                                UnitConfiguration.objects.create(
                                    project=project,
                                    tower_number=tower_num,
                                    floor_number=floor_num,
                                    unit_number=unit_number,
                                    area_type=area_type_obj,
                                    is_excluded=(floor_excluded or unit_excluded),
                                    is_commercial=floor_is_commercial,
                                )
                else:
                    # Fallback to legacy structure (no ground floor in legacy, start from floor 1)
                    floors_per_tower = project.floors_per_tower
                    units_per_floor = project.units_per_floor
                    number_of_towers = project.number_of_towers
                    
                    for tower_num in range(1, number_of_towers + 1):
                        for floor_num in range(1, floors_per_tower + 1):
                            floor_excluded = request.POST.get(f'tower_{tower_num}_floor_{floor_num}_excluded') == 'on'
                            floor_is_commercial = request.POST.get(f'tower_{tower_num}_floor_{floor_num}_is_commercial') == 'on'
                            
                            for unit_idx in range(1, units_per_floor + 1):
                                # Floor 0 (Ground): 001, 002, 003... Floor 1: 101, 102, 103... Floor 7: 701, 702, 703...
                                unit_number = floor_num * 100 + unit_idx if floor_num > 0 else unit_idx
                                unit_excluded = request.POST.get(f'tower_{tower_num}_floor_{floor_num}_unit_{unit_idx}_excluded') == 'on'
                                area_type_key = request.POST.get(f'tower_{tower_num}_floor_{floor_num}_unit_{unit_idx}_area_type')
                                area_type_id = area_type_map.get(area_type_key) if area_type_key else None
                                
                                # Get the actual area_type object if ID exists
                                area_type_obj = None
                                if area_type_id and not (floor_excluded or unit_excluded):
                                    try:
                                        area_type_obj = ConfigurationAreaType.objects.get(id=area_type_id)
                                    except ConfigurationAreaType.DoesNotExist:
                                        pass
                                
                                UnitConfiguration.objects.create(
                                    project=project,
                                    tower_number=tower_num,
                                    floor_number=floor_num,
                                    unit_number=unit_number,
                                    area_type=area_type_obj,
                                    is_excluded=(floor_excluded or unit_excluded),
                                    is_commercial=floor_is_commercial,
                                )
            
            return JsonResponse({'success': True, 'step': 5})
        
        elif step == '5':
            # Step 5: Settings & Assignment - Final update
            default_commission_percent = request.POST.get('default_commission_percent') or 0
            auto_assignment_strategy = request.POST.get('auto_assignment_strategy', 'manual')
            site_head_id = request.POST.get('site_head') or None
            
            project.default_commission_percent = Decimal(str(default_commission_percent))
            project.auto_assignment_strategy = auto_assignment_strategy
            project.site_head_id = site_head_id
            project.save()
            
            # Create/Update Highrise Pricing
            from projects.models import HighrisePricing
            highrise_enabled = request.POST.get('highrise_enabled') == 'on'
            if highrise_enabled:
                highrise_pricing, created = HighrisePricing.objects.get_or_create(
                    project=project,
                    defaults={
                        'is_enabled': True,
                        'floor_threshold': int(request.POST.get('highrise_floor_threshold', 10)),
                        'base_price_per_sqft': Decimal(request.POST.get('highrise_base_price_per_sqft', 0)) if request.POST.get('highrise_base_price_per_sqft') else None,
                        'pricing_type': request.POST.get('highrise_pricing_type', 'per_sqft'),
                        'fixed_price_increment': Decimal(request.POST.get('highrise_fixed_price_increment', 0)) if request.POST.get('highrise_fixed_price_increment') else Decimal('0'),
                        'per_sqft_increment': Decimal(request.POST.get('highrise_per_sqft_increment', 20)) if request.POST.get('highrise_per_sqft_increment') else Decimal('20'),
                        'development_charges_type': request.POST.get('highrise_dev_charges_type', 'fixed'),
                        'development_charges_fixed': Decimal(request.POST.get('highrise_dev_charges_fixed', 0)) if request.POST.get('highrise_dev_charges_fixed') else Decimal('0'),
                        'development_charges_per_sqft': Decimal(request.POST.get('highrise_dev_charges_per_sqft', 0)) if request.POST.get('highrise_dev_charges_per_sqft') else Decimal('0'),
                        'parking_price': Decimal(request.POST.get('highrise_parking_price', 0)) if request.POST.get('highrise_parking_price') else Decimal('0'),
                        'parking_negotiable': request.POST.get('highrise_parking_negotiable') == 'on',
                        'include_parking_in_calculation': request.POST.get('highrise_include_parking') == 'on',
                    }
                )
                if not created:
                    # Update existing
                    highrise_pricing.is_enabled = True
                    highrise_pricing.floor_threshold = int(request.POST.get('highrise_floor_threshold', 10))
                    highrise_pricing.base_price_per_sqft = Decimal(request.POST.get('highrise_base_price_per_sqft', 0)) if request.POST.get('highrise_base_price_per_sqft') else None
                    highrise_pricing.pricing_type = request.POST.get('highrise_pricing_type', 'per_sqft')
                    highrise_pricing.fixed_price_increment = Decimal(request.POST.get('highrise_fixed_price_increment', 0)) if request.POST.get('highrise_fixed_price_increment') else Decimal('0')
                    highrise_pricing.per_sqft_increment = Decimal(request.POST.get('highrise_per_sqft_increment', 20)) if request.POST.get('highrise_per_sqft_increment') else Decimal('20')
                    highrise_pricing.development_charges_type = request.POST.get('highrise_dev_charges_type', 'fixed')
                    highrise_pricing.development_charges_fixed = Decimal(request.POST.get('highrise_dev_charges_fixed', 0)) if request.POST.get('highrise_dev_charges_fixed') else Decimal('0')
                    highrise_pricing.development_charges_per_sqft = Decimal(request.POST.get('highrise_dev_charges_per_sqft', 0)) if request.POST.get('highrise_dev_charges_per_sqft') else Decimal('0')
                    highrise_pricing.parking_price = Decimal(request.POST.get('highrise_parking_price', 0)) if request.POST.get('highrise_parking_price') else Decimal('0')
                    highrise_pricing.parking_negotiable = request.POST.get('highrise_parking_negotiable') == 'on'
                    highrise_pricing.include_parking_in_calculation = request.POST.get('highrise_include_parking') == 'on'
                    highrise_pricing.save()
            else:
                # Disable highrise pricing if checkbox is unchecked
                HighrisePricing.objects.filter(project=project).update(is_enabled=False)
            
            messages.success(request, f'Project "{project.name}" updated successfully!')
            return JsonResponse({
                'success': True,
                'redirect_url': reverse('projects:detail', kwargs={'pk': project.pk})
            })
        
    
    # GET request - show form with existing data
    mandate_owners = User.objects.filter(role='mandate_owner')
    site_heads = User.objects.filter(role='site_head')
    
    # Get existing configurations
    configurations = project.configurations.all()
    
    # Get all area types for dropdown population
    from projects.models import ConfigurationAreaType
    all_area_types = ConfigurationAreaType.objects.filter(configuration__project=project).select_related('configuration')
    
    # Get existing unit configurations
    from projects.models import UnitConfiguration, TowerFloorConfig
    # Create a key-based lookup: "tower_floor_unit" -> unit_config
    unit_configurations = {}
    for uc in project.unit_configurations.all().select_related('area_type'):
        key = f"{uc.tower_number}_{uc.floor_number}_{uc.unit_number}"
        unit_configurations[key] = uc
    
    # Get existing tower floor configs
    tower_floor_configs = TowerFloorConfig.objects.filter(project=project).order_by('tower_number')
    
    # Get commercial floors data from session (if available from step 2)
    commercial_floors_data = request.session.get('edit_project_data', {}).get('commercial_floors', {})
    
    # Also get commercial floors from existing unit configurations
    existing_commercial_floors = {}
    for uc in project.unit_configurations.filter(is_commercial=True).select_related():
        tower_key = uc.tower_number
        if tower_key not in existing_commercial_floors:
            existing_commercial_floors[tower_key] = {}
        # Count units per floor for commercial floors
        floor_key = uc.floor_number
        if floor_key not in existing_commercial_floors[tower_key]:
            existing_commercial_floors[tower_key][floor_key] = 0
        existing_commercial_floors[tower_key][floor_key] += 1
    
    # Merge session data with existing data (session takes precedence)
    for tower_num, floors_dict in commercial_floors_data.items():
        tower_num_int = int(tower_num) if isinstance(tower_num, str) and tower_num.isdigit() else tower_num
        if tower_num_int not in existing_commercial_floors:
            existing_commercial_floors[tower_num_int] = {}
        # Convert floor numbers to int if they're strings
        if isinstance(floors_dict, dict):
            floors_dict_int = {int(k) if isinstance(k, str) and k.isdigit() else k: v for k, v in floors_dict.items()}
            existing_commercial_floors[tower_num_int].update(floors_dict_int)
    
    # Convert to JSON string for template
    import json
    commercial_floors_json = json.dumps(existing_commercial_floors)
    
    # Get project type choices for dropdown
    project_type_choices = Project.PROJECT_TYPE_CHOICES
    
    # Get highrise pricing if exists
    from projects.models import HighrisePricing
    highrise_pricing = None
    try:
        highrise_pricing = project.highrise_pricing
    except HighrisePricing.DoesNotExist:
        pass
    
    context = {
        'project': project,
        'mandate_owners': mandate_owners,
        'site_heads': site_heads,
        'configurations': configurations,
        'all_area_types': all_area_types,
        'unit_configurations': unit_configurations,
        'tower_floor_configs': tower_floor_configs,
        'commercial_floors_data': commercial_floors_json,  # Pass as JSON string
        'project_type_choices': project_type_choices,
        'highrise_pricing': highrise_pricing,
    }
    return render(request, 'projects/edit.html', context)


@login_required
def unit_selection(request, pk):
    """Interactive unit selection page (BookMyShow-style UI)"""
    project = get_object_or_404(Project, pk=pk)
    lead_id = request.GET.get('lead_id')  # Optional lead_id for booking flow
    
    # Permission check - Mandate Owner has same permissions as Super Admin
    # Site Heads can view units for projects they manage
    # Closing and Sourcing managers can view units for projects they're assigned to
    # Telecallers can view units for projects they're assigned to
    if request.user.is_super_admin() or request.user.is_mandate_owner():
        pass  # Super admin and Mandate Owner can see all
    elif request.user.is_site_head():
        if project.site_head != request.user:
            messages.error(request, 'You do not have permission to view this project.')
            return redirect('projects:list')
    elif request.user.is_closing_manager() or request.user.is_sourcing_manager():
        # Check if user is assigned to this project
        if project not in request.user.assigned_projects.all():
            messages.error(request, 'You do not have permission to view this project.')
            return redirect('projects:list')
    elif request.user.is_telecaller():
        if project not in request.user.assigned_projects.all():
            messages.error(request, 'You do not have permission to view this project.')
            return redirect('projects:list')
    else:
        messages.error(request, 'You do not have permission to view this project.')
        return redirect('projects:list')
    
    # Get all unit configurations with related data
    # Filter out non-commercial ground floors (floor 0) - they're vacant/parking
    unit_configs = UnitConfiguration.objects.filter(project=project).select_related(
        'area_type', 
        'area_type__configuration'
    ).exclude(
        floor_number=0,
        is_commercial=False
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
            booking_unit_num = int(booking.unit_number) if booking.unit_number and booking.unit_number.isdigit() else None
            booking_floor = booking.floor
            
            # Extract tower number from tower_wing (could be "Tower 1", "1", "Tower1", etc.)
            booking_tower = None
            if booking.tower_wing:
                # Try to extract number from tower_wing string
                import re
                tower_match = re.search(r'\d+', str(booking.tower_wing))
                if tower_match:
                    booking_tower = int(tower_match.group())
            
            if booking_unit_num and booking_floor:
                # Include tower in the key to avoid matching units from different towers
                if booking_tower:
                    key = f"{booking_tower}_{booking_floor}_{booking_unit_num}"
                else:
                    # Fallback: if no tower info, use floor and unit (less accurate but better than nothing)
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
        # Match by tower, floor, and unit number to avoid matching units from different towers
        booking_key = f"{unit_config.tower_number}_{unit_config.floor_number}_{unit_config.unit_number}"
        # Also check fallback key (without tower) for older bookings that might not have tower info
        fallback_key = f"{unit_config.floor_number}_{unit_config.unit_number}"
        is_booked = booking_key in booked_units or fallback_key in booked_units
        
        units_by_tower[tower_key][floor_key].append({
            'unit_config': unit_config,
            'pricing_info': pricing_info,
            'is_booked': is_booked,
            'booking': booked_units.get(booking_key) or booked_units.get(fallback_key),
        })
    
    context = {
        'project': project,
        'units_by_tower': units_by_tower,
        'configurations': configurations,
        'booked_units': booked_units,
        'lead_id': lead_id,  # Pass lead_id to template for booking flow
    }
    return render(request, 'projects/unit_selection.html', context)


@login_required
def migrate_leads(request, pk):
    """Duplicate leads from one project to another - Super Admin and Mandate Owners only"""
    project = get_object_or_404(Project, pk=pk)
    if not (request.user.is_super_admin() or request.user.is_mandate_owner()):
        messages.error(request, 'You do not have permission to duplicate leads.')
        return redirect('projects:detail', pk=project.pk)
    
    if request.method == 'POST':
        target_project_id = request.POST.get('target_project')
        if not target_project_id:
            messages.error(request, 'Please select a target project.')
            return redirect('projects:migrate_leads', pk=project.pk)
        
        target_project = get_object_or_404(Project, pk=target_project_id)
        
        # Get selected lead IDs or duplicate all if none selected
        from leads.models import LeadProjectAssociation
        selected_lead_ids = request.POST.getlist('lead_ids')
        
        # Get associations for the source project
        if selected_lead_ids:
            # Duplicate only selected leads
            associations_to_migrate = LeadProjectAssociation.objects.filter(
                project=project,
                lead_id__in=selected_lead_ids,
                is_archived=False
            )
        else:
            # Duplicate all leads if none selected
            associations_to_migrate = LeadProjectAssociation.objects.filter(
                project=project,
                is_archived=False
            )
        
        count = associations_to_migrate.count()
        if count > 0:
            # Duplicate leads instead of transferring them
            duplicated_count = 0
            for association in associations_to_migrate:
                lead = association.lead
                
                # Get or create the lead (deduplicate by phone)
                lead_defaults = {
                    # Client Information
                    'name': lead.name,
                    'email': lead.email,
                    'age': lead.age,
                    'gender': lead.gender,
                    'locality': lead.locality,
                    'current_residence': lead.current_residence,
                    'occupation': lead.occupation,
                    'company_name': lead.company_name,
                    'designation': lead.designation,
                    # Requirement Details
                    'budget': lead.budget,
                    'purpose': lead.purpose,
                    'visit_type': lead.visit_type,
                    'is_first_visit': lead.is_first_visit,
                    'how_did_you_hear': lead.how_did_you_hear,
                    'visit_source': lead.visit_source,
                    # CP Information
                    'channel_partner': lead.channel_partner,
                    'cp_firm_name': lead.cp_firm_name,
                    'cp_name': lead.cp_name,
                    'cp_phone': lead.cp_phone,
                    'cp_rera_number': lead.cp_rera_number,
                    # Notes
                    'notes': f"[Duplicated from {project.name}] {lead.notes}" if lead.notes else f"[Duplicated from {project.name}]",
                    # System Metadata
                    'created_by': request.user,
                }
                new_lead, lead_created = Lead.objects.get_or_create(
                    phone=lead.phone,
                    defaults=lead_defaults
                )
                
                # Copy configurations if they exist
                if lead.configurations.exists():
                    new_lead.configurations.set(lead.configurations.all())
                
                # Create new association for target project
                LeadProjectAssociation.objects.get_or_create(
                    lead=new_lead,
                    project=target_project,
                    defaults={
                        'status': 'new',  # Reset to new for the duplicate
                        'is_pretagged': False,  # Reset pretagging
                        'pretag_status': '',
                        'phone_verified': False,
                        'assigned_to': None,
                        'assigned_at': None,
                        'assigned_by': None,
                        'notes': f"[Duplicated from {project.name}] {association.notes}" if association.notes else f"[Duplicated from {project.name}]",
                        'created_by': request.user,
                    }
                )
                duplicated_count += 1
            
            messages.success(request, f'Successfully duplicated {duplicated_count} lead(s) to {target_project.name}. Original leads remain in {project.name}.')
        else:
            messages.warning(request, 'No leads selected for duplication.')
        
        return redirect('projects:detail', pk=project.pk)
    
    # GET request - show form
    # Get all projects owned by the same mandate owner (or all projects for mandate owners)
    if request.user.is_mandate_owner():
        # Mandate owners can migrate to any project
        target_projects = Project.objects.filter(is_active=True).exclude(pk=project.pk).order_by('name')
    else:
        # For other roles, only projects with same mandate owner
        target_projects = Project.objects.filter(
            mandate_owner=project.mandate_owner
        ).exclude(pk=project.pk).order_by('name')
    
    # Get leads for the source project - use LeadProjectAssociation
    from leads.models import LeadProjectAssociation
    association_ids = LeadProjectAssociation.objects.filter(
        project=project,
        is_archived=False
    ).values_list('lead_id', flat=True).distinct()
    leads = Lead.objects.filter(id__in=association_ids, is_archived=False).order_by('-created_at')
    
    context = {
        'source_project': project,  # Use source_project for template consistency
        'project': project,  # Also include project for backward compatibility
        'target_projects': target_projects,
        'leads': leads,
    }
    return render(request, 'projects/migrate_leads.html', context)


@login_required
def assign_employees(request, pk):
    """Assign employees (closing, sourcing, telecallers) to a project - Super Admin and Mandate Owners only"""
    project = get_object_or_404(Project, pk=pk)
    
    # Permission check
    if not (request.user.is_super_admin() or request.user.is_mandate_owner()):
        messages.error(request, 'You do not have permission to assign employees to projects.')
        return redirect('projects:detail', pk=project.pk)
    
    if request.method == 'POST':
        # Get selected employee IDs
        selected_employee_ids = request.POST.getlist('employees')
        selected_employee_ids = [int(eid) for eid in selected_employee_ids if eid]
        
        # Mandate owners and Super admins can assign any employee
        available_employees = User.objects.filter(
            role__in=['closing_manager', 'sourcing_manager', 'telecaller'],
            is_active=True
        )
        
        # Validate that all selected employees are in the available list
        valid_employee_ids = set(available_employees.values_list('id', flat=True))
        selected_employee_ids = [eid for eid in selected_employee_ids if eid in valid_employee_ids]
        
        # Update project assignments (works for all three roles: closing_manager, sourcing_manager, telecaller)
        project.assigned_telecallers.set(selected_employee_ids)
        
        messages.success(request, f'Successfully updated employee assignments for {project.name}.')
        return redirect('projects:detail', pk=project.pk)
    
    # GET request - show form
    # Mandate owners and Super admins can see all employees
    employees = User.objects.filter(
        role__in=['closing_manager', 'sourcing_manager', 'telecaller'],
        is_active=True
    ).order_by('role', 'username')
    
    # Get currently assigned employees for this project
    assigned_employee_ids = set(project.assigned_telecallers.values_list('id', flat=True))
    
    # Group employees by role and mark assigned status
    employees_by_role = {
        'closing_manager': [],
        'sourcing_manager': [],
        'telecaller': [],
    }
    
    for employee in employees:
        is_assigned = employee.id in assigned_employee_ids
        role_key = employee.role
        if role_key in employees_by_role:
            employees_by_role[role_key].append({
                'employee': employee,
                'is_assigned': is_assigned,
            })
    
    context = {
        'project': project,
        'employees_by_role': employees_by_role,
    }
    return render(request, 'projects/assign_employees.html', context)


@login_required
def unit_calculation(request, pk, unit_id):
    """Unit calculation page with negotiated price and booking conversion"""
    project = get_object_or_404(Project, pk=pk)
    unit_config = get_object_or_404(UnitConfiguration, pk=unit_id, project=project)
    
    # Permission check
    if request.user.is_super_admin() or request.user.is_mandate_owner():
        pass
    elif request.user.is_site_head():
        if project.site_head != request.user:
            messages.error(request, 'You do not have permission to view this project.')
            return redirect('projects:list')
    elif request.user.is_closing_manager() or request.user.is_sourcing_manager():
        if project not in request.user.assigned_projects.all():
            messages.error(request, 'You do not have permission to view this project.')
            return redirect('projects:list')
    elif request.user.is_telecaller():
        if project not in request.user.assigned_projects.all():
            messages.error(request, 'You do not have permission to view this project.')
            return redirect('projects:list')
    else:
        messages.error(request, 'You do not have permission to view this project.')
        return redirect('projects:list')
    
    # Get pricing information
    pricing_info = None
    if unit_config.area_type and unit_config.area_type.configuration:
        config = unit_config.area_type.configuration
        area_type = unit_config.area_type
        
        # Check if highrise pricing is enabled
        from projects.models import HighrisePricing
        highrise_pricing = None
        try:
            highrise_pricing = project.highrise_pricing
        except HighrisePricing.DoesNotExist:
            pass
        
        # Calculate price per sqft - use highrise pricing if enabled
        base_price_per_sqft = config.price_per_sqft or Decimal('0')
        if highrise_pricing and highrise_pricing.is_enabled:
            # Use highrise pricing calculation
            floor_number = unit_config.floor_number
            adjusted_price_per_sqft = highrise_pricing.calculate_price_per_sqft(
                floor_number=floor_number,
                base_price_per_sqft=base_price_per_sqft
            )
            price_per_sqft = adjusted_price_per_sqft
        else:
            price_per_sqft = base_price_per_sqft
        
        # Calculate agreement value using adjusted price
        if price_per_sqft and area_type.buildup_area:
            agreement_value = price_per_sqft * area_type.buildup_area
            
            # Add fixed total price increment if using fixed_total pricing
            if highrise_pricing and highrise_pricing.is_enabled and highrise_pricing.pricing_type == 'fixed_total':
                total_increment = highrise_pricing.calculate_total_price_increment(unit_config.floor_number)
                agreement_value += total_increment
        else:
            agreement_value = None
        
        # Calculate cost breakdown
        if agreement_value:
            stamp_duty = agreement_value * (config.stamp_duty_percent / 100)
            gst = agreement_value * (config.gst_percent / 100)
            
            # Get development charges - use highrise if enabled, otherwise use config
            if highrise_pricing and highrise_pricing.is_enabled:
                development_charges = highrise_pricing.calculate_development_charges(
                    buildup_area=area_type.buildup_area
                )
            else:
                development_charges = config.development_charges or Decimal('0')
            
            # Get parking price - use highrise if enabled
            parking_price = Decimal('0')
            if highrise_pricing and highrise_pricing.is_enabled:
                parking_price = highrise_pricing.get_parking_price()
            
            total = agreement_value + stamp_duty + gst + config.registration_charges + config.legal_charges + development_charges + parking_price
            
            cost_breakdown = {
                'agreement_value': agreement_value,
                'stamp_duty': stamp_duty,
                'gst': gst,
                'registration_charges': config.registration_charges,
                'legal_charges': config.legal_charges,
                'development_charges': development_charges,
                'parking_price': parking_price,
                'total': total
            }
        else:
            cost_breakdown = None
        
        pricing_info = {
            'agreement_value': agreement_value,
            'total_cost': cost_breakdown['total'] if cost_breakdown else None,
            'cost_breakdown': cost_breakdown,
            'price_per_sqft': price_per_sqft,
            'base_price_per_sqft': base_price_per_sqft,  # Original price before highrise adjustment
            'stamp_duty_percent': config.stamp_duty_percent,
            'gst_percent': config.gst_percent,
            'carpet_area': area_type.carpet_area,
            'buildup_area': area_type.buildup_area,
            'rera_area': area_type.rera_area,
            'configuration_name': config.name,
            'area_display': area_type.get_display_name(),
            'highrise_pricing': highrise_pricing,
            'floor_number': unit_config.floor_number,
        }
    
    # Get visited leads for this project (for booking conversion)
    # Get associations for visited leads in this project
    from leads.models import LeadProjectAssociation
    visited_associations = LeadProjectAssociation.objects.filter(
        project=project,
        is_archived=False
    ).filter(
        Q(status__in=['visit_completed', 'discussion', 'hot', 'ready_to_book']) |
        Q(is_pretagged=True, pretag_status='verified') |
        Q(phone_verified=True)  # Include any phone verified leads
    ).select_related('lead').order_by('-updated_at')
    
    # Get unique leads (exclude those already booked)
    visited_lead_ids = visited_associations.values_list('lead_id', flat=True).distinct()
    # Exclude leads that have bookings for this project
    from bookings.models import Booking
    booked_lead_ids = Booking.objects.filter(
        project=project,
        is_archived=False
    ).values_list('lead_id', flat=True).distinct()
    visited_lead_ids = [lid for lid in visited_lead_ids if lid not in booked_lead_ids]
    visited_leads = Lead.objects.filter(
        id__in=visited_lead_ids,
        is_archived=False
    ).order_by('-updated_at')
    
    # Get channel partners linked to this project
    from channel_partners.models import ChannelPartner
    channel_partners = ChannelPartner.objects.filter(
        linked_projects=project,
        status='active'
    ).order_by('cp_name')
    
    context = {
        'project': project,
        'unit_config': unit_config,
        'pricing_info': pricing_info,
        'visited_leads': visited_leads,
        'channel_partners': channel_partners,
    }
    return render(request, 'projects/unit_calculation.html', context)


@login_required
def multi_unit_calculation(request, pk):
    """Multi-unit calculation page with dynamic pricing for multiple units"""
    project = get_object_or_404(Project, pk=pk)
    
    # Permission check
    if request.user.is_super_admin() or request.user.is_mandate_owner():
        pass
    elif request.user.is_site_head():
        if project.site_head != request.user:
            messages.error(request, 'You do not have permission to view this project.')
            return redirect('projects:list')
    elif request.user.is_closing_manager() or request.user.is_sourcing_manager():
        if project not in request.user.assigned_projects.all():
            messages.error(request, 'You do not have permission to view this project.')
            return redirect('projects:list')
    elif request.user.is_telecaller():
        if project not in request.user.assigned_projects.all():
            messages.error(request, 'You do not have permission to view this project.')
            return redirect('projects:list')
    else:
        messages.error(request, 'You do not have permission to view this project.')
        return redirect('projects:list')
    
    # Get unit IDs from query string
    unit_ids_param = request.GET.get('unit_ids', '')
    if not unit_ids_param:
        messages.error(request, 'No units selected for calculation.')
        return redirect('projects:unit_selection', pk=project.pk)
    
    unit_ids = [int(uid) for uid in unit_ids_param.split(',') if uid.strip().isdigit()]
    if not unit_ids:
        messages.error(request, 'Invalid unit selection.')
        return redirect('projects:unit_selection', pk=project.pk)
    
    # Get unit configurations
    unit_configs = UnitConfiguration.objects.filter(
        id__in=unit_ids,
        project=project
    ).select_related('area_type', 'area_type__configuration').order_by('tower_number', 'floor_number', 'unit_number')
    
    if not unit_configs.exists():
        messages.error(request, 'Selected units not found.')
        return redirect('projects:unit_selection', pk=project.pk)
    
    # Check if highrise pricing is enabled
    from projects.models import HighrisePricing
    highrise_pricing = None
    try:
        highrise_pricing = project.highrise_pricing
    except HighrisePricing.DoesNotExist:
        pass
    
    # Calculate pricing for each unit
    units_data = []
    total_agreement_value = Decimal('0')
    total_stamp_duty = Decimal('0')
    total_gst = Decimal('0')
    total_registration = Decimal('0')
    total_legal = Decimal('0')
    total_development = Decimal('0')
    total_parking = Decimal('0')
    total_cost = Decimal('0')
    total_carpet_area = Decimal('0')
    total_buildup_area = Decimal('0')
    
    for unit_config in unit_configs:
        if not unit_config.area_type or not unit_config.area_type.configuration:
            continue
            
        config = unit_config.area_type.configuration
        area_type = unit_config.area_type
        
        # Calculate price per sqft - use highrise pricing if enabled
        base_price_per_sqft = config.price_per_sqft or Decimal('0')
        if highrise_pricing and highrise_pricing.is_enabled:
            price_per_sqft = highrise_pricing.calculate_price_per_sqft(
                floor_number=unit_config.floor_number,
                base_price_per_sqft=base_price_per_sqft
            )
        else:
            price_per_sqft = base_price_per_sqft
        
        # Calculate agreement value
        if price_per_sqft and area_type.buildup_area:
            agreement_value = price_per_sqft * area_type.buildup_area
            
            # Add fixed total price increment if using fixed_total pricing
            if highrise_pricing and highrise_pricing.is_enabled and highrise_pricing.pricing_type == 'fixed_total':
                total_increment = highrise_pricing.calculate_total_price_increment(unit_config.floor_number)
                agreement_value += total_increment
        else:
            agreement_value = Decimal('0')
        
        # Calculate cost breakdown
        stamp_duty = agreement_value * (config.stamp_duty_percent / 100)
        gst = agreement_value * (config.gst_percent / 100)
        
        # Get development charges
        if highrise_pricing and highrise_pricing.is_enabled:
            development_charges = highrise_pricing.calculate_development_charges(
                buildup_area=area_type.buildup_area
            )
        else:
            development_charges = config.development_charges or Decimal('0')
        
        # Get parking price
        parking_price = Decimal('0')
        if highrise_pricing and highrise_pricing.is_enabled:
            parking_price = highrise_pricing.get_parking_price()
        
        unit_total = agreement_value + stamp_duty + gst + config.registration_charges + config.legal_charges + development_charges + parking_price
        
        # Accumulate totals
        total_agreement_value += agreement_value
        total_stamp_duty += stamp_duty
        total_gst += gst
        total_registration += config.registration_charges
        total_legal += config.legal_charges
        total_development += development_charges
        total_parking += parking_price
        total_cost += unit_total
        total_carpet_area += area_type.carpet_area
        total_buildup_area += area_type.buildup_area
        
        units_data.append({
            'unit_config': unit_config,
            'configuration_name': config.name,
            'area_display': area_type.get_display_name(),
            'carpet_area': area_type.carpet_area,
            'buildup_area': area_type.buildup_area,
            'rera_area': area_type.rera_area,
            'price_per_sqft': price_per_sqft,
            'base_price_per_sqft': base_price_per_sqft,
            'agreement_value': agreement_value,
            'stamp_duty': stamp_duty,
            'gst': gst,
            'registration_charges': config.registration_charges,
            'legal_charges': config.legal_charges,
            'development_charges': development_charges,
            'parking_price': parking_price,
            'total': unit_total,
            'stamp_duty_percent': config.stamp_duty_percent,
            'gst_percent': config.gst_percent,
        })
    
    # Calculate average price per sqft
    avg_price_per_sqft = total_agreement_value / total_buildup_area if total_buildup_area > 0 else Decimal('0')
    
    # Get visited leads for booking conversion
    from leads.models import LeadProjectAssociation
    visited_associations = LeadProjectAssociation.objects.filter(
        project=project,
        is_archived=False
    ).filter(
        Q(status__in=['visit_completed', 'discussion', 'hot', 'ready_to_book']) |
        Q(is_pretagged=True, pretag_status='verified') |
        Q(phone_verified=True)
    ).select_related('lead').order_by('-updated_at')
    
    # Get unique leads (exclude those already booked)
    visited_lead_ids = visited_associations.values_list('lead_id', flat=True).distinct()
    from bookings.models import Booking
    booked_lead_ids = Booking.objects.filter(
        project=project,
        is_archived=False
    ).values_list('lead_id', flat=True).distinct()
    visited_lead_ids = [lid for lid in visited_lead_ids if lid not in booked_lead_ids]
    visited_leads = Lead.objects.filter(
        id__in=visited_lead_ids,
        is_archived=False
    ).order_by('-updated_at')
    
    # Get channel partners linked to this project
    from channel_partners.models import ChannelPartner
    channel_partners = ChannelPartner.objects.filter(
        linked_projects=project,
        status='active'
    ).order_by('cp_name')
    
    # Get stamp duty and GST percentages (use first unit's config as reference)
    stamp_duty_percent = units_data[0]['stamp_duty_percent'] if units_data else 5
    gst_percent = units_data[0]['gst_percent'] if units_data else 5
    
    context = {
        'project': project,
        'units_data': units_data,
        'total_agreement_value': total_agreement_value,
        'total_stamp_duty': total_stamp_duty,
        'total_gst': total_gst,
        'total_registration': total_registration,
        'total_legal': total_legal,
        'total_development': total_development,
        'total_parking': total_parking,
        'total_cost': total_cost,
        'total_carpet_area': total_carpet_area,
        'total_buildup_area': total_buildup_area,
        'avg_price_per_sqft': avg_price_per_sqft,
        'highrise_pricing': highrise_pricing,
        'visited_leads': visited_leads,
        'channel_partners': channel_partners,
        'stamp_duty_percent': stamp_duty_percent,
        'gst_percent': gst_percent,
        'unit_ids': ','.join([str(unit['unit_config'].id) for unit in units_data]),
    }
    return render(request, 'projects/multi_unit_calculation.html', context)


@login_required
def search_visited_leads(request, pk):
    """API endpoint to search visited leads for booking conversion"""
    project = get_object_or_404(Project, pk=pk)
    
    # Permission check
    if not (request.user.is_super_admin() or request.user.is_mandate_owner() or 
            request.user.is_site_head() or request.user.is_closing_manager()):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    # Get all visited leads for this project (not just assigned to user)
    # Note: We include booked leads so they can book additional units
    from leads.models import LeadProjectAssociation
    visited_associations = LeadProjectAssociation.objects.filter(
        project=project,
        is_archived=False
    ).filter(
        Q(status__in=['visit_completed', 'discussion', 'hot', 'ready_to_book', 'booked']) |
        Q(is_pretagged=True, pretag_status='verified') |
        Q(phone_verified=True)
    ).select_related('lead', 'lead__channel_partner')
    
    # Search by name, phone, email
    if query:
        visited_associations = visited_associations.filter(
            Q(lead__name__icontains=query) |
            Q(lead__phone__icontains=query) |
            Q(lead__email__icontains=query)
        )
    
    # Get unique leads
    lead_ids = visited_associations.values_list('lead_id', flat=True).distinct()
    leads = Lead.objects.filter(id__in=lead_ids, is_archived=False)[:20]
    
    results = []
    for lead in leads:
        # Get primary association for this project
        assoc = visited_associations.filter(lead=lead).first()
        results.append({
            'id': lead.id,
            'name': lead.name,
            'phone': lead.phone,
            'email': lead.email or '',
            'budget': float(lead.budget) if lead.budget else 0,
            'configurations': [c.display_name for c in lead.configurations.all()],
            'cp_name': lead.channel_partner.cp_name if lead.channel_partner else (lead.cp_name or ''),
            'cp_firm_name': lead.channel_partner.firm_name if lead.channel_partner else (lead.cp_firm_name or ''),
            'status': assoc.get_status_display() if assoc else 'Unknown',
        })
    
    return JsonResponse({'results': results})


@login_required
@require_http_methods(["POST"])
def project_archive_data(request, pk):
    """Archive all bookings and lead associations for a project - Super Admin and Mandate Owners only"""
    project = get_object_or_404(Project, pk=pk)
    
    if not (request.user.is_super_admin() or request.user.is_mandate_owner()):
        messages.error(request, 'You do not have permission to archive project data.')
        return redirect('projects:detail', pk=project.pk)
    
    from leads.models import LeadProjectAssociation
    from bookings.models import Booking
    
    # Archive all bookings
    bookings_count = Booking.objects.filter(project=project, is_archived=False).update(is_archived=True)
    
    # Archive all lead associations
    associations_count = LeadProjectAssociation.objects.filter(project=project, is_archived=False).update(is_archived=True)
    
    messages.success(request, f'Archived {bookings_count} booking(s) and {associations_count} lead association(s) for project "{project.name}". You can now delete the project.')
    return redirect('projects:detail', pk=project.pk)


@login_required
@require_http_methods(["POST", "DELETE"])
def project_delete(request, pk):
    """Delete project - Super Admin and Mandate Owners only"""
    project = get_object_or_404(Project, pk=pk)
    
    if not (request.user.is_super_admin() or request.user.is_mandate_owner()):
        messages.error(request, 'You do not have permission to delete projects.')
        return redirect('projects:list')
    
    # Check if project has any bookings or leads
    from leads.models import LeadProjectAssociation
    has_bookings = Booking.objects.filter(project=project, is_archived=False).exists()
    has_leads = LeadProjectAssociation.objects.filter(project=project, is_archived=False).exists()
    
    if has_bookings or has_leads:
        messages.error(request, f'Cannot delete project "{project.name}" because it has associated bookings or leads. Please archive them first.')
        return redirect('projects:detail', pk=project.pk)
    
    project_name = project.name
    project.delete()
    
    messages.success(request, f'Project "{project_name}" has been deleted successfully.')
    return redirect('projects:list')
