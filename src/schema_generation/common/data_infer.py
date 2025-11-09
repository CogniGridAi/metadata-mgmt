import re
import json
from typing import Tuple, Optional
from datetime import datetime
from decimal import Decimal, InvalidOperation

def infer_types(value: str) -> Tuple[Optional[str], str]:
    """
    Infer both business type (semantic) and data type (primitive) of a value.
    
    Returns:
        Tuple[business_type, data_type]
        - business_type: Semantic meaning (email, url, phone_number, etc.) or None
        - data_type: Primitive type (string, integer, float, boolean, null, etc.)
    """
    if not value or value.strip() == '':
        return None, 'null'
    
    value = value.strip()
    original_value = value
    
    # 1. Boolean (data type, not business type)
    if value.lower() in ('true', 'false', '1', '0', 'yes', 'no', 'y', 'n', 't', 'f'):
        return None, 'boolean'
    
    # 2. UUID (business type)
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if re.match(uuid_pattern, value, re.IGNORECASE):
        return 'uuid', 'string'
    
    # 3. Email (business type)
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(email_pattern, value):
        return 'email', 'string'
    
    # 4. URL (business type)
    url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    if re.match(url_pattern, value, re.IGNORECASE):
        return 'url', 'string'
    
    # 5. IP Address IPv4 (business type)
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ipv4_pattern, value):
        parts = value.split('.')
        if all(0 <= int(p) <= 255 for p in parts):
            return 'ip_address', 'string'
    
    # 6. IP Address IPv6 (business type)
    ipv6_pattern = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
    if re.match(ipv6_pattern, value):
        return 'ipv6_address', 'string'
    
    # 7. MAC Address (business type)
    mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
    if re.match(mac_pattern, value):
        return 'mac_address', 'string'
    
    # 8. Credit Card (business type)
    cc_cleaned = re.sub(r'[\s-]', '', value)
    if re.match(r'^\d{13,19}$', cc_cleaned):
        return 'credit_card', 'string'
    
    # 9. Phone Number (business type)
    phone_patterns = [
        r'^\+?[\d\s\-\(\)]{10,}$',
        r'^\d{3}-\d{3}-\d{4}$',
        r'^\(\d{3}\)\s?\d{3}-\d{4}$',
        r'^\+\d{1,3}[\s\-]?\d{1,4}[\s\-]?\d{1,4}[\s\-]?\d{1,9}$',
    ]
    if any(re.match(pattern, value) for pattern in phone_patterns):
        return 'phone_number', 'string'
    
    # 10. JSON (business type)
    if (value.startswith('{') and value.endswith('}')) or \
       (value.startswith('[') and value.endswith(']')):
        try:
            json.loads(value)
            return 'json', 'string'
        except (json.JSONDecodeError, ValueError):
            pass
    
    # 11. Array/List (business type)
    if ',' in value and not re.match(r'^-?\d+\.?\d*,\d+\.?\d*$', value):
        parts = [p.strip() for p in value.split(',')]
        if len(parts) > 1:
            return 'array', 'string'
    
    # 12. Percentage (business type)
    if value.endswith('%'):
        num_part = value[:-1].strip()
        try:
            float(num_part)
            return 'percentage', 'number'
        except ValueError:
            pass
    
    # 13. Currency (business type)
    currency_pattern = r'^[\$€£¥₹]\s?[\d,]+\.?\d*$'
    if re.match(currency_pattern, value):
        return 'currency', 'string'
    
    # 14. Date/Time formats
    date_time_formats = [
        '%Y-%m-%d',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%S.%f%z',
        '%m/%d/%Y',
        '%m-%d-%Y',
        '%m/%d/%Y %H:%M:%S',
        '%d/%m/%Y',
        '%d-%m-%Y',
        '%d/%m/%Y %H:%M:%S',
        '%Y/%m/%d',
        '%d.%m.%Y',
        '%Y.%m.%d',
        '%H:%M:%S',
        '%H:%M',
    ]
    
    # Check if it's a datetime
    for fmt in date_time_formats:
        try:
            datetime.strptime(value, fmt)
            if 'T' in fmt or ' ' in fmt or '%H' in fmt:
                return 'datetime', 'datetime'
            else:
                return 'date', 'date'
        except ValueError:
            continue
    
    # Check if it's a Unix timestamp
    try:
        timestamp = float(value)
        if 0 <= timestamp <= 4102444800:
            dt = datetime.fromtimestamp(timestamp)
            return 'timestamp', 'number'
    except (ValueError, OSError, OverflowError):
        pass
    
    # 15. Integer (data type)
    try:
        int_val = int(value)
        data_type = 'integer'
        # Could also check for business types like age, count, etc. if needed
        return None, data_type
    except ValueError:
        pass
    
    # 16. Float/Number (data type)
    try:
        float(value)
        if 'e' in value.lower():
            return None, 'number'  # scientific notation
        if '.' in value:
            return None, 'float'
        return None, 'number'
    except ValueError:
        pass
    
    # 17. Decimal (data type)
    try:
        Decimal(value)
        return None, 'decimal'
    except (InvalidOperation, ValueError):
        pass
    
    # 18. Postal Code / ZIP Code (business type)
    postal_patterns = [
        r'^\d{5}(-\d{4})?$',
        r'^[A-Z]\d[A-Z]\s?\d[A-Z]\d$',
        r'^[A-Z]{1,2}\d{1,2}\s?\d[A-Z]{2}$',
    ]
    if any(re.match(pattern, value, re.IGNORECASE) for pattern in postal_patterns):
        return 'postal_code', 'string'
    
    # 19. ISBN (business type)
    isbn_pattern = r'^(ISBN[- ]?)?(\d{10}|\d{13})$'
    if re.match(isbn_pattern, value):
        return 'isbn', 'string'
    
    # 20. Base64 (business type)
    base64_pattern = r'^[A-Za-z0-9+/]+=*$'
    if len(value) % 4 == 0 and re.match(base64_pattern, value) and len(value) > 20:
        return 'base64', 'string'
    
    # 21. Hex color code (business type)
    hex_color_pattern = r'^#?[0-9A-Fa-f]{6}$'
    if re.match(hex_color_pattern, value):
        return 'hex_color', 'string'
    
    # 22. Default to string (data type)
    return None, 'string'
