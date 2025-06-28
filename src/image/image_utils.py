"""
GenConfig Image Utilities

This module provides common image processing operations for the GenConfig system,
including resizing, format conversion, transparency handling, and other image
manipulation utilities needed for trait processing and composite generation.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
import tempfile

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.file_utils import validate_file_exists, ensure_directory_exists, get_file_size, FileOperationError


class ImageProcessingError(Exception):
    """Custom exception for image processing errors"""
    pass


class ResizeMethod(Enum):
    """Image resize algorithms"""
    NEAREST = Image.Resampling.NEAREST
    BILINEAR = Image.Resampling.BILINEAR
    BICUBIC = Image.Resampling.BICUBIC
    LANCZOS = Image.Resampling.LANCZOS
    BOX = Image.Resampling.BOX
    HAMMING = Image.Resampling.HAMMING


class ImageFormat(Enum):
    """Supported image formats"""
    PNG = "PNG"
    JPEG = "JPEG"
    WEBP = "WEBP"
    BMP = "BMP"
    TIFF = "TIFF"
    

class TransparencyMode(Enum):
    """Transparency handling modes"""
    PRESERVE = "preserve"      # Keep existing transparency
    REMOVE = "remove"          # Remove transparency, use background color
    ADD = "add"               # Add transparency channel if missing
    REPLACE = "replace"       # Replace transparency with specific color


@dataclass
class ImageProcessingResult:
    """Result of image processing operation"""
    success: bool
    input_path: Optional[str] = None
    output_path: Optional[str] = None
    original_size: Optional[Tuple[int, int]] = None
    final_size: Optional[Tuple[int, int]] = None
    original_format: Optional[str] = None
    final_format: Optional[str] = None
    original_mode: Optional[str] = None
    final_mode: Optional[str] = None
    file_size_bytes: int = 0
    processing_time: float = 0.0
    operations_applied: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes"""
        return self.file_size_bytes / (1024 * 1024)
    
    @property
    def size_changed(self) -> bool:
        """Check if image size was changed"""
        return self.original_size != self.final_size
    
    @property
    def format_changed(self) -> bool:
        """Check if image format was changed"""
        return self.original_format != self.final_format


