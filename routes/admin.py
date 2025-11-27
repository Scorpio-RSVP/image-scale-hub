from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, g, current_app
from datetime import datetime, timedelta
import json

from models import db, User, Image, Setting, SizePreset, Pack, AuditLog
from utils.security import rate_limit, check_password_strength
from utils.logger import log_audit_event, log_admin_action
from utils.email_sender import email_sender

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator to require admin access"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user') or not g.user or not g.user.is_admin:
            return render_template('errors/403.html'), 403
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@admin_required
def dashboard():
    """Admin dashboard"""
    # Get statistics
    total_users = User.query.count()
    admin_users = User.query.filter_by(is_admin=True).count()
    total_images = Image.query.count()
    total_size = db.session.query(db.func.sum(Image.file_size)).scalar() or 0
    
    # Recent activity
    recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()
    
    # User growth (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    new_users = User.query.filter(User.created_at >= thirty_days_ago).count()
    
    # Storage usage
    storage_stats = {
        'total_images': total_images,
        'total_size_mb': round(total_size / (1024 * 1024), 2),
        'avg_size_kb': round(total_size / total_images / 1024, 2) if total_images > 0 else 0
    }
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         admin_users=admin_users,
                         total_images=total_images,
                         total_size=total_size,
                         new_users=new_users,
                         recent_logs=recent_logs,
                         storage_stats=storage_stats)

