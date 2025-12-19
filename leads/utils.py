"""
Utility functions for leads module
"""
import random
import hashlib
import hmac
import re
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


def generate_otp():
    """Generate a 6-digit OTP"""
    return str(random.randint(100000, 999999))


def hash_otp(otp, secret_key=None):
    """Hash OTP using SHA256 HMAC with OTP_SECRET"""
    if secret_key is None:
        # Use OTP_SECRET if available, fallback to SECRET_KEY
        secret_key = getattr(settings, 'OTP_SECRET', None)
        if not secret_key:
            secret_key = getattr(settings, 'SECRET_KEY', 'default-secret-key')
    
    return hmac.new(
        secret_key.encode('utf-8'),
        otp.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def verify_otp(otp, otp_hash, secret_key=None):
    """Verify OTP against stored hash using constant-time comparison"""
    if secret_key is None:
        # Use OTP_SECRET if available, fallback to SECRET_KEY
        secret_key = getattr(settings, 'OTP_SECRET', None)
        if not secret_key:
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


def normalize_phone(phone):
    """
    Normalize phone number to +91 format.
    Handles various input formats:
    - +91XXXXXXXXXX
    - 91XXXXXXXXXX
    - 0XXXXXXXXXX
    - XXXXXXXXXX (10 digits)
    Returns: +91XXXXXXXXXX (always with +91 prefix)
    """
    if not phone:
        return ''
    
    # Convert to string and remove all spaces, dashes, parentheses
    clean_phone = str(phone).strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    # Remove +91 or 91 prefix if present
    if clean_phone.startswith('+91'):
        clean_phone = clean_phone[3:]
    elif clean_phone.startswith('91') and len(clean_phone) > 10:
        clean_phone = clean_phone[2:]
    elif clean_phone.startswith('0') and len(clean_phone) > 10:
        clean_phone = clean_phone[1:]
    
    # Ensure it's 10 digits
    if len(clean_phone) != 10 or not clean_phone.isdigit():
        # Return as-is if invalid (let validation handle it)
        return phone
    
    # Return with +91 prefix
    return f'+91{clean_phone}'


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
        'pretag': '*SM:* {sm_name}\n*CP firm :* {cp_firm}\n\n*Project Name:* {project_name}\n*Date of Visit:* {visit_date}\n*Timing:* {visit_time}\n\n*Client Name:* {client_name}\n*Client No:* {client_phone}\n\n*Requirement:* {requirement}\n*Budget:* {budget}\n*Residing Location:* {residing_location}\n\n*Salaried:* {salaried}\n*Approx Annual Income:* {annual_income}\n\n*Source:* CP – {cp_name}',
        'at_site': '*SM:* {sm_name}\n*CP firm :* {cp_firm}\n\n*At site*\n\n*Project Name:* {project_name}\n*Date of Visit:* {visit_date}\n*Timing:* {visit_time}\n\n*Client Name:* {client_name}\n*Client No:* {client_phone}\n\n*Requirement:* {requirement}\n*Budget:* {budget}\n*Residing Location:* {residing_location}\n\n*Salaried:* {salaried}\n*Approx Annual Income:* {annual_income}\n\n*Source:* CP – {cp_name}',
        'closing_manager': '*Client Name:* {client_name}\n*CM Name:* {cm_name}\n*CP Firm:* {cp_firm}\n*SM:* {sm_name}\n\n*Visited On:* {visited_on}\n\n*Current Residence:* {current_residence}\n*Residence Location:* {residence_location}\n*Work Location:* {work_location}\n*Ethnicity:* {ethnicity}\n\n*Typology:* {typology}\n*Carpet Area:* {carpet_area} sq.ft\n*OCR:* {ocr}\n\n*Loan Requirement:* {loan_requirement}\n*Loan Eligibility:* {loan_eligibility}\n\n*Purpose of Buying:* {purpose}\n*Budget:* {budget}\n\n*TCO Offered:* {tco_offered}\n*TCO Expectation:* {tco_expectation}\n\n*Detailed Remarks:*\n{remarks}\n\n*Senior Intervention:* {senior_intervention}',
    }


def normalize_configuration_name(config_str):
    """
    Normalize configuration string to handle variations like:
    - "1BHK", "1bhk", "1 BHK", "1 bhk", "1Bhk"
    - "1 or 2 BHK", "1/2 BHK", "1bhk/2bhk"
    - "1/2/3 BHK"
    Returns normalized string for matching
    """
    if not config_str:
        return ''
    
    # Convert to uppercase and remove extra spaces
    normalized = str(config_str).upper().strip()
    
    # Remove common separators and normalize
    normalized = normalized.replace('/', ' ').replace('-', ' ').replace('OR', ' ').replace('AND', ' ')
    
    # Remove extra spaces
    normalized = ' '.join(normalized.split())
    
    # Normalize BHK variations
    normalized = re.sub(r'\s*BHK\s*', ' BHK ', normalized, flags=re.IGNORECASE)
    normalized = normalized.strip()
    
    return normalized


