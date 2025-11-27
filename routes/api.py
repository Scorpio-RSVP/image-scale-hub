from flask import Blueprint, jsonify, g
from datetime import datetime, timedelta

from models import db, User, Image, SizePreset, Pack, Setting
from utils.security import rate_limit

api_bp = Blueprint('api', __name__)

def api_auth_required(f):
    """Decorator to require API authentication"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # For now, use session auth (can be extended to API keys later)
        if not hasattr(g, 'user') or not g.user:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

@api_bp.route('/presets')
@rate_limit(max_per_hour=100)
def get_presets():
    """Get active size presets"""
    presets = SizePreset.query.filter_by(is_active=True).order_by(SizePreset.order_num).all()
    
    return jsonify({
        'success': True,
        'presets': [preset.to_dict() for preset in presets]
    })

@api_bp.route('/packs')
@rate_limit(max_per_hour=100)
def get_packs():
    """Get active packs"""
    packs = Pack.query.filter_by(is_active=True).order_by(Pack.created_at).all()
    
    return jsonify({
        'success': True,
        'packs': [pack.to_dict() for pack in packs]
    })

@api_bp.route('/images')
@api_auth_required
@rate_limit(max_per_hour=200)
def get_images():
    """Get user's images"""
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 20)), 100)
    tool_filter = request.args.get('tool', '')
    
    # Build query
    query = Image.query.filter_by(user_id=g.user.id)
    
    if tool_filter and tool_filter != 'all':
        query = query.filter(Image.tool_used == tool_filter)
    
    # Paginate
    images = query.order_by(Image.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'success': True,
        'images': [image.to_dict() for image in images.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': images.total,
            'pages': images.pages,
            'has_next': images.has_next,
            'has_prev': images.has_prev
        }
    })

@api_bp.route('/images/<int:image_id>')
@api_auth_required
@rate_limit(max_per_hour=200)
def get_image(image_id):
    """Get specific image"""
    image = Image.query.get_or_404(image_id)
    
    # Check ownership
    if image.user_id != g.user.id and not g.user.is_admin:
        return jsonify({'error': 'Permission denied'}), 403
    
    return jsonify({
        'success': True,
        'image': image.to_dict()
    })

@api_bp.route('/stats')
@api_auth_required
@rate_limit(max_per_hour=50)
def get_user_stats():
    """Get user statistics"""
    total_images = Image.query.filter_by(user_id=g.user.id).count()
    total_size = db.session.query(db.func.sum(Image.file_size)).filter_by(user_id=g.user.id).scalar() or 0
    
    # Tool usage breakdown
    tool_stats = db.session.query(
        Image.tool_used,
        db.func.count(Image.id).label('count')
    ).filter_by(user_id=g.user.id).group_by(Image.tool_used).all()
    
    # Recent activity (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_images = Image.query.filter(
        Image.user_id == g.user.id,
        Image.created_at >= seven_days_ago
    ).count()
    
    return jsonify({
        'success': True,
        'stats': {
            'total_images': total_images,
            'total_size': total_size,
            'recent_images': recent_images,
            'tool_breakdown': {stat.tool_used: stat.count for stat in tool_stats}
        }
    })

@api_bp.route('/settings')
@rate_limit(max_per_hour=50)
def get_settings():
    """Get public application settings"""
    settings = {
        'app_name': Setting.get('app_name', 'Scorpio Image Resizer'),
        'app_tagline': Setting.get('app_tagline', 'Professional Image Processing'),
        'max_file_size': int(Setting.get('max_file_size', '10485760')),
        'allowed_extensions': Setting.get('allowed_extensions', 'jpg,jpeg,png,webp').split(','),
        'version': current_app.config.get('APP_VERSION', '1.0.0')
    }
    
    return jsonify({
        'success': True,
        'settings': settings
    })

@api_bp.route('/health')
@rate_limit(max_per_hour=1000)
def health_check():
    """API health check"""
    # Check database connection
    try:
        db.session.execute('SELECT 1')
        db_status = 'healthy'
    except:
        db_status = 'unhealthy'
    
    return jsonify({
        'status': 'healthy' if db_status == 'healthy' else 'unhealthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': current_app.config.get('APP_VERSION', '1.0.0'),
        'database': db_status
    })

# Import request for API routes
from flask import request

@api_bp.route('/images/<int:image_id>', methods=['DELETE'])
@api_auth_required
@rate_limit(max_per_hour=50)
def delete_image_api(image_id):
    """Delete image via API"""
    image = Image.query.get_or_404(image_id)
    
    # Check ownership
    if image.user_id != g.user.id and not g.user.is_admin:
        return jsonify({'error': 'Permission denied'}), 403
    
    filename = image.saved_filename
    db.session.delete(image)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Image deleted successfully'
    })

@api_bp.route('/upload-url', methods=['POST'])
@api_auth_required
@rate_limit(max_per_hour=50)
def get_upload_url():
    """Get temporary upload URL (placeholder for future implementation)"""
    return jsonify({
        'success': True,
        'message': 'Direct upload not implemented yet',
        'upload_method': 'form_post'
    })
