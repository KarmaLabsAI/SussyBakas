"""
GenConfig Image Validator

This module provides validation for generated composite images according to
GenConfig specifications. It validates format, dimensions, file integrity,
image quality, and other requirements for composite NFT images.
"""

import os
import sys
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from PIL import Image, UnidentifiedImageError

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.logic_validator import ValidationResult, ValidationIssue, ValidationSeverity
from utils.file_utils import validate_file_exists, get_file_size, calculate_file_hash, FileOperationError


class ImageValidationError(Exception):
    """Custom exception for image validation errors"""
    pass


@dataclass
class ImageValidationInfo:
    """Information about a validated image"""
    file_path: str
    file_name: str
    file_size: int
    file_hash: Optional[str] = None
    image_format: Optional[str] = None
    image_mode: Optional[str] = None
    image_size: Optional[Tuple[int, int]] = None
    has_transparency: Optional[bool] = None
    has_alpha_channel: Optional[bool] = None
    bit_depth: Optional[int] = None
    compression_quality: Optional[str] = None
    pixel_data_integrity: Optional[bool] = None
    
    # Quality metrics
    total_pixels: int = 0
    transparent_pixels: int = 0
    opaque_pixels: int = 0
    partially_transparent_pixels: int = 0
    
    @property
    def transparency_ratio(self) -> float:
        """Ratio of transparent pixels to total pixels"""
        return self.transparent_pixels / self.total_pixels if self.total_pixels > 0 else 0.0
    
    @property
    def opacity_ratio(self) -> float:
        """Ratio of opaque pixels to total pixels"""
        return self.opaque_pixels / self.total_pixels if self.total_pixels > 0 else 0.0


class ImageValidationMode(Enum):
    """Image validation modes"""
    STRICT = "strict"           # All requirements must pass
    NORMAL = "normal"           # Standard validation
    PERMISSIVE = "permissive"   # Only critical errors fail validation


def validate_image(file_path: Union[str, Path], 
                  expected_size: Tuple[int, int] = (600, 600),
                  validation_mode: ImageValidationMode = ImageValidationMode.NORMAL) -> ValidationResult:
    """
    Validate a single composite image file
    
    Args:
        file_path: Path to the image file to validate
        expected_size: Expected (width, height) dimensions
        validation_mode: Validation strictness mode
        
    Returns:
        ValidationResult: Complete validation result
    """
    validator = ImageValidator(
        validation_mode=validation_mode,
        expected_size=expected_size
    )
    return validator.validate_image(file_path)


