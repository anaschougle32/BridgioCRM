from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Count, Q, Sum
from django.core.paginator import Paginator
from .models import User
from projects.models import Project
from leads.models import Lead
from bookings.models import Booking
from channel_partners.models import ChannelPartner


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('dashboard')


@login_required
def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@login_required
def user_list(request):
    """User management - Super Admin and Mandate Owners"""
    if not (request.user.is_super_admin() or request.user.is_mandate_owner()):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    users = User.objects.all()
    
    # Mandate Owner can only see their employees
    if request.user.is_mandate_owner():
        users = users.filter(
            Q(mandate_owner=request.user) | Q(pk=request.user.pk)
        )
    
    # Search
    search = request.GET.get('search', '')
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    # Filter by role
    role = request.GET.get('role', '')
    if role:
        users = users.filter(role=role)
    
    # Pagination
    paginator = Paginator(users, 25)
    page = request.GET.get('page', 1)
    users_page = paginator.get_page(page)
    
    context = {
        'users': users_page,
        'role_choices': User.ROLE_CHOICES,
        'search': search,
        'selected_role': role,
    }
    return render(request, 'accounts/user_list.html', context)


@login_required
def user_create(request):
    """Create new user - Super Admin and Mandate Owners"""
    if not (request.user.is_super_admin() or request.user.is_mandate_owner()):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')
        phone = request.POST.get('phone', '')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        mandate_owner_id = request.POST.get('mandate_owner')
        is_active = request.POST.get('is_active') == 'on'
        
        # Role restrictions
        if request.user.is_mandate_owner():
            # Mandate owners can only create: site_head, closing_manager, sourcing_manager, telecaller
            allowed_roles = ['site_head', 'closing_manager', 'sourcing_manager', 'telecaller']
            if role not in allowed_roles:
                messages.error(request, 'You can only create Site Heads, Closing Managers, Sourcing Managers, and Telecallers.')
                return redirect('accounts:user_create')
            # Force mandate_owner to be the current user
            mandate_owner_id = request.user.id
        
        # Super Admin can create Mandate Owners and Site Heads
        if request.user.is_super_admin() and role == 'mandate_owner':
            mandate_owner_id = None
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('accounts:user_create')
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=role,
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            mandate_owner_id=mandate_owner_id if mandate_owner_id else None,
            is_active=is_active
        )
        
        # Assign projects for telecallers
        if role == 'telecaller':
            project_ids = request.POST.getlist('assigned_projects')
            if project_ids:
                from projects.models import Project
                projects = Project.objects.filter(id__in=project_ids, is_active=True)
                user.assigned_projects.set(projects)
        
        messages.success(request, f'User {user.username} created successfully!')
        return redirect('accounts:user_list')
    
    # Get mandate owners for dropdown (only for Super Admin)
    mandate_owners = None
    if request.user.is_super_admin():
        mandate_owners = User.objects.filter(role='mandate_owner', is_active=True)
    
    # Determine allowed roles
    if request.user.is_super_admin():
        allowed_roles = User.ROLE_CHOICES
    else:  # Mandate Owner
        allowed_roles = [
            ('site_head', 'Site Head'),
            ('closing_manager', 'Closing Manager'),
            ('sourcing_manager', 'Sourcing Manager'),
            ('telecaller', 'Telecaller'),
        ]
    
    # Get projects for telecaller assignment (only for Super Admin and Mandate Owners)
    projects = None
    if request.user.is_super_admin():
        projects = Project.objects.filter(is_active=True)
    elif request.user.is_mandate_owner():
        projects = Project.objects.filter(mandate_owner=request.user, is_active=True)
    
    context = {
        'role_choices': allowed_roles,
        'mandate_owners': mandate_owners,
        'projects': projects,
    }
    return render(request, 'accounts/user_create.html', context)


@login_required
def user_edit(request, pk):
    """Edit user - Super Admin and Mandate Owners"""
    user = get_object_or_404(User, pk=pk)
    
    if not (request.user.is_super_admin() or request.user.is_mandate_owner()):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    # Mandate Owner can only edit their employees
    if request.user.is_mandate_owner() and user.mandate_owner != request.user and user != request.user:
        messages.error(request, 'You can only edit your employees.')
        return redirect('accounts:user_list')
    
    if request.method == 'POST':
        user.email = request.POST.get('email', user.email)
        user.phone = request.POST.get('phone', '')
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.is_active = request.POST.get('is_active') == 'on'
        
        # Role can only be changed by Super Admin
        if request.user.is_super_admin():
            user.role = request.POST.get('role', user.role)
            mandate_owner_id = request.POST.get('mandate_owner')
            if mandate_owner_id:
                user.mandate_owner_id = mandate_owner_id
            elif user.role == 'mandate_owner':
                user.mandate_owner = None
        
        # Password change
        new_password = request.POST.get('password', '')
        if new_password:
            user.set_password(new_password)
        
        # Update project assignments for telecallers
        if user.role == 'telecaller':
            project_ids = request.POST.getlist('assigned_projects')
            from projects.models import Project
            if project_ids:
                projects = Project.objects.filter(id__in=project_ids, is_active=True)
                user.assigned_projects.set(projects)
            else:
                user.assigned_projects.clear()
        
        user.save()
        messages.success(request, f'User {user.username} updated successfully!')
        return redirect('accounts:user_list')
    
    # Get mandate owners for dropdown (only for Super Admin)
    mandate_owners = None
    if request.user.is_super_admin():
        mandate_owners = User.objects.filter(role='mandate_owner', is_active=True)
    
    # Get projects for telecaller assignment
    projects = None
    if request.user.is_super_admin():
        projects = Project.objects.filter(is_active=True)
    elif request.user.is_mandate_owner():
        projects = Project.objects.filter(mandate_owner=request.user, is_active=True)
    
    # Get user's assigned projects
    user_assigned_projects = []
    if user.role == 'telecaller' and projects:
        user_assigned_projects = list(user.assigned_projects.values_list('id', flat=True))
    
    context = {
        'user_obj': user,
        'role_choices': User.ROLE_CHOICES if request.user.is_super_admin() else None,
        'mandate_owners': mandate_owners,
        'projects': projects,
        'user_assigned_projects': user_assigned_projects,
    }
    return render(request, 'accounts/user_edit.html', context)


@login_required
def user_toggle_active(request, pk):
    """Toggle user active status"""
    if not (request.user.is_super_admin() or request.user.is_mandate_owner()):
        messages.error(request, 'You do not have permission.')
        return redirect('dashboard')
    
    user = get_object_or_404(User, pk=pk)
    
    # Mandate Owner can only toggle their employees
    if request.user.is_mandate_owner() and user.mandate_owner != request.user:
        messages.error(request, 'You can only manage your employees.')
        return redirect('accounts:user_list')
    
    user.is_active = not user.is_active
    user.save()
    
    status = 'activated' if user.is_active else 'deactivated'
    messages.success(request, f'User {user.username} {status} successfully!')
    return redirect('accounts:user_list')
