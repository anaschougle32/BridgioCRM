from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from datetime import timedelta
from django.template.loader import render_to_string
try:
    import openpyxl
except ImportError:
    openpyxl = None
import csv
import io
from .models import Lead, OtpLog, CallLog, FollowUpReminder, DailyAssignmentQuota
from projects.models import Project
from accounts.models import User
from .utils import (
    generate_otp, hash_otp, verify_otp, get_sms_deep_link,
    get_phone_display, get_tel_link, get_whatsapp_link, get_whatsapp_templates
)


@login_required
def lead_list(request):
    """List all leads with filtering"""
    leads = Lead.objects.filter(is_archived=False)
    
    # Role-based filtering
    # Super Admin sees all leads
    if request.user.is_super_admin() or (request.user.is_superuser and request.user.is_staff):
        pass  # No filtering for super admin
    elif request.user.is_telecaller() or request.user.is_closing_manager():
        # Telecallers and Closing Managers see only their assigned leads
        leads = leads.filter(assigned_to=request.user)
    elif request.user.is_site_head():
        # Site head sees leads for their projects
        leads = leads.filter(project__site_head=request.user)
    elif request.user.is_mandate_owner():
        # Mandate owner sees leads for their projects
        leads = leads.filter(project__mandate_owner=request.user)
    elif request.user.is_sourcing_manager():
        # Sourcing managers see leads they created or are assigned to
        leads = leads.filter(Q(created_by=request.user) | Q(assigned_to=request.user))
    
    # Search
    search = request.GET.get('search', '')
    if search:
        leads = leads.filter(
            Q(name__icontains=search) |
            Q(phone__icontains=search) |
            Q(email__icontains=search)
        )
    
    # Filter by status
    status = request.GET.get('status', '')
    if status:
        leads = leads.filter(status=status)
    
    # Filter by project
    project_id = request.GET.get('project', '')
    if project_id:
        leads = leads.filter(project_id=project_id)
    
    # Filter by pretag status
    pretag_status = request.GET.get('pretag_status', '')
    if pretag_status:
        leads = leads.filter(pretag_status=pretag_status)
    
    # Order by created date
    leads = leads.order_by('-created_at')
    
    # Get reminders and callbacks for notification badges
    from datetime import datetime, timedelta
    now = timezone.now()
    today = now.date()
    
    # Prefetch reminders and call logs for each lead
    leads = leads.prefetch_related('reminders', 'call_logs')
    
    # Pagination
    paginator = Paginator(leads, 25)
    page = request.GET.get('page', 1)
    leads_page = paginator.get_page(page)
    
    # Get reminders and callbacks for each lead in the page
    lead_notifications = {}
    for lead in leads_page:
        # Get upcoming reminders (today and future)
        upcoming_reminders = lead.reminders.filter(
            is_completed=False,
            reminder_date__gte=now
        ).order_by('reminder_date')[:3]
        
        # Get overdue reminders
        overdue_reminders = lead.reminders.filter(
            is_completed=False,
            reminder_date__lt=now
        ).count()
        
        # Get today's callbacks
        today_callbacks = lead.reminders.filter(
            is_completed=False,
            reminder_type='callback',
            reminder_date__date=today
        ).count()
        
        # Get tel link for phone button
        tel_link = get_tel_link(lead.phone)
        
        lead_notifications[lead.id] = {
            'upcoming_reminders': list(upcoming_reminders),
            'overdue_count': overdue_reminders,
            'today_callbacks': today_callbacks,
            'tel_link': tel_link,
        }
    
    context = {
        'leads': leads_page,
        'projects': Project.objects.filter(is_active=True),
        'status_choices': Lead.LEAD_STATUS_CHOICES,
        'pretag_status_choices': Lead.PRETAG_STATUS_CHOICES,
        'search': search,
        'selected_status': status,
        'selected_project': project_id,
        'selected_pretag_status': pretag_status,
        'lead_notifications': lead_notifications,
        'now': now,
        'today': today,
    }
    return render(request, 'leads/list.html', context)


