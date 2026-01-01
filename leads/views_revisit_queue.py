"""
Views for Revisit and Queue Visit features
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from datetime import datetime

from .models import Lead, LeadProjectAssociation, GlobalConfiguration
from projects.models import Project


@login_required
def schedule_revisit(request, pk):
    """Schedule a revisit for a lead - Closing Managers only"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)
    
    # Permission check
    if not (request.user.is_closing_manager() or request.user.is_super_admin() or request.user.is_mandate_owner()):
        return JsonResponse({'success': False, 'error': 'You do not have permission to schedule revisits.'}, status=403)
    
    lead = get_object_or_404(Lead, pk=pk, is_archived=False)
    
    # Get the previous visit association
    project_id = request.POST.get('project_id')
    if not project_id:
        return JsonResponse({'success': False, 'error': 'Project ID is required.'}, status=400)
    
    project = get_object_or_404(Project, pk=project_id)
    
    # Get previous association
    previous_association = lead.project_associations.filter(
        project=project,
        is_archived=False
    ).order_by('-created_at').first()
    
    if not previous_association:
        return JsonResponse({'success': False, 'error': 'No previous visit found for this project.'}, status=400)
    
    # Get form data
    visit_date_str = request.POST.get('visit_date', '')
    visit_time_str = request.POST.get('visit_time', '')
    time_frame = request.POST.get('time_frame', '')
    revisit_reason = request.POST.get('revisit_reason', '')
    
    # Parse date and time
    visit_scheduled_date = None
    if visit_date_str and visit_time_str:
        try:
            datetime_str = f"{visit_date_str} {visit_time_str}"
            visit_scheduled_date = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
            visit_scheduled_date = timezone.make_aware(visit_scheduled_date)
        except (ValueError, TypeError):
            pass
    
    # Calculate revisit count
    revisit_count = lead.project_associations.filter(
        project=project,
        is_revisit=True,
        is_archived=False
    ).count() + 1
    
    # Create new revisit association
    try:
        revisit_association = LeadProjectAssociation.objects.create(
            lead=lead,
            project=project,
            status='visit_scheduled',
            is_revisit=True,
            revisit_count=revisit_count,
            revisit_reason=revisit_reason,
            previous_visit=previous_association,
            time_frame=time_frame if time_frame else None,
            visit_scheduled_date=visit_scheduled_date,
            phone_verified=True,  # No OTP needed for revisits
            assigned_to=previous_association.assigned_to,
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Revisit scheduled successfully! This is revisit #{revisit_count}.',
            'revisit_id': revisit_association.id
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def queue_visit(request):
    """Queue Visit page for Telecallers (Receptionist feature)"""
    if not request.user.is_telecaller():
        messages.error(request, 'Only telecallers can access the queue visit feature.')
        return redirect('dashboard')
    
    # Get telecaller's assigned projects
    assigned_projects = request.user.assigned_projects.filter(is_active=True)
    
    # Get global configurations
    configurations = GlobalConfiguration.objects.filter(is_active=True).order_by('order', 'name')
    
    if request.method == 'POST':
        # Handle queue visit submission
        phone = request.POST.get('phone', '').strip()
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        project_id = request.POST.get('project')
        
        if not phone or not name or not project_id:
            messages.error(request, 'Phone, name, and project are required.')
            return redirect('leads:queue_visit')
        
        project = get_object_or_404(Project, pk=project_id, is_active=True)
        
        # Check if project is assigned to telecaller
        if project not in assigned_projects:
            messages.error(request, 'You can only queue visits for your assigned projects.')
            return redirect('leads:queue_visit')
        
        # Get or create lead
        lead, created = Lead.objects.get_or_create(
            phone=phone,
            defaults={
                'name': name,
                'email': email,
            }
        )
        
        # If lead exists, update name and email if provided
        if not created:
            if name:
                lead.name = name
            if email:
                lead.email = email
            lead.save()
        
        # Get additional lead details from form
        age = request.POST.get('age')
        gender = request.POST.get('gender')
        locality = request.POST.get('locality')
        current_residence = request.POST.get('current_residence')
        occupation = request.POST.get('occupation')
        company_name = request.POST.get('company_name')
        designation = request.POST.get('designation')
        purpose = request.POST.get('purpose')
        budget_min = request.POST.get('budget_min')
        budget_max = request.POST.get('budget_max')
        visit_type = request.POST.get('visit_type')
        visit_source = request.POST.get('visit_source')
        
        # Update lead details
        if age:
            lead.age = int(age)
        if gender:
            lead.gender = gender
        if locality:
            lead.locality = locality
        if current_residence:
            lead.current_residence = current_residence
        if occupation:
            lead.occupation = occupation
        if company_name:
            lead.company_name = company_name
        if designation:
            lead.designation = designation
        if purpose:
            lead.purpose = purpose
        if budget_min:
            lead.budget_min = float(budget_min)
        if budget_max:
            lead.budget_max = float(budget_max)
        if visit_type:
            lead.visit_type = visit_type
        if visit_source:
            lead.visit_source = visit_source
        
        lead.save()
        
        # Handle configurations
        configuration_ids = request.POST.getlist('configurations')
        if configuration_ids:
            lead.configurations.set(configuration_ids)
        
        # Create or update association with queued_visit status
        association, assoc_created = LeadProjectAssociation.objects.get_or_create(
            lead=lead,
            project=project,
            defaults={
                'status': 'queued_visit',
                'queued_at': timezone.now(),
                'queued_by': request.user,
                'phone_verified': True,  # Already verified by telecaller
                'created_by': request.user,
            }
        )
        
        if not assoc_created:
            # Update existing association
            association.status = 'queued_visit'
            association.queued_at = timezone.now()
            association.queued_by = request.user
            association.phone_verified = True
            association.save()
        
        messages.success(request, f'Visit queued successfully for {lead.name}! Closing manager will be notified.')
        return redirect('leads:queue_visit')
    
    context = {
        'projects': assigned_projects,
        'configurations': configurations,
    }
    return render(request, 'leads/queue_visit.html', context)


@login_required
def visit_queue(request):
    """Visit Queue page for Closing Managers - shows all queued visits"""
    if not (request.user.is_closing_manager() or request.user.is_super_admin() or request.user.is_mandate_owner() or request.user.is_site_head()):
        messages.error(request, 'You do not have permission to view the visit queue.')
        return redirect('dashboard')
    
    # Get projects based on user role
    if request.user.is_super_admin() or request.user.is_mandate_owner():
        assigned_projects = Project.objects.filter(is_active=True)
    elif request.user.is_site_head():
        assigned_projects = Project.objects.filter(site_head=request.user, is_active=True)
    else:  # Closing Manager
        assigned_projects = request.user.assigned_projects.filter(is_active=True)
    
    # Get queued visits
    queued_associations = LeadProjectAssociation.objects.filter(
        project__in=assigned_projects,
        status='queued_visit',
        is_archived=False
    ).select_related('lead', 'project', 'queued_by').order_by('queued_at')
    
    # Search
    search = request.GET.get('search', '')
    if search:
        queued_associations = queued_associations.filter(
            Q(lead__name__icontains=search) |
            Q(lead__phone__icontains=search) |
            Q(project__name__icontains=search)
        )
    
    # Filter by project
    project_id = request.GET.get('project', '')
    if project_id:
        queued_associations = queued_associations.filter(project_id=project_id)
    
    context = {
        'queued_associations': queued_associations,
        'projects': assigned_projects,
        'search': search,
        'selected_project': project_id,
    }
    return render(request, 'leads/visit_queue.html', context)


@login_required
def mark_visit_done(request, association_id):
    """Mark a queued visit as completed - Closing Managers only"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)
    
    # Permission check
    if not (request.user.is_closing_manager() or request.user.is_super_admin() or request.user.is_mandate_owner() or request.user.is_site_head()):
        return JsonResponse({'success': False, 'error': 'You do not have permission to mark visits as done.'}, status=403)
    
    association = get_object_or_404(LeadProjectAssociation, pk=association_id, is_archived=False)
    
    # Check if user has permission for this project
    if request.user.is_closing_manager():
        if association.project not in request.user.assigned_projects.all():
            return JsonResponse({'success': False, 'error': 'You can only mark visits as done for your assigned projects.'}, status=403)
    elif request.user.is_site_head():
        if association.project.site_head != request.user:
            return JsonResponse({'success': False, 'error': 'You can only mark visits as done for your projects.'}, status=403)
    
    # Check if status is queued_visit
    if association.status != 'queued_visit':
        return JsonResponse({'success': False, 'error': 'This visit is not in the queue.'}, status=400)
    
    # Mark as visit completed
    association.status = 'visit_completed'
    association.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Visit marked as completed for {association.lead.name}!'
    })