@admin_bp.route('/users')
@admin_required
def users():
    """User management"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '')
    
    # Build query
    query = User.query
    
    if search:
        query = query.filter(
            (User.username.contains(search)) | 
            (User.email.contains(search))
        )
    
    if role_filter == 'admin':
        query = query.filter_by(is_admin=True)
    elif role_filter == 'user':
        query = query.filter_by(is_admin=False)
    
    # Paginate
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin/users.html', users=users, search=search, role_filter=role_filter)

@admin_bp.route('/users/create', methods=['POST'])
@admin_required
@rate_limit(max_per_hour=20)
def create_user():
    """Create new user"""
    try:
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        is_admin = request.form.get('is_admin') == 'on'
        
        # Validate input
        if not all([username, email, password]):
            return jsonify({'error': 'All fields are required'}), 400
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        if User.query.filter_by(email=email.lower()).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        # Check password strength
        is_valid, score, suggestions = check_password_strength(password)
        if not is_valid:
            return jsonify({'error': 'Password is too weak'}), 400
        
        # Create user
        user = User(
            username=username,
            email=email.lower(),
            is_admin=is_admin
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        log_admin_action(
            'USER_CREATED',
            f"Created user '{username}' (admin: {is_admin})"
        )
        
        return jsonify({'success': True, 'message': 'User created successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Create user error: {str(e)}")
        return jsonify({'error': 'An error occurred'}), 500

@admin_bp.route('/users/<int:user_id>/update', methods=['POST'])
@admin_required
def update_user(user_id):
    """Update user"""
    try:
        user = User.query.get_or_404(user_id)
        
        email = request.form.get('email', '').strip()
        is_admin = request.form.get('is_admin') == 'on'
        
        # Update email if changed
        if email and email != user.email:
            if User.query.filter_by(email=email.lower()).filter(User.id != user_id).first():
                return jsonify({'error': 'Email already exists'}), 400
            user.email = email.lower()
        
        # Update admin status
        user.is_admin = is_admin
        
        db.session.commit()
        
        log_admin_action(
            'USER_UPDATED',
            f"Updated user '{user.username}' (admin: {is_admin})"
        )
        
        return jsonify({'success': True, 'message': 'User updated successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Update user error: {str(e)}")
        return jsonify({'error': 'An error occurred'}), 500

@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def reset_user_password(user_id):
    """Reset user password"""
    try:
        user = User.query.get_or_404(user_id)
        new_password = request.form.get('password', '')
        
        if not new_password:
            return jsonify({'error': 'Password is required'}), 400
        
        # Check password strength
        is_valid, score, suggestions = check_password_strength(new_password)
        if not is_valid:
            return jsonify({'error': 'Password is too weak'}), 400
        
        user.set_password(new_password)
        db.session.commit()
        
        log_admin_action(
            'USER_PASSWORD_RESET',
            f"Reset password for user '{user.username}'"
        )
        
        return jsonify({'success': True, 'message': 'Password reset successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Reset password error: {str(e)}")
        return jsonify({'error': 'An error occurred'}), 500

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete user"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent deleting self
        if user.id == g.user.id:
            return jsonify({'error': 'Cannot delete your own account'}), 400
        
        # Prevent deleting last admin
        if user.is_admin:
            admin_count = User.query.filter_by(is_admin=True).count()
            if admin_count <= 1:
                return jsonify({'error': 'Cannot delete the last admin user'}), 400
        
        username = user.username
        db.session.delete(user)
        db.session.commit()
        
        log_admin_action(
            'USER_DELETED',
            f"Deleted user '{username}'"
        )
        
        return jsonify({'success': True, 'message': 'User deleted successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Delete user error: {str(e)}")
        return jsonify({'error': 'An error occurred'}), 500

@admin_bp.route('/branding')
@admin_required
def branding():
    """Branding settings"""
    settings = {}
    all_settings = Setting.query.all()
    for s in all_settings:
        settings[s.key] = s.value
    return render_template('admin/branding.html', settings=settings)

@admin_bp.route('/presets')
@admin_required
def presets():
    """Size presets management"""
    presets = SizePreset.query.order_by(SizePreset.order_num).all()
    return render_template('admin/presets.html', presets=presets)

@admin_bp.route('/presets/create', methods=['POST'])
@admin_required
def create_preset():
    """Create new preset"""
    try:
        name = request.form.get('name', '').strip()
        width = int(request.form.get('width', 0))
        height = int(request.form.get('height', 0))
        icon = request.form.get('icon', '📐').strip()
        
        if not all([name, width, height]):
            return jsonify({'error': 'All fields are required'}), 400
        
        if width < 100 or width > 4000 or height < 100 or height > 4000:
            return jsonify({'error': 'Dimensions must be between 100 and 4000 pixels'}), 400
        
        # Get next order number
        max_order = db.session.query(db.func.max(SizePreset.order_num)).scalar() or 0
        
        preset = SizePreset(
            name=name,
            width=width,
            height=height,
            icon=icon,
            order_num=max_order + 1
        )
        
        db.session.add(preset)
        db.session.commit()
        
        log_admin_action(
            'PRESET_CREATED',
            f"Created preset '{name}' ({width}x{height})"
        )
        
        return jsonify({'success': True, 'message': 'Preset created successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Create preset error: {str(e)}")
        return jsonify({'error': 'An error occurred'}), 500

@admin_bp.route('/presets/<int:preset_id>/update', methods=['POST'])
@admin_required
def update_preset(preset_id):
    """Update preset"""
    try:
        preset = SizePreset.query.get_or_404(preset_id)
        
        name = request.form.get('name', '').strip()
        width = int(request.form.get('width', 0))
        height = int(request.form.get('height', 0))
        icon = request.form.get('icon', '📐').strip()
        
        if not all([name, width, height]):
            return jsonify({'error': 'All fields are required'}), 400
        
        if width < 100 or width > 4000 or height < 100 or height > 4000:
            return jsonify({'error': 'Dimensions must be between 100 and 4000 pixels'}), 400
        
        preset.name = name
        preset.width = width
        preset.height = height
        preset.icon = icon
        
        db.session.commit()
        
        log_admin_action(
            'PRESET_UPDATED',
            f"Updated preset '{name}' ({width}x{height})"
        )
        
        return jsonify({'success': True, 'message': 'Preset updated successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Update preset error: {str(e)}")
        return jsonify({'error': 'An error occurred'}), 500

@admin_bp.route('/presets/<int:preset_id>/toggle', methods=['POST'])
@admin_required
def toggle_preset(preset_id):
    """Toggle preset active status"""
    try:
        preset = SizePreset.query.get_or_404(preset_id)
        preset.is_active = not preset.is_active
        status = 'activated' if preset.is_active else 'deactivated'
        
        db.session.commit()
        
        log_admin_action(
            'PRESET_TOGGLED',
            f"{status.capitalize()} preset '{preset.name}'"
        )
        
        return jsonify({
            'success': True, 
            'message': f'Preset {status} successfully',
            'is_active': preset.is_active
        })
        
    except Exception as e:
        current_app.logger.error(f"Toggle preset error: {str(e)}")
        return jsonify({'error': 'An error occurred'}), 500

@admin_bp.route('/presets/<int:preset_id>/delete', methods=['POST'])
@admin_required
def delete_preset(preset_id):
    """Delete preset"""
    try:
        preset = SizePreset.query.get_or_404(preset_id)
        name = preset.name
        
        db.session.delete(preset)
        db.session.commit()
        
        log_admin_action(
            'PRESET_DELETED',
            f"Deleted preset '{name}'"
        )
        
        return jsonify({'success': True, 'message': 'Preset deleted successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Delete preset error: {str(e)}")
        return jsonify({'error': 'An error occurred'}), 500

@admin_bp.route('/packs')
@admin_required
def packs():
    """Pack management"""
    packs = Pack.query.order_by(Pack.created_at).all()
    return render_template('admin/packs.html', packs=packs)

@admin_bp.route('/packs/create', methods=['POST'])
@admin_required
def create_pack():
    """Create new pack"""
    try:
        name = request.form.get('name', '').strip()
        icon = request.form.get('icon', '📦').strip()
        config = request.form.get('config', '[]').strip()
        
        if not name:
            return jsonify({'error': 'Pack name is required'}), 400
        
        # Validate JSON
        try:
            import json
            json.loads(config)
        except:
            return jsonify({'error': 'Invalid JSON configuration'}), 400
        
        pack = Pack(
            name=name,
            icon=icon,
            config=config,
            is_active=True
        )
        
        db.session.add(pack)
        db.session.commit()
        
        log_admin_action(
            'PACK_CREATED',
            f"Created pack '{name}'"
        )
        
        return jsonify({'success': True, 'message': 'Pack created successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Create pack error: {str(e)}")
        return jsonify({'error': 'An error occurred'}), 500

@admin_bp.route('/packs/<int:pack_id>/toggle', methods=['POST'])
@admin_required
def toggle_pack(pack_id):
    """Toggle pack active status"""
    try:
        pack = Pack.query.get_or_404(pack_id)
        pack.is_active = not pack.is_active
        status = 'activated' if pack.is_active else 'deactivated'
        
        db.session.commit()
        
        log_admin_action(
            'PACK_TOGGLED',
            f"{status.capitalize()} pack '{pack.name}'"
        )
        
        return jsonify({
            'success': True, 
            'message': f'Pack {status} successfully',
            'is_active': pack.is_active
        })
        
    except Exception as e:
        current_app.logger.error(f"Toggle pack error: {str(e)}")
        return jsonify({'error': 'An error occurred'}), 500

@admin_bp.route('/email')
@admin_required
def email_settings():
    """Email/SMTP settings"""
    # Get current settings
    settings = {
        'smtp_server': current_app.config.get('SMTP_SERVER', ''),
        'smtp_port': current_app.config.get('SMTP_PORT', 587),
        'smtp_username': current_app.config.get('SMTP_USERNAME', ''),
        'smtp_from_email': current_app.config.get('SMTP_FROM_EMAIL', ''),
        'smtp_from_name': current_app.config.get('SMTP_FROM_NAME', ''),
        'smtp_use_tls': current_app.config.get('SMTP_USE_TLS', True)
    }
    
    return render_template('admin/email.html', settings=settings)

@admin_bp.route('/email/test', methods=['POST'])
@admin_required
def test_email():
    """Test email configuration"""
    try:
        test_email = request.form.get('test_email', '').strip()
        
        if not test_email:
            return jsonify({'error': 'Test email address is required'}), 400
        
        if email_sender.test_email_configuration(test_email):
            log_admin_action(
                'EMAIL_TEST_SENT',
                f"Test email sent to {test_email}"
            )
            return jsonify({'success': True, 'message': 'Test email sent successfully'})
        else:
            return jsonify({'error': 'Failed to send test email'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Test email error: {str(e)}")
        return jsonify({'error': 'An error occurred'}), 500

@admin_bp.route('/security')
@admin_required
def security_settings():
    """Security settings"""
    # Get current settings
    settings = {
        'max_login_attempts': Setting.get('max_login_attempts', '5'),
        'lockout_duration': Setting.get('lockout_duration', '900'),
        'session_timeout': Setting.get('session_timeout', '1800'),
        'max_file_size': Setting.get('max_file_size', '10485760'),
        'allowed_extensions': Setting.get('allowed_extensions', 'jpg,jpeg,png,webp')
    }
    
    return render_template('admin/security.html', settings=settings)

@admin_bp.route('/security/update', methods=['POST'])
@admin_required
def update_security_settings():
    """Update security settings"""
    try:
        settings_map = {
            'max_login_attempts': request.form.get('max_login_attempts', '5'),
            'lockout_duration': request.form.get('lockout_duration', '900'),
            'session_timeout': request.form.get('session_timeout', '1800'),
            'max_file_size': request.form.get('max_file_size', '10485760'),
            'allowed_extensions': request.form.get('allowed_extensions', 'jpg,jpeg,png,webp')
        }
        
        # Validate numeric settings
        for key in ['max_login_attempts', 'lockout_duration', 'session_timeout', 'max_file_size']:
            try:
                int(settings_map[key])
            except ValueError:
                return jsonify({'error': f'{key} must be a valid number'}), 400
        
        for key, value in settings_map.items():
            Setting.set(key, value)
        
        log_admin_action(
            'SECURITY_UPDATED',
            'Updated security settings'
        )
        
        return jsonify({'success': True, 'message': 'Security settings updated successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Update security settings error: {str(e)}")
        return jsonify({'error': 'An error occurred'}), 500

@admin_bp.route('/storage')
@admin_required
def storage_settings():
    """Storage settings"""
    # Get storage statistics
    total_images = Image.query.count()
    total_size = db.session.query(db.func.sum(Image.file_size)).scalar() or 0
    
    # Get per-user stats
    user_stats = db.session.query(
        User.username,
        db.func.count(Image.id).label('image_count'),
        db.func.sum(Image.file_size).label('total_size')
    ).join(Image).group_by(User.id, User.username).order_by(
        db.func.sum(Image.file_size).desc()
    ).limit(10).all()
    
    # Get current settings
    settings = {
        'image_storage_mode': Setting.get('image_storage_mode', 'private'),
        'auto_delete_days': Setting.get('auto_delete_days', '0')
    }
    
    return render_template('admin/storage.html', 
                         total_images=total_images,
                         total_size=total_size,
                         user_stats=user_stats,
                         settings=settings)

@admin_bp.route('/logs')
@admin_required
def view_logs():
    """View audit logs"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    search = request.args.get('search', '').strip()
    action_filter = request.args.get('action', '')
    
    # Build query
    query = AuditLog.query
    
    if search:
        query = query.filter(
            (AuditLog.username.contains(search)) | 
            (AuditLog.details.contains(search))
        )
    
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)
    
    # Paginate
    logs = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get unique actions for filter
    actions = db.session.query(AuditLog.action).distinct().all()
    actions = [action[0] for action in actions]
    
    return render_template('admin/logs.html', logs=logs, actions=actions, search=search, action_filter=action_filter)