@login_required
def lead_create(request):
    """Create new visit (Available to all user types) - Multi-step form with OTP"""
    if request.method == 'POST':
        step = request.POST.get('step', '1')
        
        if step == '1':
            # Step 1: Client Information - Store in session
            request.session['new_visit_data'] = {
                'name': request.POST.get('name'),
                'phone': request.POST.get('phone'),
                'email': request.POST.get('email', ''),
                'age': request.POST.get('age', ''),
                'gender': request.POST.get('gender', ''),
                'locality': request.POST.get('locality', ''),
                'current_residence': request.POST.get('current_residence', ''),
                'occupation': request.POST.get('occupation', ''),
                'company_name': request.POST.get('company_name', ''),
                'designation': request.POST.get('designation', ''),
            }
            request.session.modified = True
            return JsonResponse({'success': True, 'step': 2})
        
        elif step == '2':
            # Step 2: OTP Verification
            otp_code = request.POST.get('otp', '').strip()
            phone = request.session.get('new_visit_data', {}).get('phone', '')
            
            if not phone:
                return JsonResponse({'success': False, 'error': 'Phone number not found. Please start over.'}, status=400)
            
            # Check if OTP was sent
            if 'new_visit_otp' not in request.session:
                return JsonResponse({'success': False, 'error': 'Please send OTP first.'}, status=400)
            
            # Verify OTP
            stored_otp = request.session.get('new_visit_otp', {})
            if stored_otp.get('code') == otp_code and stored_otp.get('phone') == phone:
                # OTP verified
                request.session['new_visit_otp_verified'] = True
                request.session.modified = True
                return JsonResponse({'success': True, 'step': 3})
            else:
                return JsonResponse({'success': False, 'error': 'Invalid OTP. Please try again.'}, status=400)
        
        elif step == '3':
            # Step 3: Requirements - Store in session (including project_id for OTP resend)
            if not request.session.get('new_visit_otp_verified'):
                return JsonResponse({'success': False, 'error': 'OTP verification required. Please verify OTP first.'}, status=400)
            
            visit_data = request.session.get('new_visit_data', {})
            project_id = request.POST.get('project')
            if not project_id:
                return JsonResponse({'success': False, 'error': 'Project is required.'}, status=400)
            
            visit_data.update({
                'project': project_id,
                'project_id': project_id,  # Store separately for OTP message
                'budget': request.POST.get('budget', ''),
                'purpose': request.POST.get('purpose', ''),
                'visit_type': request.POST.get('visit_type', ''),
                'is_first_visit': request.POST.get('is_first_visit', 'true'),
                'how_did_you_hear': request.POST.get('how_did_you_hear', ''),
            })
            request.session['new_visit_data'] = visit_data
            request.session.modified = True
            return JsonResponse({'success': True, 'step': 4})
        
        elif step == '4':
            # Step 4: CP (Optional) - Create lead
            if not request.session.get('new_visit_otp_verified'):
                return JsonResponse({'success': False, 'error': 'OTP verification required. Please verify OTP first.'}, status=400)
            
            try:
                visit_data = request.session.get('new_visit_data', {})
                project_id = visit_data.get('project')
                
                if not project_id:
                    return JsonResponse({'success': False, 'error': 'Project is required.'}, status=400)
                
                project = Project.objects.get(id=project_id, is_active=True)
                
                # Create lead
                lead = Lead.objects.create(
                    name=visit_data.get('name'),
                    phone=visit_data.get('phone'),
                    email=visit_data.get('email', ''),
                    age=int(visit_data.get('age')) if visit_data.get('age') else None,
                    gender=visit_data.get('gender', ''),
                    locality=visit_data.get('locality', ''),
                    current_residence=visit_data.get('current_residence', ''),
                    occupation=visit_data.get('occupation', ''),
                    company_name=visit_data.get('company_name', ''),
                    designation=visit_data.get('designation', ''),
                    project=project,
                    budget=float(visit_data.get('budget')) if visit_data.get('budget') else None,
                    purpose=visit_data.get('purpose', ''),
                    visit_type=visit_data.get('visit_type', ''),
                    is_first_visit=visit_data.get('is_first_visit', 'true') == 'true',
                    how_did_you_hear=visit_data.get('how_did_you_hear', ''),
                    cp_firm_name=request.POST.get('cp_firm_name', ''),
                    cp_name=request.POST.get('cp_name', ''),
                    cp_phone=request.POST.get('cp_phone', ''),
                    cp_rera_number=request.POST.get('cp_rera_number', ''),
                    is_pretagged=False,
                    phone_verified=True,  # OTP verified
                    status='new',
                    created_by=request.user,
                )
                
                # Clear session data
                request.session.pop('new_visit_data', None)
                request.session.pop('new_visit_otp', None)
                request.session.pop('new_visit_otp_verified', None)
                
                # Return JSON response with proper redirect URL
                redirect_url = reverse('leads:detail', kwargs={'pk': lead.id})
                
                return JsonResponse({
                    'success': True,
                    'message': f'New visit created successfully! Lead #{lead.id} has been added.',
                    'redirect_url': redirect_url
                })
                
            except Project.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Invalid project selected.'}, status=400)
            except ValueError as e:
                return JsonResponse({'success': False, 'error': f'Invalid data: {str(e)}'}, status=400)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error creating new visit: {str(e)}", exc_info=True)
                return JsonResponse({'success': False, 'error': f'Error creating new visit: {str(e)}'}, status=500)
    
    # Handle OTP sending
    if request.method == 'POST' and request.POST.get('action') == 'send_otp':
        phone = request.POST.get('phone', '')
        if not phone:
            return JsonResponse({'success': False, 'error': 'Phone number is required.'}, status=400)
        
        # Get project name from POST data or session
        project_name = None
        project_id = request.POST.get('project_id') or request.session.get('new_visit_data', {}).get('project_id')
        if project_id:
            try:
                project = Project.objects.get(id=project_id, is_active=True)
                project_name = project.name
                # Store in session for future use
                if 'new_visit_data' not in request.session:
                    request.session['new_visit_data'] = {}
                request.session['new_visit_data']['project_id'] = project_id
                request.session.modified = True
            except (Project.DoesNotExist, ValueError):
                pass
        
        # Generate OTP
        otp_code = generate_otp()
        whatsapp_link = get_sms_deep_link(phone, otp_code, project_name)  # Function name kept for compatibility, but returns WhatsApp link
        
        # Store OTP in session
        request.session['new_visit_otp'] = {
            'code': otp_code,
            'phone': phone,
            'created_at': timezone.now().isoformat(),
        }
        
        return JsonResponse({
            'success': True,
            'otp_code': otp_code,
            'sms_link': whatsapp_link,  # Keep variable name for template compatibility
        })
    
    context = {
        'projects': Project.objects.filter(is_active=True),
    }
    return render(request, 'leads/create.html', context)


