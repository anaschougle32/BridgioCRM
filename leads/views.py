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
    generate_otp, hash_otp, verify_otp as verify_otp_hash, get_sms_deep_link,
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
    """Create new visit (Available to all user types) - Multi-step form WITH OTP
    
    Flow: Client Info → OTP Verification → Requirements → CP Details
    OTP is sent via WhatsApp deep link for cost savings.
    """
    if request.method == 'POST':
        # Handle OTP sending (action='send_otp')
        if request.POST.get('action') == 'send_otp':
            phone = request.POST.get('phone', '').strip()
            if not phone:
                return JsonResponse({'success': False, 'error': 'Phone number is required.'}, status=400)
            
            # Generate OTP
            otp_code = generate_otp()
            otp_hash = hash_otp(otp_code)
            
            # Store OTP in session (temporary, for verification in step 2)
            request.session['new_visit_otp'] = {
                'otp_hash': otp_hash,
                'otp_code': otp_code,  # Store temporarily for WhatsApp link generation
                'phone': phone,
                'created_at': timezone.now().isoformat(),
            }
            request.session.modified = True
            
            # Get project name from session if available (from step 3)
            project_name = None
            visit_data = request.session.get('new_visit_data', {})
            if visit_data.get('project'):
                try:
                    project = Project.objects.get(id=visit_data.get('project'), is_active=True)
                    project_name = project.name
                except Project.DoesNotExist:
                    pass
            
            # Generate WhatsApp deep link
            from .sms_adapter import send_sms
            sms_response = send_sms(phone, otp_code, project_name=project_name)
            
            whatsapp_link = sms_response.get('whatsapp_link', '')
            
            return JsonResponse({
                'success': True,
                'whatsapp_link': whatsapp_link,
                'message': 'OTP sent successfully. WhatsApp will open automatically.'
            })
        
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
            if not otp_code or len(otp_code) != 6:
                return JsonResponse({'success': False, 'error': 'Please enter a valid 6-digit OTP.'}, status=400)
            
            # Get stored OTP from session
            otp_data = request.session.get('new_visit_otp', {})
            if not otp_data:
                return JsonResponse({'success': False, 'error': 'No OTP found. Please send a new OTP.'}, status=400)
            
            # Verify OTP using utility function
            stored_hash = otp_data.get('otp_hash')
            if not stored_hash:
                return JsonResponse({'success': False, 'error': 'Invalid OTP session. Please send a new OTP.'}, status=400)
            
            is_valid = verify_otp_hash(otp_code, stored_hash)
            
            if not is_valid:
                return JsonResponse({'success': False, 'error': 'Invalid OTP. Please try again.'}, status=400)
            
            # OTP verified - mark as verified in session
            request.session['new_visit_otp_verified'] = True
            request.session.modified = True
            
            return JsonResponse({'success': True, 'step': 3})  # Move to Requirements
        
        elif step == '3':
            # Step 3: Requirements
            # Check if OTP was verified
            if not request.session.get('new_visit_otp_verified'):
                return JsonResponse({'success': False, 'error': 'Please verify OTP first.'}, status=400)
            
            visit_data = request.session.get('new_visit_data', {})
            project_id = request.POST.get('project')
            if not project_id:
                return JsonResponse({'success': False, 'error': 'Project is required.'}, status=400)
            
            visit_data.update({
                'project': project_id,
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
            # Check if OTP was verified
            if not request.session.get('new_visit_otp_verified'):
                return JsonResponse({'success': False, 'error': 'Please verify OTP first.'}, status=400)
            try:
                visit_data = request.session.get('new_visit_data', {})
                project_id = visit_data.get('project')
                
                if not project_id:
                    return JsonResponse({'success': False, 'error': 'Project is required.'}, status=400)
                
                project = Project.objects.get(id=project_id, is_active=True)
                
                # Create lead (phone_verified=True since OTP was verified in step 2)
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
                    phone_verified=True,  # OTP was verified in step 2
                    status='visit_completed',  # Visit is completed when created via New Visit form
                    visit_source=request.POST.get('visit_source', 'walkin'),  # Default to walkin, can be changed
                    created_by=request.user,
                )
                
                # Create OTP log entry for audit trail
                otp_data = request.session.get('new_visit_otp', {})
                if otp_data:
                    OtpLog.objects.create(
                        lead=lead,
                        otp_hash=otp_data.get('otp_hash', ''),
                        expires_at=timezone.now() + timedelta(minutes=5),
                        is_verified=True,
                        verified_at=timezone.now(),
                        sent_by=request.user,
                        attempts=1,
                        max_attempts=3,
                    )
                
                # Clear session data
                request.session.pop('new_visit_data', None)
                request.session.pop('new_visit_otp', None)
                request.session.pop('new_visit_otp_verified', None)
                
                # Return JSON response with proper redirect URL
                try:
                    redirect_url = reverse('leads:detail', kwargs={'pk': lead.id})
                    # Ensure redirect_url is a valid string
                    if not redirect_url or redirect_url == 'undefined' or redirect_url == 'null':
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Invalid redirect_url generated: {redirect_url} for lead.id={lead.id}")
                        redirect_url = reverse('leads:list')
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error generating redirect URL: {str(e)}", exc_info=True)
                    redirect_url = reverse('leads:list')
                
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
        
        # If POST but no valid step, return error
        else:
            return JsonResponse({'success': False, 'error': 'Invalid step or request.'}, status=400)
    
    # GET request - show form
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
    """Send OTP to lead - Only Closing Managers, Site Heads, and Super Admins"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)
    
    lead = get_object_or_404(Lead, pk=pk, is_archived=False)
    
    # Permission check - Only Closing Managers, Site Heads, and Super Admins can send OTP
    if not (request.user.is_closing_manager() or request.user.is_site_head() or request.user.is_super_admin()):
        return JsonResponse({'success': False, 'error': 'Only Closing Managers can send OTP.'}, status=403)
    
    # For Closing Managers, ensure they can only send OTP for assigned leads
    if request.user.is_closing_manager() and lead.assigned_to != request.user:
        return JsonResponse({'success': False, 'error': 'You can only send OTP for leads assigned to you.'}, status=403)
    
    # Check if there's an active OTP that hasn't expired
    now = timezone.now()
    active_otp = lead.otp_logs.filter(
        is_verified=False,
        expires_at__gt=now,
        attempts__lt=3
    ).order_by('-created_at').first()
    
    if active_otp:
        # Return HTML for the OTP verification form (no OTP code shown)
        context = {
            'lead': lead,
            'latest_otp': active_otp,
            'now': now,
        }
        html = render_to_string('leads/otp_controls.html', context, request=request)
        return HttpResponse(html)
    
    # Generate OTP
    otp_code = generate_otp()
    otp_hash = hash_otp(otp_code)
    
    # Create OTP log (only hash, no plaintext)
    expires_at = now + timedelta(minutes=5)
    otp_log = OtpLog.objects.create(
        lead=lead,
        otp_hash=otp_hash,
        expires_at=expires_at,
        sent_by=request.user,
        attempts=0,
        max_attempts=3,
    )
    
    # Send SMS via adapter (with WhatsApp fallback)
    from .sms_adapter import send_sms
    # Pass OTP code and project name separately - adapter will format the message
    sms_response = send_sms(lead.phone, otp_code, project_name=lead.project.name)
    
    # Store gateway response
    import json
    otp_log.gateway_response = json.dumps(sms_response)
    otp_log.save()
    
    # Return HTML for the OTP verification form
    context = {
        'lead': lead,
        'latest_otp': otp_log,
        'now': now,
        'sms_response': sms_response,
    }
    html = render_to_string('leads/otp_controls.html', context, request=request)
    
    # If using WhatsApp fallback, add JavaScript to open it
    if sms_response.get('status') == 'fallback' and sms_response.get('whatsapp_link'):
        whatsapp_link = sms_response['whatsapp_link']
        html += f'''
        <script>
            // Automatically open WhatsApp when OTP is generated (fallback mode)
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
    """Verify OTP - Only Closing Managers, Site Heads, and Super Admins"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)
    
    lead = get_object_or_404(Lead, pk=pk, is_archived=False)
    
    # Permission check - Only Closing Managers, Site Heads, and Super Admins can verify OTP
    if not (request.user.is_closing_manager() or request.user.is_site_head() or request.user.is_super_admin()):
        return JsonResponse({'success': False, 'error': 'Only Closing Managers can verify OTP.'}, status=403)
    
    # For Closing Managers, ensure they can only verify OTP for assigned leads
    if request.user.is_closing_manager() and lead.assigned_to != request.user:
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
    
    # Verify OTP using utility function
    is_valid = verify_otp_hash(otp_code, otp_log.otp_hash)
    
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
def visits_list(request):
    """List all visited leads (status='visit_completed') - Super Admin, Mandate Owner, Site Head only"""
    if not (request.user.is_super_admin() or request.user.is_mandate_owner() or request.user.is_site_head()):
        messages.error(request, 'You do not have permission to view visits.')
        return redirect('dashboard')
    
    # Get filter parameters
    project_id = request.GET.get('project', '')
    visit_source = request.GET.get('visit_source', '')
    search_query = request.GET.get('search', '')
    
    # Base queryset - only visited leads
    if request.user.is_super_admin():
        leads_qs = Lead.objects.filter(status='visit_completed', is_archived=False)
    elif request.user.is_mandate_owner():
        leads_qs = Lead.objects.filter(
            project__mandate_owner=request.user,
            status='visit_completed',
            is_archived=False
        )
    else:  # Site Head
        leads_qs = Lead.objects.filter(
            project__site_head=request.user,
            status='visit_completed',
            is_archived=False
        )
    
    # Apply filters
    if project_id:
        leads_qs = leads_qs.filter(project_id=project_id)
    
    if visit_source:
        leads_qs = leads_qs.filter(visit_source=visit_source)
    
    if search_query:
        leads_qs = leads_qs.filter(
            Q(name__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Get projects for filter dropdown
    if request.user.is_super_admin():
        projects = Project.objects.filter(is_active=True).order_by('name')
    elif request.user.is_mandate_owner():
        projects = Project.objects.filter(mandate_owner=request.user, is_active=True).order_by('name')
    else:  # Site Head
        projects = Project.objects.filter(site_head=request.user, is_active=True).order_by('name')
    
    # Calculate metrics
    total_visits = leads_qs.count()
    visits_by_source = leads_qs.values('visit_source').annotate(count=Count('id'))
    visits_by_project = leads_qs.values('project__name').annotate(count=Count('id')).order_by('-count')[:10]
    
    # Pagination
    paginator = Paginator(leads_qs.order_by('-created_at'), 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'leads': page_obj,
        'projects': projects,
        'selected_project': project_id,
        'selected_visit_source': visit_source,
        'search_query': search_query,
        'total_visits': total_visits,
        'visits_by_source': visits_by_source,
        'visits_by_project': visits_by_project,
    }
    return render(request, 'leads/visits_list.html', context)


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
            
            # Use atomic transaction with row locking to prevent race conditions
            from django.db import transaction
            with transaction.atomic():
                assigned_count = 0
                
                for assignment in assignments:
                    employee = get_object_or_404(employees, pk=assignment['employee_id'])
                    num_leads = assignment['num_leads']
                    
                    # Use select_for_update to lock rows and prevent concurrent assignment
                    leads_to_assign = list(
                        Lead.objects.select_for_update(skip_locked=True)
                        .filter(
                            project=project,
                            assigned_to__isnull=True,
                            is_archived=False
                        )
                        .order_by('created_at')[:num_leads]
                    )
                    
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


def _create_column_mapper(headers):
    """
    Create an intelligent column mapper that auto-detects column names.
    Returns a function that can extract values by field name.
    """
    # Normalize headers: strip, lowercase, remove special chars
    normalized_headers = {}
    for idx, header in enumerate(headers):
        if header:
            normalized = str(header).strip().lower().replace('_', ' ').replace('-', ' ')
            normalized_headers[normalized] = idx
    
    # Define field mappings with common variations
    # Note: This is for LEADS upload only. Visits are created separately when leads actually visit.
    field_mappings = {
        'name': ['name', 'full name', 'client name', 'customer name', 'person name', 'contact name', 'lead name'],
        'phone': ['phone', 'mobile', 'contact', 'contact number', 'phone number', 'mobile number', 'cell', 'cell phone', 'whatsapp', 'whatsapp number'],
        'email': ['email', 'e mail', 'email address', 'mail', 'email id'],
        'age': ['age'],
        'gender': ['gender', 'sex'],
        'locality': ['locality', 'area', 'location', 'city', 'address'],
        'current_residence': ['current residence', 'residence', 'residence type', 'living in', 'own rent'],
        'occupation': ['occupation', 'profession', 'job', 'work'],
        'company_name': ['company name', 'company', 'organization', 'org', 'firm name'],
        'designation': ['designation', 'position', 'title', 'role', 'job title'],
        'budget': ['budget', 'price range', 'budget range', 'expected budget', 'investment amount'],
        'purpose': ['purpose', 'requirement', 'need', 'buying purpose'],
        'visit_type': ['visit type', 'visit', 'accompanied by', 'family alone'],
        'is_first_visit': ['first visit', 'is first visit', 'new visit', 'revisit'],
        'how_did_you_hear': ['how did you hear', 'source', 'referral source', 'lead source', 'marketing source'],
        'status': ['status', 'lead status', 'stage', 'current status', 'lead stage'],  # IMPORTANT: Lead Status
        'cp_firm_name': ['cp firm name', 'channel partner firm', 'cp firm', 'partner firm', 'broker firm'],
        'cp_name': ['cp name', 'channel partner name', 'cp', 'partner name', 'broker name'],
        'cp_phone': ['cp phone', 'channel partner phone', 'cp mobile', 'partner phone', 'broker phone'],
        'cp_rera_number': ['cp rera number', 'rera number', 'cp rera', 'rera id', 'rera'],
        'is_pretagged': ['is pretagged', 'pretagged', 'pretag', 'is pretag', 'pretagged lead'],
    }
    
    # Create reverse mapping: field -> column index
    field_to_index = {}
    for field, variations in field_mappings.items():
        for variation in variations:
            if variation in normalized_headers:
                field_to_index[field] = normalized_headers[variation]
                break
    
    def get_value(field_name):
        """Get value for a field by trying all variations"""
        if field_name in field_to_index:
            idx = field_to_index[field_name]
            if idx < len(headers):
                return headers[idx]
        return None
    
    return get_value, field_to_index


@login_required
def upload_analyze(request):
    """Analyze uploaded file and return headers with auto-mapping"""
    if not (request.user.is_super_admin() or request.user.is_site_head()):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)
    
    try:
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return JsonResponse({'success': False, 'error': 'No file provided'}, status=400)
        
        # Store file in session temporarily
        import uuid
        session_id = str(uuid.uuid4())
        
        # Read headers
        file_name = uploaded_file.name.lower()
        headers = []
        
        if file_name.endswith('.csv'):
            decoded_file = uploaded_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            headers = list(reader.fieldnames or [])
            # Store file content in session
            request.session[f'upload_file_{session_id}'] = {
                'name': uploaded_file.name,
                'content': decoded_file,
                'type': 'csv'
            }
        else:
            if openpyxl is None:
                return JsonResponse({'success': False, 'error': 'openpyxl not installed'}, status=500)
            workbook = openpyxl.load_workbook(uploaded_file)
            worksheet = workbook.active
            headers = [str(cell.value).strip() if cell.value else '' for cell in worksheet[1]]
            # Store file in session (we'll need to save it temporarily)
            uploaded_file.seek(0)
            file_content = uploaded_file.read()
            request.session[f'upload_file_{session_id}'] = {
                'name': uploaded_file.name,
                'content': file_content,
                'type': 'excel'
            }
        
        request.session.modified = True
        
        # Auto-detect mapping
        get_value, field_map = _create_column_mapper(headers)
        
        # Convert field_map (index-based) to header-based mapping
        auto_mapping = {}
        for field, col_idx in field_map.items():
            if col_idx < len(headers):
                auto_mapping[headers[col_idx]] = field
        
        return JsonResponse({
            'success': True,
            'session_id': session_id,
            'headers': headers,
            'mapping': auto_mapping
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def upload_preview(request):
    """Preview upload with custom mapping"""
    if not (request.user.is_super_admin() or request.user.is_site_head()):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)
    
    try:
        session_id = request.POST.get('session_id')
        mapping_json = request.POST.get('mapping')
        
        if not session_id or not mapping_json:
            return JsonResponse({'success': False, 'error': 'Missing parameters'}, status=400)
        
        # Get file from session
        file_data = request.session.get(f'upload_file_{session_id}')
        if not file_data:
            return JsonResponse({'success': False, 'error': 'File not found in session'}, status=400)
        
        # Parse mapping
        import json
        mapping = json.loads(mapping_json)
        
        # Count rows and validate
        total_rows = 0
        valid_rows = 0
        errors = 0
        
        if file_data['type'] == 'csv':
            io_string = io.StringIO(file_data['content'])
            reader = csv.DictReader(io_string)
            # Create reverse mapping: field -> header
            field_to_header = {v: k for k, v in mapping.items()}
            
            for row_num, row in enumerate(reader, start=2):
                total_rows += 1
                # Check required fields using mapping
                name_header = field_to_header.get('name', '')
                phone_header = field_to_header.get('phone', '')
                
                name = row.get(name_header, '').strip() if name_header else ''
                phone = row.get(phone_header, '').strip() if phone_header else ''
                
                # Clean phone number (remove spaces, handle multiple contacts)
                if phone:
                    phone = phone.split(',')[0].strip()  # Take first phone if multiple
                    phone = phone.replace(' ', '').replace('-', '')
                
                if name and phone:
                    valid_rows += 1
                else:
                    errors += 1
        else:
            # Excel preview
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                tmp.write(file_data['content'])
                tmp_path = tmp.name
            
            try:
                workbook = openpyxl.load_workbook(tmp_path)
                worksheet = workbook.active
                headers = [str(cell.value).strip() if cell.value else '' for cell in worksheet[1]]
                
                # Create reverse mapping: field -> header
                field_to_header = {v: k for k, v in mapping.items()}
                
                for row_num, row in enumerate(worksheet.iter_rows(min_row=2, values_only=False), start=2):
                    total_rows += 1
                    # Get name and phone using mapping
                    name_header = field_to_header.get('name', '')
                    phone_header = field_to_header.get('phone', '')
                    
                    name = ''
                    phone = ''
                    if name_header in headers:
                        name_idx = headers.index(name_header)
                        if name_idx < len(row):
                            name = str(row[name_idx].value).strip() if row[name_idx].value else ''
                    if phone_header in headers:
                        phone_idx = headers.index(phone_header)
                        if phone_idx < len(row):
                            phone = str(row[phone_idx].value).strip() if row[phone_idx].value else ''
                            # Clean phone number (remove spaces, handle multiple contacts)
                            if phone:
                                phone = phone.split(',')[0].strip()  # Take first phone if multiple
                                phone = phone.replace(' ', '').replace('-', '')
                    
                    if name and phone:
                        valid_rows += 1
                    else:
                        errors += 1
            finally:
                os.unlink(tmp_path)
        
        return JsonResponse({
            'success': True,
            'total_rows': total_rows,
            'valid_rows': valid_rows,
            'errors': errors
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def lead_upload(request):
    """Upload leads via Excel/CSV (Admin and Site Head only) with auto-mapping and manual mapping support"""
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
            
            # Check if manual mapping is provided
            manual_mapping_json = request.POST.get('mapping')
            session_id = request.POST.get('session_id')
            
            # Parse manual mapping if provided
            manual_mapping = {}
            if manual_mapping_json:
                import json
                try:
                    manual_mapping = json.loads(manual_mapping_json)
                except:
                    pass
            
            # Process file
            leads_created = 0
            errors = []
            mapping_info = []
            field_map = {}
            headers = []
            
            if file_name.endswith('.csv'):
                # Process CSV
                if session_id and request.session.get(f'upload_file_{session_id}'):
                    file_data = request.session.get(f'upload_file_{session_id}')
                    decoded_file = file_data['content']
                    # Clean up session
                    del request.session[f'upload_file_{session_id}']
                else:
                    decoded_file = uploaded_file.read().decode('utf-8')
                
                io_string = io.StringIO(decoded_file)
                reader = csv.DictReader(io_string)
                
                # Get headers from CSV
                csv_headers = reader.fieldnames or []
                headers = csv_headers
                
                # Use manual mapping if provided, otherwise auto-detect
                if manual_mapping:
                    # Manual mapping: header -> field
                    header_to_field = manual_mapping
                else:
                    get_value, field_map = _create_column_mapper(csv_headers)
                    # Convert to header->field format
                    header_to_field = {}
                    for field, col_idx in field_map.items():
                        if col_idx < len(csv_headers):
                            header_to_field[csv_headers[col_idx]] = field
                
                # Store mapping info for user feedback
                if field_map:
                    mapping_info.append(f"Detected columns: {', '.join([f'{k} → {csv_headers[field_map[k]]}' for k in ['name', 'phone'] if k in field_map])}")
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Use manual or auto-mapping to get values
                        def get_row_value(field_name):
                            if manual_mapping:
                                # Find header mapped to this field
                                header = None
                                for h, f in header_to_field.items():
                                    if f == field_name:
                                        header = h
                                        break
                                if header:
                                    return str(row.get(header, '')).strip() if row.get(header) else ''
                            else:
                                col_idx = field_map.get(field_name)
                                if col_idx is not None and col_idx < len(csv_headers):
                                    col_name = csv_headers[col_idx]
                                    return str(row.get(col_name, '')).strip() if row.get(col_name) else ''
                            return ''
                        
                        # Required fields
                        name = get_row_value('name')
                        phone = get_row_value('phone')
                        
                        # Clean phone number (handle multiple contacts, remove spaces)
                        if phone:
                            phone = phone.split(',')[0].strip()  # Take first phone if multiple
                            phone = phone.replace(' ', '').replace('-', '').replace('/', '')
                            # Remove leading +91 or 91
                            if phone.startswith('+91'):
                                phone = phone[3:]
                            elif phone.startswith('91') and len(phone) > 10:
                                phone = phone[2:]
                        
                        if not name or not phone:
                            errors.append(f"Row {row_num}: Name and Phone are required")
                            continue
                        
                        # Check for duplicate phone
                        if Lead.objects.filter(phone=phone, project=project, is_archived=False).exists():
                            errors.append(f"Row {row_num}: Lead with phone {phone} already exists")
                            continue
                        
                        # Get simplified fields (only what's needed for leads upload)
                        configuration_str = get_row_value('configuration')
                        budget_str = get_row_value('budget')
                        feedback = get_row_value('feedback')
                        cp_id = get_row_value('cp_id')
                        
                        # Parse configuration - try to match to ProjectConfiguration
                        configuration = None
                        if configuration_str:
                            try:
                                from projects.models import ProjectConfiguration
                                config_qs = ProjectConfiguration.objects.filter(
                                    project=project,
                                    name__icontains=configuration_str
                                )
                                if config_qs.exists():
                                    configuration = config_qs.first()
                            except:
                                pass
                        
                        # Parse budget - handle ranges like "35-40 L", "1.2-1.3 Cr", "Open Budget", "Low Budget"
                        budget = None
                        if budget_str:
                            budget_str = budget_str.strip()
                            # Handle "Open Budget" and "Low Budget"
                            if budget_str.lower() in ['open budget', 'open']:
                                budget = None  # Will be stored in notes
                            elif budget_str.lower() in ['low budget', 'low']:
                                budget = None  # Will be stored in notes
                            else:
                                # Parse numeric ranges
                                try:
                                    import re
                                    from decimal import Decimal
                                    budget_clean = budget_str.replace(' ', '').upper()
                                    if 'L' in budget_clean or 'LAKH' in budget_clean:
                                        numbers = re.findall(r'\d+\.?\d*', budget_clean)
                                        if numbers:
                                            avg = sum(float(n) for n in numbers) / len(numbers)
                                            budget = Decimal(avg * 100000)
                                    elif 'CR' in budget_clean or 'CRORE' in budget_clean:
                                        numbers = re.findall(r'\d+\.?\d*', budget_clean)
                                        if numbers:
                                            avg = sum(float(n) for n in numbers) / len(numbers)
                                            budget = Decimal(avg * 10000000)
                                    else:
                                        # Try direct number parsing
                                        numbers = re.findall(r'\d+\.?\d*', budget_clean)
                                        if numbers:
                                            avg = sum(float(n) for n in numbers) / len(numbers)
                                            # Assume lakhs if less than 100, crores if more
                                            if avg < 100:
                                                budget = Decimal(avg * 100000)
                                            else:
                                                budget = Decimal(avg * 10000000)
                                except:
                                    budget = None
                        
                        # Get CP data if provided
                        channel_partner = None
                        is_cp_data = request.POST.get('is_cp_data', 'no') == 'yes'
                        if is_cp_data:
                            cp_id_from_form = request.POST.get('channel_partner_id')
                            if cp_id_from_form:
                                try:
                                    from channel_partners.models import ChannelPartner
                                    channel_partner = ChannelPartner.objects.get(pk=cp_id_from_form)
                                except:
                                    pass
                        elif cp_id:
                            # Try to find CP by ID
                            try:
                                from channel_partners.models import ChannelPartner
                                channel_partner = ChannelPartner.objects.filter(cp_unique_id=cp_id).first()
                            except:
                                pass
                        
                        # Get Lead Status
                        status_str = get_row_value('status')
                        # Map feedback to status if status not provided
                        if not status_str and feedback:
                            feedback_lower = feedback.lower()
                            if 'interested' in feedback_lower or 'intrested' in feedback_lower:
                                status_str = 'hot'
                            elif 'not interested' in feedback_lower or 'not intrested' in feedback_lower:
                                status_str = 'lost'
                            elif 'call back' in feedback_lower or 'callback' in feedback_lower:
                                status_str = 'contacted'
                            elif 'busy' in feedback_lower or 'not answering' in feedback_lower:
                                status_str = 'contacted'
                            elif 'already booked' in feedback_lower:
                                status_str = 'lost'
                            else:
                                status_str = 'contacted'
                        
                        # Validate status against choices
                        valid_statuses = [choice[0] for choice in Lead.LEAD_STATUS_CHOICES]
                        if status_str:
                            status_str = status_str.lower().strip()
                            status_matched = None
                            for valid_status in valid_statuses:
                                if status_str == valid_status or status_str.replace('_', ' ') == valid_status.replace('_', ' '):
                                    status_matched = valid_status
                                    break
                            if not status_matched:
                                for valid_status, display_name in Lead.LEAD_STATUS_CHOICES:
                                    display_lower = display_name.lower()
                                    if status_str == display_lower or status_str in display_lower or display_lower in status_str:
                                        status_matched = valid_status
                                        break
                            status = status_matched if status_matched else 'new'
                        else:
                            status = 'new'
                        
                        # Handle pretagged leads (if CP data)
                        is_pretagged = is_cp_data and channel_partner is not None
                        
                        # Store feedback in notes
                        notes = ''
                        if feedback:
                            notes = f"Feedback: {feedback}"
                        if budget_str and budget is None:
                            # Budget is "Open Budget" or "Low Budget"
                            if notes:
                                notes += f"\nBudget: {budget_str}"
                            else:
                                notes = f"Budget: {budget_str}"
                        
                        # Create lead with simplified fields
                        Lead.objects.create(
                            name=name,
                            phone=phone,
                            project=project,
                            configuration=configuration,
                            budget=budget,
                            notes=notes,
                            channel_partner=channel_partner,
                            is_pretagged=is_pretagged,
                            pretag_status='pending_verification' if is_pretagged else '',
                            phone_verified=False,
                            status=status,
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
                
                # Get file from session if available
                if session_id and request.session.get(f'upload_file_{session_id}'):
                    file_data = request.session.get(f'upload_file_{session_id}')
                    import tempfile
                    import os
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                        tmp.write(file_data['content'])
                        tmp_path = tmp.name
                    try:
                        workbook = openpyxl.load_workbook(tmp_path)
                    finally:
                        os.unlink(tmp_path)
                    # Clean up session
                    del request.session[f'upload_file_{session_id}']
                else:
                    workbook = openpyxl.load_workbook(uploaded_file)
                
                worksheet = workbook.active
                
                # Get header row
                headers = [str(cell.value).strip() if cell.value else '' for cell in worksheet[1]]
                
                # Use manual mapping if provided, otherwise auto-detect
                if manual_mapping:
                    header_to_field = manual_mapping
                else:
                    get_value, field_map = _create_column_mapper(headers)
                    # Convert to header->field format
                    header_to_field = {}
                    for field, col_idx in field_map.items():
                        if col_idx < len(headers):
                            header_to_field[headers[col_idx]] = field
                
                # Store mapping info for user feedback
                if field_map:
                    mapping_info.append(f"Detected columns: {', '.join([f'{k} → {headers[field_map[k]]}' for k in ['name', 'phone'] if k in field_map])}")
                
                for row_num, row in enumerate(worksheet.iter_rows(min_row=2, values_only=False), start=2):
                    try:
                        # Use manual or auto-mapping to get values
                        def get_row_value(field_name):
                            if manual_mapping:
                                # Find header mapped to this field
                                header = None
                                for h, f in header_to_field.items():
                                    if f == field_name:
                                        header = h
                                        break
                                if header and header in headers:
                                    col_idx = headers.index(header)
                                    if col_idx < len(row):
                                        cell = row[col_idx]
                                        return str(cell.value).strip() if cell.value else ''
                            else:
                                col_idx = field_map.get(field_name)
                                if col_idx is not None and col_idx < len(row):
                                    cell = row[col_idx]
                                    return str(cell.value).strip() if cell.value else ''
                            return ''
                        
                        # Required fields
                        name = get_row_value('name')
                        phone = get_row_value('phone')
                        
                        # Clean phone number (handle multiple contacts, remove spaces)
                        if phone:
                            phone = phone.split(',')[0].strip()  # Take first phone if multiple
                            phone = phone.replace(' ', '').replace('-', '').replace('/', '')
                            # Remove leading +91 or 91
                            if phone.startswith('+91'):
                                phone = phone[3:]
                            elif phone.startswith('91') and len(phone) > 10:
                                phone = phone[2:]
                        
                        if not name or not phone:
                            errors.append(f"Row {row_num}: Name and Phone are required")
                            continue
                        
                        # Check for duplicate phone
                        if Lead.objects.filter(phone=phone, project=project, is_archived=False).exists():
                            errors.append(f"Row {row_num}: Lead with phone {phone} already exists")
                            continue
                        
                        # Get simplified fields (only what's needed for leads upload)
                        configuration_str = get_row_value('configuration')
                        budget_str = get_row_value('budget')
                        feedback = get_row_value('feedback')
                        cp_id = get_row_value('cp_id')
                        
                        # Parse configuration - try to match to ProjectConfiguration
                        configuration = None
                        if configuration_str:
                            try:
                                from projects.models import ProjectConfiguration
                                config_qs = ProjectConfiguration.objects.filter(
                                    project=project,
                                    name__icontains=configuration_str
                                )
                                if config_qs.exists():
                                    configuration = config_qs.first()
                            except:
                                pass
                        
                        # Parse budget - handle ranges like "35-40 L", "1.2-1.3 Cr", "Open Budget", "Low Budget"
                        budget = None
                        if budget_str:
                            budget_str = budget_str.strip()
                            # Handle "Open Budget" and "Low Budget"
                            if budget_str.lower() in ['open budget', 'open']:
                                budget = None  # Will be stored in notes
                            elif budget_str.lower() in ['low budget', 'low']:
                                budget = None  # Will be stored in notes
                            else:
                                # Parse numeric ranges
                                try:
                                    import re
                                    from decimal import Decimal
                                    budget_clean = budget_str.replace(' ', '').upper()
                                    if 'L' in budget_clean or 'LAKH' in budget_clean:
                                        numbers = re.findall(r'\d+\.?\d*', budget_clean)
                                        if numbers:
                                            avg = sum(float(n) for n in numbers) / len(numbers)
                                            budget = Decimal(avg * 100000)
                                    elif 'CR' in budget_clean or 'CRORE' in budget_clean:
                                        numbers = re.findall(r'\d+\.?\d*', budget_clean)
                                        if numbers:
                                            avg = sum(float(n) for n in numbers) / len(numbers)
                                            budget = Decimal(avg * 10000000)
                                    else:
                                        # Try direct number parsing
                                        numbers = re.findall(r'\d+\.?\d*', budget_clean)
                                        if numbers:
                                            avg = sum(float(n) for n in numbers) / len(numbers)
                                            # Assume lakhs if less than 100, crores if more
                                            if avg < 100:
                                                budget = Decimal(avg * 100000)
                                            else:
                                                budget = Decimal(avg * 10000000)
                                except:
                                    budget = None
                        
                        # Get CP data if provided
                        channel_partner = None
                        is_cp_data = request.POST.get('is_cp_data', 'no') == 'yes'
                        if is_cp_data:
                            cp_id_from_form = request.POST.get('channel_partner_id')
                            if cp_id_from_form:
                                try:
                                    from channel_partners.models import ChannelPartner
                                    channel_partner = ChannelPartner.objects.get(pk=cp_id_from_form)
                                except:
                                    pass
                        elif cp_id:
                            # Try to find CP by ID
                            try:
                                from channel_partners.models import ChannelPartner
                                channel_partner = ChannelPartner.objects.filter(cp_unique_id=cp_id).first()
                            except:
                                pass
                        
                        # Get Lead Status
                        status_str = get_row_value('status')
                        # Map feedback to status if status not provided
                        if not status_str and feedback:
                            feedback_lower = feedback.lower()
                            if 'interested' in feedback_lower or 'intrested' in feedback_lower:
                                status_str = 'hot'
                            elif 'not interested' in feedback_lower or 'not intrested' in feedback_lower:
                                status_str = 'lost'
                            elif 'call back' in feedback_lower or 'callback' in feedback_lower:
                                status_str = 'contacted'
                            elif 'busy' in feedback_lower or 'not answering' in feedback_lower:
                                status_str = 'contacted'
                            elif 'already booked' in feedback_lower:
                                status_str = 'lost'
                            else:
                                status_str = 'contacted'
                        
                        # Validate status against choices
                        valid_statuses = [choice[0] for choice in Lead.LEAD_STATUS_CHOICES]
                        if status_str:
                            status_str = status_str.lower().strip()
                            status_matched = None
                            for valid_status in valid_statuses:
                                if status_str == valid_status or status_str.replace('_', ' ') == valid_status.replace('_', ' '):
                                    status_matched = valid_status
                                    break
                            if not status_matched:
                                for valid_status, display_name in Lead.LEAD_STATUS_CHOICES:
                                    display_lower = display_name.lower()
                                    if status_str == display_lower or status_str in display_lower or display_lower in status_str:
                                        status_matched = valid_status
                                        break
                            status = status_matched if status_matched else 'new'
                        else:
                            status = 'new'
                        
                        # Handle pretagged leads (if CP data)
                        is_pretagged = is_cp_data and channel_partner is not None
                        
                        # Store feedback in notes
                        notes = ''
                        if feedback:
                            notes = f"Feedback: {feedback}"
                        if budget_str and budget is None:
                            # Budget is "Open Budget" or "Low Budget"
                            if notes:
                                notes += f"\nBudget: {budget_str}"
                            else:
                                notes = f"Budget: {budget_str}"
                        
                        # Create lead with simplified fields
                        Lead.objects.create(
                            name=name,
                            phone=phone,
                            project=project,
                            configuration=configuration,
                            budget=budget,
                            notes=notes,
                            channel_partner=channel_partner,
                            is_pretagged=is_pretagged,
                            pretag_status='pending_verification' if is_pretagged else '',
                            phone_verified=False,
                            status=status,
                            created_by=request.user,
                        )
                        leads_created += 1
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
            
            if leads_created > 0:
                success_msg = f'Successfully uploaded {leads_created} lead(s)!'
                if mapping_info:
                    success_msg += f" {' '.join(mapping_info)}"
                messages.success(request, success_msg)
            
            if errors:
                # Check if errors are due to missing required columns
                missing_name_phone = sum(1 for e in errors if 'Name and Phone are required' in e)
                if missing_name_phone > 0 and 'name' not in field_map and 'phone' not in field_map:
                    messages.error(request, 
                        f'Could not auto-detect "Name" and "Phone" columns. '
                        f'Please ensure your file has columns with names like: Name/Full Name/Client Name and Phone/Mobile/Contact Number. '
                        f'Found columns: {", ".join(headers[:10])}...')
                else:
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
                from django.db import transaction
                # Use atomic transaction with row locking to prevent race conditions
                with transaction.atomic():
                    # Get quotas
                    quotas = DailyAssignmentQuota.objects.filter(
                        project=project,
                        is_active=True
                    )
                    
                    assigned_count = 0
                    for quota in quotas:
                        # Use select_for_update to lock rows and prevent concurrent assignment
                        leads_to_assign = list(
                            Lead.objects.select_for_update(skip_locked=True)
                            .filter(
                                project=project,
                                assigned_to__isnull=True,
                                is_archived=False
                            )
                            .order_by('created_at')[:quota.daily_quota]
                        )
                        
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
