"""
Utility functions for Channel Partner upload column mapping
"""

def _create_cp_column_mapper(headers):
    """
    Create an intelligent column mapper for CP uploads that auto-detects column names.
    Returns a function that can extract values by field name and a field_to_index mapping.
    """
    # Normalize headers: strip, lowercase, remove special chars
    normalized_headers = {}
    for idx, header in enumerate(headers):
        if header:
            normalized = str(header).strip().lower().replace('_', ' ').replace('-', ' ')
            normalized_headers[normalized] = idx
    
    # Define field mappings with common variations for CP fields
    field_mappings = {
        'name': ['name', 'cp name', 'channel partner name', 'cp', 'partner name', 'broker name', 'contact name'],
        'firm_name': ['firm name', 'firm', 'company name', 'company', 'organization', 'org', 'agency name'],
        'phone': ['phone', 'mobile', 'contact', 'contact number', 'phone number', 'mobile number', 'cell', 'cell phone', 'whatsapp', 'whatsapp number', 'phone 1', 'primary phone'],
        'phone2': ['phone 2', 'phone2', 'secondary phone', 'alternate phone', 'mobile 2', 'contact 2'],
        'locality': ['locality', 'area', 'location', 'city', 'address', 'working area', 'service area'],
        'team_size': ['team size', 'team', 'employees', 'staff', 'team members', 'no of employees'],
        'owner_name': ['owner name', 'owner', 'proprietor name', 'proprietor', 'director name', 'manager name'],
        'owner_number': ['owner number', 'owner phone', 'owner mobile', 'proprietor phone', 'director phone'],
        'rera_id': ['rera id', 'rera', 'rera number', 'rera registration', 'rera registration number'],
        'status': ['status', 'active', 'inactive', 'state'],
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