@login_required
def lead_pretag(request):
    """Create pretagged lead (Sourcing Manager only)"""
    if not request.user.is_sourcing_manager():
        messages.error(request, 'Only Sourcing Managers can create pretagged leads.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        try:
            # Get primary project (first selected)
            project_ids = request.POST.getlist('projects')
            if not project_ids:
                messages.error(request, 'At least one project is required.')
                return redirect('leads:pretag')
            
            primary_project = Project.objects.get(id=project_ids[0], is_active=True)
            
            # Create lead with pretag flags
            lead = Lead.objects.create(
                # Client Information
                name=request.POST.get('name'),
                phone=request.POST.get('phone'),
                email=request.POST.get('email', ''),
                age=int(request.POST.get('age')) if request.POST.get('age') else None,
                gender=request.POST.get('gender', ''),
                locality=request.POST.get('locality', ''),
                current_residence=request.POST.get('current_residence', ''),
                occupation=request.POST.get('occupation', ''),
                company_name=request.POST.get('company_name', ''),
                designation=request.POST.get('designation', ''),
                
                # Requirement Details
                project=primary_project,  # Primary project
                configuration=None,
                budget=float(request.POST.get('budget')) if request.POST.get('budget') else None,
                purpose=request.POST.get('purpose', ''),
                visit_type=request.POST.get('visit_type', ''),
                is_first_visit=request.POST.get('is_first_visit', 'true') == 'true',
                how_did_you_hear=request.POST.get('how_did_you_hear', ''),
                
                # CP Information (Mandatory for Pretag)
                cp_firm_name=request.POST.get('cp_firm_name', ''),
                cp_name=request.POST.get('cp_name', ''),
                cp_phone=request.POST.get('cp_phone', ''),
                cp_rera_number=request.POST.get('cp_rera_number', ''),
                
                # Pretagging Flags
                is_pretagged=True,
                pretag_status='pending_verification',
                phone_verified=False,
                
                # Status
                status='new',
                
                # Creator
                created_by=request.user,
            )
            
            # If multiple projects selected, create additional leads for universal tagging
            if len(project_ids) > 1:
                for project_id in project_ids[1:]:
                    try:
                        additional_project = Project.objects.get(id=project_id, is_active=True)
                        Lead.objects.create(
                            name=lead.name,
                            phone=lead.phone,
                            email=lead.email,
                            age=lead.age,
                            gender=lead.gender,
                            locality=lead.locality,
                            current_residence=lead.current_residence,
                            occupation=lead.occupation,
                            company_name=lead.company_name,
                            designation=lead.designation,
                            project=additional_project,
                            budget=lead.budget,
                            purpose=lead.purpose,
                            visit_type=lead.visit_type,
                            is_first_visit=lead.is_first_visit,
                            how_did_you_hear=lead.how_did_you_hear,
                            cp_firm_name=lead.cp_firm_name,
                            cp_name=lead.cp_name,
                            cp_phone=lead.cp_phone,
                            cp_rera_number=lead.cp_rera_number,
                            is_pretagged=True,
                            pretag_status='pending_verification',
                            phone_verified=False,
                            status='new',
                            created_by=request.user,
                        )
                    except Project.DoesNotExist:
                        continue
            
            messages.success(request, f'Pretagged lead created successfully! Lead #{lead.id} is pending OTP verification by Closing Manager.')
            return redirect('leads:detail', pk=lead.id)
            
        except Project.DoesNotExist:
            messages.error(request, 'Invalid project selected.')
        except Exception as e:
            messages.error(request, f'Error creating pretagged lead: {str(e)}')
    
    context = {
        'projects': Project.objects.filter(is_active=True),
    }
    return render(request, 'leads/pretag.html', context)


@login_required
def lead_detail(request, pk):
    """Lead detail view"""
    lead = get_object_or_404(Lead, pk=pk, is_archived=False)
    
    # Permission check
    if request.user.is_telecaller() or request.user.is_closing_manager():
        if lead.assigned_to != request.user:
            messages.error(request, 'You do not have permission to view this lead.')
            return redirect('leads:list')
    elif request.user.is_site_head():
        if lead.project.site_head != request.user:
            messages.error(request, 'You do not have permission to view this lead.')
            return redirect('leads:list')
    elif request.user.is_mandate_owner():
        if lead.project.mandate_owner != request.user:
            messages.error(request, 'You do not have permission to view this lead.')
            return redirect('leads:list')
    elif request.user.is_sourcing_manager():
        if lead.created_by != request.user and lead.assigned_to != request.user:
            messages.error(request, 'You do not have permission to view this lead.')
            return redirect('leads:list')
    
    # Get latest OTP log for this lead
    latest_otp = lead.otp_logs.filter(is_verified=False).order_by('-created_at').first()
    
    # Get call logs
    call_logs = lead.call_logs.all()[:10]  # Last 10 calls
    
    # Get reminders
    reminders = lead.reminders.filter(is_completed=False).order_by('reminder_date')[:5]
    
    # Get WhatsApp templates
    whatsapp_templates = get_whatsapp_templates()
    
    context = {
        'lead': lead,
        'latest_otp': latest_otp,
        'now': timezone.now(),
        'call_logs': call_logs,
        'reminders': reminders,
        'whatsapp_templates': whatsapp_templates,
        'phone_display': get_phone_display(lead.phone),
        'tel_link': get_tel_link(lead.phone),
    }
    return render(request, 'leads/detail.html', context)


@login_required
def send_otp(request, pk):
    """Send OTP to lead - Available for all user types on all leads"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)
    
    lead = get_object_or_404(Lead, pk=pk, is_archived=False)
    
    # Permission check - user must be assigned to lead or be admin/site head
    if request.user.is_telecaller() or request.user.is_closing_manager():
        if lead.assigned_to != request.user:
            return JsonResponse({'success': False, 'error': 'You can only send OTP for leads assigned to you.'}, status=403)
    
    # Check if there's an active OTP that hasn't expired
    now = timezone.now()
    active_otp = lead.otp_logs.filter(
        is_verified=False,
        expires_at__gt=now,
        attempts__lt=3
    ).order_by('-created_at').first()
    
    if active_otp:
        # Return HTML for the OTP verification form
        whatsapp_link = get_sms_deep_link(lead.phone, active_otp.otp_code, lead.project.name)
        context = {
            'lead': lead,
            'latest_otp': active_otp,
            'now': now,
            'sms_link': whatsapp_link,  # Keep variable name for template compatibility
            'otp_code': active_otp.otp_code,
        }
        html = render_to_string('leads/otp_controls.html', context, request=request)
        # Add JavaScript to open WhatsApp if user wants to resend
        html += f'''
        <script>
            // Option to open WhatsApp again if needed
            const whatsappLink = '{whatsapp_link}';
            if (whatsappLink) {{
                // Store link for manual opening if needed
                window.currentWhatsAppLink = whatsappLink;
            }}
        </script>
        '''
        return HttpResponse(html)
    
    # Generate OTP
    otp_code = generate_otp()
    otp_hash = hash_otp(otp_code)
    
    # Create OTP log
    expires_at = now + timedelta(minutes=5)
    otp_log = OtpLog.objects.create(
        lead=lead,
        otp_hash=otp_hash,
        otp_code=otp_code,  # For display in development only
        expires_at=expires_at,
        sent_by=request.user,
        attempts=0,
        max_attempts=3,
    )
    
    # Generate WhatsApp deep link (opens WhatsApp)
    whatsapp_link = get_sms_deep_link(lead.phone, otp_code, lead.project.name)
    
    # Return HTML for the OTP verification form with WhatsApp link
    # Include JavaScript to automatically open WhatsApp
    context = {
        'lead': lead,
        'latest_otp': otp_log,
        'now': now,
        'sms_link': whatsapp_link,  # Keep variable name for template compatibility
        'otp_code': otp_code,  # Show OTP for manual entry if WhatsApp doesn't open
    }
    html = render_to_string('leads/otp_controls.html', context, request=request)
    
    # Add JavaScript to automatically open WhatsApp
    html += f'''
    <script>
        // Automatically open WhatsApp when OTP is generated
        (function() {{
            const whatsappLink = '{whatsapp_link}';
            if (whatsappLink) {{
                // Open WhatsApp in new tab/window
                window.open(whatsappLink, '_blank');
            }}
        }})();
    </script>
    '''
    
    # Return HTML directly for htmx
    return HttpResponse(html)


@login_required
def verify_otp(request, pk):
    """Verify OTP - Available for all user types"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)
    
    lead = get_object_or_404(Lead, pk=pk, is_archived=False)
    
    # Permission check - user must be assigned to lead or be admin/site head
    if request.user.is_telecaller() or request.user.is_closing_manager():
        if lead.assigned_to != request.user:
            return JsonResponse({'success': False, 'error': 'You can only verify OTP for leads assigned to you.'}, status=403)
    
    otp_code = request.POST.get('otp', '').strip()
    if not otp_code or len(otp_code) != 6:
        return JsonResponse({'success': False, 'error': 'Invalid OTP format. Please enter a 6-digit code.'}, status=400)
    
    # Get latest unverified OTP
    now = timezone.now()
    otp_log = lead.otp_logs.filter(
        is_verified=False,
        expires_at__gt=now
    ).order_by('-created_at').first()
    
    if not otp_log:
        return JsonResponse({'success': False, 'error': 'No active OTP found. Please send a new OTP.'}, status=400)
    
    # Check attempts
    if otp_log.attempts >= otp_log.max_attempts:
        return JsonResponse({
            'success': False, 
            'error': f'Maximum attempts ({otp_log.max_attempts}) exceeded. Please send a new OTP.'
        }, status=400)
    
    # Verify OTP
    is_valid = verify_otp(otp_code, otp_log.otp_hash)
    
    otp_log.attempts += 1
    
    if is_valid:
        # Mark OTP as verified
        otp_log.is_verified = True
        otp_log.verified_at = now
        otp_log.save()
        
        # Update lead
        lead.phone_verified = True
        if lead.is_pretagged:
            lead.pretag_status = 'verified'
        lead.save()
        
        # Create audit log
        from accounts.models import AuditLog
        AuditLog.objects.create(
            user=request.user,
            action='otp_verified',
            model_name='Lead',
            object_id=lead.id,
            details=f'OTP verified for lead {lead.name} ({lead.phone})',
        )
        
        # Return updated HTML
        lead.refresh_from_db()
        context = {
            'lead': lead,
            'latest_otp': None,
            'now': now,
        }
        html = render_to_string('leads/otp_section.html', context, request=request)
        
        # Return HTML directly for htmx
        return HttpResponse(html)
    else:
        otp_log.save()
        remaining_attempts = otp_log.max_attempts - otp_log.attempts
        
        if remaining_attempts > 0:
            return JsonResponse({
                'success': False,
                'error': f'Invalid OTP. {remaining_attempts} attempt(s) remaining.',
            }, status=400)
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid OTP. Maximum attempts exceeded. Please send a new OTP.',
            }, status=400)


