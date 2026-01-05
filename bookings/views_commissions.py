from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import Booking, Commission
from projects.models import Project
from accounts.models import User
from channel_partners.models import ChannelPartner


@login_required
def commission_list(request):
    """Commission list with filters - Super Admin and Mandate Owners only"""
    if not (request.user.is_super_admin() or request.user.is_mandate_owner()):
        messages.error(request, 'You do not have permission to view commissions.')
        return redirect('dashboard')
    
    # Get commissions
    commissions = Commission.objects.all().select_related(
        'booking', 'booking__lead', 'booking__project',
        'channel_partner', 'employee', 'approved_by', 'paid_by'
    )
    
    # Filters
    status_filter = request.GET.get('status', '')
    commission_type = request.GET.get('commission_type', '')
    project_filter = request.GET.get('project', '')
    cp_filter = request.GET.get('channel_partner', '')
    employee_filter = request.GET.get('employee', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Apply filters
    if status_filter:
        commissions = commissions.filter(status=status_filter)
    if commission_type:
        commissions = commissions.filter(commission_type=commission_type)
    if project_filter:
        commissions = commissions.filter(booking__project_id=project_filter)
    if cp_filter:
        commissions = commissions.filter(channel_partner_id=cp_filter)
    if employee_filter:
        commissions = commissions.filter(employee_id=employee_filter)
    if date_from:
        commissions = commissions.filter(created_at__date__gte=date_from)
    if date_to:
        commissions = commissions.filter(created_at__date__lte=date_to)
    
    # Order
    commissions = commissions.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(commissions, 25)
    page = request.GET.get('page', 1)
    commissions_page = paginator.get_page(page)
    
    # Get filter options
    projects = Project.objects.filter(is_active=True).order_by('name')
    channel_partners = ChannelPartner.objects.filter(status='active').order_by('cp_name')
    employees = User.objects.filter(
        role__in=['closing_manager', 'sourcing_manager', 'telecaller'],
        is_active=True
    ).order_by('username')
    
    # Calculate totals
    total_pending = commissions.filter(status='pending').aggregate(
        total=Sum('commission_amount')
    )['total'] or 0
    total_approved = commissions.filter(status='approved').aggregate(
        total=Sum('commission_amount')
    )['total'] or 0
    total_paid = commissions.filter(status='paid').aggregate(
        total=Sum('commission_amount')
    )['total'] or 0
    
    context = {
        'commissions': commissions_page,
        'projects': projects,
        'channel_partners': channel_partners,
        'employees': employees,
        'total_pending': total_pending,
        'total_approved': total_approved,
        'total_paid': total_paid,
        'status_choices': Commission.STATUS_CHOICES,
        'commission_type_choices': Commission.COMMISSION_TYPE_CHOICES,
        'filters': {
            'status': status_filter,
            'commission_type': commission_type,
            'project': project_filter,
            'channel_partner': cp_filter,
            'employee': employee_filter,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    return render(request, 'bookings/commissions/list.html', context)


@login_required
def commission_approve(request, pk):
    """Approve commission - Super Admin and Mandate Owners only"""
    if not (request.user.is_super_admin() or request.user.is_mandate_owner()):
        messages.error(request, 'You do not have permission to approve commissions.')
        return redirect('dashboard')
    
    commission = get_object_or_404(Commission, pk=pk)
    
    if commission.status != 'pending':
        messages.error(request, 'This commission cannot be approved.')
        return redirect('bookings:commission_list')
    
    commission.approve(request.user)
    messages.success(request, f'Commission of ₹{commission.commission_amount} approved successfully.')
    
    return redirect('bookings:commission_list')


@login_required
def commission_mark_paid(request, pk):
    """Mark commission as paid - Super Admin and Mandate Owners only"""
    if not (request.user.is_super_admin() or request.user.is_mandate_owner()):
        messages.error(request, 'You do not have permission to mark commissions as paid.')
        return redirect('dashboard')
    
    commission = get_object_or_404(Commission, pk=pk)
    
    if commission.status != 'approved':
        messages.error(request, 'This commission must be approved before marking as paid.')
        return redirect('bookings:commission_list')
    
    commission.mark_paid(request.user)
    messages.success(request, f'Commission of ₹{commission.commission_amount} marked as paid.')
    
    return redirect('bookings:commission_list')


@login_required
def commission_bulk_approve(request):
    """Bulk approve commissions - Super Admin and Mandate Owners only"""
    if not (request.user.is_super_admin() or request.user.is_mandate_owner()):
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    commission_ids = request.POST.getlist('commission_ids')
    if not commission_ids:
        return JsonResponse({'success': False, 'error': 'No commissions selected'})
    
    approved_count = 0
    for commission_id in commission_ids:
        try:
            commission = Commission.objects.get(pk=commission_id, status='pending')
            commission.approve(request.user)
            approved_count += 1
        except Commission.DoesNotExist:
            continue
    
    return JsonResponse({
        'success': True,
        'message': f'Successfully approved {approved_count} commissions.'
    })


@login_required
def commission_dashboard(request):
    """Commission dashboard with analytics - Super Admin and Mandate Owners only"""
    if not (request.user.is_super_admin() or request.user.is_mandate_owner()):
        messages.error(request, 'You do not have permission to view commission dashboard.')
        return redirect('dashboard')
    
    today = timezone.now().date()
    this_month_start = today.replace(day=1)
    last_month_start = (this_month_start - timezone.timedelta(days=1)).replace(day=1)
    
    # Commission statistics
    all_commissions = Commission.objects.all()
    
    # Monthly stats
    this_month_commissions = all_commissions.filter(created_at__date__gte=this_month_start)
    last_month_commissions = all_commissions.filter(
        created_at__date__gte=last_month_start,
        created_at__date__lt=this_month_start
    )
    
    # Status breakdown
    status_breakdown = all_commissions.values('status').annotate(
        count=Count('id'),
        total_amount=Sum('commission_amount')
    ).order_by('status')
    
    # Type breakdown
    type_breakdown = all_commissions.values('commission_type').annotate(
        count=Count('id'),
        total_amount=Sum('commission_amount')
    ).order_by('commission_type')
    
    # Top performers
    top_cps = ChannelPartner.objects.filter(
        commissions__status='paid'
    ).annotate(
        total_commission=Sum('commissions__commission_amount'),
        commission_count=Count('commissions')
    ).order_by('-total_commission')[:10]
    
    top_employees = User.objects.filter(
        commissions_received__status='paid'
    ).annotate(
        total_commission=Sum('commissions_received__commission_amount'),
        commission_count=Count('commissions_received')
    ).order_by('-total_commission')[:10]
    
    # Recent commissions
    recent_commissions = all_commissions.select_related(
        'booking__lead', 'channel_partner', 'employee'
    ).order_by('-created_at')[:10]
    
    context = {
        'this_month_total': this_month_commissions.aggregate(
            total=Sum('commission_amount')
        )['total'] or 0,
        'this_month_count': this_month_commissions.count(),
        'last_month_total': last_month_commissions.aggregate(
            total=Sum('commission_amount')
        )['total'] or 0,
        'last_month_count': last_month_commissions.count(),
        'pending_total': all_commissions.filter(status='pending').aggregate(
            total=Sum('commission_amount')
        )['total'] or 0,
        'pending_count': all_commissions.filter(status='pending').count(),
        'approved_total': all_commissions.filter(status='approved').aggregate(
            total=Sum('commission_amount')
        )['total'] or 0,
        'approved_count': all_commissions.filter(status='approved').count(),
        'paid_total': all_commissions.filter(status='paid').aggregate(
            total=Sum('commission_amount')
        )['total'] or 0,
        'paid_count': all_commissions.filter(status='paid').count(),
        'status_breakdown': status_breakdown,
        'type_breakdown': type_breakdown,
        'top_cps': top_cps,
        'top_employees': top_employees,
        'recent_commissions': recent_commissions,
    }
    
    return render(request, 'bookings/commissions/dashboard.html', context)


@login_required
def booking_commissions(request, pk):
    """View commissions for a specific booking"""
    booking = get_object_or_404(Booking, pk=pk)
    
    # Permission check
    if request.user.is_super_admin() or request.user.is_mandate_owner():
        pass  # Can see all
    elif request.user.is_site_head():
        if booking.project.site_head != request.user:
            messages.error(request, 'You do not have permission to view this booking.')
            return redirect('bookings:list')
    elif request.user.is_closing_manager():
        if booking.project not in request.user.assigned_projects.all():
            messages.error(request, 'You do not have permission to view this booking.')
            return redirect('bookings:list')
    else:
        messages.error(request, 'You do not have permission to view booking commissions.')
        return redirect('dashboard')
    
    commissions = booking.commissions.select_related(
        'channel_partner', 'employee', 'approved_by', 'paid_by'
    ).order_by('-created_at')
    
    context = {
        'booking': booking,
        'commissions': commissions,
        'total_commission': booking.total_commission_amount,
    }
    
    return render(request, 'bookings/commissions/booking_detail.html', context)