class ImageUtilities:
    """
    Collection of image processing utilities for GenConfig trait and composite operations
    """
    
    # GenConfig standard sizes
    TRAIT_SIZE = (200, 200)
    COMPOSITE_SIZE = (600, 600)
    
    # Default quality settings
    DEFAULT_JPEG_QUALITY = 95
    DEFAULT_WEBP_QUALITY = 95
    
    def __init__(self, default_background: str = "#FFFFFF"):
        """
        Initialize image utilities
        
        Args:
            default_background: Default background color for transparency removal
        """
        self.default_background = default_background
    
    def resize_image(self, 
                    input_path: Union[str, Path],
                    output_path: Union[str, Path],
                    target_size: Tuple[int, int],
                    method: ResizeMethod = ResizeMethod.LANCZOS,
                    maintain_aspect_ratio: bool = False,
                    background_color: Optional[str] = None) -> ImageProcessingResult:
        """
        Resize an image to target dimensions
        
        Args:
            input_path: Path to input image
            output_path: Path for output image
            target_size: Target (width, height) dimensions
            method: Resize algorithm to use
            maintain_aspect_ratio: Whether to maintain aspect ratio (pad if needed)
            background_color: Background color for padding (if maintaining aspect ratio)
            
        Returns:
            ImageProcessingResult: Processing result with details
        """
        import time
        start_time = time.time()
        
        result = ImageProcessingResult(
            success=False,
            input_path=str(input_path),
            output_path=str(output_path)
        )
        
        try:
            # Validate input
            if not validate_file_exists(input_path):
                raise ImageProcessingError(f"Input file not found: {input_path}")
            
            # Load image
            with Image.open(input_path) as img:
                result.original_size = img.size
                result.original_format = img.format
                result.original_mode = img.mode
                
                # Resize image
                if maintain_aspect_ratio:
                    resized_img = self._resize_with_aspect_ratio(
                        img, target_size, background_color or self.default_background
                    )
                    result.operations_applied.append(f"resize_with_aspect_ratio_{method.name.lower()}")
                else:
                    resized_img = img.resize(target_size, method.value)
                    result.operations_applied.append(f"resize_{method.name.lower()}")
                
                # Save result
                ensure_directory_exists(str(Path(output_path).parent))
                resized_img.save(output_path)
                
                result.final_size = resized_img.size
                result.final_format = Path(output_path).suffix.upper().lstrip('.')
                result.final_mode = resized_img.mode
                result.file_size_bytes = get_file_size(output_path)
                result.success = True
                
                # Add warnings for significant size changes
                original_area = result.original_size[0] * result.original_size[1]
                final_area = result.final_size[0] * result.final_size[1]
                size_ratio = final_area / original_area if original_area > 0 else 0
                
                if size_ratio > 4:
                    result.warnings.append("Image was significantly upscaled, quality may be reduced")
                elif size_ratio < 0.25:
                    result.warnings.append("Image was significantly downscaled, detail may be lost")
        
        except Exception as e:
            result.success = False
            result.errors.append(f"Resize failed: {str(e)}")
        
        finally:
            result.processing_time = time.time() - start_time
        
        return result
    
    def convert_format(self,
                      input_path: Union[str, Path],
                      output_path: Union[str, Path],
                      target_format: ImageFormat,
                      quality: Optional[int] = None,
                      preserve_transparency: bool = True) -> ImageProcessingResult:
        """
        Convert image format while preserving quality and transparency
        
        Args:
            input_path: Path to input image
            output_path: Path for output image
            target_format: Target image format
            quality: Compression quality (for JPEG/WEBP)
            preserve_transparency: Whether to preserve transparency in conversion
            
        Returns:
            ImageProcessingResult: Processing result with details
        """
        import time
        start_time = time.time()
        
        result = ImageProcessingResult(
            success=False,
            input_path=str(input_path),
            output_path=str(output_path)
        )
        
        try:
            # Validate input
            if not validate_file_exists(input_path):
                raise ImageProcessingError(f"Input file not found: {input_path}")
            
            # Load image
            with Image.open(input_path) as img:
                result.original_size = img.size
                result.original_format = img.format
                result.original_mode = img.mode
                
                # Handle format conversion
                converted_img = self._convert_image_format(
                    img, target_format, preserve_transparency, quality
                )
                
                # Save result
                ensure_directory_exists(str(Path(output_path).parent))
                save_kwargs = self._get_save_kwargs(target_format, quality)
                converted_img.save(output_path, target_format.value, **save_kwargs)
                
                result.final_size = converted_img.size
                result.final_format = target_format.value
                result.final_mode = converted_img.mode
                result.file_size_bytes = get_file_size(output_path)
                result.operations_applied.append(f"convert_to_{target_format.value.lower()}")
                result.success = True
                
                # Add transparency warnings
                if img.mode in ['RGBA', 'LA'] and target_format in [ImageFormat.JPEG]:
                    result.warnings.append("Transparency was removed due to format limitations")
        
        except Exception as e:
            result.success = False
            result.errors.append(f"Format conversion failed: {str(e)}")
        
        finally:
            result.processing_time = time.time() - start_time
        
        return result
    
    def handle_transparency(self,
                           input_path: Union[str, Path],
                           output_path: Union[str, Path],
                           mode: TransparencyMode,
                           background_color: Optional[str] = None,
                           transparency_threshold: int = 128) -> ImageProcessingResult:
        """
        Handle transparency in images (add, remove, preserve, or replace)
        
        Args:
            input_path: Path to input image
            output_path: Path for output image
            mode: Transparency handling mode
            background_color: Background color for transparency removal/replacement
            transparency_threshold: Alpha threshold for transparency operations
            
        Returns:
            ImageProcessingResult: Processing result with details
        """
        import time
        start_time = time.time()
        
        result = ImageProcessingResult(
            success=False,
            input_path=str(input_path),
            output_path=str(output_path)
        )
        
        try:
            # Validate input
            if not validate_file_exists(input_path):
                raise ImageProcessingError(f"Input file not found: {input_path}")
            
            # Load image
            with Image.open(input_path) as img:
                result.original_size = img.size
                result.original_format = img.format
                result.original_mode = img.mode
                
                # Handle transparency based on mode
                processed_img = self._process_transparency(
                    img, mode, background_color or self.default_background, transparency_threshold
                )
                
                # Save result
                ensure_directory_exists(str(Path(output_path).parent))
                processed_img.save(output_path)
                
                result.final_size = processed_img.size
                result.final_format = Path(output_path).suffix.upper().lstrip('.')
                result.final_mode = processed_img.mode
                result.file_size_bytes = get_file_size(output_path)
                result.operations_applied.append(f"transparency_{mode.value}")
                result.success = True
        
        except Exception as e:
            result.success = False
            result.errors.append(f"Transparency processing failed: {str(e)}")
        
        finally:
            result.processing_time = time.time() - start_time
        
        return result
    
    def optimize_image(self,
                      input_path: Union[str, Path],
                      output_path: Union[str, Path],
                      max_file_size: Optional[int] = None,
                      target_format: Optional[ImageFormat] = None,
                      quality_range: Tuple[int, int] = (50, 95)) -> ImageProcessingResult:
        """
        Optimize image for file size while maintaining acceptable quality
        
        Args:
            input_path: Path to input image
            output_path: Path for output image
            max_file_size: Maximum file size in bytes
            target_format: Target format for optimization
            quality_range: (min_quality, max_quality) for compression
            
        Returns:
            ImageProcessingResult: Processing result with details
        """
        import time
        start_time = time.time()
        
        result = ImageProcessingResult(
            success=False,
            input_path=str(input_path),
            output_path=str(output_path)
        )
        
        try:
            # Validate input
            if not validate_file_exists(input_path):
                raise ImageProcessingError(f"Input file not found: {input_path}")
            
            # Load image
            with Image.open(input_path) as img:
                result.original_size = img.size
                result.original_format = img.format
                result.original_mode = img.mode
                
                # Determine best format for optimization
                if target_format is None:
                    target_format = self._choose_optimal_format(img)
                
                # Optimize image
                optimized_img, final_quality = self._optimize_for_size(
                    img, target_format, max_file_size, quality_range
                )
                
                # Save result
                ensure_directory_exists(str(Path(output_path).parent))
                save_kwargs = self._get_save_kwargs(target_format, final_quality)
                optimized_img.save(output_path, target_format.value, **save_kwargs)
                
                result.final_size = optimized_img.size
                result.final_format = target_format.value
                result.final_mode = optimized_img.mode
                result.file_size_bytes = get_file_size(output_path)
                result.operations_applied.append(f"optimize_quality_{final_quality}")
                result.success = True
        
        except Exception as e:
            result.success = False
            result.errors.append(f"Image optimization failed: {str(e)}")
        
        finally:
            result.processing_time = time.time() - start_time
        
        return result
    
    def create_thumbnail(self,
                        input_path: Union[str, Path],
                        output_path: Union[str, Path],
                        thumbnail_size: Tuple[int, int] = (150, 150),
                        maintain_aspect_ratio: bool = True) -> ImageProcessingResult:
        """
        Create a thumbnail version of an image
        
        Args:
            input_path: Path to input image
            output_path: Path for thumbnail output
            thumbnail_size: Maximum thumbnail dimensions
            maintain_aspect_ratio: Whether to maintain aspect ratio
            
        Returns:
            ImageProcessingResult: Processing result with details
        """
        return self.resize_image(
            input_path, output_path, thumbnail_size,
            method=ResizeMethod.LANCZOS,
            maintain_aspect_ratio=maintain_aspect_ratio
        )
    
    # Private helper methods
    
    def _resize_with_aspect_ratio(self, img: Image.Image, target_size: Tuple[int, int],
                                 background_color: str) -> Image.Image:
        """Resize image while maintaining aspect ratio with padding"""
        # Calculate scaling factor
        scale_w = target_size[0] / img.size[0]
        scale_h = target_size[1] / img.size[1]
        scale = min(scale_w, scale_h)
        
        # Calculate new size
        new_width = int(img.size[0] * scale)
        new_height = int(img.size[1] * scale)
        
        # Resize image
        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Create new image with target size and background
        if resized.mode == 'RGBA':
            new_img = Image.new('RGBA', target_size, (255, 255, 255, 0))
        else:
            new_img = Image.new('RGB', target_size, background_color)
        
        # Calculate position to center the resized image
        x = (target_size[0] - new_width) // 2
        y = (target_size[1] - new_height) // 2
        
        # Paste resized image onto centered background
        if resized.mode == 'RGBA':
            new_img.paste(resized, (x, y), resized)
        else:
            new_img.paste(resized, (x, y))
        
        return new_img
    
    def _convert_image_format(self, img: Image.Image, target_format: ImageFormat,
                             preserve_transparency: bool, quality: Optional[int]) -> Image.Image:
        """Convert image to target format with transparency handling"""
        if target_format == ImageFormat.PNG:
            # PNG supports transparency
            if img.mode not in ['RGBA', 'LA', 'P']:
                return img.convert('RGBA')
            return img.copy()
        
        elif target_format == ImageFormat.WEBP:
            # WEBP supports transparency
            if preserve_transparency and img.mode in ['RGBA', 'LA', 'P']:
                return img.convert('RGBA')
            else:
                return img.convert('RGB')
        
        elif target_format in [ImageFormat.JPEG, ImageFormat.BMP]:
            # These formats don't support transparency
            if img.mode in ['RGBA', 'LA', 'P']:
                # Create background and composite
                background = Image.new('RGB', img.size, self.default_background)
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if len(img.split()) > 3 else None)
                return background
            else:
                return img.convert('RGB')
        
        else:
            # Default handling
            return img.copy()
    
    def _process_transparency(self, img: Image.Image, mode: TransparencyMode,
                             background_color: str, threshold: int) -> Image.Image:
        """Process transparency according to specified mode"""
        if mode == TransparencyMode.PRESERVE:
            return img.copy()
        
        elif mode == TransparencyMode.REMOVE:
            if img.mode in ['RGBA', 'LA', 'P']:
                background = Image.new('RGB', img.size, background_color)
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if len(img.split()) > 3:
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                return background
            else:
                return img.convert('RGB')
        
        elif mode == TransparencyMode.ADD:
            if img.mode not in ['RGBA', 'LA', 'P']:
                return img.convert('RGBA')
            return img.copy()
        
        elif mode == TransparencyMode.REPLACE:
            if img.mode in ['RGBA', 'LA']:
                # Replace transparent pixels with background color
                img_copy = img.copy()
                if img.mode == 'RGBA':
                    r, g, b, a = img_copy.split()
                    rgb = Image.merge('RGB', (r, g, b))
                    background = Image.new('RGB', img.size, background_color)
                    
                    # Create mask for non-transparent pixels
                    mask = a.point(lambda x: 255 if x > threshold else 0)
                    background.paste(rgb, mask=mask)
                    
                    # Convert back to RGBA with modified transparency
                    return background.convert('RGBA')
                else:
                    return img_copy
            return img.copy()
        
        return img.copy()
    
    def _choose_optimal_format(self, img: Image.Image) -> ImageFormat:
        """Choose optimal format based on image characteristics"""
        if img.mode in ['RGBA', 'LA', 'P'] and self._has_transparency(img):
            return ImageFormat.PNG
        else:
            return ImageFormat.JPEG
    
    def _has_transparency(self, img: Image.Image) -> bool:
        """Check if image has actual transparency"""
        if img.mode == 'RGBA':
            alpha = img.split()[-1]
            return alpha.getextrema()[0] < 255
        elif img.mode == 'LA':
            alpha = img.split()[-1]
            return alpha.getextrema()[0] < 255
        elif img.mode == 'P':
            return 'transparency' in img.info
        return False
    
    def _optimize_for_size(self, img: Image.Image, target_format: ImageFormat,
                          max_file_size: Optional[int], quality_range: Tuple[int, int]) -> Tuple[Image.Image, int]:
        """Optimize image for file size constraints"""
        min_quality, max_quality = quality_range
        
        if max_file_size is None:
            return img.copy(), max_quality
        
        # Binary search for optimal quality
        best_quality = max_quality
        best_img = img.copy()
        
        for quality in range(max_quality, min_quality - 1, -5):
            with tempfile.NamedTemporaryFile(suffix=f'.{target_format.value.lower()}') as temp_file:
                temp_img = img.copy()
                save_kwargs = self._get_save_kwargs(target_format, quality)
                temp_img.save(temp_file.name, target_format.value, **save_kwargs)
                
                file_size = get_file_size(temp_file.name)
                if file_size <= max_file_size:
                    best_quality = quality
                    best_img = temp_img
                    break
        
        return best_img, best_quality
    
    def _get_save_kwargs(self, format_type: ImageFormat, quality: Optional[int]) -> Dict[str, Any]:
        """Get save keyword arguments for specific format"""
        kwargs = {'optimize': True}
        
        if format_type == ImageFormat.JPEG:
            kwargs['quality'] = quality or self.DEFAULT_JPEG_QUALITY
        elif format_type == ImageFormat.WEBP:
            kwargs['quality'] = quality or self.DEFAULT_WEBP_QUALITY
        
        return kwargs