class ImageValidator:
    """
    Validator for generated composite images
    
    Validates composite images according to GenConfig specification:
    - Format: PNG with RGBA support
    - Dimensions: Must match configured final size (default: 600×600 pixels)
    - File Integrity: Valid image data, no corruption
    - Quality: Proper transparency handling, reasonable file size
    """
    
    # Constants from GenConfig specification
    VALID_FORMAT = "PNG"
    VALID_EXTENSION = ".png"
    DEFAULT_EXPECTED_SIZE = (600, 600)
    VALID_MODES = ['RGBA', 'RGB', 'L', 'LA', 'P']
    PREFERRED_MODE = 'RGBA'
    
    # File size limits (configurable)
    MIN_FILE_SIZE = 1000      # 1KB minimum
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB maximum
    REASONABLE_MAX_SIZE = 10 * 1024 * 1024  # 10MB reasonable maximum
    
    def __init__(self, 
                 validation_mode: ImageValidationMode = ImageValidationMode.NORMAL,
                 expected_size: Optional[Tuple[int, int]] = None,
                 calculate_hash: bool = True,
                 check_quality_metrics: bool = True):
        """
        Initialize image validator
        
        Args:
            validation_mode: Validation strictness mode
            expected_size: Expected (width, height) dimensions
            calculate_hash: Whether to calculate file hash for integrity
            check_quality_metrics: Whether to perform quality analysis
        """
        self.validation_mode = validation_mode
        self.expected_size = expected_size or self.DEFAULT_EXPECTED_SIZE
        self.calculate_hash = calculate_hash
        self.check_quality_metrics = check_quality_metrics
        self.issues: List[ValidationIssue] = []
    
    def validate_image(self, file_path: Union[str, Path]) -> ValidationResult:
        """
        Validate a composite image against GenConfig requirements
        
        Args:
            file_path: Path to the image file to validate
            
        Returns:
            ValidationResult: Complete validation result with issues
        """
        self.issues = []
        file_path_str = str(file_path)
        
        # Get basic file information
        image_info = self._get_image_info(file_path_str)
        
        # Perform all validation checks
        self._validate_file_existence(image_info)
        self._validate_file_format(image_info)
        self._validate_file_size(image_info)
        self._validate_image_properties(image_info)
        
        if self.check_quality_metrics:
            self._validate_image_quality(image_info)
        
        # Determine if image is valid based on validation mode
        error_count = len([issue for issue in self.issues 
                          if issue.severity == ValidationSeverity.ERROR])
        warning_count = len([issue for issue in self.issues 
                           if issue.severity == ValidationSeverity.WARNING])
        
        # Apply validation mode logic
        if self.validation_mode == ImageValidationMode.STRICT:
            is_valid = error_count == 0 and warning_count == 0
        elif self.validation_mode == ImageValidationMode.PERMISSIVE:
            is_valid = error_count == 0
        else:  # NORMAL mode
            is_valid = error_count == 0
        
        return ValidationResult(is_valid=is_valid, issues=self.issues.copy())
    
    def _get_image_info(self, file_path: str) -> ImageValidationInfo:
        """Extract comprehensive image information"""
        path = Path(file_path)
        
        image_info = ImageValidationInfo(
            file_path=file_path,
            file_name=path.name,
            file_size=0
        )
        
        # Get file size if file exists
        if path.exists():
            try:
                image_info.file_size = get_file_size(file_path)
                
                if self.calculate_hash:
                    image_info.file_hash = calculate_file_hash(file_path, 'sha256')
                    
            except Exception as e:
                self._add_issue(
                    ValidationSeverity.WARNING,
                    "file_access",
                    f"Could not access file properties: {e}",
                    file_path
                )
        
        return image_info
    
    def _validate_file_existence(self, image_info: ImageValidationInfo) -> None:
        """Validate that the file exists and is accessible"""
        if not validate_file_exists(image_info.file_path):
            self._add_issue(
                ValidationSeverity.ERROR,
                "file_existence",
                f"Image file does not exist or is not accessible: {image_info.file_path}",
                image_info.file_path,
                "Ensure the file exists and has proper permissions"
            )
    
    def _validate_file_format(self, image_info: ImageValidationInfo) -> None:
        """Validate file format and extension"""
        path = Path(image_info.file_path)
        
        # Check file extension
        if path.suffix.lower() != self.VALID_EXTENSION:
            self._add_issue(
                ValidationSeverity.ERROR,
                "file_format",
                f"Invalid file extension '{path.suffix}', expected '{self.VALID_EXTENSION}'",
                image_info.file_path,
                f"Ensure file has {self.VALID_EXTENSION} extension"
            )
        
        # Try to open and verify format
        if path.exists():
            try:
                with Image.open(image_info.file_path) as img:
                    image_info.image_format = img.format
                    
                    if img.format != self.VALID_FORMAT:
                        self._add_issue(
                            ValidationSeverity.ERROR,
                            "image_format",
                            f"Invalid image format '{img.format}', expected '{self.VALID_FORMAT}'",
                            image_info.file_path,
                            f"Convert image to {self.VALID_FORMAT} format"
                        )
                        
            except UnidentifiedImageError:
                self._add_issue(
                    ValidationSeverity.ERROR,
                    "image_format",
                    "File is not a valid image or is corrupted",
                    image_info.file_path,
                    "Ensure file contains valid image data"
                )
            except Exception as e:
                self._add_issue(
                    ValidationSeverity.ERROR,
                    "image_access",
                    f"Cannot open image file: {e}",
                    image_info.file_path,
                    "Check file integrity and permissions"
                )
    
    def _validate_file_size(self, image_info: ImageValidationInfo) -> None:
        """Validate file size is within reasonable limits"""
        file_size = image_info.file_size
        
        if file_size == 0:
            self._add_issue(
                ValidationSeverity.ERROR,
                "file_size",
                "File is empty (0 bytes)",
                image_info.file_path,
                "Ensure the file contains valid image data"
            )
        elif file_size < self.MIN_FILE_SIZE:
            self._add_issue(
                ValidationSeverity.WARNING,
                "file_size",
                f"File size {file_size} bytes is unusually small for a composite image",
                image_info.file_path,
                "Verify the image contains proper composite data"
            )
        elif file_size > self.MAX_FILE_SIZE:
            size_mb = file_size / (1024 * 1024)
            max_mb = self.MAX_FILE_SIZE / (1024 * 1024)
            self._add_issue(
                ValidationSeverity.ERROR,
                "file_size",
                f"File size {size_mb:.2f}MB exceeds maximum {max_mb:.1f}MB",
                image_info.file_path,
                "Optimize or compress the image to reduce file size"
            )
        elif file_size > self.REASONABLE_MAX_SIZE:
            size_mb = file_size / (1024 * 1024)
            reasonable_mb = self.REASONABLE_MAX_SIZE / (1024 * 1024)
            self._add_issue(
                ValidationSeverity.WARNING,
                "file_size",
                f"File size {size_mb:.2f}MB is larger than typical ({reasonable_mb:.1f}MB)",
                image_info.file_path,
                "Consider optimizing the image to reduce file size"
            )
    
    def _validate_image_properties(self, image_info: ImageValidationInfo) -> None:
        """Validate image properties like dimensions, mode, etc."""
        if not Path(image_info.file_path).exists():
            return
        
        try:
            with Image.open(image_info.file_path) as img:
                image_info.image_size = img.size
                image_info.image_mode = img.mode
                image_info.has_alpha_channel = img.mode in ['RGBA', 'LA'] or 'transparency' in img.info
                
                # Validate dimensions
                self._validate_dimensions(img, image_info)
                
                # Validate color mode
                self._validate_color_mode(img, image_info)
                
                # Check for transparency support
                self._check_transparency_support(img, image_info)
                
                # Test image integrity
                image_info.pixel_data_integrity = self._check_image_corruption(img)
                if not image_info.pixel_data_integrity:
                    self._add_issue(
                        ValidationSeverity.ERROR,
                        "image_corruption",
                        "Image data appears to be corrupted",
                        image_info.file_path,
                        "Regenerate the image or check source files"
                    )
                
        except Exception as e:
            self._add_issue(
                ValidationSeverity.ERROR,
                "image_properties",
                f"Cannot analyze image properties: {e}",
                image_info.file_path,
                "Check file integrity and format"
            )
    
    def _validate_dimensions(self, img: Image.Image, image_info: ImageValidationInfo) -> None:
        """Validate image dimensions match expected size"""
        actual_size = img.size
        expected_size = self.expected_size
        
        if actual_size != expected_size:
            self._add_issue(
                ValidationSeverity.ERROR,
                "image_dimensions",
                f"Invalid dimensions {actual_size}, expected {expected_size}",
                image_info.file_path,
                f"Resize image to {expected_size[0]}×{expected_size[1]} pixels"
            )
        
        # Check aspect ratio
        actual_ratio = actual_size[0] / actual_size[1] if actual_size[1] > 0 else 0
        expected_ratio = expected_size[0] / expected_size[1] if expected_size[1] > 0 else 0
        
        if abs(actual_ratio - expected_ratio) > 0.01:  # Allow small floating point differences
            self._add_issue(
                ValidationSeverity.WARNING,
                "aspect_ratio",
                f"Aspect ratio {actual_ratio:.3f} differs from expected {expected_ratio:.3f}",
                image_info.file_path,
                "Verify image proportions are correct"
            )
    
    def _validate_color_mode(self, img: Image.Image, image_info: ImageValidationInfo) -> None:
        """Validate image color mode"""
        if img.mode not in self.VALID_MODES:
            self._add_issue(
                ValidationSeverity.ERROR,
                "color_mode",
                f"Invalid color mode '{img.mode}', expected one of {self.VALID_MODES}",
                image_info.file_path,
                f"Convert image to {self.PREFERRED_MODE} mode"
            )
        elif img.mode != self.PREFERRED_MODE:
            self._add_issue(
                ValidationSeverity.WARNING,
                "color_mode",
                f"Color mode '{img.mode}' is valid but '{self.PREFERRED_MODE}' is preferred",
                image_info.file_path,
                f"Consider converting to {self.PREFERRED_MODE} for best compatibility"
            )
    
    def _check_transparency_support(self, img: Image.Image, image_info: ImageValidationInfo) -> None:
        """Check if image properly supports transparency"""
        has_transparency = img.mode in ['RGBA', 'LA'] or 'transparency' in img.info
        image_info.has_transparency = has_transparency
        
        if not has_transparency:
            self._add_issue(
                ValidationSeverity.WARNING,
                "transparency",
                "Image does not support transparency",
                image_info.file_path,
                "Consider using RGBA mode for proper transparency support"
            )
    
    def _validate_image_quality(self, image_info: ImageValidationInfo) -> None:
        """Perform quality analysis on the image"""
        if not Path(image_info.file_path).exists():
            return
        
        try:
            with Image.open(image_info.file_path) as img:
                # Analyze pixel distribution
                pixel_stats = self._analyze_pixel_distribution(img)
                
                image_info.total_pixels = pixel_stats['total']
                image_info.transparent_pixels = pixel_stats['transparent']
                image_info.opaque_pixels = pixel_stats['opaque']
                image_info.partially_transparent_pixels = pixel_stats['partial']
                
                # Quality checks
                if image_info.total_pixels == image_info.transparent_pixels:
                    self._add_issue(
                        ValidationSeverity.WARNING,
                        "image_quality",
                        "Image appears to be completely transparent",
                        image_info.file_path,
                        "Verify image contains visible content"
                    )
                elif image_info.transparent_pixels == 0 and img.mode == 'RGBA':
                    self._add_issue(
                        ValidationSeverity.INFO,
                        "image_quality",
                        "Image has no transparent pixels (fully opaque)",
                        image_info.file_path,
                        "This may be expected for background layers"
                    )
                
                # Check for reasonable content
                opacity_ratio = image_info.opacity_ratio
                if opacity_ratio < 0.05:  # Less than 5% opaque
                    self._add_issue(
                        ValidationSeverity.WARNING,
                        "image_quality",
                        f"Image has very little opaque content ({opacity_ratio:.1%} opaque)",
                        image_info.file_path,
                        "Verify image contains sufficient visible content"
                    )
                
        except Exception as e:
            self._add_issue(
                ValidationSeverity.WARNING,
                "quality_analysis",
                f"Could not perform quality analysis: {e}",
                image_info.file_path,
                "Quality analysis skipped due to error"
            )
    
    def _analyze_pixel_distribution(self, image: Image.Image) -> Dict[str, int]:
        """Analyze pixel distribution for quality assessment"""
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        pixels = list(image.getdata())
        total_pixels = len(pixels)
        transparent_count = 0
        opaque_count = 0
        partial_count = 0
        
        for r, g, b, a in pixels:
            if a == 0:
                transparent_count += 1
            elif a == 255:
                opaque_count += 1
            else:
                partial_count += 1
        
        return {
            'total': total_pixels,
            'transparent': transparent_count,
            'opaque': opaque_count,
            'partial': partial_count
        }
    
    def _check_image_corruption(self, image: Image.Image) -> bool:
        """Check for image corruption by attempting various operations"""
        try:
            # Test basic operations that would fail on corrupted images
            image.size
            image.mode
            image.getbbox()
            
            # Test pixel access
            width, height = image.size
            if width > 0 and height > 0:
                image.getpixel((0, 0))
                image.getpixel((width-1, height-1))
            
            # Test conversion
            test_image = image.convert('RGB')
            test_image.size
            
            return True
            
        except Exception:
            return False
    
    def _add_issue(self, severity: ValidationSeverity, category: str,
                   message: str, path: Optional[str] = None,
                   suggestion: Optional[str] = None) -> None:
        """Add a validation issue to the results"""
        issue = ValidationIssue(
            severity=severity,
            category=category,
            message=message,
            path=path,
            suggestion=suggestion
        )
        self.issues.append(issue)


