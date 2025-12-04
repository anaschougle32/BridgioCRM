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
    
    def form_valid(self, form):
        """Handle successful login"""
        try:
            return super().form_valid(form)
        except Exception as e:
            # Log error but don't expose it to user
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Login error: {str(e)}", exc_info=True)
            # Return form with error
            return self.form_invalid(form)


@login_required
def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@login_required
def user_list(request):
    """User management - Super Admin, Mandate Owners, and Site Heads"""
    # Super Admin and Mandate Owners see all users
    # Site Heads see only employees assigned to their projects
    if request.user.is_super_admin() or request.user.is_mandate_owner():
        users = User.objects.all()
    elif request.user.is_site_head():
        # Site Head sees only employees assigned to their projects
        site_head_projects = Project.objects.filter(site_head=request.user, is_active=True)
        users = User.objects.filter(
            Q(role='closing_manager') | Q(role='sourcing_manager') | Q(role='telecaller'),
            assigned_projects__in=site_head_projects,
            is_active=True
        ).distinct()
    else:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
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
    
    # Order by created_at to avoid pagination warning
    users = users.order_by('-created_at')
    
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
        try:
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip()
            password = request.POST.get('password', '').strip()
            role = request.POST.get('role', '').strip()
            phone = request.POST.get('phone', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            mandate_owner_id = request.POST.get('mandate_owner', '').strip()
            is_active = request.POST.get('is_active') == 'on'
            
            # Validation
            if not username:
                messages.error(request, 'Username is required.')
                return redirect('accounts:user_create')
            if not email:
                messages.error(request, 'Email is required.')
                return redirect('accounts:user_create')
            if not password:
                messages.error(request, 'Password is required.')
                return redirect('accounts:user_create')
            if not role:
                messages.error(request, 'Role is required.')
                return redirect('accounts:user_create')
            
            # Role restrictions
            if request.user.is_mandate_owner():
                # Mandate owners can only create: site_head, closing_manager, sourcing_manager, telecaller
                allowed_roles = ['site_head', 'closing_manager', 'sourcing_manager', 'telecaller']
                if role not in allowed_roles:
                    messages.error(request, 'You can only create Site Heads, Closing Managers, Sourcing Managers, and Telecallers.')
                    return redirect('accounts:user_create')
                # Force mandate_owner to be the current user
                mandate_owner_id = str(request.user.id)
            
            # Super Admin can create Mandate Owners (mandate owners cannot create other mandate owners)
            if request.user.is_super_admin() and role == 'mandate_owner':
                mandate_owner_id = None
            
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists.')
                return redirect('accounts:user_create')
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists.')
                return redirect('accounts:user_create')
            
            # Create user with basic fields first
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            
            # Set custom fields after creation
            user.role = role
            user.phone = phone if phone else None
            user.is_active = is_active
            if mandate_owner_id:
                try:
                    user.mandate_owner_id = int(mandate_owner_id)
                except (ValueError, TypeError):
                    user.mandate_owner_id = None
            user.save()
            
            # Assign projects for closing managers, sourcing managers, and telecallers
            if role in ['closing_manager', 'sourcing_manager', 'telecaller']:
                project_ids = request.POST.getlist('assigned_projects')
                if project_ids:
                    projects = Project.objects.filter(id__in=project_ids, is_active=True)
                    user.assigned_projects.set(projects)
            
            messages.success(request, f'User {user.username} created successfully!')
            return redirect('accounts:user_list')
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creating user: {str(e)}", exc_info=True)
            messages.error(request, f'Error creating user: {str(e)}')
            return redirect('accounts:user_create')
    
    # Get mandate owners for dropdown (Super Admin and Mandate Owners)
    mandate_owners = None
    if request.user.is_super_admin() or request.user.is_mandate_owner():
        mandate_owners = User.objects.filter(role='mandate_owner', is_active=True)
    
    # Determine allowed roles - Mandate Owners have same permissions as Super Admin
    if request.user.is_super_admin() or request.user.is_mandate_owner():
        allowed_roles = User.ROLE_CHOICES
    else:
        allowed_roles = [
            ('site_head', 'Site Head'),
            ('closing_manager', 'Closing Manager'),
            ('sourcing_manager', 'Sourcing Manager'),
            ('telecaller', 'Telecaller'),
        ]
    
    # Get projects for telecaller assignment - Mandate Owners see ALL projects
    projects = None
    if request.user.is_super_admin() or request.user.is_mandate_owner():
        projects = Project.objects.filter(is_active=True)
    
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
    
    # Mandate Owners have same permissions as Super Admin - they can edit all users
    
    if request.method == 'POST':
        user.email = request.POST.get('email', user.email)
        user.phone = request.POST.get('phone', '')
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.is_active = request.POST.get('is_active') == 'on'
        
        # Role can be changed by Super Admin and Mandate Owners
        if request.user.is_super_admin() or request.user.is_mandate_owner():
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
        
        # Update project assignments for closing managers, sourcing managers, and telecallers
        if user.role in ['closing_manager', 'sourcing_manager', 'telecaller']:
            project_ids = request.POST.getlist('assigned_projects')
            if project_ids:
                projects = Project.objects.filter(id__in=project_ids, is_active=True)
                user.assigned_projects.set(projects)
            else:
                user.assigned_projects.clear()
        
        user.save()
        messages.success(request, f'User {user.username} updated successfully!')
        return redirect('accounts:user_list')
    
    # Get mandate owners for dropdown (Super Admin and Mandate Owners)
    mandate_owners = None
    if request.user.is_super_admin() or request.user.is_mandate_owner():
        mandate_owners = User.objects.filter(role='mandate_owner', is_active=True)
    
    # Get projects for telecaller assignment - Mandate Owners see ALL projects
    projects = None
    if request.user.is_super_admin() or request.user.is_mandate_owner():
        projects = Project.objects.filter(is_active=True)
    
    # Get user's assigned projects (for closing managers, sourcing managers, and telecallers)
    user_assigned_projects = []
    if user.role in ['closing_manager', 'sourcing_manager', 'telecaller'] and projects:
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
    user = get_object_or_404(User, pk=pk)
    
    # Permission check
    if request.user.is_super_admin() or request.user.is_mandate_owner():
        # Super Admin and Mandate Owners can toggle all users
        pass
    elif request.user.is_site_head():
        # Site Heads can only toggle employees assigned to their projects
        site_head_projects = Project.objects.filter(site_head=request.user, is_active=True)
        if user.role not in ['closing_manager', 'sourcing_manager', 'telecaller'] or not user.assigned_projects.filter(id__in=site_head_projects).exists():
            messages.error(request, 'You can only manage employees assigned to your projects.')
            return redirect('accounts:user_list')
    else:
        messages.error(request, 'You do not have permission.')
        return redirect('dashboard')
    
    user.is_active = not user.is_active
    user.save()
    
    status = 'activated' if user.is_active else 'deactivated'
    messages.success(request, f'User {user.username} {status} successfully!')
    return redirect('accounts:user_list')
