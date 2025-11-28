from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from .models import ChannelPartner
from projects.models import Project
from bookings.models import Booking


@login_required
def cp_list(request):
    """List all channel partners"""
    if not (request.user.is_super_admin() or request.user.is_mandate_owner() or 
            request.user.is_site_head() or request.user.is_closing_manager() or 
            request.user.is_sourcing_manager()):
        messages.error(request, 'You do not have permission to view channel partners.')
        return redirect('dashboard')
    
    cps = ChannelPartner.objects.filter(is_active=True)
    
    # Mandate Owner sees CPs linked to their projects
    if request.user.is_mandate_owner():
        cps = cps.filter(linked_projects__mandate_owner=request.user).distinct()
    
    # Search
    search = request.GET.get('search', '')
    if search:
        cps = cps.filter(
            Q(firm_name__icontains=search) |
            Q(cp_name__icontains=search) |
            Q(phone__icontains=search) |
            Q(email__icontains=search)
        )
    
    # Filter by CP type
    cp_type = request.GET.get('cp_type', '')
    if cp_type:
        cps = cps.filter(cp_type=cp_type)
    
    # Annotate with stats - filter by mandate owner's projects if needed
    if request.user.is_mandate_owner():
        cps = cps.annotate(
            lead_count=Count('leads', filter=Q(leads__project__mandate_owner=request.user, leads__is_archived=False)),
            booking_count=Count('bookings', filter=Q(bookings__project__mandate_owner=request.user, bookings__is_archived=False)),
            total_revenue=Sum('bookings__payments__amount', filter=Q(bookings__project__mandate_owner=request.user))
        ).order_by('-total_revenue', '-booking_count')
    else:
        cps = cps.annotate(
            lead_count=Count('leads', filter=Q(leads__is_archived=False)),
            booking_count=Count('bookings', filter=Q(bookings__is_archived=False)),
            total_revenue=Sum('bookings__payments__amount')
        ).order_by('-total_revenue', '-booking_count')
    
    # Pagination
    paginator = Paginator(cps, 25)
    page = request.GET.get('page', 1)
    cps_page = paginator.get_page(page)
    
    context = {
        'cps': cps_page,
        'cp_type_choices': ChannelPartner.CP_TYPE_CHOICES,
        'search': search,
        'selected_cp_type': cp_type,
    }
    return render(request, 'channel_partners/list.html', context)


@login_required
def cp_detail(request, pk):
    """Channel Partner detail view"""
    cp = get_object_or_404(ChannelPartner, pk=pk, is_active=True)
    
    if not (request.user.is_super_admin() or request.user.is_mandate_owner() or 
            request.user.is_site_head() or request.user.is_closing_manager() or 
            request.user.is_sourcing_manager()):
        messages.error(request, 'You do not have permission to view channel partners.')
        return redirect('dashboard')
    
    # Permission check for Mandate Owner
    if request.user.is_mandate_owner():
        if not cp.linked_projects.filter(mandate_owner=request.user).exists():
            messages.error(request, 'You do not have permission to view this channel partner.')
            return redirect('channel_partners:list')
    
    # Get stats - filter by mandate owner if needed
    if request.user.is_mandate_owner():
        leads = cp.leads.filter(project__mandate_owner=request.user, is_archived=False)
        bookings = cp.bookings.filter(project__mandate_owner=request.user, is_archived=False)
        from bookings.models import Payment
        total_revenue = Payment.objects.filter(
            booking__channel_partner=cp,
            booking__project__mandate_owner=request.user
        ).aggregate(total=Sum('amount'))['total'] or 0
        linked_projects = cp.linked_projects.filter(mandate_owner=request.user)
    elif request.user.is_sourcing_manager():
        # Sourcing Manager sees all CP data
        leads = cp.leads.filter(is_archived=False)
        bookings = cp.bookings.filter(is_archived=False)
        from bookings.models import Payment
        total_revenue = Payment.objects.filter(booking__channel_partner=cp).aggregate(
            total=Sum('amount')
        )['total'] or 0
        linked_projects = cp.linked_projects.all()
    else:
        leads = cp.leads.filter(is_archived=False)
        bookings = cp.bookings.filter(is_archived=False)
        from bookings.models import Payment
        total_revenue = Payment.objects.filter(booking__channel_partner=cp).aggregate(
            total=Sum('amount')
        )['total'] or 0
        linked_projects = cp.linked_projects.all()
    
    # Get project-wise stats for Sourcing Managers
    project_stats = []
    if request.user.is_sourcing_manager():
        for project in linked_projects:
            project_leads = leads.filter(project=project)
            project_bookings = bookings.filter(project=project)
            project_revenue = Payment.objects.filter(
                booking__channel_partner=cp,
                booking__project=project
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            project_stats.append({
                'project': project,
                'leads_count': project_leads.count(),
                'bookings_count': project_bookings.count(),
                'revenue': project_revenue,
            })
    
    context = {
        'cp': cp,
        'leads_count': leads.count(),
        'bookings_count': bookings.count(),
        'total_revenue': total_revenue,
        'linked_projects': linked_projects,
        'project_stats': project_stats if request.user.is_sourcing_manager() else None,
        'is_sourcing_manager': request.user.is_sourcing_manager(),
    }
    return render(request, 'channel_partners/detail.html', context)
