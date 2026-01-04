from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from datetime import timedelta
from leads.models import Lead
from bookings.models import Booking, Payment
from projects.models import Project
from accounts.models import User
from channel_partners.models import ChannelPartner


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
    
    # Status breakdown - use LeadProjectAssociation
    from leads.models import LeadProjectAssociation
    status_breakdown = LeadProjectAssociation.objects.filter(
        is_archived=False
    ).values('status').annotate(
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
        lead_count=Count('lead_associations', filter=Q(lead_associations__is_archived=False)),
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
            # Use LeadProjectAssociation instead of Lead for assigned_to
            from leads.models import LeadProjectAssociation
            if user.is_super_admin() or user.is_mandate_owner() or (user.is_superuser and user.is_staff):
                calls_count = LeadProjectAssociation.objects.filter(assigned_to=emp, is_archived=False).count()
            else:
                calls_count = LeadProjectAssociation.objects.filter(
                    assigned_to=emp,
                    project__mandate_owner=user,
                    is_archived=False
                ).count()
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


@login_required
def employee_performance(request):
    """Comprehensive employee performance metrics - Super Admin, Mandate Owner, Site Head"""
    if not (request.user.is_super_admin() or request.user.is_mandate_owner() or request.user.is_site_head()):
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, 'You do not have permission to view employee performance.')
        return redirect('dashboard')
    
    user = request.user
    today = timezone.now().date()
    this_month_start = today.replace(day=1)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    last_month_end = this_month_start - timedelta(days=1)
    this_week_start = today - timedelta(days=today.weekday())
    
    # Get employees based on user role
    if user.is_super_admin() or user.is_mandate_owner():
        employees = User.objects.filter(is_active=True).exclude(role='super_admin')
    elif user.is_site_head():
        # Site Head sees employees assigned to their projects
        site_head_projects = Project.objects.filter(site_head=user, is_active=True)
        employees = User.objects.filter(
            Q(role='closing_manager') | Q(role='telecaller') | Q(role='sourcing_manager'),
            assigned_projects__in=site_head_projects
        ).distinct()
    else:
        employees = User.objects.none()
    
    employee_metrics = []
    for emp in employees:
        metrics = {
            'user': emp,
            'role': emp.get_role_display(),
            'role_code': emp.role,
        }
        
        # Base filters based on user role - using LeadProjectAssociation
        from leads.models import LeadProjectAssociation
        if user.is_super_admin() or user.is_mandate_owner():
            emp_associations = LeadProjectAssociation.objects.filter(is_archived=False)
            emp_bookings = Booking.objects.filter(is_archived=False)
            emp_payments = Payment.objects.all()
        else:  # Site Head
            site_head_projects = Project.objects.filter(site_head=user, is_active=True)
            emp_associations = LeadProjectAssociation.objects.filter(
                project__in=site_head_projects,
                is_archived=False
            )
            emp_bookings = Booking.objects.filter(project__in=site_head_projects, is_archived=False)
            emp_payments = Payment.objects.filter(booking__project__in=site_head_projects)
        
        if emp.is_closing_manager():
            # Closing Manager Metrics
            from leads.models import CallLog
            # Total calls made
            if user.is_super_admin() or user.is_mandate_owner():
                metrics['total_calls'] = CallLog.objects.filter(user=emp).count()
            else:
                site_head_projects = Project.objects.filter(site_head=user, is_active=True)
                lead_ids = LeadProjectAssociation.objects.filter(project__in=site_head_projects).values_list('lead_id', flat=True)
                metrics['total_calls'] = CallLog.objects.filter(lead_id__in=lead_ids, user=emp).count()
            
            # Total visits handled
            metrics['total_visits_handled'] = emp_associations.filter(
                assigned_to=emp
            ).filter(
                Q(status='visit_completed') | Q(phone_verified=True)
            ).count()
            metrics['visits_this_month'] = emp_associations.filter(
                assigned_to=emp
            ).filter(
                Q(status='visit_completed') | Q(phone_verified=True)
            ).filter(
                updated_at__date__gte=this_month_start
            ).count()
            
            # Total bookings done (using credit fields)
            metrics['total_bookings'] = emp_bookings.filter(credited_to_closing_manager=emp).count()
            metrics['bookings_this_month'] = emp_bookings.filter(credited_to_closing_manager=emp, created_at__date__gte=this_month_start).count()
            metrics['bookings_this_week'] = emp_bookings.filter(credited_to_closing_manager=emp, created_at__date__gte=this_week_start).count()
            
            # Total visit to conversion ratio
            if metrics['total_visits_handled'] > 0:
                metrics['visit_to_conversion_ratio'] = (metrics['total_bookings'] / metrics['total_visits_handled']) * 100
            else:
                metrics['visit_to_conversion_ratio'] = 0
            
            # Additional metrics for backward compatibility
            metrics['total_leads'] = emp_associations.filter(assigned_to=emp).count()
            metrics['leads_this_month'] = emp_associations.filter(assigned_to=emp, created_at__date__gte=this_month_start).count()
            metrics['leads_this_week'] = emp_associations.filter(assigned_to=emp, created_at__date__gte=this_week_start).count()
            total_revenue_raw = emp_payments.filter(booking__credited_to_closing_manager=emp).aggregate(total=Sum('amount'))['total']
            metrics['total_revenue'] = float(total_revenue_raw) if total_revenue_raw is not None else 0
            
            revenue_this_month_raw = emp_payments.filter(
                booking__credited_to_closing_manager=emp
            ).filter(
                payment_date__gte=this_month_start
            ).aggregate(total=Sum('amount'))['total']
            metrics['revenue_this_month'] = float(revenue_this_month_raw) if revenue_this_month_raw is not None else 0
            assigned_leads = emp_associations.filter(assigned_to=emp).count()
            if assigned_leads > 0:
                metrics['conversion_rate'] = (metrics['total_bookings'] / assigned_leads) * 100
            else:
                metrics['conversion_rate'] = 0
            metrics['pending_otp'] = emp_associations.filter(
                assigned_to=emp,
                is_pretagged=True,
                pretag_status='pending_verification'
            ).count()
            metrics['visits_completed'] = metrics['total_visits_handled']
            
        elif emp.is_sourcing_manager():
            # Sourcing Manager Metrics
            from channel_partners.models import ChannelPartner
            # Total CPs active
            if user.is_super_admin() or user.is_mandate_owner():
                metrics['total_cps_active'] = ChannelPartner.objects.filter(
                    status='active',
                    is_active=True
                ).count()
            else:
                site_head_projects = Project.objects.filter(site_head=user, is_active=True)
                metrics['total_cps_active'] = ChannelPartner.objects.filter(
                    linked_projects__in=site_head_projects,
                    status='active',
                    is_active=True
                ).distinct().count()
            
            # Total visits done by CPs (leads with CP that have visits)
            cp_lead_ids = Lead.objects.filter(
                channel_partner__isnull=False,
                is_archived=False
            ).values_list('id', flat=True)
            cp_visits = emp_associations.filter(
                lead_id__in=cp_lead_ids
            ).filter(
                Q(status='visit_completed') | Q(phone_verified=True)
            )
            if user.is_super_admin() or user.is_mandate_owner():
                metrics['total_visits_by_cps'] = cp_visits.count()
            else:
                site_head_projects = Project.objects.filter(site_head=user, is_active=True)
                metrics['total_visits_by_cps'] = cp_visits.filter(project__in=site_head_projects).count()
            
            # Total conversion done (CP client handled by closer) - using credit fields
            cp_bookings = emp_bookings.filter(credited_to_sourcing_manager=emp)
            if user.is_super_admin() or user.is_mandate_owner():
                metrics['total_conversion_done'] = cp_bookings.count()
            else:
                site_head_projects = Project.objects.filter(site_head=user, is_active=True)
                metrics['total_conversion_done'] = cp_bookings.filter(project__in=site_head_projects).count()
            
            # Total conversion ratio of CP visits to conversion
            if metrics['total_visits_by_cps'] > 0:
                metrics['cp_visits_to_conversion_ratio'] = (metrics['total_conversion_done'] / metrics['total_visits_by_cps']) * 100
            else:
                metrics['cp_visits_to_conversion_ratio'] = 0
            
            # Additional metrics for backward compatibility
            metrics['total_leads_created'] = emp_associations.filter(created_by=emp).count()
            metrics['leads_this_month'] = emp_associations.filter(created_by=emp, created_at__date__gte=this_month_start).count()
            metrics['leads_this_week'] = emp_associations.filter(created_by=emp, created_at__date__gte=this_week_start).count()
            metrics['pretagged_leads'] = emp_associations.filter(created_by=emp, is_pretagged=True).count()
            metrics['pretagged_this_month'] = emp_associations.filter(
                created_by=emp,
                is_pretagged=True,
                created_at__date__gte=this_month_start
            ).count()
            metrics['verified_pretagged'] = emp_associations.filter(
                created_by=emp,
                is_pretagged=True,
                phone_verified=True
            ).count()
            if metrics['pretagged_leads'] > 0:
                metrics['conversion_rate'] = (metrics['verified_pretagged'] / metrics['pretagged_leads']) * 100
            else:
                metrics['conversion_rate'] = 0
            
        elif emp.is_telecaller():
            # Telecaller Metrics
            from leads.models import CallLog, FollowUpReminder
            
            # Total calls made
            if user.is_super_admin() or user.is_mandate_owner():
                metrics['total_calls'] = CallLog.objects.filter(user=emp).count()
                metrics['calls_this_month'] = CallLog.objects.filter(
                    user=emp,
                    created_at__date__gte=this_month_start
                ).count()
            else:
                site_head_projects = Project.objects.filter(site_head=user, is_active=True)
                lead_ids = LeadProjectAssociation.objects.filter(project__in=site_head_projects).values_list('lead_id', flat=True)
                metrics['total_calls'] = CallLog.objects.filter(lead_id__in=lead_ids, user=emp).count()
                metrics['calls_this_month'] = CallLog.objects.filter(
                    lead_id__in=lead_ids,
                    user=emp,
                    created_at__date__gte=this_month_start
                ).count()
            
            # Total leads assigned
            metrics['total_leads_assigned'] = emp_associations.filter(assigned_to=emp).count()
            metrics['leads_this_month'] = emp_associations.filter(assigned_to=emp, created_at__date__gte=this_month_start).count()
            metrics['leads_this_week'] = emp_associations.filter(assigned_to=emp, created_at__date__gte=this_week_start).count()
            
            # Scheduled visits
            metrics['scheduled_visits'] = emp_associations.filter(assigned_to=emp, status='visit_scheduled').count()
            metrics['scheduled_this_month'] = emp_associations.filter(
                assigned_to=emp,
                status='visit_scheduled',
                created_at__date__gte=this_month_start
            ).count()
            
            # Visits completed (OTP verified)
            metrics['visits_completed'] = emp_associations.filter(
                assigned_to=emp,
                phone_verified=True
            ).count()
            
            # Visit to conversion ratio (if applicable) - using credit fields
            telecaller_bookings = emp_bookings.filter(credited_to_telecaller=emp).count()
            if metrics['visits_completed'] > 0:
                metrics['visit_to_conversion_ratio'] = (telecaller_bookings / metrics['visits_completed']) * 100
            else:
                metrics['visit_to_conversion_ratio'] = 0
            
            # Follow-up reminders
            lead_ids = emp_associations.values_list('lead_id', flat=True)
            metrics['active_reminders'] = FollowUpReminder.objects.filter(
                lead_id__in=lead_ids,
                is_completed=False
            ).count()
            
            # Untouched leads (>24 hours)
            yesterday = timezone.now() - timedelta(hours=24)
            metrics['untouched_leads'] = emp_associations.filter(
                assigned_to=emp,
                status='new',
                created_at__lt=yesterday
            ).count()
        
        # Add project assignments for all employees (for site heads display)
        metrics['assigned_projects'] = list(emp.assigned_projects.filter(is_active=True).values_list('name', flat=True))
        
        employee_metrics.append(metrics)
    
    # Sort by role, then by performance
    employee_metrics.sort(key=lambda x: (x['role_code'], -x.get('total_bookings', x.get('total_leads_created', x.get('total_leads_assigned', 0)))))
    
    context = {
        'employee_metrics': employee_metrics,
        'today': today,
        'this_month_start': this_month_start,
        'last_month_start': last_month_start,
        'is_site_head': user.is_site_head(),
    }
    return render(request, 'reports/employee_performance.html', context)