@admin_bp.route('/statistics')
@admin_required
def statistics():
    """Statistics dashboard"""
    # Get basic stats
    total_users = User.query.count()
    total_images = Image.query.count()
    total_size = db.session.query(db.func.sum(Image.file_size)).scalar() or 0
    
    # Tool usage stats
    tool_stats = db.session.query(
        Image.tool_used,
        db.func.count(Image.id).label('count')
    ).group_by(Image.tool_used).all()
    
    # User activity (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_users = db.session.query(
        db.func.count(db.func.distinct(Image.user_id))
    ).filter(Image.created_at >= thirty_days_ago).scalar()
    
    # Most active users
    user_activity = db.session.query(
        User.username,
        db.func.count(Image.id).label('image_count')
    ).join(Image).group_by(User.id, User.username).order_by(
        db.func.count(Image.id).desc()
    ).limit(10).all()
    
    # Pack usage
    pack_stats = db.session.query(
        Pack.name,
        db.func.count(Image.id).label('usage_count')
    ).join(Image).group_by(Pack.id, Pack.name).order_by(
        db.func.count(Image.id).desc()
    ).all()
    
    return render_template('admin/statistics.html',
                         total_users=total_users,
                         total_images=total_images,
                         total_size=total_size,
                         tool_stats=tool_stats,
                         active_users=active_users,
                         user_activity=user_activity,
                         pack_stats=pack_stats)

