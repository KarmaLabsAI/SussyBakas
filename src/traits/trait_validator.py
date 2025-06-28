"""
GenConfig Trait File Validator

This module provides validation for individual trait image files according to
GenConfig specifications. It validates format, dimensions, transparency, file size,
naming conventions, and other requirements for trait images.
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from PIL import Image

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.logic_validator import ValidationResult, ValidationIssue, ValidationSeverity
from utils.file_utils import validate_file_exists, get_file_size, ValidationError


class TraitValidationError(Exception):
    """Custom exception for trait validation errors"""
    pass


@dataclass
class TraitFileInfo:
    """Information about a trait file"""
    file_path: str
    file_name: str
    file_size: int
    image_format: Optional[str] = None
    image_mode: Optional[str] = None
    image_size: Optional[Tuple[int, int]] = None
    has_transparency: Optional[bool] = None
    is_valid_name: Optional[bool] = None
    name_parts: Optional[Dict[str, str]] = None


class TraitFileValidator:
    """
    Validator for individual trait image files
    
    Validates trait files according to GenConfig specification:
    - Format: PNG with transparency support
    - Dimensions: Must match configured cell size (default: 200×200 pixels)
    - Color Mode: RGBA (32-bit) or other transparency-supporting modes
    - File Size: Maximum 2MB per trait image
    - Naming Convention: trait-{descriptive-name}-{unique-id}.png
    """
    
    # Constants from GenConfig specification
    VALID_FORMAT = "PNG"
    VALID_EXTENSION = ".png"
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
    DEFAULT_EXPECTED_SIZE = (200, 200)
    TRANSPARENCY_MODES = ['RGBA', 'LA', 'P']  # Modes that support transparency
    NAMING_PATTERN = re.compile(r'^trait-([a-zA-Z0-9\-_]+)-(\d{3})\.png$')
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize trait file validator
        
        Args:
            strict_mode: Whether to treat warnings as errors
        """
        self.strict_mode = strict_mode
        self.issues: List[ValidationIssue] = []
    
    def validate_file(self, file_path: Union[str, Path], 
                     expected_size: Optional[Tuple[int, int]] = None) -> ValidationResult:
        """
        Validate a single trait file against GenConfig requirements
        
        Args:
            file_path: Path to the trait file to validate
            expected_size: Expected (width, height) dimensions, defaults to (200, 200)
            
        Returns:
            ValidationResult: Complete validation result with issues
        """
        self.issues = []
        file_path_str = str(file_path)
        
        if expected_size is None:
            expected_size = self.DEFAULT_EXPECTED_SIZE
        
        # Get basic file information
        file_info = self._get_file_info(file_path_str)
        
        # Perform all validation checks
        self._validate_file_existence(file_info)
        self._validate_file_extension(file_info)
        self._validate_file_size(file_info)
        self._validate_naming_convention(file_info)
        self._validate_image_properties(file_info, expected_size)
        
        # Determine if file is valid
        error_count = len([issue for issue in self.issues 
                          if issue.severity == ValidationSeverity.ERROR])
        warning_count = len([issue for issue in self.issues 
                           if issue.severity == ValidationSeverity.WARNING])
        
        # In strict mode, warnings are treated as errors
        is_valid = error_count == 0 and (not self.strict_mode or warning_count == 0)
        
        return ValidationResult(is_valid=is_valid, issues=self.issues.copy())
    
    def _get_file_info(self, file_path: str) -> TraitFileInfo:
        """Extract basic file information"""
        path = Path(file_path)
        
        file_info = TraitFileInfo(
            file_path=file_path,
            file_name=path.name,
            file_size=0
        )
        
        # Get file size if file exists
        if path.exists():
            try:
                file_info.file_size = get_file_size(file_path)
            except Exception:
                pass
        
        return file_info
    
    def _validate_file_existence(self, file_info: TraitFileInfo) -> None:
        """Validate that the file exists and is accessible"""
        if not validate_file_exists(file_info.file_path):
            self._add_issue(
                ValidationSeverity.ERROR,
                "file_existence",
                f"Trait file does not exist or is not accessible: {file_info.file_path}",
                file_info.file_path,
                "Ensure the file exists and has proper permissions"
            )
    
    def _validate_file_extension(self, file_info: TraitFileInfo) -> None:
        """Validate file extension is .png"""
        path = Path(file_info.file_path)
        
        if path.suffix.lower() != self.VALID_EXTENSION:
            self._add_issue(
                ValidationSeverity.ERROR,
                "file_format",
                f"Invalid file extension '{path.suffix}', must be '{self.VALID_EXTENSION}'",
                file_info.file_path,
                f"Rename file to use {self.VALID_EXTENSION} extension"
            )
    
    def _validate_file_size(self, file_info: TraitFileInfo) -> None:
        """Validate file size is within limits"""
        if file_info.file_size > self.MAX_FILE_SIZE:
            size_mb = file_info.file_size / (1024 * 1024)
            max_mb = self.MAX_FILE_SIZE / (1024 * 1024)
            self._add_issue(
                ValidationSeverity.ERROR,
                "file_size",
                f"File size {size_mb:.2f}MB exceeds maximum {max_mb:.1f}MB",
                file_info.file_path,
                "Compress or optimize the image to reduce file size"
            )
        elif file_info.file_size == 0:
            self._add_issue(
                ValidationSeverity.ERROR,
                "file_size",
                "File is empty (0 bytes)",
                file_info.file_path,
                "Ensure the file contains valid image data"
            )
        elif file_info.file_size < 100:  # Very small files are suspicious
            self._add_issue(
                ValidationSeverity.WARNING,
                "file_size",
                f"File size {file_info.file_size} bytes is very small",
                file_info.file_path,
                "Verify the file contains proper image data"
            )
    
    def _validate_naming_convention(self, file_info: TraitFileInfo) -> None:
        """Validate naming convention: trait-{descriptive-name}-{unique-id}.png"""
        match = self.NAMING_PATTERN.match(file_info.file_name)
        
        if not match:
            self._add_issue(
                ValidationSeverity.ERROR,
                "naming_convention",
                f"Invalid filename format: '{file_info.file_name}'",
                file_info.file_path,
                "Use format: trait-{descriptive-name}-{unique-id}.png (e.g., trait-red-bg-001.png)"
            )
            file_info.is_valid_name = False
        else:
            file_info.is_valid_name = True
            file_info.name_parts = {
                "descriptive_name": match.group(1),
                "unique_id": match.group(2)
            }
            
            # Additional naming validation
            descriptive_name = match.group(1)
            unique_id = match.group(2)
            
            # Check descriptive name is reasonable
            if len(descriptive_name) < 2:
                self._add_issue(
                    ValidationSeverity.WARNING,
                    "naming_convention",
                    f"Descriptive name '{descriptive_name}' is very short",
                    file_info.file_path,
                    "Use a more descriptive name for better organization"
                )
            
            # Check unique ID is properly formatted
            if not unique_id.isdigit() or len(unique_id) != 3:
                self._add_issue(
                    ValidationSeverity.ERROR,
                    "naming_convention",
                    f"Invalid unique ID format '{unique_id}', must be 3-digit number (001-999)",
                    file_info.file_path,
                    "Use a 3-digit zero-padded number (e.g., 001, 042, 123)"
                )
    
    def _validate_image_properties(self, file_info: TraitFileInfo, 
                                  expected_size: Tuple[int, int]) -> None:
        """Validate image format, mode, dimensions, and transparency"""
        if not validate_file_exists(file_info.file_path):
            return  # Skip if file doesn't exist (already reported)
        
        try:
            with Image.open(file_info.file_path) as img:
                file_info.image_format = img.format
                file_info.image_mode = img.mode
                file_info.image_size = img.size
                file_info.has_transparency = self._check_transparency(img)
                
                # Validate image format
                if img.format != self.VALID_FORMAT:
                    self._add_issue(
                        ValidationSeverity.ERROR,
                        "image_format",
                        f"Invalid image format '{img.format}', must be '{self.VALID_FORMAT}'",
                        file_info.file_path,
                        f"Convert image to {self.VALID_FORMAT} format"
                    )
                
                # Validate image mode supports transparency
                if img.mode not in self.TRANSPARENCY_MODES:
                    self._add_issue(
                        ValidationSeverity.ERROR,
                        "image_transparency",
                        f"Image mode '{img.mode}' does not support transparency",
                        file_info.file_path,
                        f"Convert to mode that supports transparency: {', '.join(self.TRANSPARENCY_MODES)}"
                    )
                
                # Validate dimensions
                if img.size != expected_size:
                    self._add_issue(
                        ValidationSeverity.ERROR,
                        "image_dimensions",
                        f"Image size {img.size} does not match expected {expected_size}",
                        file_info.file_path,
                        f"Resize image to {expected_size[0]}×{expected_size[1]} pixels"
                    )
                
                # Check if image actually has transparent pixels (for informational purposes)
                if img.mode in self.TRANSPARENCY_MODES and not file_info.has_transparency:
                    self._add_issue(
                        ValidationSeverity.INFO,
                        "image_transparency",
                        "Image supports transparency but appears to have no transparent pixels",
                        file_info.file_path,
                        "Consider using transparency for better layering in composites"
                    )
                
                # Validate reasonable dimensions (not too large or small)
                width, height = img.size
                if width > 1000 or height > 1000:
                    self._add_issue(
                        ValidationSeverity.WARNING,
                        "image_dimensions",
                        f"Image dimensions {img.size} are very large",
                        file_info.file_path,
                        "Consider reducing size for better performance"
                    )
                elif width < 50 or height < 50:
                    self._add_issue(
                        ValidationSeverity.WARNING,
                        "image_dimensions",
                        f"Image dimensions {img.size} are very small",
                        file_info.file_path,
                        "Verify image quality is sufficient for NFT generation"
                    )
                
        except Exception as e:
            self._add_issue(
                ValidationSeverity.ERROR,
                "image_corruption",
                f"Cannot open or read image file: {e}",
                file_info.file_path,
                "Ensure file is a valid image and not corrupted"
            )
    
    def _check_transparency(self, img: Image.Image) -> bool:
        """Check if image actually has transparent pixels"""
        try:
            if img.mode == 'RGBA':
                # Check if any pixel has alpha < 255
                alpha_channel = img.split()[-1]
                return alpha_channel.getextrema()[0] < 255
            elif img.mode == 'LA':
                # Grayscale with alpha
                alpha_channel = img.split()[-1]
                return alpha_channel.getextrema()[0] < 255
            elif img.mode == 'P':
                # Palette mode with possible transparency
                return 'transparency' in img.info
            else:
                return False
        except Exception:
            return False
    
    def _add_issue(self, severity: ValidationSeverity, category: str,
                   message: str, path: Optional[str] = None,
                   suggestion: Optional[str] = None) -> None:
        """Add validation issue to the list"""
        issue = ValidationIssue(
            severity=severity,
            category=category,
            message=message,
            path=path,
            suggestion=suggestion
        )
        self.issues.append(issue)


