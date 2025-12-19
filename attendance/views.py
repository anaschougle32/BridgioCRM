from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.conf import settings
from .models import Attendance
from projects.models import Project


@login_required
def attendance_list(request):
    """List all attendance records"""
    attendances = Attendance.objects.all()
    
    # Role-based filtering - Mandate Owner has same permissions as Super Admin
    if request.user.is_super_admin() or request.user.is_mandate_owner() or (request.user.is_superuser and request.user.is_staff):
        pass  # Super admin and mandate owner see all
    elif request.user.is_site_head():
        attendances = attendances.filter(project__site_head=request.user)
    else:
        attendances = attendances.filter(user=request.user)
    
    # Filter by project
    project_id = request.GET.get('project', '')
    if project_id:
        attendances = attendances.filter(project_id=project_id)
    
    # Filter by date
    date_filter = request.GET.get('date', '')
    if date_filter:
        attendances = attendances.filter(check_in_time__date=date_filter)
    else:
        # Default to today
        today = timezone.now().date()
        attendances = attendances.filter(check_in_time__date=today)
    
    # Filter by user
    user_id = request.GET.get('user', '')
    if user_id and (request.user.is_super_admin() or request.user.is_site_head()):
        attendances = attendances.filter(user_id=user_id)
    
    # Order by check-in time
    attendances = attendances.order_by('-check_in_time')
    
    # Pagination
    paginator = Paginator(attendances, 25)
    page = request.GET.get('page', 1)
    attendances_page = paginator.get_page(page)
    
    # Get projects for filter - Mandate Owner has same permissions as Super Admin
    if request.user.is_super_admin() or request.user.is_mandate_owner():
        projects = Project.objects.filter(is_active=True)
    elif request.user.is_site_head():
        projects = Project.objects.filter(site_head=request.user, is_active=True)
    else:
        projects = Project.objects.none()
    
    context = {
        'attendances': attendances_page,
        'projects': projects,
        'selected_project': project_id,
        'selected_date': date_filter or timezone.now().date().isoformat(),
        'selected_user': user_id,
    }
    return render(request, 'attendance/list.html', context)


@login_required
def attendance_summary(request):
    """Attendance summary/overview"""
    if not (request.user.is_super_admin() or request.user.is_mandate_owner() or 
            request.user.is_site_head()):
        messages.error(request, 'You do not have permission to view attendance summary.')
        return redirect('dashboard')
    
    from accounts.models import User
    from django.db.models import Count, Q
    
    today = timezone.now().date()
    
    # Get projects - Mandate Owner has same permissions as Super Admin
    if request.user.is_super_admin() or request.user.is_mandate_owner():
        projects = Project.objects.filter(is_active=True)
        users = User.objects.filter(is_active=True)
    else:  # Site Head
        projects = Project.objects.filter(site_head=request.user, is_active=True)
        users = User.objects.filter(mandate_owner=request.user.mandate_owner, is_active=True)
    
    # Project-wise attendance stats
    project_stats = []
    for project in projects:
        today_attendance = Attendance.objects.filter(
            project=project,
            check_in_time__date=today,
            is_valid=True
        ).count()
        project_stats.append({
            'project': project,
            'today_attendance': today_attendance,
        })
    
    # User-wise attendance stats
    user_stats = []
    for user in users:
        today_attendance = Attendance.objects.filter(
            user=user,
            check_in_time__date=today,
            is_valid=True
        ).count()
        user_stats.append({
            'user': user,
            'today_attendance': today_attendance,
        })
    
    context = {
        'project_stats': project_stats,
        'user_stats': user_stats,
        'today': today,
    }
    return render(request, 'attendance/summary.html', context)


@login_required
def attendance_checkin(request):
    """Check-in with geo-location and selfie"""
    if request.method == 'POST':
        try:
            # Get project
            project_id = request.POST.get('project')
            project = None
            if project_id:
                project = get_object_or_404(Project, pk=project_id, is_active=True)
            
            # Get geo-location
            latitude = float(request.POST.get('latitude', 0))
            longitude = float(request.POST.get('longitude', 0))
            accuracy_radius = float(request.POST.get('accuracy_radius', 100))
            
            # Validate location if project has coordinates
            is_within_radius = True
            if project and project.latitude and project.longitude:
                # Calculate distance (simple haversine approximation)
                from math import radians, cos, sin, asin, sqrt
                lat1, lon1 = radians(float(project.latitude)), radians(float(project.longitude))
                lat2, lon2 = radians(latitude), radians(longitude)
                dlon = lon2 - lon1
                dlat = lat2 - lat1
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * asin(sqrt(a))
                distance_km = 6371 * c  # Earth radius in km
                distance_m = distance_km * 1000
                is_within_radius = distance_m <= 20  # Must be within 20m
            
            # Get selfie
            selfie_photo = request.FILES.get('selfie_photo')
            if not selfie_photo:
                return JsonResponse({'success': False, 'error': 'Selfie photo is required.'}, status=400)
            
            # Get user agent and IP
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            ip_address = request.META.get('REMOTE_ADDR', '')
            
            # Create attendance record
            attendance = Attendance.objects.create(
                user=request.user,
                project=project,
                latitude=latitude,
                longitude=longitude,
                accuracy_radius=accuracy_radius,
                selfie_photo=selfie_photo,
                is_within_radius=is_within_radius,
                is_valid=is_within_radius,  # Invalid if not within radius
                user_agent=user_agent,
                ip_address=ip_address,
            )
            
            if is_within_radius:
                messages.success(request, 'Check-in successful!')
                return redirect('attendance:list')
            else:
                messages.warning(request, 'Check-in recorded but you are not within 20m of the project location.')
                return redirect('attendance:list')
                
        except Exception as e:
            messages.error(request, f'Error during check-in: {str(e)}')
    
    # Get available projects for user
    if request.user.is_super_admin() or request.user.is_mandate_owner():
        projects = Project.objects.filter(is_active=True)
    elif request.user.is_site_head():
        projects = Project.objects.filter(site_head=request.user, is_active=True)
    else:
        # For other roles, show projects they're assigned to
        # Use assigned_projects relationship instead of leads__assigned_to
        projects = request.user.assigned_projects.filter(is_active=True).distinct()
    
    context = {
        'projects': projects,
        'GOOGLE_MAPS_API_KEY': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
    }
    return render(request, 'attendance/checkin.html', context)