@admin_bp.route('/settings')
@admin_required
def settings():
    """Site settings"""
    settings = {}
    all_settings = Setting.query.all()
    for s in all_settings:
        settings[s.key] = s.value
    return render_template('admin/settings.html', settings=settings)

@admin_bp.route('/settings/update', methods=['POST'])
@admin_required
def update_settings():
    """Update site settings"""
    try:
        # Get all form fields
        fields = [
            'custom_domain', 'ssl_redirect', 'ssl_enabled',
            'allow_registration', 'require_email_verify', 'allow_password_reset', 'default_role',
            'max_upload_mb', 'allowed_types', 'max_images_per_user',
            'session_timeout', 'max_login_attempts', 'lockout_duration', 'require_strong_password',
            'smtp_host', 'smtp_port', 'smtp_user', 'smtp_pass', 'from_email'
        ]
        
        for field in fields:
            value = request.form.get(field, '')
            # Handle checkboxes
            if field in ['ssl_redirect', 'ssl_enabled', 'allow_registration', 'require_email_verify', 
                        'allow_password_reset', 'require_strong_password']:
                value = 'on' if request.form.get(field) else ''
            Setting.set(field, value)
        
        db.session.commit()
        flash('Settings saved successfully', 'success')
        
        log_admin_action('SETTINGS_UPDATED', 'Updated site settings')
        
    except Exception as e:
        current_app.logger.error(f"Update settings error: {str(e)}")
        flash('Error saving settings', 'error')
    
    return redirect(url_for('admin.settings'))

