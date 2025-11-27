from flask import Flask, render_template, request, redirect, url_for, session, g, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import secrets

from config import config
from models import db, User, Image, Setting, SizePreset, Pack, AuditLog, PasswordReset, init_default_data
from utils.logger import setup_logging, log_audit_event, log_security_event
from utils.security import rate_limit, validate_csrf_token, generate_csrf_token, get_client_ip
from utils.email_sender import email_sender

# Create Flask app
def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    email_sender.init_app(app)
    
    # Setup logging
    audit_logger = setup_logging(app)
    
    # Make audit logger available to routes
    app.audit_logger = audit_logger
    
    # Before request handlers
    @app.before_request
    def before_request():
        # Log request start
        g.request_start_time = datetime.utcnow()
        g.client_ip = get_client_ip()
        
        # Set CSRF token for session
        if 'csrf_token' not in session:
            session['csrf_token'] = generate_csrf_token()
        
        # Load user if logged in
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
            if user and not user.is_locked():
                g.user = user
                # Update last login
                if user.last_login and (datetime.utcnow() - user.last_login).seconds > 3600:
                    user.last_login = datetime.utcnow()
                    db.session.commit()
            else:
                # Clear session if user not found or locked
                session.clear()
                g.user = None
    
    @app.after_request
    def after_request(response):
        # Log request end
        if hasattr(g, 'request_start_time'):
            duration = datetime.utcnow() - g.request_start_time
            app.logger.info(f"Request completed in {duration.total_seconds():.3f}s")
        return response
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Not found'}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f"Internal error: {error}", exc_info=True)
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        log_security_event(app.audit_logger, 'RATE_LIMIT_EXCEEDED', f"Path: {request.path}")
        return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
    
    # Helper functions
    def login_required(f):
        """Decorator to require login"""
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'user') or not g.user:
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Authentication required'}), 401
                return redirect(url_for('auth.login', next=request.url))
            return f(*args, **kwargs)
        return decorated_function
    
    def admin_required(f):
        """Decorator to require admin access"""
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'user') or not g.user or not g.user.is_admin:
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Admin access required'}), 403
                return render_template('errors/403.html'), 403
            return f(*args, **kwargs)
        return decorated_function
    
    # Make decorators available to templates
    app.jinja_env.globals['login_required'] = login_required
    app.jinja_env.globals['admin_required'] = admin_required
    
    # Template context processors
    @app.context_processor
    def inject_app_vars():
        """Inject global variables into templates"""
        return {
            'app_name': app.config.get('APP_NAME', 'Scorpio Image Resizer'),
            'app_version': app.config.get('APP_VERSION', '1.0.0'),
            'current_year': datetime.now().year,
            'Setting': Setting
        }
    
    @app.context_processor
    def inject_user():
        """Inject current user into templates"""
        return {'user': getattr(g, 'user', None)}
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.images import images_bp
    from routes.admin import admin_bp
    from routes.api import api_bp
    
    app.register_blueprint(auth_bp, url_prefix='/')
    app.register_blueprint(images_bp, url_prefix='/')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Main routes
    @app.route('/')
    def index():
        """Main application route"""
        if hasattr(g, 'user') and g.user:
            return redirect(url_for('images.app'))
        else:
            return redirect(url_for('auth.login'))
    
    @app.route('/health')
    def health_check():
        """Health check endpoint for Docker"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': app.config.get('APP_VERSION', '1.0.0')
        })
    
    @app.route('/favicon.ico')
    def favicon():
        """Serve favicon"""
        return send_file('static/images/favicon.ico')
    
    # Initialize database
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Initialize default data
        init_default_data()
        
        # Create default admin user if none exists
        if not User.query.filter_by(is_admin=True).first():
            admin_user = User(
                username='admin',
                email='admin@scorpiorsvp.com',
                is_admin=True
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            
            # Log without request context
            app.logger.info('Default admin user created during initialization')
    
    return app

# Create app instance
app = create_app(os.getenv('FLASK_CONFIG', 'default'))

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config.get('DEBUG', False)
    )