# Convenience Functions

def resize_image(input_path: Union[str, Path],
                output_path: Union[str, Path],
                target_size: Tuple[int, int],
                method: str = "lanczos") -> bool:
    """
    Resize an image to target dimensions
    
    Args:
        input_path: Path to input image
        output_path: Path for output image
        target_size: Target (width, height) dimensions
        method: Resize method name
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not validate_file_exists(input_path):
            return False
        
        # Map method name to PIL constant
        method_map = {
            "nearest": Image.Resampling.NEAREST,
            "bilinear": Image.Resampling.BILINEAR,
            "bicubic": Image.Resampling.BICUBIC,
            "lanczos": Image.Resampling.LANCZOS,
            "box": Image.Resampling.BOX,
            "hamming": Image.Resampling.HAMMING
        }
        
        resize_method = method_map.get(method.lower(), Image.Resampling.LANCZOS)
        
        # Load, resize, and save image
        with Image.open(input_path) as img:
            resized_img = img.resize(target_size, resize_method)
            
            # Ensure output directory exists
            ensure_directory_exists(str(Path(output_path).parent))
            
            # Save image
            resized_img.save(output_path)
            
        return True
        
    except Exception:
        return False


def convert_image_format(input_path: Union[str, Path],
                        output_path: Union[str, Path],
                        target_format: str) -> bool:
    """
    Convert image format
    
    Args:
        input_path: Path to input image
        output_path: Path for output image
        target_format: Target format name (PNG, JPEG, WEBP, etc.)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not validate_file_exists(input_path):
            return False
        
        with Image.open(input_path) as img:
            # Handle transparency for formats that don't support it
            if target_format.upper() in ['JPEG', 'BMP'] and img.mode in ['RGBA', 'LA', 'P']:
                # Create white background for transparent images
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if len(img.split()) > 3:
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                img = background
            
            # Ensure output directory exists
            ensure_directory_exists(str(Path(output_path).parent))
            
            # Save in target format
            img.save(output_path, target_format.upper())
            
        return True
        
    except Exception:
        return False


