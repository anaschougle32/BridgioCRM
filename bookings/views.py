from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import Booking, Payment
from leads.models import Lead
from projects.models import Project
from channel_partners.models import ChannelPartner


@login_required
def booking_list(request):
    """List all bookings - Super Admin sees all"""
    bookings = Booking.objects.filter(is_archived=False)
    
    # Role-based filtering
    if request.user.is_super_admin() or (request.user.is_superuser and request.user.is_staff):
        pass  # Super admin sees all
    elif request.user.is_mandate_owner():
        bookings = bookings.filter(project__mandate_owner=request.user)
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
    
    # Annotate with payment totals
    bookings = bookings.annotate(
        total_paid=Sum('payments__amount')
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
    
    # Permission check
    if request.user.is_super_admin() or (request.user.is_superuser and request.user.is_staff):
        pass
    elif request.user.is_mandate_owner() and booking.project.mandate_owner != request.user:
        messages.error(request, 'You do not have permission to view this booking.')
        return redirect('bookings:list')
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
    
    # Permission check - Only Closing Managers can create bookings
    if not (request.user.is_closing_manager() or request.user.is_super_admin()):
        messages.error(request, 'Only Closing Managers can create bookings.')
        return redirect('leads:detail', pk=lead_id)
    
    # Check if lead is assigned to user (for Closing Managers)
    if request.user.is_closing_manager() and lead.assigned_to != request.user:
        messages.error(request, 'You can only create bookings for leads assigned to you.')
        return redirect('leads:detail', pk=lead_id)
    
    # Check if booking already exists
    if hasattr(lead, 'booking'):
        messages.info(request, 'This lead already has a booking.')
        return redirect('bookings:detail', pk=lead.booking.id)
    
    # Check if lead is verified (for pretagged leads)
    if lead.is_pretagged and not lead.phone_verified:
        messages.error(request, 'Cannot create booking for unverified pretagged lead. Please verify OTP first.')
        return redirect('leads:detail', pk=lead_id)
    
    if request.method == 'POST':
        try:
            # Get channel partner if CP details exist
            channel_partner = None
            if lead.cp_name and lead.cp_phone:
                # Try to find existing CP or create new one
                channel_partner, created = ChannelPartner.objects.get_or_create(
                    phone=lead.cp_phone,
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
            cp_commission_percent = lead.project.default_commission_percent if channel_partner else 0.00
            
            # Create booking
            booking = Booking.objects.create(
                lead=lead,
                project=lead.project,
                tower_wing=request.POST.get('tower_wing', ''),
                unit_number=request.POST.get('unit_number', ''),
                carpet_area=float(request.POST.get('carpet_area')) if request.POST.get('carpet_area') else None,
                floor=int(request.POST.get('floor')) if request.POST.get('floor') else None,
                final_negotiated_price=float(request.POST.get('final_negotiated_price', 0)),
                token_amount=float(request.POST.get('token_amount', 0)),
                channel_partner=channel_partner,
                cp_commission_percent=cp_commission_percent,
                created_by=request.user,
            )
            
            # Update lead status
            lead.status = 'booked'
            lead.save()
            
            # Create audit log
            from accounts.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action='booking_created',
                model_name='Booking',
                object_id=booking.id,
                details=f'Booking created for lead {lead.name} - Unit {booking.unit_number}',
            )
            
            messages.success(request, f'Booking created successfully! Booking #{booking.id}')
            return redirect('bookings:detail', pk=booking.id)
            
        except Exception as e:
            messages.error(request, f'Error creating booking: {str(e)}')
    
    # Get available channel partners for dropdown
    channel_partners = ChannelPartner.objects.filter(is_active=True)
    if lead.project.mandate_owner:
        channel_partners = channel_partners.filter(linked_projects__mandate_owner=lead.project.mandate_owner).distinct()
    
    context = {
        'lead': lead,
        'project': lead.project,
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
                object_id=payment.id,
                details=f'Payment of ₹{payment.amount} added to booking {booking.id}',
            )
            
            messages.success(request, f'Payment of ₹{payment.amount} added successfully!')
            return redirect('bookings:detail', pk=booking_id)
            
        except Exception as e:
            messages.error(request, f'Error adding payment: {str(e)}')
    
    context = {
        'booking': booking,
    }
    return render(request, 'bookings/payment_create.html', context)
