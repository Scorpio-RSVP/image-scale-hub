from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, g, current_app
from datetime import datetime, timedelta
import re

from models import db, User, AuditLog, PasswordReset, Image
from utils.security import rate_limit, validate_csrf_token, check_password_strength, is_safe_url
from utils.email_sender import email_sender
from utils.logger import log_audit_event, log_security_event

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
@rate_limit(max_per_hour=30)
def login():
    """Handle user login"""
    if request.method == 'GET':
        # Redirect if already logged in
        if hasattr(g, 'user') and g.user:
            next_url = request.args.get('next')
            if next_url and is_safe_url(next_url):
                return redirect(next_url)
            return redirect(url_for('images.app'))
        
        return render_template('login.html')
    
    elif request.method == 'POST':
        try:
            # Get form data
            username_or_email = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            remember = request.form.get('remember') == 'on'
            
            # Validate input
            if not username_or_email or not password:
                flash('Please enter username/email and password', 'error')
                return render_template('login.html')
            
            # Find user by username or email
            user = User.query.filter(
                (User.username == username_or_email) | 
                (User.email == username_or_email.lower())
            ).first()
            
            # Check if user exists and password is correct
            if not user or not user.check_password(password):
                log_security_event(
                    current_app.audit_logger,
                    'LOGIN_FAILED',
                    f"Invalid credentials for: {username_or_email}"
                )
                flash('Invalid username/email or password', 'error')
                return render_template('login.html')
            
            # Check if account is locked
            if user.is_locked():
                flash('Account is temporarily locked. Please try again later.', 'error')
                return render_template('login.html')
            
            # Reset failed attempts on successful login
            if user.failed_login_attempts > 0:
                user.failed_login_attempts = 0
                user.locked_until = None
            
            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Create session
            session['user_id'] = user.id
            session.permanent = remember
            
            # Log successful login
            log_audit_event(
                current_app.audit_logger,
                user.id,
                user.username,
                'LOGIN_SUCCESS',
                f"User logged in from {request.remote_addr}"
            )
            
            # Redirect to intended URL or default
            next_url = request.form.get('next') or request.args.get('next')
            if next_url and is_safe_url(next_url):
                return redirect(next_url)
            return redirect(url_for('images.app'))
            
        except Exception as e:
            current_app.logger.error(f"Login error: {str(e)}")
            flash('An error occurred during login. Please try again.', 'error')
            return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """Handle user logout"""
    user_id = session.get('user_id')
    username = getattr(g.user, 'username', 'Unknown') if hasattr(g, 'user') else 'Unknown'
    
    # Clear session
    session.clear()
    
    # Log logout
    if user_id:
        log_audit_event(
            current_app.audit_logger,
            user_id,
            username,
            'LOGOUT',
            f"User logged out from {request.remote_addr}"
        )
    
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@rate_limit(max_per_hour=5)
def forgot_password():
    """Handle password reset requests"""
    if request.method == 'GET':
        return render_template('forgot_password.html')
    
    elif request.method == 'POST':
        try:
            username_or_email = request.form.get('username', '').strip()
            
            if not username_or_email:
                flash('Please enter your username or email address', 'error')
                return render_template('forgot_password.html')
            
            # Find user
            user = User.query.filter(
                (User.username == username_or_email) | 
                (User.email == username_or_email.lower())
            ).first()
            
            if user:
                # Create password reset token
                reset_token = PasswordReset.create_token(user.id)
                
                # Send reset email
                if email_sender.send_password_reset(user, reset_token.token):
                    log_audit_event(
                        current_app.audit_logger,
                        user.id,
                        user.username,
                        'PASSWORD_RESET_REQUESTED',
                        f"Password reset requested from {request.remote_addr}"
                    )
                    flash('Password reset instructions have been sent to your email address.', 'success')
                else:
                    flash('Failed to send reset email. Please try again later.', 'error')
            else:
                # Don't reveal if user exists or not
                flash('If an account exists with that username/email, password reset instructions have been sent.', 'info')
            
            return render_template('forgot_password.html')
            
        except Exception as e:
            current_app.logger.error(f"Forgot password error: {str(e)}")
            flash('An error occurred. Please try again.', 'error')
            return render_template('forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
@rate_limit(max_per_hour=10)
def reset_password(token):
    """Handle password reset"""
    # Find valid token
    reset_token = PasswordReset.query.filter_by(token=token).first()
    
    if not reset_token or not reset_token.is_valid():
        flash('Invalid or expired reset token. Please request a new password reset.', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'GET':
        return render_template('reset_password.html', token=token)
    
    elif request.method == 'POST':
        try:
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            # Validate passwords
            if not password or not confirm_password:
                flash('Please enter and confirm your new password', 'error')
                return render_template('reset_password.html', token=token)
            
            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return render_template('reset_password.html', token=token)
            
            # Check password strength
            is_valid, score, suggestions = check_password_strength(password)
            if not is_valid:
                flash('Password is too weak. ' + '; '.join(suggestions[:2]), 'error')
                return render_template('reset_password.html', token=token)
            
            # Update user password
            user = reset_token.user
            user.set_password(password)
            
            # Mark token as used
            reset_token.used = True
            
            # Reset failed login attempts
            user.failed_login_attempts = 0
            user.locked_until = None
            
            db.session.commit()
            
            # Log password reset
            log_audit_event(
                current_app.audit_logger,
                user.id,
                user.username,
                'PASSWORD_RESET_COMPLETED',
                f"Password reset completed from {request.remote_addr}"
            )
            
            flash('Your password has been reset successfully. You can now log in with your new password.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            current_app.logger.error(f"Reset password error: {str(e)}")
            flash('An error occurred. Please try again.', 'error')
            return render_template('reset_password.html', token=token)

@auth_bp.route('/register', methods=['GET', 'POST'])
@rate_limit(max_per_hour=5)
def register():
    """Handle user registration (if enabled)"""
    # Check if registration is enabled
    registration_enabled = current_app.config.get('ENABLE_REGISTRATION', False)
    if not registration_enabled:
        flash('User registration is currently disabled.', 'error')
        return redirect(url_for('auth.login'))
    
    if request.method == 'GET':
        return render_template('register.html')
    
    elif request.method == 'POST':
        try:
            # Get form data
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            # Validate input
            if not all([username, email, password, confirm_password]):
                flash('Please fill in all fields', 'error')
                return render_template('register.html')
            
            # Validate email format
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                flash('Invalid email address', 'error')
                return render_template('register.html')
            
            # Validate username
            if len(username) < 3 or len(username) > 20:
                flash('Username must be between 3 and 20 characters', 'error')
                return render_template('register.html')
            
            if not re.match(r'^[a-zA-Z0-9_]+$', username):
                flash('Username can only contain letters, numbers, and underscores', 'error')
                return render_template('register.html')
            
            # Check if passwords match
            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return render_template('register.html')
            
            # Check password strength
            is_valid, score, suggestions = check_password_strength(password)
            if not is_valid:
                flash('Password is too weak. ' + '; '.join(suggestions[:2]), 'error')
                return render_template('register.html')
            
            # Check if user already exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists', 'error')
                return render_template('register.html')
            
            if User.query.filter_by(email=email.lower()).first():
                flash('Email address already registered', 'error')
                return render_template('register.html')
            
            # Create new user
            user = User(
                username=username,
                email=email.lower(),
                is_admin=False
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            # Log user creation
            log_audit_event(
                current_app.audit_logger,
                user.id,
                user.username,
                'USER_REGISTERED',
                f"New user registered from {request.remote_addr}"
            )
            
            # Send welcome email
            try:
                email_sender.send_welcome_email(user)
            except Exception as e:
                current_app.logger.warning(f"Failed to send welcome email: {str(e)}")
            
            flash('Account created successfully! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            current_app.logger.error(f"Registration error: {str(e)}")
            flash('An error occurred during registration. Please try again.', 'error')
            return render_template('register.html')

@auth_bp.route('/profile')
def profile():
    """User profile page"""
    if not hasattr(g, 'user') or not g.user:
        return redirect(url_for('auth.login'))
    
    # Get user statistics
    total_images = Image.query.filter_by(user_id=g.user.id).count()
    total_size = db.session.query(db.func.sum(Image.file_size)).filter_by(user_id=g.user.id).scalar() or 0
    
    # Get recent images
    recent_images = Image.query.filter_by(user_id=g.user.id).order_by(Image.created_at.desc()).limit(5).all()
    
    return render_template('profile.html', 
                         total_images=total_images,
                         total_size=total_size,
                         recent_images=recent_images)

@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    """Change user password"""
    if not hasattr(g, 'user') or not g.user:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate current password
        if not g.user.check_password(current_password):
            log_security_event(
                current_app.audit_logger,
                'PASSWORD_CHANGE_FAILED',
                f"Invalid current password for user {g.user.username}"
            )
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        # Validate new password
        if new_password != confirm_password:
            return jsonify({'error': 'New passwords do not match'}), 400
        
        # Check password strength
        is_valid, score, suggestions = check_password_strength(new_password)
        if not is_valid:
            return jsonify({'error': 'Password is too weak. ' + '; '.join(suggestions[:2])}), 400
        
        # Update password
        g.user.set_password(new_password)
        db.session.commit()
        
        # Log password change
        log_audit_event(
            current_app.audit_logger,
            g.user.id,
            g.user.username,
            'PASSWORD_CHANGED',
            'User changed their password'
        )
        
        return jsonify({'success': True, 'message': 'Password changed successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Change password error: {str(e)}")
        return jsonify({'error': 'An error occurred'}), 500
