from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, g, send_file, current_app
from datetime import datetime
import io
import base64
import zipfile
from werkzeug.utils import secure_filename

from models import db, User, Image, SizePreset, Pack
from utils.image_processor import (
    add_blur_borders, compress_image, resize_image, process_pack,
    validate_image_file, get_image_info, format_file_size
)
from utils.security import rate_limit, sanitize_filename
from utils.logger import log_audit_event, log_image_processing

images_bp = Blueprint('images', __name__)

def login_required(f):
    """Decorator to require login"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user') or not g.user:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@images_bp.route('/app')
@login_required
def app():
    """Main application page"""
    # Get active presets
    presets = SizePreset.query.filter_by(is_active=True).order_by(SizePreset.order_num).all()
    
    # Get active packs
    packs = Pack.query.filter_by(is_active=True).order_by(Pack.created_at).all()
    
    return render_template('index.html', presets=presets, packs=packs)

@images_bp.route('/upload', methods=['POST'])
@login_required
@rate_limit(max_per_hour=100)
def upload_image():
    """Handle image upload"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Read file data
        file_data = file.read()
        filename = sanitize_filename(file.filename)
        
        # Validate file
        validate_image_file(
            file_data, 
            filename, 
            max_size=current_app.config.get('MAX_FILE_SIZE', 10485760),
            allowed_extensions=current_app.config.get('ALLOWED_EXTENSIONS', ['jpg', 'jpeg', 'png', 'webp'])
        )
        
        # Get image info
        image_info = get_image_info(file_data)
        
        # Store file data temporarily in session for processing
        session['uploaded_file'] = {
            'data': base64.b64encode(file_data).decode('utf-8'),
            'filename': filename,
            'info': image_info
        }
        
        log_audit_event(
            current_app.audit_logger,
            g.user.id,
            g.user.username,
            'IMAGE_UPLOADED',
            f"Uploaded {filename} ({format_file_size(len(file_data))})"
        )
        
        return jsonify({
            'success': True,
            'filename': filename,
            'info': image_info
        })
        
    except Exception as e:
        current_app.logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 400