def match_configuration(config_str, project):
    """
    Match configuration string to ProjectConfiguration objects using NLP-like fuzzy matching.
    Handles flexible matching for variations with improved intelligence.
    """
    if not config_str:
        return None
    
    from projects.models import ProjectConfiguration
    import logging
    from difflib import SequenceMatcher
    logger = logging.getLogger(__name__)
    
    config_str = str(config_str).strip()
    if not config_str:
        return None
    
    # Normalize the input
    normalized_input = normalize_configuration_name(config_str)
    
    # Get all configurations for this project
    all_configs = list(project.configurations.all())
    
    if not all_configs:
        logger.warning(f"No configurations found for project '{project.name}' (ID: {project.id})")
        return None
    
    # Extract key numbers from input (e.g., "1", "2" from "1 or 2 BHK")
    input_numbers = set(re.findall(r'\d+', normalized_input))
    
    # Score each configuration
    best_match = None
    best_score = 0.0
    
    for config in all_configs:
        normalized_config = normalize_configuration_name(config.name)
        score = 0.0
        
        # 1. Exact match (highest priority)
        if normalized_input == normalized_config:
            logger.info(f"Exact match: '{config_str}' -> '{config.name}' for project '{project.name}'")
            return config
        
        # 2. Contains match (high priority)
        if normalized_input in normalized_config or normalized_config in normalized_input:
            score = 0.9
        # 3. Fuzzy string similarity (using SequenceMatcher)
        else:
            similarity = SequenceMatcher(None, normalized_input, normalized_config).ratio()
            score = similarity * 0.7
        
        # 4. Number matching boost
        config_numbers = set(re.findall(r'\d+', normalized_config))
        if input_numbers and config_numbers:
            # Calculate number overlap
            overlap = len(input_numbers & config_numbers) / max(len(input_numbers), len(config_numbers))
            score += overlap * 0.3
        
        # 5. Word overlap (for "1 or 2 BHK" matching "1BHK" or "2BHK")
        input_words = set(normalized_input.split())
        config_words = set(normalized_config.split())
        if input_words and config_words:
            word_overlap = len(input_words & config_words) / max(len(input_words), len(config_words))
            score += word_overlap * 0.2
        
        if score > best_score:
            best_score = score
            best_match = config
    
    # Threshold for acceptance (0.5 = 50% similarity)
    if best_match and best_score >= 0.5:
        logger.info(f"Fuzzy match (score: {best_score:.2f}): '{config_str}' -> '{best_match.name}' for project '{project.name}'")
        return best_match
    
    logger.warning(f"No match found for configuration '{config_str}' in project '{project.name}'. Available: {[c.name for c in all_configs]}")
    return None


def parse_budget(budget_str):
    """
    Parse budget string with flexible handling.
    Handles:
    - "35-40 L", "35-40L", "35L", "35 L"
    - "1.2-1.3 Cr", "1.2Cr", "1.2 Cr"
    - "5000000" (direct rupees)
    - "Open Budget", "Low Budget"
    Returns Decimal or None
    """
    if not budget_str:
        return None
    
    budget_str = str(budget_str).strip()
    if not budget_str:
        return None
    
    # Extract numbers and units using regex
    # Pattern: number(s) followed by unit (L/Cr) or just numbers
    budget_pattern = r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*([LC]R?|LAKHS?|CRORES?)'
    match = re.search(budget_pattern, budget_str, re.IGNORECASE)
    
    if match:
        # Range format: "35-40 L" or "1.2-1.3 Cr"
        lower = float(match.group(1))
        upper = float(match.group(2))
        unit = match.group(3).upper()
        
        # Use average of range
        avg = (lower + upper) / 2
        
        if 'CR' in unit or 'CRORE' in unit:
            return Decimal(str(avg * 10000000))
        elif 'L' in unit or 'LAKH' in unit:
            return Decimal(str(avg * 100000))
    
    # Single number with unit: "35L", "1.2Cr"
    single_pattern = r'(\d+\.?\d*)\s*([LC]R?|LAKHS?|CRORES?)'
    match = re.search(single_pattern, budget_str, re.IGNORECASE)
    if match:
        value = float(match.group(1))
        unit = match.group(2).upper()
        
        if 'CR' in unit or 'CRORE' in unit:
            return Decimal(str(value * 10000000))
        elif 'L' in unit or 'LAKH' in unit:
            return Decimal(str(value * 100000))
    
    # Pure number (assume rupees): "5000000"
    number_only = re.search(r'(\d+\.?\d*)', budget_str)
    if number_only:
        try:
            return Decimal(number_only.group(1))
        except:
            pass
    
    # Handle "Open Budget" and "Low Budget"
    if budget_str.lower() in ['open budget', 'open', 'low budget', 'low']:
        return None  # Will be stored in notes
    
    try:
        # Clean the string
        budget_clean = budget_str.replace(' ', '').replace(',', '').upper()
        
        # Handle lakhs
        if 'L' in budget_clean or 'LAKH' in budget_clean:
            numbers = re.findall(r'\d+\.?\d*', budget_clean)
            if numbers:
                # If range, take average
                avg = sum(float(n) for n in numbers) / len(numbers)
                return Decimal(avg * 100000)
        
        # Handle crores
        elif 'CR' in budget_clean or 'CRORE' in budget_clean:
            numbers = re.findall(r'\d+\.?\d*', budget_clean)
            if numbers:
                avg = sum(float(n) for n in numbers) / len(numbers)
                return Decimal(avg * 10000000)
        
        # Try direct number parsing
        else:
            numbers = re.findall(r'\d+\.?\d*', budget_clean)
            if numbers:
                avg = sum(float(n) for n in numbers) / len(numbers)
                # If it's a large number (> 100000), assume it's already in rupees
                if avg >= 100000:
                    return Decimal(avg)
                # Otherwise assume lakhs
                elif avg < 100:
                    return Decimal(avg * 100000)
                else:
                    # Could be in thousands, assume lakhs
                    return Decimal(avg * 100000)
    except Exception:
        return None
    
    return None
