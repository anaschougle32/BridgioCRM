from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from datetime import timedelta
from leads.models import Lead
from bookings.models import Booking, Payment
from projects.models import Project
from accounts.models import User


@login_required
def mandate_owner_reports(request):
    """Comprehensive reports for Mandate Owner and Super Admin"""
    if not (request.user.is_mandate_owner() or request.user.is_super_admin() or (request.user.is_superuser and request.user.is_staff)):
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, 'You do not have permission to view reports.')
        return redirect('dashboard')
    
    user = request.user
    today = timezone.now().date()
    this_month_start = today.replace(day=1)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    last_month_end = this_month_start - timedelta(days=1)
    
    # Get all projects - Super Admin and Mandate Owner see all projects
    if user.is_super_admin() or user.is_mandate_owner() or (user.is_superuser and user.is_staff):
        projects = Project.objects.filter(is_active=True)
    else:
        projects = Project.objects.filter(mandate_owner=user, is_active=True)
    
    # Lead Analytics - Super Admin and Mandate Owner see all leads
    if user.is_super_admin() or user.is_mandate_owner() or (user.is_superuser and user.is_staff):
        all_leads = Lead.objects.filter(is_archived=False)
    else:
        all_leads = Lead.objects.filter(project__mandate_owner=user, is_archived=False)
    leads_this_month = all_leads.filter(created_at__date__gte=this_month_start)
    leads_last_month = all_leads.filter(created_at__date__gte=last_month_start, created_at__date__lte=last_month_end)
    
    # Status breakdown
    status_breakdown = all_leads.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Booking Analytics - Super Admin and Mandate Owner see all bookings
    if user.is_super_admin() or user.is_mandate_owner() or (user.is_superuser and user.is_staff):
        all_bookings = Booking.objects.filter(is_archived=False)
    else:
        all_bookings = Booking.objects.filter(project__mandate_owner=user, is_archived=False)
    bookings_this_month = all_bookings.filter(created_at__date__gte=this_month_start)
    
    # Revenue Analytics - Super Admin and Mandate Owner see all revenue
    if user.is_super_admin() or user.is_mandate_owner() or (user.is_superuser and user.is_staff):
        total_revenue = Payment.objects.all().aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        revenue_this_month = Payment.objects.filter(
            payment_date__gte=this_month_start
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        revenue_last_month = Payment.objects.filter(
            payment_date__gte=last_month_start,
            payment_date__lte=last_month_end
        ).aggregate(total=Sum('amount'))['total'] or 0
    else:
        total_revenue = Payment.objects.filter(booking__project__mandate_owner=user).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        revenue_this_month = Payment.objects.filter(
            booking__project__mandate_owner=user,
            payment_date__gte=this_month_start
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        revenue_last_month = Payment.objects.filter(
            booking__project__mandate_owner=user,
            payment_date__gte=last_month_start,
            payment_date__lte=last_month_end
        ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Project Performance
    project_performance = projects.annotate(
        lead_count=Count('leads', filter=Q(leads__is_archived=False)),
        booking_count=Count('bookings', filter=Q(bookings__is_archived=False)),
        revenue=Sum('bookings__payments__amount')
    ).order_by('-revenue')
    
    # Calculate conversion rates
    for project in project_performance:
        if project.lead_count > 0:
            project.conversion_rate = (project.booking_count / project.lead_count) * 100
        else:
            project.conversion_rate = 0
    
    # Employee Performance - Super Admin and Mandate Owner see all employees
    if user.is_super_admin() or user.is_mandate_owner() or (user.is_superuser and user.is_staff):
        employees = User.objects.filter(is_active=True).exclude(role='super_admin')
    else:
        employees = User.objects.filter(mandate_owner=user, is_active=True)
    
    employee_performance = []
    for emp in employees:
        if emp.is_closing_manager():
            if user.is_super_admin() or user.is_mandate_owner() or (user.is_superuser and user.is_staff):
                bookings_count = Booking.objects.filter(created_by=emp).count()
            else:
                bookings_count = Booking.objects.filter(created_by=emp, project__mandate_owner=user).count()
            employee_performance.append({
                'user': emp,
                'role': emp.get_role_display(),
                'bookings': bookings_count,
            })
        elif emp.is_sourcing_manager():
            if user.is_super_admin() or user.is_mandate_owner() or (user.is_superuser and user.is_staff):
                leads_count = Lead.objects.filter(created_by=emp).count()
            else:
                leads_count = Lead.objects.filter(created_by=emp, project__mandate_owner=user).count()
            employee_performance.append({
                'user': emp,
                'role': emp.get_role_display(),
                'leads': leads_count,
            })
        elif emp.is_telecaller():
            if user.is_super_admin() or user.is_mandate_owner() or (user.is_superuser and user.is_staff):
                calls_count = Lead.objects.filter(assigned_to=emp).count()
            else:
                calls_count = Lead.objects.filter(assigned_to=emp, project__mandate_owner=user).count()
            employee_performance.append({
                'user': emp,
                'role': emp.get_role_display(),
                'assigned_leads': calls_count,
            })
    
    # Monthly Trends (last 6 months)
    monthly_trends = []
    for i in range(6):
        month_start = (this_month_start - timedelta(days=30*i)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        month_leads = all_leads.filter(created_at__date__gte=month_start, created_at__date__lte=month_end).count()
        month_bookings = all_bookings.filter(created_at__date__gte=month_start, created_at__date__lte=month_end).count()
        if user.is_super_admin() or user.is_mandate_owner() or (user.is_superuser and user.is_staff):
            month_revenue = Payment.objects.filter(
                payment_date__gte=month_start,
                payment_date__lte=month_end
            ).aggregate(total=Sum('amount'))['total'] or 0
        else:
            month_revenue = Payment.objects.filter(
                booking__project__mandate_owner=user,
                payment_date__gte=month_start,
                payment_date__lte=month_end
            ).aggregate(total=Sum('amount'))['total'] or 0
        
        monthly_trends.append({
            'month': month_start.strftime('%b %Y'),
            'leads': month_leads,
            'bookings': month_bookings,
            'revenue': month_revenue,
        })
    monthly_trends.reverse()
    
    context = {
        'total_leads': all_leads.count(),
        'leads_this_month': leads_this_month.count(),
        'leads_last_month': leads_last_month.count(),
        'total_bookings': all_bookings.count(),
        'bookings_this_month': bookings_this_month.count(),
        'total_revenue': total_revenue,
        'revenue_this_month': revenue_this_month,
        'revenue_last_month': revenue_last_month,
        'status_breakdown': status_breakdown,
        'project_performance': project_performance,
        'employee_performance': employee_performance,
        'monthly_trends': monthly_trends,
        'total_projects': projects.count(),
    }
    return render(request, 'reports/mandate_owner_reports.html', context)