@login_required
def cp_performance(request):
    """Channel Partner Performance Dashboard - Super Admin, Mandate Owner, Site Head, Sourcing Manager"""
    if not (request.user.is_super_admin() or request.user.is_mandate_owner() or request.user.is_site_head() or request.user.is_sourcing_manager()):
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, 'You do not have permission to view CP performance.')
        return redirect('dashboard')
    
    user = request.user
    today = timezone.now().date()
    this_month_start = today.replace(day=1)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    last_month_end = this_month_start - timedelta(days=1)
    this_week_start = today - timedelta(days=today.weekday())
    
    # Get channel partners based on user role
    if user.is_super_admin() or user.is_mandate_owner():
        cps = ChannelPartner.objects.filter(status='active', is_active=True)
    elif user.is_site_head():
        # Site Head sees CPs linked to their projects
        site_head_projects = Project.objects.filter(site_head=user, is_active=True)
        cps = ChannelPartner.objects.filter(
            linked_projects__in=site_head_projects,
            status='active',
            is_active=True
        ).distinct()
    elif user.is_sourcing_manager():
        # Sourcing Manager sees all CPs (same as regular CP list)
        cps = ChannelPartner.objects.filter(status='active', is_active=True)
    else:
        cps = ChannelPartner.objects.none()
    
    cp_metrics = []
    for cp in cps:
        metrics = {
            'cp': cp,
            'cp_name': cp.cp_name,
            'firm_name': cp.firm_name,
            'cp_id': cp.cp_unique_id,
            'phone': cp.phone,
            'status': cp.status,
        }
        
        # Base filters based on user role - using LeadProjectAssociation
        from leads.models import LeadProjectAssociation
        if user.is_super_admin() or user.is_mandate_owner():
            cp_lead_ids = Lead.objects.filter(
                Q(channel_partner=cp) | Q(cp_phone=cp.phone),
                is_archived=False
            ).values_list('id', flat=True)
            cp_associations = LeadProjectAssociation.objects.filter(
                lead_id__in=cp_lead_ids,
                is_archived=False
            )
            cp_bookings = Booking.objects.filter(
                Q(channel_partner=cp) | Q(lead__channel_partner=cp) | Q(lead__cp_phone=cp.phone),
                is_archived=False
            )
            cp_payments = Payment.objects.filter(
                Q(booking__channel_partner=cp) | 
                Q(booking__lead__channel_partner=cp) | 
                Q(booking__lead__cp_phone=cp.phone)
            )
        elif user.is_site_head():
            site_head_projects = Project.objects.filter(site_head=user, is_active=True)
            cp_lead_ids = Lead.objects.filter(
                Q(channel_partner=cp) | Q(cp_phone=cp.phone),
                is_archived=False
            ).values_list('id', flat=True)
            cp_associations = LeadProjectAssociation.objects.filter(
                lead_id__in=cp_lead_ids,
                project__in=site_head_projects,
                is_archived=False
            )
            cp_bookings = Booking.objects.filter(
                Q(channel_partner=cp) | Q(lead__channel_partner=cp) | Q(lead__cp_phone=cp.phone),
                project__in=site_head_projects,
                is_archived=False
            )
            cp_payments = Payment.objects.filter(
                Q(booking__channel_partner=cp) | 
                Q(booking__lead__channel_partner=cp) | 
                Q(booking__lead__cp_phone=cp.phone),
                booking__project__in=site_head_projects
            )
        else:  # Sourcing Manager - sees all data like super admin
            cp_lead_ids = Lead.objects.filter(
                Q(channel_partner=cp) | Q(cp_phone=cp.phone),
                is_archived=False
            ).values_list('id', flat=True)
            cp_associations = LeadProjectAssociation.objects.filter(
                lead_id__in=cp_lead_ids,
                is_archived=False
            )
            cp_bookings = Booking.objects.filter(
                Q(channel_partner=cp) | Q(lead__channel_partner=cp) | Q(lead__cp_phone=cp.phone),
                is_archived=False
            )
            cp_payments = Payment.objects.filter(
                Q(booking__channel_partner=cp) | 
                Q(booking__lead__channel_partner=cp) | 
                Q(booking__lead__cp_phone=cp.phone)
            )
        
        # CPs active number (always 1 if CP is active, 0 if inactive)
        metrics['cps_active_number'] = 1 if cp.status == 'active' and cp.is_active else 0
        
        # Total leads brought by CP
        metrics['total_leads'] = cp_associations.count()
        metrics['leads_this_month'] = cp_associations.filter(created_at__date__gte=this_month_start).count()
        metrics['leads_this_week'] = cp_associations.filter(created_at__date__gte=this_week_start).count()
        metrics['leads_last_month'] = cp_associations.filter(
            created_at__date__gte=last_month_start,
            created_at__date__lte=last_month_end
        ).count()
        
        # CP visits on projects (visit_completed or pretagged verified)
        metrics['cp_visits'] = cp_associations.filter(
            Q(status='visit_completed') | Q(is_pretagged=True, phone_verified=True)
        ).count()
        metrics['cp_visits_this_month'] = cp_associations.filter(
            Q(status='visit_completed') | Q(is_pretagged=True, phone_verified=True),
            updated_at__date__gte=this_month_start
        ).count()
        metrics['visited_leads'] = metrics['cp_visits']  # Keep for backward compatibility
        metrics['visited_this_month'] = metrics['cp_visits_this_month']  # Keep for backward compatibility
        
        # CP bookings on projects
        metrics['cp_bookings'] = cp_bookings.count()
        metrics['cp_bookings_this_month'] = cp_bookings.filter(created_at__date__gte=this_month_start).count()
        metrics['total_bookings'] = metrics['cp_bookings']  # Keep for backward compatibility
        metrics['bookings_this_month'] = metrics['cp_bookings_this_month']
        metrics['bookings_this_week'] = cp_bookings.filter(created_at__date__gte=this_week_start).count()
        metrics['bookings_last_month'] = cp_bookings.filter(
            created_at__date__gte=last_month_start,
            created_at__date__lte=last_month_end
        ).count()
        
        # Revenue generated - DEBUG
        total_revenue_raw = cp_payments.aggregate(total=Sum('amount'))['total']
        print(f"DEBUG: CP {cp.cp_name} - total_revenue_raw: {total_revenue_raw} (type: {type(total_revenue_raw)})")
        print(f"DEBUG: CP {cp.cp_name} - cp_payments count: {cp_payments.count()}")
        if cp_payments.exists():
            print(f"DEBUG: CP {cp.cp_name} - First payment amount: {cp_payments.first().amount} (type: {type(cp_payments.first().amount)})")
        metrics['total_revenue'] = float(total_revenue_raw) if total_revenue_raw is not None else 0
        print(f"DEBUG: CP {cp.cp_name} - final total_revenue: {metrics['total_revenue']} (type: {type(metrics['total_revenue'])})")
        
        revenue_this_month_raw = cp_payments.filter(
            payment_date__gte=this_month_start
        ).aggregate(total=Sum('amount'))['total']
        metrics['revenue_this_month'] = float(revenue_this_month_raw) if revenue_this_month_raw is not None else 0
        
        # Overall visit to conversion ratio of CPs
        if metrics['cp_visits'] > 0:
            metrics['visit_to_conversion_ratio'] = (metrics['cp_bookings'] / metrics['cp_visits']) * 100
        else:
            metrics['visit_to_conversion_ratio'] = 0
        
        # Conversion rates (for backward compatibility)
        if metrics['total_leads'] > 0:
            metrics['lead_to_visit_rate'] = (metrics['cp_visits'] / metrics['total_leads']) * 100
            metrics['lead_to_booking_rate'] = (metrics['cp_bookings'] / metrics['total_leads']) * 100
        else:
            metrics['lead_to_visit_rate'] = 0
            metrics['lead_to_booking_rate'] = 0
        
        metrics['visit_to_booking_rate'] = metrics['visit_to_conversion_ratio']  # Alias
        
        # Average booking value
        if metrics['total_bookings'] > 0:
            avg_booking = cp_bookings.aggregate(avg=Avg('final_negotiated_price'))['avg'] or 0
            metrics['avg_booking_value'] = avg_booking
        else:
            metrics['avg_booking_value'] = 0
        
        # Commission (if available)
        total_commission = 0
        for booking in cp_bookings:
            if booking.cp_commission_percent and booking.final_negotiated_price:
                commission = (booking.final_negotiated_price * booking.cp_commission_percent) / 100
                total_commission += commission
        metrics['total_commission'] = total_commission
        
        # Projects linked
        metrics['linked_projects_count'] = cp.linked_projects.filter(is_active=True).count()
        
        cp_metrics.append(metrics)
    
    # Search and filter
    search = request.GET.get('search', '').strip()
    selected_status = request.GET.get('status', '')
    selected_project = request.GET.get('project', '')
    
    if search:
        cp_metrics = [m for m in cp_metrics if (
            search.lower() in m['cp_name'].lower() or
            search.lower() in m['firm_name'].lower() or
            search.lower() in m['phone'] or
            (m['cp_id'] and search.lower() in m['cp_id'].lower())
        )]
    
    if selected_status:
        cp_metrics = [m for m in cp_metrics if m['status'] == selected_status]
    
    if selected_project:
        # Filter by project - check if CP is linked to selected project
        try:
            project = Project.objects.get(pk=selected_project)
            cp_metrics = [m for m in cp_metrics if project in m['cp'].linked_projects.all()]
        except Project.DoesNotExist:
            pass
    
    # Get all projects for filter dropdown
    if user.is_super_admin() or user.is_mandate_owner():
        projects = Project.objects.filter(is_active=True).order_by('name')
    elif user.is_site_head():
        projects = Project.objects.filter(site_head=user, is_active=True).order_by('name')
    elif user.is_sourcing_manager():
        projects = user.assigned_projects.filter(is_active=True).order_by('name')
    else:
        projects = Project.objects.none()
    
    # Sort by total bookings (descending)
    cp_metrics.sort(key=lambda x: x['total_bookings'], reverse=True)
    
    # Calculate total revenue - DEBUG
    print(f"DEBUG: Calculating total revenue from {len(cp_metrics)} CPs")
    for i, m in enumerate(cp_metrics):
        print(f"DEBUG: CP {i} - {m['cp_name']}: total_revenue = {m['total_revenue']} (type: {type(m['total_revenue'])})")
    total_revenue = sum(float(m['total_revenue']) for m in cp_metrics)
    print(f"DEBUG: Final total_revenue: {total_revenue} (type: {type(total_revenue)})")
    
    context = {
        'cp_metrics': cp_metrics,
        'today': today,
        'this_month_start': this_month_start,
        'last_month_start': last_month_start,
        'total_cps': len(cp_metrics),
        'total_revenue': total_revenue,
        'search': search,
        'selected_status': selected_status,
        'selected_project': selected_project,
        'projects': projects,
    }
    return render(request, 'reports/cp_performance.html', context)