@login_required
def upcoming_visits(request):
    """Upcoming Visits view for Closing Managers - shows pretagged leads"""
    if not request.user.is_closing_manager():
        messages.error(request, 'Only Closing Managers can view upcoming visits.')
        return redirect('dashboard')
    
    # Get pretagged leads that are pending verification
    leads = Lead.objects.filter(
        is_pretagged=True,
        pretag_status='pending_verification',
        assigned_to=request.user
    ).order_by('created_at')
    
    # Search
    search = request.GET.get('search', '')
    if search:
        leads = leads.filter(
            Q(name__icontains=search) |
            Q(phone__icontains=search) |
            Q(project__name__icontains=search)
        )
    
    # Filter by project
    project_id = request.GET.get('project', '')
    if project_id:
        leads = leads.filter(project_id=project_id)
    
    # Pagination
    paginator = Paginator(leads, 25)
    page = request.GET.get('page', 1)
    leads_page = paginator.get_page(page)
    
    context = {
        'leads': leads_page,
        'projects': Project.objects.filter(is_active=True),
        'search': search,
        'selected_project': project_id,
    }
    return render(request, 'leads/upcoming_visits.html', context)


@login_required
def log_call(request, pk):
    """Log a call outcome for a lead"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)
    
    lead = get_object_or_404(Lead, pk=pk, is_archived=False)
    
    # Permission check
    if request.user.is_telecaller() or request.user.is_closing_manager():
        if lead.assigned_to != request.user:
            return JsonResponse({'success': False, 'error': 'You do not have permission to log calls for this lead.'}, status=403)
    
    outcome = request.POST.get('outcome')
    notes = request.POST.get('notes', '')
    next_action = request.POST.get('next_action', '')
    
    if outcome not in dict(CallLog.OUTCOME_CHOICES):
        return JsonResponse({'success': False, 'error': 'Invalid call outcome.'}, status=400)
    
    # Create call log
    call_log = CallLog.objects.create(
        lead=lead,
        called_by=request.user,
        outcome=outcome,
        notes=notes,
    )
    
    # Handle next action
    if next_action == 'callback':
        # Create reminder for callback
        reminder_date_str = request.POST.get('reminder_date', '')
        if reminder_date_str:
            try:
                from datetime import datetime
                reminder_date = datetime.strptime(reminder_date_str, '%Y-%m-%dT%H:%M')
                FollowUpReminder.objects.create(
                    lead=lead,
                    reminder_date=reminder_date,
                    notes=f'Callback reminder: {notes}',
                    created_by=request.user,
                )
            except ValueError:
                pass
    elif next_action == 'schedule_visit':
        lead.status = 'visit_scheduled'
        lead.save()
    elif next_action == 'not_interested':
        lead.status = 'lost'
        lead.save()
    
    # Update lead status based on outcome
    if outcome == 'connected':
        if lead.status == 'new':
            lead.status = 'contacted'
            lead.save()
    
    # Return HTML to close modal and show success
    return HttpResponse('<div class="p-3 bg-green-50 text-green-800 rounded-lg mb-4">Call logged successfully!</div><script>setTimeout(() => { const modal = document.getElementById("log-call-modal"); if (modal) modal.classList.add("hidden"); location.reload(); }, 1500);</script>')


@login_required
def create_reminder(request, pk):
    """Create a reminder for a lead"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)
    
    lead = get_object_or_404(Lead, pk=pk, is_archived=False)
    
    reminder_date_str = request.POST.get('reminder_date', '')
    reminder_type = request.POST.get('reminder_type', 'callback')
    notes = request.POST.get('notes', '')
    
    if not reminder_date_str:
        return JsonResponse({'success': False, 'error': 'Reminder date is required.'}, status=400)
    
    try:
        from datetime import datetime
        reminder_date = datetime.strptime(reminder_date_str, '%Y-%m-%dT%H:%M')
        
        reminder = FollowUpReminder.objects.create(
            lead=lead,
            reminder_date=reminder_date,
            reminder_type=reminder_type,
            notes=notes,
            created_by=request.user,
        )
        
        # Return HTML to close modal and show success
        return HttpResponse('<div class="p-3 bg-green-50 text-green-800 rounded-lg mb-4">Reminder created successfully!</div><script>setTimeout(() => { document.getElementById("reminder-modal").classList.add("hidden"); location.reload(); }, 1500);</script>')
    
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid date format.'}, status=400)