def handle_image_transparency(input_path: Union[str, Path],
                             output_path: Union[str, Path],
                             mode: str = "preserve") -> bool:
    """
    Handle transparency in images
    
    Args:
        input_path: Path to input image
        output_path: Path for output image
        mode: Transparency mode (preserve, remove, add, replace)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not validate_file_exists(input_path):
            return False
        
        with Image.open(input_path) as img:
            if mode.lower() == "preserve":
                # Keep original transparency
                processed_img = img.copy()
                
            elif mode.lower() == "remove":
                # Remove transparency by compositing on white background
                if img.mode in ['RGBA', 'LA', 'P']:
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    if len(img.split()) > 3:
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img)
                    processed_img = background
                else:
                    processed_img = img.convert('RGB')
                    
            elif mode.lower() == "add":
                # Add transparency support if missing
                if img.mode not in ['RGBA', 'LA', 'P']:
                    processed_img = img.convert('RGBA')
                else:
                    processed_img = img.copy()
                    
            elif mode.lower() == "replace":
                # Replace transparent areas with white
                if img.mode in ['RGBA', 'LA']:
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'LA':
                        img = img.convert('RGBA')
                    if len(img.split()) > 3:
                        background.paste(img, mask=img.split()[-1])
                    processed_img = background.convert('RGBA')
                else:
                    processed_img = img.convert('RGBA')
            else:
                processed_img = img.copy()
            
            # Ensure output directory exists
            ensure_directory_exists(str(Path(output_path).parent))
            
            # Save processed image
            processed_img.save(output_path)
            
        return True
        
    except Exception:
        return False


def get_image_info(image_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Get comprehensive information about an image
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Dict[str, Any]: Image information
    """
    try:
        if not validate_file_exists(image_path):
            return {"error": "File not found"}
        
        with Image.open(image_path) as img:
            return {
                "size": img.size,
                "format": img.format,
                "mode": img.mode,
                "has_transparency": img.mode in ['RGBA', 'LA', 'P'] or 'transparency' in img.info,
                "file_size": get_file_size(image_path),
                "file_path": str(image_path)
            }
    except Exception as e:
        return {"error": str(e)}


