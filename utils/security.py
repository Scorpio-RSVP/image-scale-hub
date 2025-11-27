from functools import wraps
from flask import request, abort, session, g
from datetime import datetime, timedelta
import time

# Simple in-memory rate limiter
rate_limit_storage = {}

def rate_limit(max_per_hour, per_ip=True, per_user=False):
    """
    Rate limiting decorator.
    
    Args:
        max_per_hour: Maximum requests per hour
        per_ip: Limit per IP address
        per_user: Limit per user (requires authentication)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Build the rate limit key
            key_parts = [f.__name__]
            
            if per_ip:
                key_parts.append(request.remote_addr)
            
            if per_user and hasattr(g, 'user') and g.user:
                key_parts.append(str(g.user.id))
            
            key = ':'.join(key_parts)
            now = time.time()
            
            # Initialize storage for this key
            if key not in rate_limit_storage:
                rate_limit_storage[key] = []
            
            # Remove old entries (older than 1 hour)
            rate_limit_storage[key] = [
                t for t in rate_limit_storage[key]
                if now - t < 3600
            ]
            
            # Check if limit exceeded
            if len(rate_limit_storage[key]) >= max_per_hour:
                abort(429)  # Too Many Requests
            
            # Add current request
            rate_limit_storage[key].append(now)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_file_upload(file_data, filename, max_size=10485760, allowed_extensions=None):
    """
    Validate uploaded file for security.
    
    Args:
        file_data: Binary file data
        filename: Original filename
        max_size: Maximum file size in bytes
        allowed_extensions: List of allowed extensions
    
    Returns:
        True if valid
    
    Raises:
        Exception if invalid
    """
    # Check file size
    if len(file_data) > max_size:
        raise Exception(f"File too large. Maximum size: {max_size // (1024*1024)}MB")
    
    # Check file extension
    if allowed_extensions:
        file_ext = filename.lower().split('.')[-1]
        if file_ext not in [ext.lower() for ext in allowed_extensions]:
            raise Exception(f"File type not allowed. Allowed: {', '.join(allowed_extensions)}")
    
    # Check magic bytes to verify file type
    magic_bytes = {
        b'\xFF\xD8\xFF': 'jpg',
        b'\x89PNG\r\n\x1a\n': 'png',
        b'GIF87a': 'gif',
        b'GIF89a': 'gif',
        b'RIFF': 'webp',  # WebP files start with RIFF
    }
    
    is_valid_image = False
    for magic, ext in magic_bytes.items():
        if file_data.startswith(magic):
            is_valid_image = True
            break
    
    if not is_valid_image:
        raise Exception("Invalid file format")
    
    # Additional security: check for embedded scripts
    dangerous_patterns = [
        b'<script',
        b'javascript:',
        b'vbscript:',
        b'data:text/html',
        b'<?php',
        b'<%',
        b'eval(',
        b'exec(',
    ]
    
    for pattern in dangerous_patterns:
        if pattern in file_data.lower():
            raise Exception("Dangerous content detected in file")
    
    return True

def sanitize_filename(filename):
    """
    Sanitize filename to prevent directory traversal.
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    """
    import re
    import os
    
    # Remove directory separators
    filename = os.path.basename(filename)
    
    # Remove dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    # Ensure filename is not empty
    if not filename or filename in ('.', '..'):
        filename = 'unnamed_file'
    
    return filename

def generate_csrf_token():
    """
    Generate CSRF token for form protection.
    """
    import secrets
    return secrets.token_urlsafe(32)

def validate_csrf_token(token):
    """
    Validate CSRF token.
    """
    return token == session.get('csrf_token')

def get_client_ip():
    """
    Get client IP address, accounting for proxies.
    """
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0]
    elif request.headers.get("X-Real-IP"):
        return request.headers.get("X-Real-IP")
    else:
        return request.remote_addr

def is_safe_url(target):
    """
    Check if URL is safe for redirects.
    """
    from urllib.parse import urlparse
    
    ref_url = urlparse(request.host_url)
    test_url = urlparse(target)
    
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

def check_password_strength(password):
    """
    Check password strength.
    
    Args:
        password: Password to check
    
    Returns:
        (is_valid, score, suggestions)
    """
    suggestions = []
    score = 0
    
    # Length check
    if len(password) >= 8:
        score += 1
    else:
        suggestions.append("Use at least 8 characters")
    
    # Uppercase check
    if any(c.isupper() for c in password):
        score += 1
    else:
        suggestions.append("Include uppercase letters")
    
    # Lowercase check
    if any(c.islower() for c in password):
        score += 1
    else:
        suggestions.append("Include lowercase letters")
    
    # Numbers check
    if any(c.isdigit() for c in password):
        score += 1
    else:
        suggestions.append("Include numbers")
    
    # Special characters check
    if any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
        score += 1
    else:
        suggestions.append("Include special characters")
    
    # Common patterns check
    common_patterns = ['password', '123456', 'qwerty', 'admin', 'letmein']
    if any(pattern in password.lower() for pattern in common_patterns):
        score -= 2
        suggestions.append("Avoid common patterns")
    
    is_valid = score >= 3 and len(password) >= 6
    
    return is_valid, score, suggestions
