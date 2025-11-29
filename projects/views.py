from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Q
from .models import Project, ProjectConfiguration, PaymentMilestone
from accounts.models import User
from leads.models import Lead
from bookings.models import Booking, Payment


@login_required
def project_list(request):
    """List all projects - Super Admin sees all, others see their projects"""
    if request.user.is_super_admin():
        projects = Project.objects.all()
    elif request.user.is_mandate_owner():
        projects = Project.objects.filter(mandate_owner=request.user)
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
        inventory_summary = request.POST.get('inventory_summary', '')
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
        commercial_floors = int(request.POST.get('commercial_floors', 0))
        commercial_units_per_floor = int(request.POST.get('commercial_units_per_floor', 0))
        
        # Mandate owner is current user if not super admin
        mandate_owner = request.user
        if request.user.is_super_admin():
            mandate_owner_id = request.POST.get('mandate_owner')
            if mandate_owner_id:
                mandate_owner = get_object_or_404(User, pk=mandate_owner_id, role='mandate_owner')
        
        project = Project.objects.create(
            name=name,
            builder_name=builder_name,
            location=location,
            rera_id=rera_id,
            project_type=project_type,
            starting_price=starting_price,
            inventory_summary=inventory_summary,
            latitude=latitude,
            longitude=longitude,
            default_commission_percent=default_commission_percent,
            auto_assignment_strategy=auto_assignment_strategy,
            number_of_towers=number_of_towers,
            floors_per_tower=floors_per_tower,
            units_per_floor=units_per_floor,
            has_commercial=has_commercial,
            commercial_floors=commercial_floors,
            commercial_units_per_floor=commercial_units_per_floor,
            mandate_owner=mandate_owner,
            site_head_id=site_head_id,
            is_active=True
        )
        
        # Handle image upload
        if 'image' in request.FILES:
            project.image = request.FILES['image']
            project.save()
        
        messages.success(request, f'Project {project.name} created successfully!')
        return redirect('projects:detail', pk=project.pk)
    
    # Get mandate owners for dropdown (only for Super Admin)
    mandate_owners = None
    if request.user.is_super_admin():
        mandate_owners = User.objects.filter(role='mandate_owner', is_active=True)
    
    # Get site heads
    site_heads = User.objects.filter(role='site_head', is_active=True)
    if request.user.is_mandate_owner():
        site_heads = site_heads.filter(mandate_owner=request.user)
    
    context = {
        'mandate_owners': mandate_owners,
        'site_heads': site_heads,
        'project_type_choices': Project.PROJECT_TYPE_CHOICES,
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
    
    # Get configurations
    configurations = project.configurations.all()
    
    # Get payment milestones
    milestones = project.payment_milestones.all().order_by('order')
    
    context = {
        'project': project,
        'stats': stats,
        'configurations': configurations,
        'milestones': milestones,
    }
    return render(request, 'projects/detail.html', context)


@login_required
def project_edit(request, pk):
    """Edit project - Super Admin and Mandate Owners"""
    project = get_object_or_404(Project, pk=pk)
    
    if not (request.user.is_super_admin() or request.user.is_mandate_owner()):
        messages.error(request, 'You do not have permission to edit projects.')
        return redirect('dashboard')
    
    # Mandate owner can only edit their projects
    if request.user.is_mandate_owner() and project.mandate_owner != request.user:
        messages.error(request, 'You can only edit your own projects.')
        return redirect('projects:list')
    
    if request.method == 'POST':
        project.name = request.POST.get('name')
        project.builder_name = request.POST.get('builder_name')
        project.location = request.POST.get('location')
        project.rera_id = request.POST.get('rera_id', '')
        project.project_type = request.POST.get('project_type')
        project.starting_price = request.POST.get('starting_price') or None
        project.inventory_summary = request.POST.get('inventory_summary', '')
        project.latitude = request.POST.get('latitude') or None
        project.longitude = request.POST.get('longitude') or None
        project.default_commission_percent = request.POST.get('default_commission_percent') or 0
        project.auto_assignment_strategy = request.POST.get('auto_assignment_strategy', 'manual')
        project.is_active = request.POST.get('is_active') == 'on'
        
        # Tower and Unit Structure
        project.number_of_towers = int(request.POST.get('number_of_towers', 1))
        project.floors_per_tower = int(request.POST.get('floors_per_tower', 1))
        project.units_per_floor = int(request.POST.get('units_per_floor', 1))
        project.has_commercial = request.POST.get('has_commercial') == 'on'
        project.commercial_floors = int(request.POST.get('commercial_floors', 0))
        project.commercial_units_per_floor = int(request.POST.get('commercial_units_per_floor', 0))
        
        # Site head assignment
        site_head_id = request.POST.get('site_head') or None
        project.site_head_id = site_head_id
        
        # Mandate owner (only Super Admin can change)
        if request.user.is_super_admin():
            mandate_owner_id = request.POST.get('mandate_owner')
            if mandate_owner_id:
                project.mandate_owner_id = mandate_owner_id
        
        # Handle image upload
        if 'image' in request.FILES:
            project.image = request.FILES['image']
        
        project.save()
        messages.success(request, f'Project {project.name} updated successfully!')
        return redirect('projects:detail', pk=project.pk)
    
    # Get mandate owners for dropdown (only for Super Admin)
    mandate_owners = None
    if request.user.is_super_admin():
        mandate_owners = User.objects.filter(role='mandate_owner', is_active=True)
    
    # Get site heads
    site_heads = User.objects.filter(role='site_head', is_active=True)
    if request.user.is_mandate_owner():
        site_heads = site_heads.filter(mandate_owner=request.user)
    
    context = {
        'project': project,
        'mandate_owners': mandate_owners,
        'site_heads': site_heads,
        'project_type_choices': Project.PROJECT_TYPE_CHOICES,
    }
    return render(request, 'projects/edit.html', context)