@login_required
def update_status(request, pk):
    """Update lead status"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)
    
    lead = get_object_or_404(Lead, pk=pk, is_archived=False)
    
    # Permission check
    if request.user.is_telecaller() or request.user.is_closing_manager():
        if lead.assigned_to != request.user:
            return JsonResponse({'success': False, 'error': 'You do not have permission to update this lead.'}, status=403)
    
    new_status = request.POST.get('status', '')
    if new_status not in dict(Lead.LEAD_STATUS_CHOICES):
        return JsonResponse({'success': False, 'error': 'Invalid status.'}, status=400)
    
    lead.status = new_status
    lead.save()
    
    # Create audit log
    from accounts.models import AuditLog
    AuditLog.objects.create(
        user=request.user,
        action='status_updated',
        model_name='Lead',
        object_id=lead.id,
        details=f'Lead status changed to {lead.get_status_display()}',
    )
    
    messages.success(request, f'Lead status updated to {lead.get_status_display()}.')
    return redirect('leads:list')


@login_required
def complete_reminder(request, pk, reminder_id):
    """Mark a reminder as completed"""
    reminder = get_object_or_404(FollowUpReminder, pk=reminder_id, lead_id=pk)
    reminder.is_completed = True
    reminder.completed_at = timezone.now()
    reminder.save()
    messages.success(request, 'Reminder marked as completed.')
    return redirect('leads:detail', pk=pk)


@login_required
def update_notes(request, pk):
    """Update lead notes"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)
    
    lead = get_object_or_404(Lead, pk=pk, is_archived=False)
    
    # Permission check
    if request.user.is_telecaller() or request.user.is_closing_manager():
        if lead.assigned_to != request.user:
            return JsonResponse({'success': False, 'error': 'You do not have permission to update notes for this lead.'}, status=403)
    
    notes = request.POST.get('notes', '').strip()
    lead.notes = notes
    lead.save()
    
    # Create audit log
    from accounts.models import AuditLog
    AuditLog.objects.create(
        user=request.user,
        action='notes_updated',
        model_name='Lead',
        object_id=lead.id,
        details=f'Notes updated for lead {lead.name}',
    )
    
    # Return updated HTML
    html = f'''
    <div id="notes-section">
        {'<div class="p-4 bg-gray-50 rounded-lg border border-gray-200 mb-3"><p class="text-sm text-gray-700 whitespace-pre-wrap">' + notes + '</p></div>' if notes else '<p class="text-sm text-gray-500 mb-3">No notes added yet.</p>'}
        <button onclick="document.getElementById(\'notes-modal\').classList.remove(\'hidden\')" 
                class="px-4 py-2 bg-olive-primary text-white rounded-lg hover:bg-olive-secondary transition text-sm">
            {'Edit Notes' if notes else 'Add Notes'}
        </button>
    </div>
    <script>
        setTimeout(() => {{
            document.getElementById('notes-modal').classList.add('hidden');
        }}, 1500);
    </script>
    '''
    return HttpResponse(html)