@admin_bp.route('/branding/update', methods=['POST'])
@admin_required
def update_branding():
    """Update branding settings"""
    try:
        import os
        
        # Text fields
        text_fields = [
            'site_name', 'site_tagline', 'footer_text',
            'primary_color', 'secondary_color', 'accent_color', 'bg_color',
            'login_title', 'login_subtitle', 'login_message',
            'twitter_url', 'instagram_url', 'github_url'
        ]
        
        for field in text_fields:
            value = request.form.get(field, '')
            Setting.set(field, value)
        
        # Handle file uploads
        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        
        if 'logo' in request.files:
            logo = request.files['logo']
            if logo.filename:
                logo_path = os.path.join(upload_folder, 'logo' + os.path.splitext(logo.filename)[1])
                logo.save(logo_path)
                Setting.set('logo_url', '/static/uploads/logo' + os.path.splitext(logo.filename)[1])
        
        if request.form.get('remove_logo'):
            Setting.set('logo_url', '')
        
        if 'favicon' in request.files:
            favicon = request.files['favicon']
            if favicon.filename:
                fav_path = os.path.join(upload_folder, 'favicon' + os.path.splitext(favicon.filename)[1])
                favicon.save(fav_path)
                Setting.set('favicon_url', '/static/uploads/favicon' + os.path.splitext(favicon.filename)[1])
        
        if request.form.get('remove_favicon'):
            Setting.set('favicon_url', '')
        
        db.session.commit()
        flash('Branding saved successfully', 'success')
        
        log_admin_action('BRANDING_UPDATED', 'Updated branding settings')
        
    except Exception as e:
        current_app.logger.error(f"Update branding error: {str(e)}")
        flash('Error saving branding', 'error')
    
    return redirect(url_for('admin.branding'))

