import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the base directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def get_database_url():
    """
    Get database URL with support for multiple database types.
    
    Supports:
    - SQLite (default): sqlite:////app/data/users.db
    - MySQL: mysql+pymysql://user:pass@host:port/dbname
    - PostgreSQL: postgresql://user:pass@host:port/dbname
    
    Set DATABASE_URL environment variable to use MySQL/PostgreSQL.
    """
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        # Handle Heroku-style postgres:// URLs
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        return db_url
    
    # Default to SQLite
    return 'sqlite:////app/data/users.db'

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    APP_NAME = os.environ.get('APP_NAME') or 'Image Scale Hub'
    APP_VERSION = os.environ.get('APP_VERSION') or '1.0.0'
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # Database - supports SQLite, MySQL, PostgreSQL
    SQLALCHEMY_DATABASE_URI = get_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Verify connections before use
        'pool_recycle': 300,    # Recycle connections every 5 minutes
    }
    
    # Upload settings
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_FILE_SIZE', '10485760'))  # 10MB default
    ALLOWED_EXTENSIONS = os.environ.get('ALLOWED_EXTENSIONS', 'jpg,jpeg,png,webp,gif,bmp').split(',')
    
    # Storage limits (per user, in MB)
    DEFAULT_STORAGE_LIMIT_MB = int(os.environ.get('DEFAULT_STORAGE_LIMIT_MB', '100'))
    
    # Security
    SESSION_TIMEOUT = int(os.environ.get('SESSION_TIMEOUT', '1800'))  # 30 minutes
    MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', '5'))
    LOCKOUT_DURATION = int(os.environ.get('LOCKOUT_DURATION', '900'))  # 15 minutes
    
    # Email/SMTP Configuration
    # Supports: SMTP, Gmail, SendGrid, Mailgun, AWS SES
    MAIL_PROVIDER = os.environ.get('MAIL_PROVIDER', 'smtp')  # smtp, sendgrid, mailgun, ses
    
    # SMTP Settings
    SMTP_SERVER = os.environ.get('SMTP_SERVER', '')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    SMTP_FROM_EMAIL = os.environ.get('SMTP_FROM_EMAIL', '')
    SMTP_FROM_NAME = os.environ.get('SMTP_FROM_NAME', 'Scorpio Image Resizer')
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'True').lower() == 'true'
    SMTP_USE_SSL = os.environ.get('SMTP_USE_SSL', 'False').lower() == 'true'
    
    # SendGrid (alternative to SMTP)
    SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
    
    # Mailgun (alternative to SMTP)
    MAILGUN_API_KEY = os.environ.get('MAILGUN_API_KEY', '')
    MAILGUN_DOMAIN = os.environ.get('MAILGUN_DOMAIN', '')
    
    # AWS SES (alternative to SMTP)
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
    AWS_SES_REGION = os.environ.get('AWS_SES_REGION', 'us-east-1')
    
    # Image processing
    PROCESSING_MODE = os.environ.get('PROCESSING_MODE', 'hybrid')  # server, client, hybrid
    IMAGE_STORAGE_MODE = os.environ.get('IMAGE_STORAGE_MODE', 'private')  # private, public
    
    # Update settings
    UPDATE_CHECK_URL = os.environ.get('UPDATE_CHECK_URL', '')
    ENABLE_AUTO_UPDATE = os.environ.get('ENABLE_AUTO_UPDATE', 'True').lower() == 'true'
    
    # Registration
    ENABLE_REGISTRATION = os.environ.get('ENABLE_REGISTRATION', 'False').lower() == 'true'
    
    # SSL/Domain
    FORCE_HTTPS = os.environ.get('FORCE_HTTPS', 'False').lower() == 'true'
    CUSTOM_DOMAIN = os.environ.get('CUSTOM_DOMAIN', '')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:////app/data/users_dev.db'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    # In production, ensure these are set via environment variables
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'production-secret-key-change-me'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on FLASK_CONFIG environment variable"""
    config_name = os.environ.get('FLASK_CONFIG', 'default')
    return config.get(config_name, config['default'])