@images_bp.route('/process-blur', methods=['POST'])
@login_required
@rate_limit(max_per_hour=50)
def process_blur():
    """Process image with blur effect"""
    try:
        # Get uploaded file from session
        uploaded_file = session.get('uploaded_file')
        if not uploaded_file:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file_data = base64.b64decode(uploaded_file['data'])
        original_filename = uploaded_file['filename']
        
        # Get processing parameters
        width = int(request.form.get('width', 1080))
        height = int(request.form.get('height', 1080))
        blur_amount = int(request.form.get('blur_amount', 30))
        custom_filename = request.form.get('custom_filename', '').strip()
        
        # Process image
        processed_data = add_blur_borders(file_data, width, height, blur_amount)
        
        # Generate filename
        if custom_filename:
            filename = f"{custom_filename}.png"
        else:
            name_without_ext = original_filename.rsplit('.', 1)[0]
            filename = f"{name_without_ext}-blur-{width}x{height}.png"
        
        # Save to database
        image = Image(
            user_id=g.user.id,
            original_filename=original_filename,
            saved_filename=filename,
            tool_used='blur',
            width=width,
            height=height,
            file_size=len(processed_data),
            image_data=processed_data
        )
        db.session.add(image)
        db.session.commit()
        
        # Convert to base64 for preview
        preview_data = base64.b64encode(processed_data).decode('utf-8')
        
        log_image_processing(
            'BLUR',
            f"Processed {original_filename} to {filename} ({width}x{height}, blur={blur_amount})"
        )
        
        return jsonify({
            'success': True,
            'image_id': image.id,
            'filename': filename,
            'preview': f"data:image/png;base64,{preview_data}",
            'size': format_file_size(len(processed_data)),
            'dimensions': f"{width} × {height}"
        })
        
    except Exception as e:
        current_app.logger.error(f"Blur processing error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@images_bp.route('/process-compress', methods=['POST'])
@login_required
@rate_limit(max_per_hour=50)
def process_compress():
    """Process image compression"""
    try:
        # Get uploaded file from session
        uploaded_file = session.get('uploaded_file')
        if not uploaded_file:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file_data = base64.b64decode(uploaded_file['data'])
        original_filename = uploaded_file['filename']
        original_size = len(file_data)
        
        # Get processing parameters
        compress_mode = request.form.get('compress_mode', 'quality')
        custom_filename = request.form.get('custom_filename', '').strip()
        
        if compress_mode == 'target_size':
            target_size_kb = int(request.form.get('target_size_kb', 500))
            processed_data, actual_size_kb, actual_quality = compress_image(file_data, target_size_kb=target_size_kb)
        else:
            quality = int(request.form.get('quality', 85))
            processed_data, actual_size_kb, actual_quality = compress_image(file_data, quality=quality)
        
        # Generate filename
        if custom_filename:
            filename = f"{custom_filename}.jpg"
        else:
            name_without_ext = original_filename.rsplit('.', 1)[0]
            filename = f"{name_without_ext}-compressed-{actual_size_kb}kb.jpg"
        
        # Save to database
        image = Image(
            user_id=g.user.id,
            original_filename=original_filename,
            saved_filename=filename,
            tool_used='compress',
            file_size=len(processed_data),
            image_data=processed_data
        )
        db.session.add(image)
        db.session.commit()
        
        # Convert to base64 for preview
        preview_data = base64.b64encode(processed_data).decode('utf-8')
        
        # Calculate compression stats
        space_saved = original_size - len(processed_data)
        percent_saved = round((space_saved / original_size) * 100, 1)
        
        log_image_processing(
            'COMPRESS',
            f"Compressed {original_filename} to {filename} ({format_file_size(len(processed_data))}, {percent_saved}% reduction)"
        )
        
        return jsonify({
            'success': True,
            'image_id': image.id,
            'filename': filename,
            'preview': f"data:image/jpeg;base64,{preview_data}",
            'original_size': format_file_size(original_size),
            'compressed_size': format_file_size(len(processed_data)),
            'space_saved': format_file_size(space_saved),
            'percent_saved': f"{percent_saved}%",
            'quality': actual_quality
        })
        
    except Exception as e:
        current_app.logger.error(f"Compression processing error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@images_bp.route('/process-resize', methods=['POST'])
@login_required
@rate_limit(max_per_hour=50)
def process_resize():
    """Process image resize"""
    try:
        # Get uploaded file from session
        uploaded_file = session.get('uploaded_file')
        if not uploaded_file:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file_data = base64.b64decode(uploaded_file['data'])
        original_filename = uploaded_file['filename']
        original_info = uploaded_file['info']
        
        # Get processing parameters
        resize_method = request.form.get('resize_method', 'percentage')
        custom_filename = request.form.get('custom_filename', '').strip()
        
        if resize_method == 'percentage':
            percentage = int(request.form.get('percentage', 50))
            processed_data, new_width, new_height = resize_image(file_data, percentage=percentage)
        elif resize_method == 'max_dimension':
            max_width = int(request.form.get('max_width', 1920))
            max_height = int(request.form.get('max_height', 1080))
            processed_data, new_width, new_height = resize_image(file_data, max_width=max_width, max_height=max_height)
        else:  # specific_size
            width = int(request.form.get('width', 1080))
            height = int(request.form.get('height', 720))
            processed_data, new_width, new_height = resize_image(file_data, width=width, height=height)
        
        # Generate filename
        if custom_filename:
            filename = f"{custom_filename}.png"
        else:
            name_without_ext = original_filename.rsplit('.', 1)[0]
            filename = f"{name_without_ext}-resized-{new_width}x{new_height}.png"
        
        # Save to database
        image = Image(
            user_id=g.user.id,
            original_filename=original_filename,
            saved_filename=filename,
            tool_used='resize',
            width=new_width,
            height=new_height,
            file_size=len(processed_data),
            image_data=processed_data
        )
        db.session.add(image)
        db.session.commit()
        
        # Convert to base64 for preview
        preview_data = base64.b64encode(processed_data).decode('utf-8')
        
        log_image_processing(
            'RESIZE',
            f"Resized {original_filename} to {filename} ({original_info['width']}x{original_info['height']} → {new_width}x{new_height})"
        )
        
        return jsonify({
            'success': True,
            'image_id': image.id,
            'filename': filename,
            'preview': f"data:image/png;base64,{preview_data}",
            'original_dimensions': f"{original_info['width']} × {original_info['height']}",
            'new_dimensions': f"{new_width} × {new_height}",
            'size': format_file_size(len(processed_data))
        })
        
    except Exception as e:
        current_app.logger.error(f"Resize processing error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@images_bp.route('/process-pack', methods=['POST'])
@login_required
@rate_limit(max_per_hour=30)
def process_pack():
    """Process image pack"""
    try:
        # Get uploaded file from session
        uploaded_file = session.get('uploaded_file')
        if not uploaded_file:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file_data = base64.b64decode(uploaded_file['data'])
        original_filename = uploaded_file['filename']
        
        # Get pack ID
        pack_id = int(request.form.get('pack_id'))
        pack = Pack.query.get_or_404(pack_id)
        
        if not pack.is_active:
            return jsonify({'error': 'Pack is not active'}), 400
        
        # Process pack
        pack_config = pack.get_config()
        results = process_pack(file_data, pack_config)
        
        # Save results to database
        saved_images = []
        for result in results:
            # Generate filename
            name_without_ext = original_filename.rsplit('.', 1)[0]
            filename = f"{name_without_ext}-{result['name'].lower().replace(' ', '-')}-{result['width']}x{result['height']}.png"
            
            image = Image(
                user_id=g.user.id,
                pack_id=pack.id,
                original_filename=original_filename,
                saved_filename=filename,
                tool_used='pack',
                width=result['width'],
                height=result['height'],
                file_size=result['size'],
                image_data=result['data']
            )
            db.session.add(image)
            saved_images.append(image)
        
        db.session.commit()
        
        # Prepare response
        response_results = []
        for i, result in enumerate(results):
            preview_data = base64.b64encode(result['data']).decode('utf-8')
            response_results.append({
                'image_id': saved_images[i].id,
                'name': result['name'],
                'filename': saved_images[i].saved_filename,
                'preview': f"data:image/png;base64,{preview_data}",
                'dimensions': f"{result['width']} × {result['height']}",
                'size': format_file_size(result['size'])
            })
        
        log_image_processing(
            'PACK',
            f"Processed pack '{pack.name}' for {original_filename} ({len(results)} outputs)"
        )
        
        return jsonify({
            'success': True,
            'pack_name': pack.name,
            'pack_icon': pack.icon,
            'results': response_results
        })
        
    except Exception as e:
        current_app.logger.error(f"Pack processing error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@images_bp.route('/my-files')
@login_required
def my_files():
    """Display user's files"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '').strip()
    tool_filter = request.args.get('tool', '')
    
    # Build query
    query = Image.query.filter_by(user_id=g.user.id)
    
    if search:
        query = query.filter(Image.original_filename.contains(search))
    
    if tool_filter and tool_filter != 'all':
        query = query.filter(Image.tool_used == tool_filter)
    
    # Paginate
    images = query.order_by(Image.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get statistics
    total_images = Image.query.filter_by(user_id=g.user.id).count()
    total_size = db.session.query(db.func.sum(Image.file_size)).filter_by(user_id=g.user.id).scalar() or 0
    
    return render_template('my_files.html', 
                         images=images,
                         total_images=total_images,
                         total_size=total_size,
                         search=search,
                         tool_filter=tool_filter)

@images_bp.route('/download/<int:image_id>')
@login_required
def download_image(image_id):
    """Download processed image"""
    image = Image.query.get_or_404(image_id)
    
    # Check ownership
    if image.user_id != g.user.id and not g.user.is_admin:
        flash('You do not have permission to download this image', 'error')
        return redirect(url_for('images.my_files'))
    
    # Create file-like object
    file_stream = io.BytesIO(image.image_data)
    
    log_audit_event(
        current_app.audit_logger,
        g.user.id,
        g.user.username,
        'IMAGE_DOWNLOADED',
        f"Downloaded {image.saved_filename}"
    )
    
    return send_file(
        file_stream,
        as_attachment=True,
        download_name=image.saved_filename,
        mimetype='image/png' if image.saved_filename.endswith('.png') else 'image/jpeg'
    )

@images_bp.route('/download-pack/<int:pack_id>')
@login_required
def download_pack(pack_id):
    """Download all images from a pack as ZIP"""
    pack = Pack.query.get_or_404(pack_id)
    
    # Get all images from this pack for this user
    images = Image.query.filter_by(user_id=g.user.id, pack_id=pack_id).all()
    
    if not images:
        flash('No images found for this pack', 'error')
        return redirect(url_for('images.my_files'))
    
    # Create ZIP file
    zip_stream = io.BytesIO()
    with zipfile.ZipFile(zip_stream, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for image in images:
            zip_file.writestr(image.saved_filename, image.image_data)
    
    zip_stream.seek(0)
    
    log_audit_event(
        current_app.audit_logger,
        g.user.id,
        g.user.username,
        'PACK_DOWNLOADED',
        f"Downloaded pack '{pack.name}' ({len(images)} images)"
    )
    
    return send_file(
        zip_stream,
        as_attachment=True,
        download_name=f"{pack.name.replace(' ', '_')}_images.zip",
        mimetype='application/zip'
    )

@images_bp.route('/download-all')
@login_required
def download_all():
    """Download all user images as ZIP"""
    images = Image.query.filter_by(user_id=g.user.id).all()
    
    if not images:
        flash('No images to download', 'error')
        return redirect(url_for('images.my_files'))
    
    # Create ZIP file
    zip_stream = io.BytesIO()
    with zipfile.ZipFile(zip_stream, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for image in images:
            zip_file.writestr(image.saved_filename, image.image_data)
    
    zip_stream.seek(0)
    
    log_audit_event(
        current_app.audit_logger,
        g.user.id,
        g.user.username,
        'ALL_IMAGES_DOWNLOADED',
        f"Downloaded all images ({len(images)} files)"
    )
    
    return send_file(
        zip_stream,
        as_attachment=True,
        download_name=f"scorpio_images_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
        mimetype='application/zip'
    )

@images_bp.route('/delete-image/<int:image_id>', methods=['POST'])
@login_required
def delete_image(image_id):
    """Delete an image"""
    image = Image.query.get_or_404(image_id)
    
    # Check ownership
    if image.user_id != g.user.id and not g.user.is_admin:
        return jsonify({'error': 'Permission denied'}), 403
    
    filename = image.saved_filename
    db.session.delete(image)
    db.session.commit()
    
    log_audit_event(
        current_app.audit_logger,
        g.user.id,
        g.user.username,
        'IMAGE_DELETED',
        f"Deleted {filename}"
    )
    
    return jsonify({'success': True, 'message': 'Image deleted successfully'})

@images_bp.route('/delete-pack/<int:pack_id>', methods=['POST'])
@login_required
def delete_pack(pack_id):
    """Delete all images from a pack"""
    pack = Pack.query.get_or_404(pack_id)
    
    # Get all images from this pack for this user
    images = Image.query.filter_by(user_id=g.user.id, pack_id=pack_id).all()
    
    if not images:
        return jsonify({'error': 'No images found for this pack'}), 404
    
    count = len(images)
    for image in images:
        db.session.delete(image)
    
    db.session.commit()
    
    log_audit_event(
        current_app.audit_logger,
        g.user.id,
        g.user.username,
        'PACK_DELETED',
        f"Deleted pack '{pack.name}' ({count} images)"
    )
    
    return jsonify({'success': True, 'message': f'Pack deleted successfully ({count} images)'})

@images_bp.route('/clear-all', methods=['POST'])
@login_required
def clear_all():
    """Clear all user images"""
    images = Image.query.filter_by(user_id=g.user.id).all()
    
    count = len(images)
    for image in images:
        db.session.delete(image)
    
    db.session.commit()
    
    log_audit_event(
        current_app.audit_logger,
        g.user.id,
        g.user.username,
        'ALL_IMAGES_DELETED',
        f"Cleared all images ({count} files)"
    )
    
    return jsonify({'success': True, 'message': f'All images cleared ({count} files)'})
