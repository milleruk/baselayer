"""
Challenge-related utility functions.

Includes class ID extraction from URLs and other helpers.
"""
import re
from urllib.parse import urlparse, parse_qs, urlencode


def extract_class_id(url_or_id):
    """
    Extract Peloton class ID from a URL or return normalized ID.
    
    Handles multiple URL formats:
    - https://members.onepeloton.com/classes/cycling?modal=classDetailsModal&classId=xyz
    - https://members.onepeloton.co.uk/classes/all?modal=classDetailsModal&classId=xyz
    - https://members.onepeloton.com/classes/xyz (direct class page)
    - Bare class ID like 'xyz'
    
    Args:
        url_or_id (str): A Peloton class URL or class ID
    
    Returns:
        str: The normalized class ID
    
    Raises:
        ValueError: If URL format is invalid or no class ID found
    
    Examples:
        # From modal URL
        extract_class_id('https://members.onepeloton.com/classes/cycling?classId=abc123')
        # Returns: 'abc123'
        
        # From bare ID
        extract_class_id('abc123')
        # Returns: 'abc123'
        
        # From direct class page
        extract_class_id('https://members.onepeloton.com/classes/abc123')
        # Returns: 'abc123'
    """
    if not url_or_id or not isinstance(url_or_id, str):
        raise ValueError("url_or_id must be a non-empty string")
    
    url_or_id = url_or_id.strip()
    if not url_or_id:
        raise ValueError("url_or_id cannot be empty")
    
    # Check if it looks like a URL
    if url_or_id.startswith('http://') or url_or_id.startswith('https://'):
        try:
            parsed = urlparse(url_or_id)
            
            # Try to get classId from query parameters first
            query_params = parse_qs(parsed.query)
            if 'classId' in query_params:
                class_id = query_params['classId'][0]
                if class_id:
                    return class_id.strip()
            
            # Try to extract from path (e.g., /classes/abc123)
            # Match pattern like /classes/XXXXX or /classes/cycling/XXXXX
            path_match = re.search(r'/classes/(?:[^/?]+/)?([a-zA-Z0-9_-]+)(?:[/?]|$)', parsed.path)
            if path_match:
                class_id = path_match.group(1)
                if class_id and class_id != 'cycling' and class_id != 'all':
                    return class_id.strip()
            
            raise ValueError(f"No class ID found in URL: {url_or_id}")
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Error parsing URL: {e}")
    else:
        # Assume it's a bare class ID
        # Validate that it looks like a reasonable ID (alphanumeric, underscores, hyphens)
        class_id = url_or_id.strip()
        if not re.match(r'^[a-zA-Z0-9_-]+$', class_id):
            raise ValueError(f"Invalid class ID format: {class_id}")
        return class_id


def generate_peloton_url(class_id):
    """
    Generate a standardized Peloton class URL in UK format with modal.
    
    Args:
        class_id (str): The Peloton class ID
    
    Returns:
        str: The standardized Peloton URL
    
    Examples:
        generate_peloton_url('f9800c4a3df7410abf194c3d16eafa28')
        # Returns: 'https://members.onepeloton.co.uk/classes/all?modal=classDetailsModal&classId=f9800c4a3df7410abf194c3d16eafa28'
    """
    if not class_id or not isinstance(class_id, str):
        raise ValueError("class_id must be a non-empty string")
    
    class_id = class_id.strip()
    if not class_id:
        raise ValueError("class_id cannot be empty")
    
    # Validate that it looks like a reasonable ID
    if not re.match(r'^[a-zA-Z0-9_-]+$', class_id):
        raise ValueError(f"Invalid class ID format: {class_id}")
    
    # Generate standardized URL
    return f"https://members.onepeloton.co.uk/classes/all?modal=classDetailsModal&classId={class_id}"