# Convenience functions

def validate_multiple_images(file_paths: List[Union[str, Path]],
                            expected_size: Tuple[int, int] = (600, 600),
                            validation_mode: ImageValidationMode = ImageValidationMode.NORMAL) -> Dict[str, ValidationResult]:
    """
    Validate multiple composite image files
    
    Args:
        file_paths: List of paths to image files to validate
        expected_size: Expected (width, height) dimensions
        validation_mode: Validation strictness mode
        
    Returns:
        Dict[str, ValidationResult]: Results keyed by file path
    """
    validator = ImageValidator(
        validation_mode=validation_mode,
        expected_size=expected_size
    )
    
    results = {}
    for file_path in file_paths:
        results[str(file_path)] = validator.validate_image(file_path)
    
    return results


def get_image_validation_report(result: ValidationResult, file_path: str = "") -> str:
    """
    Generate a human-readable validation report
    
    Args:
        result: Validation result to report on
        file_path: Optional file path for context
        
    Returns:
        str: Formatted validation report
    """
    if not result.issues:
        return f"✅ Image validation passed: {file_path or 'Image'}"
    
    report_lines = [f"📋 Image Validation Report: {file_path or 'Image'}"]
    report_lines.append(f"Status: {'✅ PASSED' if result.is_valid else '❌ FAILED'}")
    report_lines.append("")
    
    # Group issues by severity
    errors = [issue for issue in result.issues if issue.severity == ValidationSeverity.ERROR]
    warnings = [issue for issue in result.issues if issue.severity == ValidationSeverity.WARNING]
    info = [issue for issue in result.issues if issue.severity == ValidationSeverity.INFO]
    
    if errors:
        report_lines.append("❌ Errors:")
        for issue in errors:
            report_lines.append(f"  • {issue.message}")
            if issue.suggestion:
                report_lines.append(f"    💡 {issue.suggestion}")
        report_lines.append("")
    
    if warnings:
        report_lines.append("⚠️  Warnings:")
        for issue in warnings:
            report_lines.append(f"  • {issue.message}")
            if issue.suggestion:
                report_lines.append(f"    💡 {issue.suggestion}")
        report_lines.append("")
    
    if info:
        report_lines.append("ℹ️  Information:")
        for issue in info:
            report_lines.append(f"  • {issue.message}")
        report_lines.append("")
    
    return "\n".join(report_lines)


