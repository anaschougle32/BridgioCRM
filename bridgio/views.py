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
    try:
        user = request.user
        today = timezone.now().date()
        
        # Super Admin Dashboard - System-wide stats
        # Check both role and is_superuser for compatibility
        # First check if user has role attribute
        user_role = getattr(user, 'role', None)
        is_super_admin = (user_role == 'super_admin') if user_role else False
        is_superuser_flag = getattr(user, 'is_superuser', False)
        is_staff_flag = getattr(user, 'is_staff', False)
        
        if is_super_admin or (is_superuser_flag and is_staff_flag):
            # All leads - handle if table doesn't exist
            try:
                all_leads = Lead.objects.filter(is_archived=False)
            except Exception:
                all_leads = Lead.objects.none()
            
            try:
                all_bookings = Booking.objects.filter(is_archived=False)
            except Exception:
                all_bookings = Booking.objects.none()
            
            # Revenue calculations - handle None values
            try:
                total_revenue = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0
            except Exception:
                total_revenue = 0
            
            bookings_count = all_bookings.count() if all_bookings else 0
            
            try:
                avg_booking_value = all_bookings.aggregate(avg=Avg('final_negotiated_price'))['avg'] or 0
            except Exception:
                avg_booking_value = 0
            
            # CP Leaderboard - handle empty queryset
            try:
                cp_leaderboard = list(ChannelPartner.objects.annotate(
                    booking_count=Count('bookings'),
                    total_revenue=Sum('bookings__payments__amount')
                ).filter(booking_count__gt=0).order_by('-total_revenue')[:10])
            except Exception:
                cp_leaderboard = []
            
            # Project stats - handle empty queryset
            try:
                project_stats = list(Project.objects.annotate(
                    lead_count=Count('leads', filter=Q(leads__is_archived=False)),
                    booking_count=Count('bookings', filter=Q(bookings__is_archived=False)),
                    revenue=Sum('bookings__payments__amount')
                ).order_by('-revenue')[:10])
            except Exception:
                project_stats = []
            
            # User stats
            try:
                user_stats = list(User.objects.values('role').annotate(
                    count=Count('id')
                ).order_by('role'))
            except Exception:
                user_stats = []
            
            # Count projects and mandate owners safely
            try:
                total_projects = Project.objects.filter(is_active=True).count()
            except Exception:
                total_projects = 0
            
            try:
                total_mandate_owners = User.objects.filter(role='mandate_owner', is_active=True).count()
            except Exception:
                total_mandate_owners = 0
            
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
                'total_projects': total_projects,
                'total_mandate_owners': total_mandate_owners,
                'cp_leaderboard': cp_leaderboard,
                'project_stats': project_stats,
                'user_stats': user_stats,
            }
            return render(request, 'dashboard_super_admin.html', context)
        
        # Mandate Owner Dashboard - Same as Super Admin (they see all data)
        elif user_role == 'mandate_owner':
            # All leads - handle if table doesn't exist
            try:
                all_leads = Lead.objects.filter(is_archived=False)
            except Exception:
                all_leads = Lead.objects.none()
            
            try:
                all_bookings = Booking.objects.filter(is_archived=False)
            except Exception:
                all_bookings = Booking.objects.none()
            
            # Revenue calculations - handle None values
            try:
                total_revenue = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0
            except Exception:
                total_revenue = 0
            
            bookings_count = all_bookings.count() if all_bookings else 0
            
            try:
                avg_booking_value = all_bookings.aggregate(avg=Avg('final_negotiated_price'))['avg'] or 0
            except Exception:
                avg_booking_value = 0
            
            # CP Leaderboard - handle empty queryset
            try:
                cp_leaderboard = list(ChannelPartner.objects.annotate(
                    booking_count=Count('bookings'),
                    total_revenue=Sum('bookings__payments__amount')
                ).filter(booking_count__gt=0).order_by('-total_revenue')[:10])
            except Exception:
                cp_leaderboard = []
            
            # Project stats - handle empty queryset
            try:
                project_stats = list(Project.objects.annotate(
                    lead_count=Count('leads', filter=Q(leads__is_archived=False)),
                    booking_count=Count('bookings', filter=Q(bookings__is_archived=False)),
                    revenue=Sum('bookings__payments__amount')
                ).order_by('-revenue')[:10])
            except Exception:
                project_stats = []
            
            # User stats
            try:
                user_stats = list(User.objects.values('role').annotate(
                    count=Count('id')
                ).order_by('role'))
            except Exception:
                user_stats = []
            
            # Count projects and mandate owners safely
            try:
                total_projects = Project.objects.filter(is_active=True).count()
            except Exception:
                total_projects = 0
            
            try:
                total_mandate_owners = User.objects.filter(role='mandate_owner', is_active=True).count()
            except Exception:
                total_mandate_owners = 0
            
            context = {
                'is_mandate_owner': True,
                'total_leads': all_leads.count(),
                'new_visits_today': all_leads.filter(created_at__date=today).count(),
                'total_bookings': bookings_count,
                'pending_otp': all_leads.filter(
                    is_pretagged=True,
                    pretag_status='pending_verification'
                ).count(),
                'total_revenue': total_revenue,
                'avg_booking_value': avg_booking_value,
                'total_projects': total_projects,
                'total_mandate_owners': total_mandate_owners,
                'cp_leaderboard': cp_leaderboard,
                'project_stats': project_stats,
                'user_stats': user_stats,
            }
            return render(request, 'dashboard_super_admin.html', context)
        
        # Site Head Dashboard
        elif user_role == 'site_head':
            leads_qs = Lead.objects.filter(project__site_head=user, is_archived=False)
            bookings_qs = Booking.objects.filter(project__site_head=user, is_archived=False)
            projects = Project.objects.filter(site_head=user, is_active=True)
            
            # Unassigned leads
            unassigned_leads = leads_qs.filter(assigned_to__isnull=True).count()
            
            # Employee stats - Only show employees assigned to this site head's projects
            # Get all employees assigned to projects where this site head is in charge
            site_head_projects = Project.objects.filter(site_head=user, is_active=True)
            employees = User.objects.filter(
                Q(role='closing_manager') | Q(role='telecaller') | Q(role='sourcing_manager'),
                assigned_projects__in=site_head_projects
            ).distinct()
            
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
        elif user_role == 'closing_manager':
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
        elif user_role == 'sourcing_manager':
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
        elif user_role == 'telecaller':
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
        else:
            try:
                leads_qs = Lead.objects.filter(is_archived=False)
            except Exception:
                leads_qs = Lead.objects.none()
            
            try:
                bookings_qs = Booking.objects.filter(is_archived=False)
            except Exception:
                bookings_qs = Booking.objects.none()
            
            context = {
                'total_leads': leads_qs.count() if leads_qs else 0,
                'new_visits_today': leads_qs.filter(created_at__date=today).count() if leads_qs else 0,
                'total_bookings': bookings_qs.count() if bookings_qs else 0,
                'pending_otp': leads_qs.filter(
                    is_pretagged=True,
                    pretag_status='pending_verification'
                ).count() if leads_qs else 0,
            }
            return render(request, 'dashboard.html', context)
    except Exception as e:
        # Catch any unexpected errors and show a safe fallback
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        error_trace = traceback.format_exc()
        logger.error(f"Dashboard error: {str(e)}\n{error_trace}")
        
        # Return a minimal dashboard with error details (since DEBUG is True)
        from django.conf import settings
        context = {
            'total_leads': 0,
            'new_visits_today': 0,
            'total_bookings': 0,
            'pending_otp': 0,
            'error': str(e),
            'error_trace': error_trace if settings.DEBUG else None,
        }
        return render(request, 'dashboard.html', context)


