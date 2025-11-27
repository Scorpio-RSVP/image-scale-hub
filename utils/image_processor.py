from PIL import Image, ImageFilter, ImageOps
import io
import os
from datetime import datetime

def add_blur_borders(image_data, target_width, target_height, blur_amount=30):
    """
    Add blurred borders to image.
    
    Args:
        image_data: Binary image data
        target_width: Target canvas width
        target_height: Target canvas height
        blur_amount: Blur radius in pixels
    
    Returns:
        Binary data of processed image
    """
    try:
        # Open image from binary data
        img = Image.open(io.BytesIO(image_data))
        
        # Create canvas of target size
        canvas = Image.new('RGB', (target_width, target_height), (255, 255, 255))
        
        # Calculate scale to fit original image centered
        img_ratio = img.width / img.height
        canvas_ratio = target_width / target_height
        
        if img_ratio > canvas_ratio:
            # Image is wider, fit to width
            new_width = target_width
            new_height = int(target_width / img_ratio)
        else:
            # Image is taller, fit to height
            new_height = target_height
            new_width = int(target_height * img_ratio)
        
        # Resize original image for centered placement
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Create blurred background
        # Scale original to fill canvas, then blur
        if img.width / img.height > target_width / target_height:
            bg_height = target_height
            bg_width = int(target_height * (img.width / img.height))
        else:
            bg_width = target_width
            bg_height = int(target_width * (img.height / img.width))
        
        img_bg = img.resize((bg_width, bg_height), Image.Resampling.LANCZOS)
        img_blurred = img_bg.filter(ImageFilter.GaussianBlur(radius=blur_amount))
        
        # Calculate position to center blurred background
        bg_x = (target_width - bg_width) // 2
        bg_y = (target_height - bg_height) // 2
        
        # Paste blurred background
        canvas.paste(img_blurred, (bg_x, bg_y))
        
        # Calculate position to center sharp image
        img_x = (target_width - new_width) // 2
        img_y = (target_height - new_height) // 2
        
        # Paste sharp original over blurred background
        canvas.paste(img_resized, (img_x, img_y))
        
        # Convert to binary
        output = io.BytesIO()
        canvas.save(output, format='PNG', optimize=True)
        return output.getvalue()
        
    except Exception as e:
        raise Exception(f"Error processing blur: {str(e)}")

def compress_image(image_data, target_size_kb=None, quality=None):
    """
    Compress image to target size or quality.
    
    Args:
        image_data: Binary image data
        target_size_kb: Target file size in KB (or None)
        quality: JPEG quality 1-100 (or None)
    
    Returns:
        (binary_data, actual_size_kb, actual_quality)
    """
    try:
        img = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if necessary (for JPEG)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        if target_size_kb:
            # Binary search for quality that hits target size
            target_size_bytes = target_size_kb * 1024
            min_quality = 1
            max_quality = 100
            best_result = None
            
            while min_quality <= max_quality:
                mid_quality = (min_quality + max_quality) // 2
                
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=mid_quality, optimize=True)
                compressed_data = output.getvalue()
                compressed_size = len(compressed_data)
                
                if compressed_size <= target_size_bytes:
                    best_result = (compressed_data, compressed_size, mid_quality)
                    min_quality = mid_quality + 1  # Try higher quality
                else:
                    max_quality = mid_quality - 1  # Try lower quality
            
            if best_result:
                return best_result
            else:
                # If even quality 1 is too large, return quality 1 result
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=1, optimize=True)
                compressed_data = output.getvalue()
                return (compressed_data, len(compressed_data), 1)
        
        elif quality:
            # Compress with specified quality
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            compressed_data = output.getvalue()
            compressed_size = len(compressed_data)
            return (compressed_data, compressed_size, quality)
        
        else:
            # Default compression with quality 85
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            compressed_data = output.getvalue()
            compressed_size = len(compressed_data)
            return (compressed_data, compressed_size, 85)
            
    except Exception as e:
        raise Exception(f"Error compressing image: {str(e)}")