def create_image_validator(expected_size: Tuple[int, int] = (600, 600),
                          validation_mode: ImageValidationMode = ImageValidationMode.NORMAL,
                          calculate_hash: bool = True,
                          check_quality_metrics: bool = True) -> ImageValidator:
    """
    Create a configured image validator
    
    Args:
        expected_size: Expected image dimensions
        validation_mode: Validation strictness mode
        calculate_hash: Whether to calculate file hash
        check_quality_metrics: Whether to perform quality analysis
        
    Returns:
        ImageValidator: Configured validator instance
    """
    return ImageValidator(
        validation_mode=validation_mode,
        expected_size=expected_size,
        calculate_hash=calculate_hash,
        check_quality_metrics=check_quality_metrics
    )


def get_image_info(file_path: Union[str, Path]) -> ImageValidationInfo:
    """
    Get comprehensive information about an image file
    
    Args:
        file_path: Path to the image file
        
    Returns:
        ImageValidationInfo: Complete image information
    """
    validator = ImageValidator()
    image_info = validator._get_image_info(str(file_path))
    
    # Perform additional analysis if file exists
    if Path(file_path).exists():
        try:
            with Image.open(str(file_path)) as img:
                image_info.image_size = img.size
                image_info.image_mode = img.mode
                image_info.image_format = img.format
                image_info.has_alpha_channel = img.mode in ['RGBA', 'LA'] or 'transparency' in img.info
                image_info.pixel_data_integrity = validator._check_image_corruption(img)
                
                # Get pixel distribution
                pixel_stats = validator._analyze_pixel_distribution(img)
                image_info.total_pixels = pixel_stats['total']
                image_info.transparent_pixels = pixel_stats['transparent']
                image_info.opaque_pixels = pixel_stats['opaque']
                image_info.partially_transparent_pixels = pixel_stats['partial']
                
        except Exception:
            pass  # Info will remain with default values
    
    return image_info


