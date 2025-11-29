import random
import hashlib
import hmac
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


def generate_otp():
    """Generate a 6-digit OTP"""
    return str(random.randint(100000, 999999))


def hash_otp(otp, secret_key=None):
    """Hash OTP using SHA256 HMAC"""
    if secret_key is None:
        secret_key = getattr(settings, 'SECRET_KEY', 'default-secret-key')
    
    return hmac.new(
        secret_key.encode('utf-8'),
        otp.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def verify_otp(otp, otp_hash, secret_key=None):
    """Verify OTP against stored hash"""
    if secret_key is None:
        secret_key = getattr(settings, 'SECRET_KEY', 'default-secret-key')
    
    computed_hash = hash_otp(otp, secret_key)
    return hmac.compare_digest(computed_hash, otp_hash)


def get_sms_deep_link(phone, otp, project_name=None):
    """
    Generate WhatsApp deep link to open WhatsApp with pre-filled message
    This avoids using SMS API and saves costs by using WhatsApp directly
    
    Format: https://wa.me/91XXXXXXXXXX?text=MESSAGE
    """
    from urllib.parse import quote
    
    # Clean phone number (remove spaces, dashes, etc.)
    clean_phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    # Remove + or 91 prefix for WhatsApp (WhatsApp needs number without + or country code prefix)
    if clean_phone.startswith('+91'):
        clean_phone = clean_phone[3:]
    elif clean_phone.startswith('91'):
        clean_phone = clean_phone[2:]
    elif clean_phone.startswith('0'):
        clean_phone = clean_phone[1:]
    
    # Create WhatsApp message with project name if provided
    # Format: "Here's the OTP to confirm your visit for {project_name}. Thank you. Please provide this OTP to the executive."
    if project_name:
        message = f"Here's the OTP to confirm your visit for {project_name}. Thank you. Please provide this OTP to the executive. OTP: *{otp}*"
    else:
        message = f"Here's the OTP to confirm your visit. Thank you. Please provide this OTP to the executive. OTP: *{otp}*"
    
    # URL encode the message
    encoded_message = quote(message)
    
    # Generate WhatsApp deep link
    whatsapp_link = f'https://wa.me/{clean_phone}?text={encoded_message}'
    
    return whatsapp_link


def get_phone_display(phone):
    """Mask phone number for display (show only last 4 digits)"""
    if not phone:
        return '-'
    if len(phone) <= 4:
        return '****'
    return '****' + phone[-4:]


def get_tel_link(phone):
    """Generate tel: link for calling"""
    clean_phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    # Add country code if not present
    if not clean_phone.startswith('+91') and not clean_phone.startswith('91'):
        if clean_phone.startswith('0'):
            clean_phone = '+91' + clean_phone[1:]
        else:
            clean_phone = '+91' + clean_phone
    
    return f'tel:{clean_phone}'


def get_whatsapp_link(phone, message=''):
    """Generate WhatsApp deep link"""
    clean_phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    # Remove + or 91 prefix for WhatsApp
    if clean_phone.startswith('+91'):
        clean_phone = clean_phone[3:]
    elif clean_phone.startswith('91'):
        clean_phone = clean_phone[2:]
    elif clean_phone.startswith('0'):
        clean_phone = clean_phone[1:]
    
    # URL encode message
    from urllib.parse import quote
    encoded_message = quote(message) if message else ''
    
    if encoded_message:
        return f'https://wa.me/{clean_phone}?text={encoded_message}'
    else:
        return f'https://wa.me/{clean_phone}'


def get_whatsapp_templates():
    """Get predefined WhatsApp message templates"""
    return {
        'intro': 'Hello! Thank you for your interest in our project. I\'m calling from Bridgio CRM. How can I assist you today?',
        'project_details': 'Thank you for your interest! I\'d be happy to share project details with you. Would you like to schedule a site visit?',
        'booking_confirmation': 'Congratulations on your booking! Your booking ID is {booking_id}. We will send you further details shortly.',
    }