def standardize_trait_image(input_path: Union[str, Path],
                           output_path: Union[str, Path]) -> bool:
    """
    Standardize a trait image to GenConfig specifications
    
    Args:
        input_path: Path to input trait image
        output_path: Path for standardized output
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Resize to trait size (200x200)
        if not resize_image(input_path, output_path, (200, 200), "lanczos"):
            return False
        
        # Ensure PNG format with transparency
        if not str(output_path).lower().endswith('.png'):
            png_path = str(output_path).rsplit('.', 1)[0] + '.png'
            return convert_image_format(output_path, png_path, "PNG")
        
        return True
    except Exception:
        return False


def batch_process_images(input_paths: List[Union[str, Path]],
                        output_dir: Union[str, Path],
                        operation: str,
                        **kwargs) -> Dict[str, bool]:
    """
    Process multiple images with the same operation
    
    Args:
        input_paths: List of input image paths
        output_dir: Directory for output images
        operation: Operation name (resize, convert, standardize)
        **kwargs: Additional arguments for the operation
        
    Returns:
        Dict[str, bool]: Results keyed by input path
    """
    results = {}
    output_dir_path = Path(output_dir)
    ensure_directory_exists(str(output_dir_path))
    
    for input_path in input_paths:
        try:
            input_path_obj = Path(input_path)
            output_path = output_dir_path / input_path_obj.name
            
            if operation == "resize":
                results[str(input_path)] = resize_image(input_path, output_path, **kwargs)
            elif operation == "convert":
                results[str(input_path)] = convert_image_format(input_path, output_path, **kwargs)
            elif operation == "standardize":
                results[str(input_path)] = standardize_trait_image(input_path, output_path)
            else:
                results[str(input_path)] = False
        except Exception:
            results[str(input_path)] = False
    
    return results 