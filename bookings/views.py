from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from .models import Booking, Payment
from leads.models import Lead
from projects.models import Project
from channel_partners.models import ChannelPartner
from accounts.models import User


@login_required
def booking_list(request):
    """List all bookings - Super Admin sees all"""
    bookings = Booking.objects.filter(is_archived=False)
    
    # Role-based filtering - Mandate Owner has same permissions as Super Admin
    if request.user.is_super_admin() or request.user.is_mandate_owner() or (request.user.is_superuser and request.user.is_staff):
        pass  # Super admin and mandate owner see all
    elif request.user.is_site_head():
        bookings = bookings.filter(project__site_head=request.user)
    elif request.user.is_closing_manager():
        bookings = bookings.filter(created_by=request.user)
    else:
        messages.error(request, 'You do not have permission to view bookings.')
        return redirect('dashboard')
    
    # Search
    search = request.GET.get('search', '')
    if search:
        bookings = bookings.filter(
            Q(lead__name__icontains=search) |
            Q(lead__phone__icontains=search) |
            Q(unit_number__icontains=search) |
            Q(project__name__icontains=search)
        )
    
    # Filter by project
    project_id = request.GET.get('project', '')
    if project_id:
        bookings = bookings.filter(project_id=project_id)
    
    # Annotate with payment totals (use different name to avoid conflict with property)
    bookings = bookings.annotate(
        total_paid_amount=Sum('payments__amount')
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(bookings, 25)
    page = request.GET.get('page', 1)
    bookings_page = paginator.get_page(page)
    
    context = {
        'bookings': bookings_page,
        'projects': Project.objects.filter(is_active=True),
        'search': search,
        'selected_project': project_id,
    }
    return render(request, 'bookings/list.html', context)


@login_required
def booking_detail(request, pk):
    """Booking detail view with payments"""
    booking = get_object_or_404(Booking, pk=pk, is_archived=False)
    
    # Permission check - Mandate Owner has same permissions as Super Admin
    if request.user.is_super_admin() or request.user.is_mandate_owner() or (request.user.is_superuser and request.user.is_staff):
        pass  # Super Admin and Mandate Owner can view all bookings
    elif request.user.is_site_head() and booking.project.site_head != request.user:
        messages.error(request, 'You do not have permission to view this booking.')
        return redirect('bookings:list')
    elif request.user.is_closing_manager() and booking.created_by != request.user:
        messages.error(request, 'You do not have permission to view this booking.')
        return redirect('bookings:list')
    elif not (request.user.is_super_admin() or request.user.is_mandate_owner() or 
              request.user.is_site_head() or request.user.is_closing_manager()):
        messages.error(request, 'You do not have permission to view bookings.')
        return redirect('dashboard')
    
    # Get payments
    payments = booking.payments.all().order_by('-payment_date')
    
    context = {
        'booking': booking,
        'payments': payments,
        'total_paid': booking.total_paid,
        'remaining_balance': booking.remaining_balance,
    }
    return render(request, 'bookings/detail.html', context)


@login_required
def booking_create(request, lead_id):
    """Create booking from lead (Closing Manager only)"""
    lead = get_object_or_404(Lead, pk=lead_id, is_archived=False)
    
    # Permission check - Closing Managers, Site Heads, Telecallers, Super Admin, and Mandate Owners can create bookings
    if not (request.user.is_closing_manager() or request.user.is_site_head() or request.user.is_telecaller() or request.user.is_super_admin() or request.user.is_mandate_owner()):
        messages.error(request, 'You do not have permission to create bookings.')
        return redirect('leads:detail', pk=lead_id)
    
    # Get project from request (required for association-based booking)
    # IMPORTANT: Always use project_id from request to avoid booking on wrong project when leads are duplicated
    project_id = request.GET.get('project_id') or request.POST.get('project_id')
    if not project_id:
        # If no project_id in request, try to get from the association that was used to access this page
        # This is safer than using primary_project which might be from a different project
        from leads.models import LeadProjectAssociation
        # Try to find the most recent active association (likely the one being used)
        association = lead.project_associations.filter(is_archived=False).order_by('-created_at').first()
        if association:
            project_id = association.project.id
        else:
            # Last resort: use primary project
            primary_project = lead.primary_project
            if not primary_project:
                messages.error(request, 'Project is required to create booking. Please specify project_id in the request.')
                return redirect('leads:detail', pk=lead_id)
            project_id = primary_project.id
    
    project = get_object_or_404(Project, pk=project_id, is_active=True)
    
    # Get association for this project
    from leads.models import LeadProjectAssociation
    association = LeadProjectAssociation.objects.filter(
        lead=lead,
        project=project,
        is_archived=False
    ).first()
    
    if not association:
        messages.error(request, f'Lead is not associated with project "{project.name}". Please ensure the lead is associated with this project before creating a booking.')
        return redirect('leads:detail', pk=lead_id)
    
    # Check if lead is assigned to user (for Telecallers only)
    # Closing Managers can create bookings for any visited leads
    if request.user.is_telecaller() and association.assigned_to != request.user:
        messages.error(request, 'You can only create bookings for leads assigned to you.')
        return redirect('leads:detail', pk=lead_id)
    
    # For Closing Managers: allow if lead is visited (status='visit_completed' or phone_verified=True)
    if request.user.is_closing_manager():
        if association.status != 'visit_completed' and not association.phone_verified:
            messages.error(request, 'You can only create bookings for visited leads. Please verify the visit first.')
            return redirect('leads:detail', pk=lead_id)
    
    # For Site Heads: check if lead belongs to their project
    if request.user.is_site_head() and project.site_head != request.user:
        messages.error(request, 'You can only create bookings for leads in your projects.')
        return redirect('leads:detail', pk=lead_id)
    
    # Note: Multiple bookings are now allowed per lead (for investors booking multiple units)
    # No need to check if booking exists - lead can have multiple bookings
    
    # Check if lead is verified (for pretagged leads)
    if association.is_pretagged and not association.phone_verified:
        messages.error(request, 'Cannot create booking for unverified pretagged lead. Please verify OTP first.')
        return redirect('leads:detail', pk=lead_id)
    
    # Get selected unit IDs from query string (for multiple unit booking)
    unit_ids_param = request.GET.get('unit_ids') or request.POST.get('unit_ids')
    selected_unit_ids = []
    if unit_ids_param:
        selected_unit_ids = [int(uid) for uid in unit_ids_param.split(',') if uid.strip().isdigit()]
    
    # Redirect to unit selection page first (unless coming from unit calculation page or has selected units)
    if request.method != 'POST' and not request.GET.get('from_unit') and not selected_unit_ids:
        # Redirect to project unit selection page with lead_id
        return redirect(f"{reverse('projects:unit_selection', args=[project.id])}?lead_id={lead_id}")
    
    if request.method == 'POST':
        from django.db import transaction
        try:
            # Use atomic transaction to ensure booking, payment, and status update are all-or-nothing
            with transaction.atomic():
                # Get channel partner if CP details exist
                channel_partner = None
                if lead.cp_name and lead.cp_phone:
                    # Normalize CP phone before lookup
                    from leads.utils import normalize_phone
                    normalized_cp_phone = normalize_phone(lead.cp_phone)
                    # Try to find existing CP or create new one
                    channel_partner, created = ChannelPartner.objects.get_or_create(
                        phone=normalized_cp_phone,
                        defaults={
                            'firm_name': lead.cp_firm_name or 'N/A',
                            'cp_name': lead.cp_name,
                            'email': '',
                            'cp_type': 'individual',
                        }
                    )
                    if not created:
                        # Update existing CP if needed
                        if lead.cp_firm_name:
                            channel_partner.firm_name = lead.cp_firm_name
                            channel_partner.save()
                
                # Get CP commission percent from project
                cp_commission_percent = project.default_commission_percent if channel_partner else 0.00
                
                # Get self funding and loan percentages (if provided)
                self_funding_percent = request.POST.get('self_funding_percent', '0')
                loan_percent = request.POST.get('loan_percent', '0')
                final_negotiated_price = float(request.POST.get('final_negotiated_price', 0))
                downpayment = float(request.POST.get('downpayment', 0))
                token_amount = float(request.POST.get('token_amount', 0))
                
                # Calculate remaining amount after downpayment
                remaining_amount = final_negotiated_price - downpayment
                
                # Create notes with funding information
                funding_notes = ''
                if downpayment > 0:
                    funding_notes += f'Down Payment Made: ₹{downpayment:,.2f}. Remaining Amount: ₹{remaining_amount:,.2f}. '
                if self_funding_percent and float(self_funding_percent) > 0:
                    self_funding_amount = final_negotiated_price * (float(self_funding_percent) / 100)
                    funding_notes += f'Self Funding: {self_funding_percent}% (₹{self_funding_amount:,.2f}). '
                if loan_percent and float(loan_percent) > 0:
                    loan_amount = final_negotiated_price * (float(loan_percent) / 100)
                    funding_notes += f'Loan: {loan_percent}% (₹{loan_amount:,.2f}). '
                
                # Determine credit assignment based on visit source and CP relationship
                credited_to_closing = None
                credited_to_sourcing = None
                credited_to_telecaller = None
                
                # Get the association to check visit source and who created it
                from leads.models import LeadProjectAssociation
                lead_association = LeadProjectAssociation.objects.filter(
                    lead=lead,
                    project=project,
                    is_archived=False
                ).first()
                
                # Check if lead has CP (channel_partner or cp_phone)
                has_cp = bool(channel_partner or lead.channel_partner or lead.cp_phone)
                
                # Check visit source
                visit_source = lead.visit_source or (lead_association and getattr(lead_association, 'visit_source', None)) or 'walkin'
                
                # Check who created the visit/lead
                visit_creator = lead_association.created_by if lead_association else lead.created_by
                is_telecaller_created = visit_creator and visit_creator.is_telecaller() if visit_creator else False
                is_sourcing_created = visit_creator and visit_creator.is_sourcing_manager() if visit_creator else False
                
                # Credit Logic:
                # 1. Direct visit (no CP, no sourcing, no telecaller) → Only closing manager
                if not has_cp and not is_telecaller_created and not is_sourcing_created:
                    credited_to_closing = request.user if request.user.is_closing_manager() else None
                
                # 2. CP visit → Sourcing manager gets visit count, if booking done both closing and sourcing get credit
                elif has_cp:
                    credited_to_closing = request.user if request.user.is_closing_manager() else None
                    # Find sourcing manager assigned to this project
                    sourcing_managers = User.objects.filter(
                        role='sourcing_manager',
                        assigned_projects=project,
                        is_active=True
                    ).first()
                    if sourcing_managers:
                        credited_to_sourcing = sourcing_managers
                    # If visit was created by sourcing manager, credit them
                    elif is_sourcing_created and visit_creator:
                        credited_to_sourcing = visit_creator
                
                # 3. Telecaller calling CP leads → Telecaller, sourcing, and closing all get credit
                elif is_telecaller_created and has_cp:
                    credited_to_closing = request.user if request.user.is_closing_manager() else None
                    if visit_creator:
                        credited_to_telecaller = visit_creator
                    # Find sourcing manager assigned to this project
                    sourcing_managers = User.objects.filter(
                        role='sourcing_manager',
                        assigned_projects=project,
                        is_active=True
                    ).first()
                    if sourcing_managers:
                        credited_to_sourcing = sourcing_managers
                
                # 4. Telecaller calling non-CP leads → Only telecaller and closing get credit
                elif is_telecaller_created and not has_cp:
                    credited_to_closing = request.user if request.user.is_closing_manager() else None
                    if visit_creator:
                        credited_to_telecaller = visit_creator
                
                # Handle multiple unit booking
                unit_ids_param = request.POST.get('unit_ids', '')
                if unit_ids_param:
                    selected_unit_ids = [int(uid) for uid in unit_ids_param.split(',') if uid.strip().isdigit()]
                else:
                    selected_unit_ids = []
                
                # If multiple units selected, create booking for each unit
                if selected_unit_ids:
                    from projects.models import UnitConfiguration
                    created_bookings = []
                    total_price = final_negotiated_price
                    price_per_unit = total_price / len(selected_unit_ids) if len(selected_unit_ids) > 0 else total_price
                    token_per_unit = token_amount / len(selected_unit_ids) if len(selected_unit_ids) > 0 else token_amount
                    downpayment_per_unit = downpayment / len(selected_unit_ids) if len(selected_unit_ids) > 0 else downpayment
                    
                    for unit_id in selected_unit_ids:
                        try:
                            unit_config = UnitConfiguration.objects.get(id=unit_id, project=project)
                            
                            # Check unit availability
                            if not unit_config.is_available:
                                messages.error(request, f'Unit {unit_config.full_unit_number} is not available for booking.')
                                continue
                            
                            # Book the unit
                            success, message = unit_config.book_unit(None)  # We'll set the booking after creation
                            if not success:
                                messages.error(request, f'Cannot book unit {unit_config.full_unit_number}: {message}')
                                continue
                            
                            tower_wing = f"Tower {unit_config.tower_number}" if unit_config.tower_number else ''
                            unit_number = str(unit_config.unit_number) if unit_config.unit_number else ''
                            
                            booking = Booking.objects.create(
                                lead=lead,
                                project=project,
                                tower_wing=tower_wing,
                                unit_number=unit_number,
                                carpet_area=unit_config.area_type.carpet_area if unit_config.area_type else None,
                                floor=unit_config.floor_number,
                                final_negotiated_price=price_per_unit,
                                token_amount=token_per_unit,
                                channel_partner=channel_partner,
                                cp_commission_percent=cp_commission_percent,
                                credited_to_closing_manager=credited_to_closing,
                                credited_to_sourcing_manager=credited_to_sourcing,
                                credited_to_telecaller=credited_to_telecaller,
                                created_by=request.user,
                            )
                            created_bookings.append(booking)
                            
                            # Link the booking to the unit configuration
                            unit_config.booking = booking
                            unit_config.save(update_fields=['booking'])
                            
                            # Create downpayment entry for this unit if downpayment > 0
                            if downpayment_per_unit > 0:
                                Payment.objects.create(
                                    booking=booking,
                                    amount=downpayment_per_unit,
                                    payment_mode=request.POST.get('downpayment_mode', 'cash'),
                                    payment_date=request.POST.get('downpayment_date') or timezone.now().date(),
                                    reference_number=request.POST.get('downpayment_reference', ''),
                                    notes=f'Down payment made at booking - ₹{downpayment_per_unit:,.2f}',
                                    created_by=request.user,
                                )
                            
                            # Create initial payment if token amount > 0 (and not already recorded as downpayment)
                            if token_per_unit > 0 and token_per_unit != downpayment_per_unit:
                                Payment.objects.create(
                                    booking=booking,
                                    amount=token_per_unit,
                                    payment_mode=request.POST.get('payment_mode', 'cash'),
                                    payment_date=request.POST.get('payment_date') or timezone.now().date(),
                                    reference_number=request.POST.get('reference_number', ''),
                                    notes=f'Initial token payment for booking {booking.id}',
                                    created_by=request.user,
                                )
                            
                            # Calculate and create commissions automatically
                            booking.calculate_and_create_commissions()
                            
                            # Create audit log
                            from accounts.models import AuditLog
                            AuditLog.objects.create(
                                user=request.user,
                                action='booking_created',
                                model_name='Booking',
                                object_id=str(booking.id),
                                changes={'message': f'Booking created for lead {lead.name} - Unit {booking.unit_number}'},
                            )
                        except UnitConfiguration.DoesNotExist:
                            continue
                    
                    # Update lead notes with funding information if provided
                    if funding_notes:
                        if lead.notes:
                            lead.notes += f'\n\n{funding_notes}'
                        else:
                            lead.notes = funding_notes
                        lead.save()
                    
                    # Update association status
                    association.status = 'booked'
                    association.save()
                    
                    if created_bookings:
                        messages.success(request, f'{len(created_bookings)} booking(s) created successfully!')
                        request.session['show_confetti'] = True
                        request.session.modified = True
                        return redirect('bookings:detail', pk=created_bookings[0].id)
                    else:
                        messages.error(request, 'No bookings were created. Please check unit selection.')
                else:
                    # Single unit booking - check unit availability first
                    unit_identifier = request.POST.get('unit_identifier', '')  # e.g., T1-F2-U101
                    unit_config = None
                    
                    if unit_identifier:
                        # Try to find unit by identifier
                        unit_config = UnitConfiguration.get_unit_by_identifier(project, unit_identifier)
                    
                    if unit_config:
                        # Check unit availability
                        if not unit_config.is_available:
                            messages.error(request, f'Unit {unit_config.full_unit_number} is not available for booking.')
                            return redirect('leads:detail', pk=lead_id)
                        
                        # Book the unit
                        success, message = unit_config.book_unit(None)  # We'll set the booking after creation
                        if not success:
                            messages.error(request, f'Cannot book unit {unit_config.full_unit_number}: {message}')
                            return redirect('leads:detail', pk=lead_id)
                    
                    booking = Booking.objects.create(
                        lead=lead,
                        project=project,
                        tower_wing=request.POST.get('tower_wing', ''),
                        unit_number=request.POST.get('unit_number', ''),
                        carpet_area=float(request.POST.get('carpet_area')) if request.POST.get('carpet_area') else None,
                        floor=int(request.POST.get('floor')) if request.POST.get('floor') else None,
                        final_negotiated_price=final_negotiated_price,
                        token_amount=token_amount,
                        channel_partner=channel_partner,
                        cp_commission_percent=cp_commission_percent,
                        credited_to_closing_manager=credited_to_closing,
                        credited_to_sourcing_manager=credited_to_sourcing,
                        credited_to_telecaller=credited_to_telecaller,
                        created_by=request.user,
                    )
                    
                    # Link the booking to the unit configuration if found
                    if unit_config:
                        unit_config.booking = booking
                        unit_config.save(update_fields=['booking'])
                    
                    # Update lead notes with funding information if provided
                    if funding_notes:
                        if lead.notes:
                            lead.notes += f'\n\n{funding_notes}'
                        else:
                            lead.notes = funding_notes
                        lead.save()
                    
                    # Create downpayment entry if downpayment > 0
                    if downpayment > 0:
                        Payment.objects.create(
                            booking=booking,
                            amount=downpayment,
                            payment_mode=request.POST.get('downpayment_mode', 'cash'),
                            payment_date=request.POST.get('downpayment_date') or timezone.now().date(),
                            reference_number=request.POST.get('downpayment_reference', ''),
                            notes=f'Down payment made at booking - ₹{downpayment:,.2f}',
                            created_by=request.user,
                        )
                    
                    # Create initial payment if token amount > 0 (and not already recorded as downpayment)
                    if token_amount > 0 and token_amount != downpayment:
                        Payment.objects.create(
                            booking=booking,
                            amount=token_amount,
                            payment_mode=request.POST.get('payment_mode', 'cash'),
                            payment_date=request.POST.get('payment_date') or timezone.now().date(),
                            reference_number=request.POST.get('reference_number', ''),
                            notes=f'Initial token payment for booking {booking.id}',
                            created_by=request.user,
                        )
                    
                    # Calculate and create commissions automatically
                    booking.calculate_and_create_commissions()
                    
                    # Update association status
                    association.status = 'booked'
                    association.save()
                    
                    # Create audit log
                    from accounts.models import AuditLog
                    AuditLog.objects.create(
                        user=request.user,
                        action='booking_created',
                        model_name='Booking',
                        object_id=str(booking.id),
                        changes={'message': f'Booking created for lead {lead.name} - Unit {booking.unit_number}'},
                    )
                
                    messages.success(request, f'Booking created successfully! Booking #{booking.id}')
                    # Add confetti flag to session for display on detail page
                    request.session['show_confetti'] = True
                    request.session.modified = True
                    return redirect('bookings:detail', pk=booking.id)
            
        except Exception as e:
            messages.error(request, f'Error creating booking: {str(e)}')
    
    # Get project and association (if not already set)
    if 'project' not in locals():
        project_id = request.GET.get('project_id')
        if project_id:
            project = get_object_or_404(Project, pk=project_id, is_active=True)
        else:
            project = lead.primary_project
            if not project:
                messages.error(request, 'Project is required to create booking.')
                return redirect('leads:detail', pk=lead_id)
    
    if 'association' not in locals():
        from leads.models import LeadProjectAssociation
        association = LeadProjectAssociation.objects.filter(
            lead=lead,
            project=project,
            is_archived=False
        ).first()
    
    # Get available channel partners for dropdown
    channel_partners = ChannelPartner.objects.filter(is_active=True)
    if project.mandate_owner:
        channel_partners = channel_partners.filter(linked_projects__mandate_owner=project.mandate_owner).distinct()
    
    context = {
        'lead': lead,
        'project': project,
        'association': association,
        'channel_partners': channel_partners,
        'default_cp': None,
    }
    
    # Pre-select CP if lead has CP details
    if lead.cp_name and lead.cp_phone:
        try:
            context['default_cp'] = ChannelPartner.objects.get(phone=lead.cp_phone)
        except ChannelPartner.DoesNotExist:
            pass
    
    return render(request, 'bookings/create.html', context)


@login_required
def payment_create(request, booking_id):
    """Add payment entry to booking"""
    booking = get_object_or_404(Booking, pk=booking_id, is_archived=False)
    
    # Permission check
    if not (request.user.is_closing_manager() or request.user.is_super_admin() or 
            request.user.is_site_head() or request.user.is_mandate_owner()):
        messages.error(request, 'You do not have permission to add payments.')
        return redirect('bookings:detail', pk=booking_id)
    
    if request.method == 'POST':
        try:
            payment = Payment.objects.create(
                booking=booking,
                amount=float(request.POST.get('amount', 0)),
                payment_mode=request.POST.get('payment_mode', 'cash'),
                payment_date=request.POST.get('payment_date'),
                milestone=None,  # Can be set later if milestones are implemented
                reference_number=request.POST.get('reference_number', ''),
                notes=request.POST.get('notes', ''),
                created_by=request.user,
            )
            
            # Create audit log
            from accounts.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action='payment_added',
                model_name='Payment',
                object_id=str(payment.id),
                changes={'message': f'Payment of ₹{payment.amount} added to booking {booking.id}'},
            )
            
            messages.success(request, f'Payment of ₹{payment.amount} added successfully!')
            return redirect('bookings:detail', pk=booking_id)
            
        except Exception as e:
            messages.error(request, f'Error adding payment: {str(e)}')
    
    context = {
        'booking': booking,
    }
    return render(request, 'bookings/payment_create.html', context)


@login_required
def clear_confetti(request, pk):
    """Clear confetti flag from session"""
    if 'show_confetti' in request.session:
        del request.session['show_confetti']
        request.session.modified = True
    return JsonResponse({'success': True})