# Convenience functions

def validate_multiple_images(file_paths: List[Union[str, Path]],
                            expected_size: Tuple[int, int] = (600, 600),
                            validation_mode: ImageValidationMode = ImageValidationMode.NORMAL) -> Dict[str, ValidationResult]:
    """
    Validate multiple composite image files
    
    Args:
        file_paths: List of paths to image files to validate
        expected_size: Expected (width, height) dimensions
        validation_mode: Validation strictness mode
        
    Returns:
        Dict[str, ValidationResult]: Results keyed by file path
    """
    validator = ImageValidator(
        validation_mode=validation_mode,
        expected_size=expected_size
    )
    
    results = {}
    for file_path in file_paths:
        results[str(file_path)] = validator.validate_image(file_path)
    
    return results


def get_image_validation_report(result: ValidationResult, file_path: str = "") -> str:
    """
    Generate a human-readable validation report
    
    Args:
        result: Validation result to report on
        file_path: Optional file path for context
        
    Returns:
        str: Formatted validation report
    """
    if not result.issues:
        return f"✅ Image validation passed: {file_path or 'Image'}"
    
    report_lines = [f"📋 Image Validation Report: {file_path or 'Image'}"]
    report_lines.append(f"Status: {'✅ PASSED' if result.is_valid else '❌ FAILED'}")
    report_lines.append("")
    
    # Group issues by severity
    errors = [issue for issue in result.issues if issue.severity == ValidationSeverity.ERROR]
    warnings = [issue for issue in result.issues if issue.severity == ValidationSeverity.WARNING]
    info = [issue for issue in result.issues if issue.severity == ValidationSeverity.INFO]
    
    if errors:
        report_lines.append("❌ Errors:")
        for issue in errors:
            report_lines.append(f"  • {issue.message}")
            if issue.suggestion:
                report_lines.append(f"    💡 {issue.suggestion}")
        report_lines.append("")
    
    if warnings:
        report_lines.append("⚠️  Warnings:")
        for issue in warnings:
            report_lines.append(f"  • {issue.message}")
            if issue.suggestion:
                report_lines.append(f"    💡 {issue.suggestion}")
        report_lines.append("")
    
    if info:
        report_lines.append("ℹ️  Information:")
        for issue in info:
            report_lines.append(f"  • {issue.message}")
        report_lines.append("")
    
    return "\n".join(report_lines)


