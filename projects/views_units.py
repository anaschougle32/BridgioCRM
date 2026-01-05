from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import Project, UnitConfiguration
from bookings.models import Booking
from accounts.models import User


@login_required
def unit_inventory(request, project_id):
    """Unit inventory management for a project"""
    project = get_object_or_404(Project, pk=project_id)
    
    # Permission check
    if request.user.is_super_admin() or request.user.is_mandate_owner():
        pass  # Can see all
    elif request.user.is_site_head():
        if project.site_head != request.user:
            messages.error(request, 'You do not have permission to view this project.')
            return redirect('projects:list')
    elif request.user.is_closing_manager() or request.user.is_sourcing_manager():
        if project not in request.user.assigned_projects.all():
            messages.error(request, 'You do not have permission to view this project.')
            return redirect('projects:list')
    else:
        messages.error(request, 'You do not have permission to view unit inventory.')
        return redirect('dashboard')
    
    # Get all units for this project
    units = UnitConfiguration.objects.filter(
        project=project
    ).select_related('area_type', 'area_type__configuration', 'booking', 'blocked_by')
    
    # Filters
    status_filter = request.GET.get('status', '')
    tower_filter = request.GET.get('tower', '')
    floor_filter = request.GET.get('floor', '')
    search = request.GET.get('search', '')
    
    # Apply filters
    if status_filter:
        units = units.filter(status=status_filter)
    if tower_filter:
        units = units.filter(tower_number=tower_filter)
    if floor_filter:
        units = units.filter(floor_number=floor_filter)
    if search:
        units = units.filter(
            Q(unit_number__icontains=search) |
            Q(full_unit_number__icontains=search) |
            Q(area_type__configuration__name__icontains=search)
        )
    
    # Order
    units = units.order_by('tower_number', 'floor_number', 'unit_number')
    
    # Pagination
    paginator = Paginator(units, 50)
    page = request.GET.get('page', 1)
    units_page = paginator.get_page(page)
    
    # Calculate statistics
    stats = {
        'total_units': units.count(),
        'available': units.filter(status='available').count(),
        'booked': units.filter(status='booked').count(),
        'blocked': units.filter(status='blocked').count(),
        'reserved': units.filter(status='reserved').count(),
        'maintenance': units.filter(status='maintenance').count(),
        'sold': units.filter(status='sold').count(),
        'excluded': units.filter(is_excluded=True).count(),
    }
    
    # Get unique towers and floors for filters
    towers = sorted(set(units.values_list('tower_number', flat=True)))
    floors = sorted(set(units.values_list('floor_number', flat=True)))
    
    context = {
        'project': project,
        'units': units_page,
        'stats': stats,
        'towers': towers,
        'floors': floors,
        'status_choices': UnitConfiguration.STATUS_CHOICES,
        'filters': {
            'status': status_filter,
            'tower': tower_filter,
            'floor': floor_filter,
            'search': search,
        }
    }
    return render(request, 'projects/units/inventory.html', context)


@login_required
def block_unit(request, project_id, unit_id):
    """Block a unit for a specified time period"""
    project = get_object_or_404(Project, pk=project_id)
    unit = get_object_or_404(UnitConfiguration, pk=unit_id, project=project)
    
    # Permission check
    if not (request.user.is_closing_manager() or request.user.is_sourcing_manager() or 
            request.user.is_site_head() or request.user.is_super_admin() or request.user.is_mandate_owner()):
        messages.error(request, 'You do not have permission to block units.')
        return redirect('projects:unit_inventory', project_id=project_id)
    
    if request.method == 'POST':
        hours = int(request.POST.get('hours', 24))
        notes = request.POST.get('notes', '')
        
        success, message = unit.block_unit(request.user, hours)
        
        if success:
            if notes:
                unit.notes = notes
                unit.save(update_fields=['notes'])
            messages.success(request, message)
        else:
            messages.error(request, message)
    
    return redirect('projects:unit_inventory', project_id=project_id)


@login_required
def unblock_unit(request, project_id, unit_id):
    """Unblock a unit"""
    project = get_object_or_404(Project, pk=project_id)
    unit = get_object_or_404(UnitConfiguration, pk=unit_id, project=project)
    
    # Permission check
    if not (request.user.is_closing_manager() or request.user.is_sourcing_manager() or 
            request.user.is_site_head() or request.user.is_super_admin() or request.user.is_mandate_owner()):
        messages.error(request, 'You do not have permission to unblock units.')
        return redirect('projects:unit_inventory', project_id=project_id)
    
    success, message = unit.unblock_unit(request.user)
    
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    
    return redirect('projects:unit_inventory', project_id=project_id)