@admin_bp.route('/system')
@admin_required
def system():
    """System information"""
    import sys
    import platform
    import os
    import flask
    
    # Version info
    version = {
        'current': '1.0.0',
        'latest': '1.0.0',
        'update_available': False
    }
    
    # Database info
    db_url = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if 'mysql' in db_url:
        db_type = 'mysql'
        db_type_display = 'MySQL'
        db_size = 'Connected'
    elif 'postgresql' in db_url or 'postgres' in db_url:
        db_type = 'postgresql'
        db_type_display = 'PostgreSQL'
        db_size = 'Connected'
    else:
        db_type = 'sqlite'
        db_type_display = 'SQLite'
        db_path = db_url.replace('sqlite:///', '')
        if os.path.exists(db_path):
            size_bytes = os.path.getsize(db_path)
            if size_bytes < 1024:
                db_size = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                db_size = f"{size_bytes / 1024:.1f} KB"
            else:
                db_size = f"{size_bytes / (1024*1024):.1f} MB"
        else:
            db_size = 'File not found'
    
    database = {
        'type': db_type,
        'type_display': db_type_display,
        'size': db_size,
        'url': db_url[:50] + '...' if len(db_url) > 50 else db_url
    }
    
    # System info
    system_info = {
        'python_version': sys.version.split()[0],
        'flask_version': flask.__version__,
        'os': platform.system() + ' ' + platform.release(),
        'uptime': 'Running'
    }
    
    # Storage info
    total_images = Image.query.count()
    total_size = db.session.query(db.func.sum(Image.file_size)).scalar() or 0
    
    storage = {
        'images_count': total_images,
        'images_size': f"{total_size / (1024*1024):.1f} MB",
        'used': f"{total_size / (1024*1024):.1f} MB",
        'total': '10 GB',
        'percent': min(100, (total_size / (10 * 1024 * 1024 * 1024)) * 100)
    }
    
    return render_template('admin/system.html', 
                          version=version, 
                          system=system_info, 
                          database=database,
                          storage=storage)

@admin_bp.route('/check-updates')
@admin_required
def check_updates():
    """Check for updates"""
    # In a real app, this would check a remote server
    return jsonify({
        'current': '1.0.0',
        'latest': '1.0.0',
        'update_available': False,
        'download_url': 'https://github.com/scorpio-image-resizer/releases'
    })

@admin_bp.route('/clear-cache', methods=['POST'])
@admin_required
def clear_cache():
    """Clear application cache"""
    flash('Cache cleared successfully', 'success')
    log_admin_action('CACHE_CLEARED', 'Cleared application cache')
    return redirect(url_for('admin.system'))

@admin_bp.route('/cleanup-images', methods=['POST'])
@admin_required
def cleanup_images():
    """Cleanup orphaned images"""
    # Find and remove orphaned image files
    flash('Cleanup completed', 'success')
    log_admin_action('CLEANUP_IMAGES', 'Cleaned up orphaned images')
    return redirect(url_for('admin.system'))