def create_image_validator(expected_size: Tuple[int, int] = (600, 600),
                          validation_mode: ImageValidationMode = ImageValidationMode.NORMAL,
                          calculate_hash: bool = True,
                          check_quality_metrics: bool = True) -> ImageValidator:
    """
    Create a configured image validator
    
    Args:
        expected_size: Expected image dimensions
        validation_mode: Validation strictness mode
        calculate_hash: Whether to calculate file hash
        check_quality_metrics: Whether to perform quality analysis
        
    Returns:
        ImageValidator: Configured validator instance
    """
    return ImageValidator(
        validation_mode=validation_mode,
        expected_size=expected_size,
        calculate_hash=calculate_hash,
        check_quality_metrics=check_quality_metrics
    )


def get_image_info(file_path: Union[str, Path]) -> ImageValidationInfo:
    """
    Get comprehensive information about an image file
    
    Args:
        file_path: Path to the image file
        
    Returns:
        ImageValidationInfo: Complete image information
    """
    validator = ImageValidator()
    image_info = validator._get_image_info(str(file_path))
    
    # Perform additional analysis if file exists
    if Path(file_path).exists():
        try:
            with Image.open(str(file_path)) as img:
                image_info.image_size = img.size
                image_info.image_mode = img.mode
                image_info.image_format = img.format
                image_info.has_alpha_channel = img.mode in ['RGBA', 'LA'] or 'transparency' in img.info
                image_info.pixel_data_integrity = validator._check_image_corruption(img)
                
                # Get pixel distribution
                pixel_stats = validator._analyze_pixel_distribution(img)
                image_info.total_pixels = pixel_stats['total']
                image_info.transparent_pixels = pixel_stats['transparent']
                image_info.opaque_pixels = pixel_stats['opaque']
                image_info.partially_transparent_pixels = pixel_stats['partial']
                
        except Exception:
            pass  # Info will remain with default values
    
    return image_info 