@login_required
def update_unit_status(request, project_id, unit_id):
    """Update unit status"""
    project = get_object_or_404(Project, pk=project_id)
    unit = get_object_or_404(UnitConfiguration, pk=unit_id, project=project)
    
    # Permission check
    if not (request.user.is_site_head() or request.user.is_super_admin() or request.user.is_mandate_owner()):
        messages.error(request, 'You do not have permission to update unit status.')
        return redirect('projects:unit_inventory', project_id=project_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        if new_status in dict(UnitConfiguration.STATUS_CHOICES):
            # If booking, remove existing booking reference
            if new_status != 'booked':
                unit.booking = None
            
            unit.status = new_status
            unit.notes = notes
            
            # Clear block information if making available
            if new_status == 'available':
                unit.blocked_by = None
                unit.blocked_at = None
                unit.blocked_until = None
            
            unit.save()
            messages.success(request, f'Unit status updated to {unit.get_status_display()}.')
        else:
            messages.error(request, 'Invalid status selected.')
    
    return redirect('projects:unit_inventory', project_id=project_id)


@login_required
def unit_availability_api(request, project_id):
    """API endpoint to check unit availability"""
    project = get_object_or_404(Project, pk=project_id)
    
    # Permission check
    if request.user.is_telecaller():
        if project not in request.user.assigned_projects.all():
            return JsonResponse({'error': 'Permission denied'}, status=403)
    elif not (request.user.is_closing_manager() or request.user.is_sourcing_manager() or 
              request.user.is_site_head() or request.user.is_super_admin() or request.user.is_mandate_owner()):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Get available units
    available_units = UnitConfiguration.get_available_units(project)
    
    # Format for API response
    units_data = []
    for unit in available_units:
        unit_data = {
            'id': unit.id,
            'full_unit_number': unit.full_unit_number,
            'tower_number': unit.tower_number,
            'floor_number': unit.floor_number,
            'unit_number': unit.unit_number,
            'area_type': unit.area_type.configuration.name if unit.area_type else None,
            'carpet_area': unit.area_type.carpet_area if unit.area_type else None,
            'price': unit.area_type.base_price if unit.area_type else None,
        }
        units_data.append(unit_data)
    
    return JsonResponse({
        'available_units': units_data,
        'total_available': len(units_data)
    })


@login_required
def bulk_unit_actions(request, project_id):
    """Bulk actions on multiple units"""
    project = get_object_or_404(Project, pk=project_id)
    
    # Permission check
    if not (request.user.is_site_head() or request.user.is_super_admin() or request.user.is_mandate_owner()):
        messages.error(request, 'You do not have permission to perform bulk actions.')
        return redirect('projects:unit_inventory', project_id=project_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        unit_ids = request.POST.getlist('unit_ids')
        
        if not unit_ids:
            messages.error(request, 'No units selected.')
            return redirect('projects:unit_inventory', project_id=project_id)
        
        units = UnitConfiguration.objects.filter(
            pk__in=unit_ids,
            project=project
        )
        
        if action == 'block':
            hours = int(request.POST.get('hours', 24))
            blocked_count = 0
            
            for unit in units:
                success, _ = unit.block_unit(request.user, hours)
                if success:
                    blocked_count += 1
            
            messages.success(request, f'{blocked_count} units blocked for {hours} hours.')
        
        elif action == 'unblock':
            unblocked_count = 0
            
            for unit in units:
                success, _ = unit.unblock_unit(request.user)
                if success:
                    unblocked_count += 1
            
            messages.success(request, f'{unblocked_count} units unblocked.')
        
        elif action == 'update_status':
            new_status = request.POST.get('status')
            if new_status in dict(UnitConfiguration.STATUS_CHOICES):
                updated_count = units.update(status=new_status)
                messages.success(request, f'{updated_count} units updated to {new_status}.')
            else:
                messages.error(request, 'Invalid status selected.')
        
        else:
            messages.error(request, 'Invalid action selected.')
    
    return redirect('projects:unit_inventory', project_id=project_id)