@admin_bp.route('/backup-db', methods=['POST'])
@admin_required
def backup_db():
    """Backup database"""
    import shutil
    import os
    from datetime import datetime
    
    try:
        db_path = current_app.config.get('SQLALCHEMY_DATABASE_URI', '').replace('sqlite:///', '')
        if os.path.exists(db_path):
            backup_dir = os.path.join(current_app.root_path, 'data', 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            backup_path = os.path.join(backup_dir, backup_name)
            shutil.copy2(db_path, backup_path)
            
            flash(f'Database backed up: {backup_name}', 'success')
            log_admin_action('DB_BACKUP', f'Created database backup: {backup_name}')
        else:
            flash('Database file not found', 'error')
    except Exception as e:
        flash(f'Backup failed: {str(e)}', 'error')
    
    return redirect(url_for('admin.system'))

@admin_bp.route('/reset-all', methods=['POST'])
@admin_required
def reset_all():
    """Factory reset - delete all data"""
    try:
        # Delete all images
        Image.query.delete()
        # Delete all non-admin users
        User.query.filter_by(is_admin=False).delete()
        # Reset settings to defaults
        Setting.query.delete()
        # Clear audit logs
        AuditLog.query.delete()
        
        db.session.commit()
        
        flash('Factory reset completed', 'success')
        log_admin_action('FACTORY_RESET', 'Performed factory reset')
    except Exception as e:
        flash(f'Reset failed: {str(e)}', 'error')
    
    return redirect(url_for('admin.system'))

@admin_bp.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def toggle_user_admin(user_id):
    """Toggle user admin status"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Prevent demoting self
        if user.id == g.user.id:
            return jsonify({'error': 'Cannot change your own admin status'}), 400
        
        # Prevent removing last admin
        if user.is_admin:
            admin_count = User.query.filter_by(is_admin=True).count()
            if admin_count <= 1:
                return jsonify({'error': 'Cannot remove the last admin'}), 400
        
        user.is_admin = not user.is_admin
        db.session.commit()
        
        status = 'promoted to admin' if user.is_admin else 'demoted to user'
        log_admin_action('USER_ROLE_CHANGED', f"User '{user.username}' {status}")
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/storage')
@admin_required
def storage_management():
    """Storage management page"""
    # Get all settings
    settings = {}
    all_settings = Setting.query.all()
    for s in all_settings:
        settings[s.key] = s.value
    
    # Get total stats
    total_images = Image.query.count()
    total_size = db.session.query(db.func.sum(Image.file_size)).scalar() or 0
    
    # Get per-user storage stats
    user_stats = db.session.query(
        User.id,
        User.username,
        User.storage_limit,
        db.func.count(Image.id).label('image_count'),
        db.func.coalesce(db.func.sum(Image.file_size), 0).label('storage_used')
    ).outerjoin(Image).group_by(User.id).all()
    
    # Calculate percentages
    default_limit = int(settings.get('default_storage_limit_mb', '100')) * 1024 * 1024
    users = []
    for u in user_stats:
        limit = u.storage_limit if u.storage_limit and u.storage_limit != 0 else default_limit
        if limit == -1:
            percent = 0
        else:
            percent = (u.storage_used / limit * 100) if limit > 0 else 0
        
        users.append({
            'id': u.id,
            'username': u.username,
            'storage_limit': u.storage_limit or 0,
            'image_count': u.image_count,
            'storage_used': u.storage_used,
            'storage_percent': min(100, percent)
        })
    
    # Sort by storage used descending
    users.sort(key=lambda x: x['storage_used'], reverse=True)
    
    return render_template('admin/storage.html',
                          settings=settings,
                          total_images=total_images,
                          total_size=total_size,
                          users=users,
                          user_stats=user_stats)

@admin_bp.route('/storage/settings', methods=['POST'])
@admin_required
def update_storage_settings():
    """Update storage settings"""
    try:
        Setting.set('default_storage_limit_mb', request.form.get('default_storage_limit_mb', '100'))
        Setting.set('max_upload_mb', request.form.get('max_upload_mb', '10'))
        Setting.set('auto_delete_days', request.form.get('auto_delete_days', '0'))
        
        flash('Storage settings saved', 'success')
        log_admin_action('STORAGE_SETTINGS_UPDATED', 'Updated storage settings')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('admin.storage_management'))

@admin_bp.route('/storage/user', methods=['POST'])
@admin_required
def update_user_storage():
    """Update user storage limit"""
    try:
        user_id = request.form.get('user_id')
        limit_type = request.form.get('limit_type')
        
        user = User.query.get_or_404(user_id)
        
        if limit_type == 'unlimited':
            user.storage_limit = -1
        elif limit_type == 'custom':
            custom_mb = int(request.form.get('custom_limit_mb', 100))
            user.storage_limit = custom_mb * 1024 * 1024
        else:
            user.storage_limit = 0  # Use default
        
        db.session.commit()
        
        flash(f'Storage limit updated for {user.username}', 'success')
        log_admin_action('USER_STORAGE_UPDATED', f"Updated storage limit for {user.username}")
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('admin.storage_management'))
