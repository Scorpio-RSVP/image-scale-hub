import logging
import os
from datetime import datetime
from flask import request, g

def setup_logging(app):
    """
    Setup application logging.
    
    Args:
        app: Flask application instance
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configure logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Setup file handler for error logs
    error_handler = logging.FileHandler('logs/error.log')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(log_format))
    
    # Setup file handler for access logs
    access_handler = logging.FileHandler('logs/access.log')
    access_handler.setLevel(logging.INFO)
    access_handler.setFormatter(logging.Formatter(log_format))
    
    # Setup audit log handler
    audit_handler = logging.FileHandler('logs/audit.log')
    audit_handler.setLevel(logging.INFO)
    audit_handler.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
    
    # Add handlers to app logger
    app.logger.addHandler(error_handler)
    app.logger.addHandler(access_handler)
    
    # Create audit logger
    audit_logger = logging.getLogger('audit')
    audit_logger.addHandler(audit_handler)
    audit_logger.setLevel(logging.INFO)
    
    return audit_logger

def log_audit_event(audit_logger, user_id, username, action, details=None, ip_address=None, user_agent=None):
    """
    Log audit event.
    
    Args:
        audit_logger: Audit logger instance
        user_id: User ID (or None)
        username: Username (or None)
        action: Action performed
        details: Additional details
        ip_address: Client IP address
        user_agent: User agent string
    """
    if not ip_address:
        ip_address = get_client_ip()
    
    if not user_agent:
        user_agent = request.headers.get('User-Agent', 'Unknown')
    
    message = f"USER: {username or 'Anonymous'} ({ip_address}) | ACTION: {action}"
    
    if details:
        message += f" | DETAILS: {details}"
    
    audit_logger.info(message)

def log_security_event(audit_logger, event_type, details, severity='WARNING'):
    """
    Log security event.
    
    Args:
        audit_logger: Audit logger instance
        event_type: Type of security event
        details: Event details
        severity: Event severity
    """
    message = f"SECURITY: {event_type} | {details} | IP: {get_client_ip()}"
    
    if severity == 'CRITICAL':
        audit_logger.error(message)
    else:
        audit_logger.warning(message)

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

def log_request_start():
    """
    Log the start of a request.
    """
    app_logger = logging.getLogger(__name__)
    app_logger.info(f"Request: {request.method} {request.path} from {get_client_ip()}")

def log_request_end(response):
    """
    Log the end of a request.
    """
    app_logger = logging.getLogger(__name__)
    app_logger.info(f"Response: {response.status_code} for {request.method} {request.path}")
    return response

def log_error(error):
    """
    Log application error.
    """
    app_logger = logging.getLogger(__name__)
    app_logger.error(f"Error in {request.endpoint}: {str(error)}", exc_info=True)

def log_database_operation(operation, table, details=None):
    """
    Log database operation.
    
    Args:
        operation: Type of operation (CREATE, UPDATE, DELETE)
        table: Table name
        details: Additional details
    """
    app_logger = logging.getLogger(__name__)
    message = f"DB: {operation} on {table}"
    
    if details:
        message += f" | {details}"
    
    if hasattr(g, 'user') and g.user:
        message += f" | User: {g.user.username}"
    
    app_logger.info(message)

def log_image_processing(operation, details):
    """
    Log image processing operation.
    
    Args:
        operation: Type of operation (BLUR, COMPRESS, RESIZE, PACK)
        details: Processing details
    """
    app_logger = logging.getLogger(__name__)
    message = f"IMAGE: {operation} | {details}"
    
    if hasattr(g, 'user') and g.user:
        message += f" | User: {g.user.username}"
    
    app_logger.info(message)

def log_admin_action(action, details):
    """
    Log admin action.
    
    Args:
        action: Admin action performed
        details: Action details
    """
    app_logger = logging.getLogger(__name__)
    message = f"ADMIN: {action} | {details}"
    
    if hasattr(g, 'user') and g.user:
        message += f" | Admin: {g.user.username}"
    
    app_logger.info(message)

def cleanup_old_logs(days_to_keep=30):
    """
    Clean up old log files.
    
    Args:
        days_to_keep: Number of days to keep logs
    """
    import glob
    from datetime import datetime, timedelta
    
    logs_dir = 'logs'
    if not os.path.exists(logs_dir):
        return
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    for log_file in glob.glob(os.path.join(logs_dir, '*.log*')):
        try:
            file_time = datetime.fromtimestamp(os.path.getmtime(log_file))
            if file_time < cutoff_date:
                os.remove(log_file)
                print(f"Removed old log file: {log_file}")
        except Exception as e:
            print(f"Error removing log file {log_file}: {e}")

def get_log_stats():
    """
    Get statistics about log files.
    
    Returns:
        Dict with log statistics
    """
    import glob
    import os
    
    logs_dir = 'logs'
    if not os.path.exists(logs_dir):
        return {}
    
    stats = {}
    total_size = 0
    
    for log_file in glob.glob(os.path.join(logs_dir, '*.log')):
        try:
            file_size = os.path.getsize(log_file)
            file_name = os.path.basename(log_file)
            stats[file_name] = {
                'size': file_size,
                'size_human': format_file_size(file_size),
                'modified': datetime.fromtimestamp(os.path.getmtime(log_file)).isoformat()
            }
            total_size += file_size
        except Exception:
            continue
    
    stats['total_size'] = total_size
    stats['total_size_human'] = format_file_size(total_size)
    
    return stats

def format_file_size(size_bytes):
    """
    Format file size in human readable format.
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Formatted string
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
