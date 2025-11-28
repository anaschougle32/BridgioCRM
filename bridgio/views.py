from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from leads.models import Lead
from bookings.models import Booking, Payment
from projects.models import Project
from accounts.models import User
from channel_partners.models import ChannelPartner


@login_required
def dashboard(request):
    """Role-based dashboard"""
    user = request.user
    today = timezone.now().date()
    
    # Debug: Check user role
    # print(f"DEBUG: User: {user.username}, Role: {user.role}, is_super_admin(): {user.is_super_admin()}")
    
    # Super Admin Dashboard - System-wide stats
    # Check both role and is_superuser for compatibility
    if user.is_super_admin() or (user.is_superuser and user.is_staff):
        # All leads
        all_leads = Lead.objects.filter(is_archived=False)
        all_bookings = Booking.objects.filter(is_archived=False)
        
        # Revenue calculations
        total_revenue = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0
        bookings_count = all_bookings.count()
        avg_booking_value = all_bookings.aggregate(avg=Avg('final_negotiated_price'))['avg'] or 0
        
        # CP Leaderboard
        cp_leaderboard = ChannelPartner.objects.annotate(
            booking_count=Count('bookings'),
            total_revenue=Sum('bookings__payments__amount')
        ).filter(booking_count__gt=0).order_by('-total_revenue')[:10]
        
        # Project stats
        project_stats = Project.objects.annotate(
            lead_count=Count('leads', filter=Q(leads__is_archived=False)),
            booking_count=Count('bookings', filter=Q(bookings__is_archived=False)),
            revenue=Sum('bookings__payments__amount')
        ).order_by('-revenue')
        
        # User stats
        user_stats = User.objects.values('role').annotate(
            count=Count('id')
        ).order_by('role')
        
        context = {
            'is_super_admin': True,
            'total_leads': all_leads.count(),
            'new_visits_today': all_leads.filter(created_at__date=today).count(),
            'total_bookings': bookings_count,
            'pending_otp': all_leads.filter(
                is_pretagged=True,
                pretag_status='pending_verification'
            ).count(),
            'total_revenue': total_revenue,
            'avg_booking_value': avg_booking_value,
            'total_projects': Project.objects.filter(is_active=True).count(),
            'total_mandate_owners': User.objects.filter(role='mandate_owner', is_active=True).count(),
            'cp_leaderboard': cp_leaderboard,
            'project_stats': project_stats[:10],  # Top 10 projects
            'user_stats': user_stats,
        }
        return render(request, 'dashboard_super_admin.html', context)
    
    # Mandate Owner Dashboard
    elif user.is_mandate_owner():
        leads_qs = Lead.objects.filter(project__mandate_owner=user, is_archived=False)
        bookings_qs = Booking.objects.filter(project__mandate_owner=user, is_archived=False)
        projects = Project.objects.filter(mandate_owner=user, is_active=True)
        
        # Calculate revenue
        total_revenue = Payment.objects.filter(booking__project__mandate_owner=user).aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Project comparison with stats
        project_comparison = projects.annotate(
            lead_count=Count('leads', filter=Q(leads__is_archived=False)),
            booking_count=Count('bookings', filter=Q(bookings__is_archived=False)),
            revenue=Sum('bookings__payments__amount')
        ).order_by('-revenue', '-booking_count')
        
        # Employee stats
        employees = User.objects.filter(mandate_owner=user, is_active=True)
        employee_stats = employees.values('role').annotate(
            count=Count('id')
        ).order_by('role')
        
        context = {
            'is_mandate_owner': True,
            'total_leads': leads_qs.count(),
            'new_visits_today': leads_qs.filter(created_at__date=today).count(),
            'total_bookings': bookings_qs.count(),
            'pending_otp': leads_qs.filter(
                is_pretagged=True,
                pretag_status='pending_verification'
            ).count(),
            'total_projects': projects.count(),
            'total_revenue': total_revenue,
            'project_comparison': project_comparison,
            'employee_stats': employee_stats,
            'total_employees': employees.count(),
        }
        return render(request, 'dashboard_mandate_owner.html', context)
    
    # Site Head Dashboard
    elif user.is_site_head():
        leads_qs = Lead.objects.filter(project__site_head=user, is_archived=False)
        bookings_qs = Booking.objects.filter(project__site_head=user, is_archived=False)
        projects = Project.objects.filter(site_head=user, is_active=True)
        
        # Unassigned leads
        unassigned_leads = leads_qs.filter(assigned_to__isnull=True).count()
        
        # Employee stats
        employees = User.objects.filter(
            Q(role='closing_manager') | Q(role='telecaller') | Q(role='sourcing_manager'),
            mandate_owner=user.mandate_owner
        )
        
        context = {
            'is_site_head': True,
            'total_leads': leads_qs.count(),
            'new_visits_today': leads_qs.filter(created_at__date=today).count(),
            'total_bookings': bookings_qs.count(),
            'pending_otp': leads_qs.filter(
                is_pretagged=True,
                pretag_status='pending_verification'
            ).count(),
            'unassigned_leads': unassigned_leads,
            'projects': projects,
            'employees': employees,
        }
        return render(request, 'dashboard_site_head.html', context)
    
    # Closing Manager Dashboard
    elif user.is_closing_manager():
        leads_qs = Lead.objects.filter(assigned_to=user, is_archived=False)
        bookings_qs = Booking.objects.filter(created_by=user, is_archived=False)
        
        # Today's callbacks
        from leads.models import FollowUpReminder
        todays_callbacks = FollowUpReminder.objects.filter(
            lead__assigned_to=user,
            reminder_date__date=today,
            is_completed=False
        ).count()
        
        context = {
            'is_closing_manager': True,
            'total_leads': leads_qs.count(),
            'new_visits_today': leads_qs.filter(created_at__date=today).count(),
            'total_bookings': bookings_qs.count(),
            'pending_otp': leads_qs.filter(
                is_pretagged=True,
                pretag_status='pending_verification'
            ).count(),
            'todays_callbacks': todays_callbacks,
        }
        return render(request, 'dashboard_closing_manager.html', context)
    
    # Sourcing Manager Dashboard
    elif user.is_sourcing_manager():
        leads_qs = Lead.objects.filter(created_by=user, is_archived=False)
        
        context = {
            'is_sourcing_manager': True,
            'total_leads': leads_qs.count(),
            'new_visits_today': leads_qs.filter(created_at__date=today).count(),
            'pending_otp': leads_qs.filter(
                is_pretagged=True,
                pretag_status='pending_verification'
            ).count(),
        }
        return render(request, 'dashboard_sourcing_manager.html', context)
    
    # Telecaller Dashboard
    elif user.is_telecaller():
        leads_qs = Lead.objects.filter(assigned_to=user, is_archived=False)
        
        # Today's callbacks
        from leads.models import FollowUpReminder
        todays_callbacks = FollowUpReminder.objects.filter(
            lead__assigned_to=user,
            reminder_date__date=today,
            is_completed=False
        ).count()
        
        # Active reminders
        active_reminders = FollowUpReminder.objects.filter(
            lead__assigned_to=user,
            is_completed=False,
            reminder_date__gte=timezone.now()
        ).count()
        
        # Untouched leads (>24 hours)
        from datetime import timedelta
        yesterday = timezone.now() - timedelta(hours=24)
        untouched_leads = leads_qs.filter(
            status='new',
            created_at__lt=yesterday
        ).count()
        
        context = {
            'is_telecaller': True,
            'total_leads': leads_qs.count(),
            'new_visits_today': leads_qs.filter(created_at__date=today).count(),
            'todays_callbacks': todays_callbacks,
            'active_reminders': active_reminders,
            'untouched_leads': untouched_leads,
        }
        return render(request, 'dashboard_telecaller.html', context)
    
    # Default dashboard (fallback)
    leads_qs = Lead.objects.filter(is_archived=False)
    bookings_qs = Booking.objects.filter(is_archived=False)
    
    context = {
        'total_leads': leads_qs.count(),
        'new_visits_today': leads_qs.filter(created_at__date=today).count(),
        'total_bookings': bookings_qs.count(),
        'pending_otp': leads_qs.filter(
            is_pretagged=True,
            pretag_status='pending_verification'
        ).count(),
    }
    
    return render(request, 'dashboard.html', context)


