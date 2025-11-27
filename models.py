from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import json

db = SQLAlchemy()

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    images = db.relationship('Image', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_locked(self):
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pack_id = db.Column(db.Integer, db.ForeignKey('pack.id'), nullable=True)
    original_filename = db.Column(db.String(255), nullable=False)
    saved_filename = db.Column(db.String(255), nullable=False)
    tool_used = db.Column(db.String(20), nullable=False)  # 'blur', 'compress', 'resize', 'pack'
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    image_data = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    pack = db.relationship('Pack', backref='images')

class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def get(key, default=None):
        setting = Setting.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @staticmethod
    def set(key, value):
        setting = Setting.query.filter_by(key=key).first()
        if setting:
            setting.value = value
        else:
            setting = Setting(key=key, value=value)
            db.session.add(setting)
        db.session.commit()
        return setting

class SizePreset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    icon = db.Column(db.String(10), default='📐')
    is_active = db.Column(db.Boolean, default=True)
    order_num = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Pack(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(10), default='📦')
    is_active = db.Column(db.Boolean, default=True)
    config = db.Column(db.Text, nullable=False)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_config(self):
        return json.loads(self.config) if self.config else []

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    username = db.Column(db.String(80), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='audit_logs')

class PasswordReset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='password_resets')
    
    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)

def init_default_data():
    """Initialize default data in database"""
    # Add default settings if they don't exist
    default_settings = {
        'app_tagline': 'Professional Image Processing',
        'copyright_text': '© 2025 Image Scale Hub'
    }
    
    for key, value in default_settings.items():
        if not Setting.query.filter_by(key=key).first():
            setting = Setting(key=key, value=value)
            db.session.add(setting)
    
    # Add default presets if none exist
    if SizePreset.query.count() == 0:
        presets = [
            # Social Media
            SizePreset(name='Square', width=1080, height=1080, icon='⬜', order_num=1),
            SizePreset(name='Portrait', width=1080, height=1350, icon='📱', order_num=2),
            SizePreset(name='Story', width=1080, height=1920, icon='📲', order_num=3),
            SizePreset(name='FB Post', width=1200, height=630, icon='👍', order_num=4),
            SizePreset(name='FB Cover', width=820, height=312, icon='📘', order_num=5),
            SizePreset(name='Twitter Header', width=1500, height=500, icon='🐦', order_num=6),
            SizePreset(name='YouTube Thumb', width=1280, height=720, icon='▶️', order_num=7),
            # Tixr
            SizePreset(name='Tixr Header', width=284, height=168, icon='🎟️', order_num=8),
            SizePreset(name='Tixr Vertical', width=1080, height=1350, icon='🎫', order_num=9),
            # Other
            SizePreset(name='HD Landscape', width=1920, height=1080, icon='🖥️', order_num=10),
            SizePreset(name='Profile Pic', width=400, height=400, icon='👤', order_num=11),
            SizePreset(name='Linktree', width=1080, height=1080, icon='🔗', order_num=12),
        ]
        for preset in presets:
            db.session.add(preset)
    
    db.session.commit()