def resize_image(image_data, width=None, height=None, percentage=None, max_width=None, max_height=None):
    """
    Resize image maintaining aspect ratio.
    
    Args:
        image_data: Binary image data
        width: Specific width (height auto-calculated)
        height: Specific height (width auto-calculated)
        percentage: Scale percentage (1-100)
        max_width: Maximum width (maintains ratio)
        max_height: Maximum height (maintains ratio)
    
    Returns:
        (binary_data, new_width, new_height)
    """
    try:
        img = Image.open(io.BytesIO(image_data))
        original_width, original_height = img.size
        
        if percentage:
            # Scale by percentage
            scale = percentage / 100.0
            new_width = int(original_width * scale)
            new_height = int(original_height * scale)
        
        elif width and height:
            # Specific dimensions
            new_width = width
            new_height = height
        
        elif width:
            # Specific width, maintain aspect ratio
            new_width = width
            new_height = int(original_height * (width / original_width))
        
        elif height:
            # Specific height, maintain aspect ratio
            new_height = height
            new_width = int(original_width * (height / original_height))
        
        elif max_width or max_height:
            # Fit within maximum dimensions
            if max_width and max_height:
                # Both constraints
                scale = min(max_width / original_width, max_height / original_height)
            elif max_width:
                scale = max_width / original_width
            else:
                scale = max_height / original_height
            
            if scale >= 1:
                # Image is already small enough
                new_width = original_width
                new_height = original_height
            else:
                new_width = int(original_width * scale)
                new_height = int(original_height * scale)
        
        else:
            raise Exception("No resize parameters specified")
        
        # Resize image
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert to binary
        output = io.BytesIO()
        resized_img.save(output, format='PNG', optimize=True)
        return (output.getvalue(), new_width, new_height)
        
    except Exception as e:
        raise Exception(f"Error resizing image: {str(e)}")

def process_pack(image_data, pack_config):
    """
    Generate multiple outputs based on pack configuration.
    
    Args:
        image_data: Binary image data
        pack_config: JSON config from packs table
    
    Returns:
        List of (binary_data, filename, width, height, size)
    """
    try:
        results = []
        outputs = pack_config.get('outputs', [])
        
        for output in outputs:
            name = output.get('name', 'output')
            width = output.get('width')
            height = output.get('height')
            method = output.get('method', 'blur')
            compress = output.get('compress', False)
            compress_target = output.get('compress_target')
            
            # Process based on method
            if method == 'blur':
                processed_data = add_blur_borders(image_data, width, height)
            elif method == 'resize':
                processed_data, _, _ = resize_image(image_data, width=width, height=height)
            else:
                continue
            
            # Apply compression if needed
            if compress:
                if compress_target:
                    # Compress to target size
                    processed_data, actual_size, quality = compress_image(
                        processed_data, 
                        target_size_kb=compress_target // 1024
                    )
                else:
                    # Default compression
                    processed_data, actual_size, quality = compress_image(processed_data, quality=85)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.png"
            
            results.append({
                'data': processed_data,
                'filename': filename,
                'width': width,
                'height': height,
                'size': len(processed_data),
                'name': name
            })
        
        return results
        
    except Exception as e:
        raise Exception(f"Error processing pack: {str(e)}")

def get_image_info(image_data):
    """
    Get image metadata.
    
    Args:
        image_data: Binary image data
    
    Returns:
        Dict with width, height, format, size, mode
    """
    try:
        img = Image.open(io.BytesIO(image_data))
        return {
            'width': img.width,
            'height': img.height,
            'format': img.format,
            'size': len(image_data),
            'mode': img.mode
        }
    except Exception as e:
        raise Exception(f"Error getting image info: {str(e)}")

def strip_exif(image_data):
    """
    Remove EXIF data from image.
    
    Returns:
        Binary data without EXIF
    """
    try:
        img = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB to strip EXIF (if needed)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=95, optimize=True)
        return output.getvalue()
        
    except Exception as e:
        raise Exception(f"Error stripping EXIF: {str(e)}")

def validate_image_file(file_data, filename, max_size=10485760, allowed_extensions=None):
    """
    Validate uploaded image file.
    
    Args:
        file_data: Binary file data
        filename: Original filename
        max_size: Maximum file size in bytes
        allowed_extensions: List of allowed extensions
    
    Returns:
        True if valid, raises Exception if invalid
    """
    try:
        # Check file size
        if len(file_data) > max_size:
            raise Exception(f"File size exceeds maximum allowed size of {max_size // (1024*1024)}MB")
        
        # Check file extension
        if allowed_extensions:
            file_ext = os.path.splitext(filename)[1].lower().lstrip('.')
            if file_ext not in [ext.lower() for ext in allowed_extensions]:
                raise Exception(f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}")
        
        # Check if it's actually an image
        img = Image.open(io.BytesIO(file_data))
        img.verify()  # Verify it's a valid image
        
        # Reopen after verify (verify() closes the file)
        img = Image.open(io.BytesIO(file_data))
        
        # Check image dimensions
        if img.width < 1 or img.height < 1:
            raise Exception("Invalid image dimensions")
        
        if img.width > 4000 or img.height > 4000:
            raise Exception("Image dimensions too large (max 4000x4000)")
        
        return True
        
    except Exception as e:
        if "cannot identify image file" in str(e):
            raise Exception("Invalid image file")
        raise e

def format_file_size(size_bytes):
    """
    Format file size in human readable format.
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Formatted string (e.g., "2.3 MB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
