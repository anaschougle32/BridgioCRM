"""
SMS Adapter for OTP delivery
Supports multiple providers with fallback to WhatsApp deep link
"""
import json
import logging
from django.conf import settings
from .utils import get_sms_deep_link

logger = logging.getLogger(__name__)


class BaseSMSAdapter:
    """Base class for SMS adapters"""
    
    def send(self, phone, message):
        """
        Send SMS message
        Returns: dict with 'status' ('sent', 'failed', 'fallback') and optional 'response'
        """
        raise NotImplementedError


class WhatsAppDeepLinkAdapter(BaseSMSAdapter):
    """Fallback adapter using WhatsApp deep links (manual sending)"""
    
    def send(self, phone, message, project_name=None):
        """
        Generate WhatsApp deep link for manual sending
        Args:
            phone: Phone number
            message: Either a full message string OR a 6-digit OTP code
            project_name: Optional project name (used if message is an OTP)
        Returns dict with status='fallback' and 'whatsapp_link'
        """
        # Check if message is a 6-digit OTP code
        if isinstance(message, str) and len(message) == 6 and message.isdigit():
            # It's an OTP code - use get_sms_deep_link which formats it properly
            whatsapp_link = get_sms_deep_link(phone, message, project_name)
        else:
            # It's a full message - extract OTP if present, otherwise use message as-is
            otp = None
            if 'OTP:' in message or 'OTP is' in message:
                # Try to extract OTP from message
                import re
                match = re.search(r'OTP[:\s]*\*?(\d{6})\*?', message)
                if match:
                    otp = match.group(1)
                    whatsapp_link = get_sms_deep_link(phone, otp, project_name)
                else:
                    # Use message as-is
                    from .utils import get_whatsapp_link
                    whatsapp_link = get_whatsapp_link(phone, message)
            else:
                # Use message as-is
                from .utils import get_whatsapp_link
                whatsapp_link = get_whatsapp_link(phone, message)
        
        return {
            'status': 'fallback',
            'whatsapp_link': whatsapp_link,
            'message': 'WhatsApp deep link generated. Please send manually.',
        }


class TwilioSMSAdapter(BaseSMSAdapter):
    """Twilio SMS adapter"""
    
    def __init__(self):
        self.account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        self.auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        self.from_number = getattr(settings, 'TWILIO_PHONE_NUMBER', None)
        
        if not all([self.account_sid, self.auth_token, self.from_number]):
            raise ValueError("Twilio credentials not configured")
    
    def send(self, phone, message):
        """Send SMS via Twilio"""
        try:
            from twilio.rest import Client
            
            client = Client(self.account_sid, self.auth_token)
            
            # Use normalize_phone to format the number properly
            from .utils import normalize_phone
            clean_phone = normalize_phone(phone)
            
            # Validate that we have a proper international number
            if not clean_phone.startswith('+') or len(clean_phone) < 12:
                raise ValueError(f"Invalid phone number format: {phone}")
            
            message_obj = client.messages.create(
                body=message,
                from_=self.from_number,
                to=clean_phone
            )
            
            return {
                'status': 'sent',
                'sid': message_obj.sid,
                'response': message_obj.status,
            }
        except Exception as e:
            logger.error(f"Twilio SMS send failed: {str(e)}")
            # Fallback to WhatsApp
            return WhatsAppDeepLinkAdapter().send(phone, message)


class MSG91SMSAdapter(BaseSMSAdapter):
    """MSG91 SMS adapter"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'MSG91_API_KEY', None)
        self.sender_id = getattr(settings, 'MSG91_SENDER_ID', 'BRIDIO')
        
        if not self.api_key:
            raise ValueError("MSG91 API key not configured")
    
    def send(self, phone, message):
        """Send SMS via MSG91"""
        try:
            import requests
            
            # Format phone number
            clean_phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            if clean_phone.startswith('+91'):
                clean_phone = clean_phone[3:]
            elif clean_phone.startswith('91'):
                clean_phone = clean_phone[2:]
            elif clean_phone.startswith('0'):
                clean_phone = clean_phone[1:]
            
            url = "https://control.msg91.com/api/v5/flow/"
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "authkey": self.api_key
            }
            
            # MSG91 flow-based API (adjust based on your MSG91 setup)
            payload = {
                "template_id": getattr(settings, 'MSG91_TEMPLATE_ID', None),
                "short_url": "0",
                "recipients": [
                    {
                        "mobiles": clean_phone,
                        "OTP": message.split('OTP:')[1].strip().replace('*', '') if 'OTP:' in message else ''
                    }
                ]
            }
            
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            return {
                'status': 'sent',
                'response': response.json(),
            }
        except Exception as e:
            logger.error(f"MSG91 SMS send failed: {str(e)}")
            # Fallback to WhatsApp
            return WhatsAppDeepLinkAdapter().send(phone, message)


def get_sms_adapter():
    """
    Get the configured SMS adapter
    Falls back to WhatsApp deep link if no provider configured
    """
    sms_provider = getattr(settings, 'SMS_PROVIDER', 'whatsapp').lower()
    
    if sms_provider == 'twilio':
        try:
            return TwilioSMSAdapter()
        except ValueError:
            logger.warning("Twilio not configured, falling back to WhatsApp")
            return WhatsAppDeepLinkAdapter()
    elif sms_provider == 'msg91':
        try:
            return MSG91SMSAdapter()
        except ValueError:
            logger.warning("MSG91 not configured, falling back to WhatsApp")
            return WhatsAppDeepLinkAdapter()
    else:
        # Default: WhatsApp deep link (manual sending)
        return WhatsAppDeepLinkAdapter()


def send_sms(phone, message, project_name=None):
    """
    Convenience function to send SMS using configured adapter
    Args:
        phone: Phone number
        message: Either a full message string OR a 6-digit OTP code
        project_name: Optional project name (used if message is an OTP)
    Returns adapter response dict
    """
    adapter = get_sms_adapter()
    return adapter.send(phone, message, project_name=project_name)