@login_required
def whatsapp(request, pk):
    """Generate WhatsApp link with template"""
    lead = get_object_or_404(Lead, pk=pk, is_archived=False)
    
    template_key = request.GET.get('template', 'intro')
    templates = get_whatsapp_templates()
    
    message = templates.get(template_key, templates['intro'])
    
    # Replace placeholders if needed
    if template_key == 'booking_confirmation':
        # Try to get booking ID if exists
        try:
            booking = lead.booking
            if booking:
                message = message.format(booking_id=booking.id, name=lead.name, project_name=lead.project.name)
            else:
                message = message.format(booking_id='N/A', name=lead.name, project_name=lead.project.name)
        except:
            message = message.format(booking_id='N/A', name=lead.name, project_name=lead.project.name)
    else:
        # Replace placeholders for other templates
        message = message.format(name=lead.name, project_name=lead.project.name)
    
    whatsapp_link = get_whatsapp_link(lead.phone, message)
    
    return redirect(whatsapp_link)


@login_required
def lead_assign(request):
    """Assign leads to employees (Site Head only)"""
    if not request.user.is_site_head():
        messages.error(request, 'Only Site Heads can assign leads.')
        return redirect('dashboard')
    
    # Get projects for this site head
    projects = Project.objects.filter(site_head=request.user, is_active=True)
    
    if request.method == 'POST':
        try:
            project_id = request.POST.get('project')
            if not project_id:
                messages.error(request, 'Please select a project.')
                return redirect('leads:assign')
            
            project = get_object_or_404(Project, pk=project_id, site_head=request.user)
            
            # Get unassigned leads for this project
            unassigned_leads = Lead.objects.filter(
                project=project,
                assigned_to__isnull=True,
                is_archived=False
            ).order_by('created_at')
            
            # Get assignment data
            assignments = []
            for key, value in request.POST.items():
                if key.startswith('employee_') and value:
                    employee_id = key.replace('employee_', '')
                    num_leads = int(value)
                    if num_leads > 0:
                        assignments.append({
                            'employee_id': employee_id,
                            'num_leads': num_leads
                        })
            
            if not assignments:
                messages.error(request, 'Please assign at least one lead to an employee.')
                return redirect('leads:assign')
            
            # Get employees
            employees = User.objects.filter(
                Q(role='closing_manager') | Q(role='telecaller') | Q(role='sourcing_manager'),
                mandate_owner=request.user.mandate_owner
            )
            
            # Assign leads using round-robin
            assigned_count = 0
            employee_index = 0
            
            for assignment in assignments:
                employee = get_object_or_404(employees, pk=assignment['employee_id'])
                num_leads = assignment['num_leads']
                
                # Get leads to assign
                leads_to_assign = list(unassigned_leads[assigned_count:assigned_count + num_leads])
                
                for lead in leads_to_assign:
                    lead.assigned_to = employee
                    lead.assigned_by = request.user
                    lead.assigned_at = timezone.now()
                    lead.save()
                    assigned_count += 1
                    
                    # Create audit log
                    from accounts.models import AuditLog
                    AuditLog.objects.create(
                        user=request.user,
                        action='lead_assigned',
                        model_name='Lead',
                        object_id=lead.id,
                        details=f'Lead {lead.name} assigned to {employee.username}',
                    )
            
            messages.success(request, f'Successfully assigned {assigned_count} lead(s) to employees.')
            return redirect('leads:list')
            
        except Exception as e:
            messages.error(request, f'Error assigning leads: {str(e)}')
    
    # Get projects with unassigned leads count
    projects_with_counts = []
    for project in projects:
        unassigned_count = Lead.objects.filter(
            project=project,
            assigned_to__isnull=True,
            is_archived=False
        ).count()
        projects_with_counts.append({
            'project': project,
            'unassigned_count': unassigned_count
        })
    
    # Get employees
    employees = User.objects.filter(
        Q(role='closing_manager') | Q(role='telecaller') | Q(role='sourcing_manager'),
        mandate_owner=request.user.mandate_owner,
        is_active=True
    ).order_by('username')
    
    context = {
        'projects': projects_with_counts,
        'employees': employees,
    }
    return render(request, 'leads/assign.html', context)