def validate_trait_file(file_path: Union[str, Path], 
                       expected_size: Tuple[int, int] = (200, 200),
                       strict_mode: bool = False) -> ValidationResult:
    """
    Convenience function to validate a single trait file
    
    Args:
        file_path: Path to the trait file to validate
        expected_size: Expected (width, height) dimensions
        strict_mode: Whether to treat warnings as errors
        
    Returns:
        ValidationResult: Complete validation result with issues
    """
    validator = TraitFileValidator(strict_mode=strict_mode)
    return validator.validate_file(file_path, expected_size)


def validate_multiple_trait_files(file_paths: List[Union[str, Path]],
                                 expected_size: Tuple[int, int] = (200, 200),
                                 strict_mode: bool = False) -> Dict[str, ValidationResult]:
    """
    Validate multiple trait files
    
    Args:
        file_paths: List of paths to trait files to validate
        expected_size: Expected (width, height) dimensions
        strict_mode: Whether to treat warnings as errors
        
    Returns:
        Dict mapping file paths to their validation results
    """
    validator = TraitFileValidator(strict_mode=strict_mode)
    results = {}
    
    for file_path in file_paths:
        file_path_str = str(file_path)
        results[file_path_str] = validator.validate_file(file_path, expected_size)
    
    return results


def get_trait_validation_report(result: ValidationResult, file_path: str = "") -> str:
    """
    Generate a human-readable validation report for a trait file
    
    Args:
        result: ValidationResult to format
        file_path: Optional file path for context
        
    Returns:
        str: Formatted validation report
    """
    report_lines = []
    
    # Header
    status = "✅ VALID" if result.is_valid else "❌ INVALID"
    file_context = f" - {file_path}" if file_path else ""
    report_lines.append(f"Trait File Validation: {status}{file_context}")
    report_lines.append("=" * 60)
    
    if not result.issues:
        report_lines.append("✅ No validation issues found")
        return "\n".join(report_lines)
    
    # Summary
    summary = result.get_summary()
    report_lines.append(f"Total Issues: {summary['total_issues']}")
    report_lines.append(f"Errors: {summary['errors']}")
    report_lines.append(f"Warnings: {summary['warnings']}")
    report_lines.append(f"Info: {summary['infos']}")
    
    if summary['categories']:
        report_lines.append(f"Categories: {', '.join(summary['categories'])}")
    
    # Issues by severity
    for severity in [ValidationSeverity.ERROR, ValidationSeverity.WARNING, ValidationSeverity.INFO]:
        issues = [issue for issue in result.issues if issue.severity == severity]
        if issues:
            report_lines.append(f"\n{severity.value}S:")
            for issue in issues:
                prefix = "❌" if severity == ValidationSeverity.ERROR else "⚠️" if severity == ValidationSeverity.WARNING else "ℹ️"
                report_lines.append(f"  {prefix} {issue.message}")
                if issue.suggestion:
                    report_lines.append(f"     💡 {issue.suggestion}")
    
    return "\n".join(report_lines)
