from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum, Avg, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from decimal import Decimal
from leads.models import Lead, LeadProjectAssociation
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
                cp_leaderboard = []
                for cp in ChannelPartner.objects.filter(is_active=True):
                    booking_count = cp.bookings.filter(is_archived=False).count()
                    if booking_count > 0:
                        total_revenue = Payment.objects.filter(booking__channel_partner=cp, booking__is_archived=False).aggregate(total=Sum('amount'))['total'] or 0
                        cp_leaderboard.append({
                            'cp_name': cp.cp_name,
                            'firm_name': cp.firm_name,
                            'booking_count': booking_count,
                            'total_revenue': total_revenue
                        })
                cp_leaderboard.sort(key=lambda x: x['total_revenue'], reverse=True)
                cp_leaderboard = cp_leaderboard[:10]
            except Exception as e:
                import traceback
                traceback.print_exc()
                cp_leaderboard = []
            
            # Project stats - handle empty queryset
            try:
                project_stats = list(Project.objects.filter(is_active=True).annotate(
                    lead_count=Count('lead_associations', filter=Q(lead_associations__is_archived=False)),
                    booking_count=Count('bookings', filter=Q(bookings__is_archived=False)),
                    revenue=Coalesce(Sum('bookings__payments__amount'), Value(Decimal('0')), output_field=DecimalField())
                ).order_by('-revenue')[:10])
            except Exception as e:
                import traceback
                traceback.print_exc()
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
            
            # Pending OTP - use LeadProjectAssociation
            try:
                pending_otp = LeadProjectAssociation.objects.filter(
                    is_pretagged=True,
                    pretag_status='pending_verification',
                    is_archived=False
                ).count()
            except Exception:
                pending_otp = 0
            
            context = {
                'is_super_admin': True,
                'total_leads': all_leads.count(),
                'new_visits_today': all_leads.filter(created_at__date=today).count(),
                'total_bookings': bookings_count,
                'pending_otp': pending_otp,
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
                cp_leaderboard = []
                for cp in ChannelPartner.objects.filter(is_active=True):
                    booking_count = cp.bookings.filter(is_archived=False).count()
                    if booking_count > 0:
                        total_revenue = Payment.objects.filter(booking__channel_partner=cp, booking__is_archived=False).aggregate(total=Sum('amount'))['total'] or 0
                        cp_leaderboard.append({
                            'cp_name': cp.cp_name,
                            'firm_name': cp.firm_name,
                            'booking_count': booking_count,
                            'total_revenue': total_revenue
                        })
                cp_leaderboard.sort(key=lambda x: x['total_revenue'], reverse=True)
                cp_leaderboard = cp_leaderboard[:10]
            except Exception as e:
                import traceback
                traceback.print_exc()
                cp_leaderboard = []
            
            # Project stats - handle empty queryset
            try:
                project_stats = list(Project.objects.filter(is_active=True).annotate(
                    lead_count=Count('lead_associations', filter=Q(lead_associations__is_archived=False)),
                    booking_count=Count('bookings', filter=Q(bookings__is_archived=False)),
                    revenue=Coalesce(Sum('bookings__payments__amount'), Value(Decimal('0')), output_field=DecimalField())
                ).order_by('-revenue')[:10])
            except Exception as e:
                import traceback
                traceback.print_exc()
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
            
            # Pending OTP - use LeadProjectAssociation
            try:
                pending_otp = LeadProjectAssociation.objects.filter(
                    is_pretagged=True,
                    pretag_status='pending_verification',
                    is_archived=False
                ).count()
            except Exception:
                pending_otp = 0
            
            context = {
                'is_mandate_owner': True,
                'total_leads': all_leads.count(),
                'new_visits_today': all_leads.filter(created_at__date=today).count(),
                'total_bookings': bookings_count,
                'pending_otp': pending_otp,
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
            # Use LeadProjectAssociation for project-specific data
            site_head_projects = Project.objects.filter(site_head=user, is_active=True)
            associations = LeadProjectAssociation.objects.filter(
                project__site_head=user,
                is_archived=False
            )
            
            # Get unique leads from associations
            lead_ids = associations.values_list('lead_id', flat=True).distinct()
            leads_qs = Lead.objects.filter(id__in=lead_ids, is_archived=False)
            
            bookings_qs = Booking.objects.filter(project__site_head=user, is_archived=False)
            projects = Project.objects.filter(site_head=user, is_active=True)
            
            # Unassigned leads (associations without assigned_to)
            unassigned_leads = associations.filter(assigned_to__isnull=True).count()
            
            # Employee stats - Only show employees assigned to this site head's projects
            employees = User.objects.filter(
                Q(role='closing_manager') | Q(role='telecaller') | Q(role='sourcing_manager'),
                assigned_projects__in=site_head_projects
            ).distinct()
            
            # Pending OTP - use LeadProjectAssociation
            pending_otp = associations.filter(
                is_pretagged=True,
                pretag_status='pending_verification'
            ).count()
            
            context = {
                'is_site_head': True,
                'total_leads': leads_qs.count(),
                'new_visits_today': leads_qs.filter(created_at__date=today).count(),
                'total_bookings': bookings_qs.count(),
                'pending_otp': pending_otp,
                'unassigned_leads': unassigned_leads,
                'projects': projects,
                'employees': employees,
            }
            return render(request, 'dashboard_site_head.html', context)
        
        # Closing Manager Dashboard
        elif user_role == 'closing_manager':
            # Use LeadProjectAssociation for assigned leads
            associations = LeadProjectAssociation.objects.filter(
                assigned_to=user,
                is_archived=False
            )
            
            # Get unique leads from associations
            lead_ids = associations.values_list('lead_id', flat=True).distinct()
            leads_qs = Lead.objects.filter(id__in=lead_ids, is_archived=False)
            
            bookings_qs = Booking.objects.filter(created_by=user, is_archived=False)
            
            # Today's callbacks
            from leads.models import FollowUpReminder
            todays_callbacks = FollowUpReminder.objects.filter(
                lead__in=lead_ids,
                reminder_date__date=today,
                is_completed=False
            ).count()
            
            # Pending OTP - use LeadProjectAssociation
            pending_otp = associations.filter(
                is_pretagged=True,
                pretag_status='pending_verification'
            ).count()
            
            context = {
                'is_closing_manager': True,
                'total_leads': leads_qs.count(),
                'new_visits_today': leads_qs.filter(created_at__date=today).count(),
                'total_bookings': bookings_qs.count(),
                'pending_otp': pending_otp,
                'todays_callbacks': todays_callbacks,
            }
            return render(request, 'dashboard_closing_manager.html', context)
        
        # Sourcing Manager Dashboard
        elif user_role == 'sourcing_manager':
            # Use LeadProjectAssociation for leads created by this user
            associations = LeadProjectAssociation.objects.filter(
                created_by=user,
                is_archived=False
            )
            
            # Get unique leads from associations
            lead_ids = associations.values_list('lead_id', flat=True).distinct()
            leads_qs = Lead.objects.filter(id__in=lead_ids, is_archived=False)
            
            # Pending OTP - use LeadProjectAssociation
            pending_otp = associations.filter(
                is_pretagged=True,
                pretag_status='pending_verification'
            ).count()
            
            context = {
                'is_sourcing_manager': True,
                'total_leads': leads_qs.count(),
                'new_visits_today': leads_qs.filter(created_at__date=today).count(),
                'pending_otp': pending_otp,
            }
            return render(request, 'dashboard_sourcing_manager.html', context)
        
        # Telecaller Dashboard
        elif user_role == 'telecaller':
            # Use LeadProjectAssociation for assigned leads
            associations = LeadProjectAssociation.objects.filter(
                assigned_to=user,
                is_archived=False
            )
            
            # Get unique leads from associations
            lead_ids = associations.values_list('lead_id', flat=True).distinct()
            leads_qs = Lead.objects.filter(id__in=lead_ids, is_archived=False)
            
            # Today's callbacks
            from leads.models import FollowUpReminder
            todays_callbacks = FollowUpReminder.objects.filter(
                lead__in=lead_ids,
                reminder_date__date=today,
                is_completed=False
            ).count()
            
            # Active reminders
            active_reminders = FollowUpReminder.objects.filter(
                lead__in=lead_ids,
                is_completed=False,
                reminder_date__gte=timezone.now()
            ).count()
            
            # Untouched leads (>24 hours) - use associations
            from datetime import timedelta
            yesterday = timezone.now() - timedelta(hours=24)
            untouched_leads = associations.filter(
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
            
            # Pending OTP - use LeadProjectAssociation
            try:
                pending_otp = LeadProjectAssociation.objects.filter(
                    is_pretagged=True,
                    pretag_status='pending_verification',
                    is_archived=False
                ).count()
            except Exception:
                pending_otp = 0
            
            context = {
                'total_leads': leads_qs.count() if leads_qs else 0,
                'new_visits_today': leads_qs.filter(created_at__date=today).count() if leads_qs else 0,
                'total_bookings': bookings_qs.count() if bookings_qs else 0,
                'pending_otp': pending_otp,
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