@login_required
def lead_upload(request):
    """Upload leads via Excel/CSV (Admin and Site Head only)"""
    if not (request.user.is_super_admin() or request.user.is_site_head()):
        messages.error(request, 'Only Admins and Site Heads can upload leads.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        try:
            project_id = request.POST.get('project')
            if not project_id:
                messages.error(request, 'Please select a project.')
                return redirect('leads:upload')
            
            project = get_object_or_404(Project, pk=project_id, is_active=True)
            
            # Permission check for Site Head
            if request.user.is_site_head() and project.site_head != request.user:
                messages.error(request, 'You can only upload leads for your assigned projects.')
                return redirect('leads:upload')
            
            # Get file
            uploaded_file = request.FILES.get('file')
            if not uploaded_file:
                messages.error(request, 'Please select a file to upload.')
                return redirect('leads:upload')
            
            # Check file extension
            file_name = uploaded_file.name.lower()
            if not (file_name.endswith('.xlsx') or file_name.endswith('.xls') or file_name.endswith('.csv')):
                messages.error(request, 'Please upload an Excel (.xlsx, .xls) or CSV file.')
                return redirect('leads:upload')
            
            # Process file
            leads_created = 0
            errors = []
            
            if file_name.endswith('.csv'):
                # Process CSV
                decoded_file = uploaded_file.read().decode('utf-8')
                io_string = io.StringIO(decoded_file)
                reader = csv.DictReader(io_string)
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Required fields
                        name = row.get('Name', '').strip()
                        phone = row.get('Phone', '').strip()
                        
                        if not name or not phone:
                            errors.append(f"Row {row_num}: Name and Phone are required")
                            continue
                        
                        # Check for duplicate phone
                        if Lead.objects.filter(phone=phone, project=project, is_archived=False).exists():
                            errors.append(f"Row {row_num}: Lead with phone {phone} already exists")
                            continue
                        
                        # Create lead
                        Lead.objects.create(
                            name=name,
                            phone=phone,
                            email=row.get('Email', '').strip(),
                            age=int(row.get('Age')) if row.get('Age') else None,
                            gender=row.get('Gender', '').strip(),
                            locality=row.get('Locality', '').strip(),
                            current_residence=row.get('Current Residence', '').strip(),
                            occupation=row.get('Occupation', '').strip(),
                            company_name=row.get('Company Name', '').strip(),
                            designation=row.get('Designation', '').strip(),
                            project=project,
                            budget=float(row.get('Budget')) if row.get('Budget') else None,
                            purpose=row.get('Purpose', '').strip(),
                            visit_type=row.get('Visit Type', '').strip(),
                            is_first_visit=row.get('First Visit', 'true').lower() == 'true',
                            how_did_you_hear=row.get('How did you hear', '').strip(),
                            cp_firm_name=row.get('CP Firm Name', '').strip(),
                            cp_name=row.get('CP Name', '').strip(),
                            cp_phone=row.get('CP Phone', '').strip(),
                            cp_rera_number=row.get('CP RERA Number', '').strip(),
                            is_pretagged=False,
                            phone_verified=False,
                            status='new',
                            created_by=request.user,
                        )
                        leads_created += 1
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
            else:
                # Process Excel
                if openpyxl is None:
                    messages.error(request, 'openpyxl is not installed. Please install it: pip install openpyxl')
                    return redirect('leads:upload')
                workbook = openpyxl.load_workbook(uploaded_file)
                worksheet = workbook.active
                
                # Get header row
                headers = [cell.value for cell in worksheet[1]]
                header_map = {str(h).strip(): idx for idx, h in enumerate(headers) if h}
                
                for row_num, row in enumerate(worksheet.iter_rows(min_row=2, values_only=False), start=2):
                    try:
                        # Get values by header
                        def get_value(header_name):
                            if header_name in header_map:
                                cell = row[header_map[header_name]]
                                return str(cell.value).strip() if cell.value else ''
                            return ''
                        
                        name = get_value('Name')
                        phone = get_value('Phone')
                        
                        if not name or not phone:
                            errors.append(f"Row {row_num}: Name and Phone are required")
                            continue
                        
                        # Check for duplicate phone
                        if Lead.objects.filter(phone=phone, project=project, is_archived=False).exists():
                            errors.append(f"Row {row_num}: Lead with phone {phone} already exists")
                            continue
                        
                        # Create lead
                        Lead.objects.create(
                            name=name,
                            phone=phone,
                            email=get_value('Email'),
                            age=int(get_value('Age')) if get_value('Age') else None,
                            gender=get_value('Gender'),
                            locality=get_value('Locality'),
                            current_residence=get_value('Current Residence'),
                            occupation=get_value('Occupation'),
                            company_name=get_value('Company Name'),
                            designation=get_value('Designation'),
                            project=project,
                            budget=float(get_value('Budget')) if get_value('Budget') else None,
                            purpose=get_value('Purpose'),
                            visit_type=get_value('Visit Type'),
                            is_first_visit=get_value('First Visit').lower() == 'true',
                            how_did_you_hear=get_value('How did you hear'),
                            cp_firm_name=get_value('CP Firm Name'),
                            cp_name=get_value('CP Name'),
                            cp_phone=get_value('CP Phone'),
                            cp_rera_number=get_value('CP RERA Number'),
                            is_pretagged=False,
                            phone_verified=False,
                            status='new',
                            created_by=request.user,
                        )
                        leads_created += 1
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
            
            if leads_created > 0:
                messages.success(request, f'Successfully uploaded {leads_created} lead(s)!')
            if errors:
                error_msg = f"Errors: {'; '.join(errors[:10])}"  # Show first 10 errors
                if len(errors) > 10:
                    error_msg += f" and {len(errors) - 10} more..."
                messages.warning(request, error_msg)
            
            return redirect('leads:list')
            
        except Exception as e:
            messages.error(request, f'Error uploading file: {str(e)}')
    
    # Get available projects
    if request.user.is_super_admin():
        projects = Project.objects.filter(is_active=True)
    else:  # Site Head
        projects = Project.objects.filter(site_head=request.user, is_active=True)
    
    context = {
        'projects': projects,
    }
    return render(request, 'leads/upload.html', context)


@login_required
def lead_assign_admin(request):
    """Assign leads to employees (Admin and Site Head)"""
    if not (request.user.is_super_admin() or request.user.is_site_head()):
        messages.error(request, 'Only Admins and Site Heads can assign leads.')
        return redirect('dashboard')
    
    # Get projects
    if request.user.is_super_admin():
        projects = Project.objects.filter(is_active=True)
    else:  # Site Head
        projects = Project.objects.filter(site_head=request.user, is_active=True)
    
    if request.method == 'POST':
        try:
            project_id = request.POST.get('project')
            if not project_id:
                messages.error(request, 'Please select a project.')
                return redirect('leads:assign_admin')
            
            project = get_object_or_404(Project, pk=project_id, is_active=True)
            
            # Permission check for Site Head
            if request.user.is_site_head() and project.site_head != request.user:
                messages.error(request, 'You can only assign leads for your assigned projects.')
                return redirect('leads:assign_admin')
            
            # Get assignment data - save daily quotas
            for key, value in request.POST.items():
                if key.startswith('quota_') and value:
                    employee_id = key.replace('quota_', '')
                    daily_quota = int(value)
                    if daily_quota > 0:
                        employee = get_object_or_404(User, pk=employee_id)
                        DailyAssignmentQuota.objects.update_or_create(
                            project=project,
                            employee=employee,
                            defaults={
                                'daily_quota': daily_quota,
                                'is_active': True,
                                'created_by': request.user,
                            }
                        )
            
            # Also do immediate assignment if requested
            immediate_assign = request.POST.get('immediate_assign', 'false') == 'true'
            if immediate_assign:
                # Get unassigned leads
                unassigned_leads = Lead.objects.filter(
                    project=project,
                    assigned_to__isnull=True,
                    is_archived=False
                ).order_by('created_at')
                
                # Get quotas
                quotas = DailyAssignmentQuota.objects.filter(
                    project=project,
                    is_active=True
                )
                
                assigned_count = 0
                for quota in quotas:
                    # Get leads to assign
                    leads_to_assign = list(unassigned_leads[assigned_count:assigned_count + quota.daily_quota])
                    for lead in leads_to_assign:
                        lead.assigned_to = quota.employee
                        lead.assigned_by = request.user
                        lead.assigned_at = timezone.now()
                        lead.save()
                        assigned_count += 1
                
                if assigned_count > 0:
                    messages.success(request, f'Immediately assigned {assigned_count} lead(s) and saved daily quotas.')
                else:
                    messages.success(request, 'Daily quotas saved successfully.')
            else:
                messages.success(request, 'Daily quotas saved successfully. Leads will be auto-assigned daily.')
            
            return redirect('leads:list')
            
        except Exception as e:
            messages.error(request, f'Error saving assignment quotas: {str(e)}')
    
    # Get projects with unassigned leads count
    projects_with_counts = []
    for project in projects:
        unassigned_count = Lead.objects.filter(
            project=project,
            assigned_to__isnull=True,
            is_archived=False
        ).count()
        projects_with_counts.append({
            'project': project,
            'unassigned_count': unassigned_count
        })
    
    # Get employees with their existing quotas for selected project
    if request.user.is_super_admin():
        employees = User.objects.filter(
            Q(role='closing_manager') | Q(role='telecaller') | Q(role='sourcing_manager'),
            is_active=True
        ).order_by('username')
    else:  # Site Head
        employees = User.objects.filter(
            Q(role='closing_manager') | Q(role='telecaller') | Q(role='sourcing_manager'),
            mandate_owner=request.user.mandate_owner,
            is_active=True
        ).order_by('username')
    
    # Get existing quotas for each project-employee combination
    project_quotas = {}
    for item in projects_with_counts:
        project_quotas[str(item['project'].id)] = {}
        quotas = DailyAssignmentQuota.objects.filter(
            project=item['project'],
            is_active=True
        )
        for quota in quotas:
            project_quotas[str(item['project'].id)][str(quota.employee.id)] = quota.daily_quota
    
    import json
    context = {
        'projects': projects_with_counts,
        'employees': employees,
        'project_quotas_json': json.dumps(project_quotas),
    }
    return render(request, 'leads/assign_admin.html', context)
