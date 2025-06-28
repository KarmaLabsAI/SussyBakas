"""
Test suite for GenConfig Trait File Validator (Component 3.1)

Tests validation of individual trait image files according to GenConfig specifications.
"""

import unittest
import tempfile
import shutil
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from traits.trait_validator import (
    TraitFileValidator,
    TraitValidationError,
    TraitFileInfo,
    validate_trait_file,
    validate_multiple_trait_files,
    get_trait_validation_report
)
from config.logic_validator import ValidationResult, ValidationIssue, ValidationSeverity


class TestTraitFileInfo(unittest.TestCase):
    """Test TraitFileInfo data structure"""
    
    def test_trait_file_info_initialization(self):
        """Test TraitFileInfo can be created with required fields"""
        info = TraitFileInfo(
            file_path="/path/to/trait.png",
            file_name="trait.png",
            file_size=1024
        )
        
        self.assertEqual(info.file_path, "/path/to/trait.png")
        self.assertEqual(info.file_name, "trait.png")
        self.assertEqual(info.file_size, 1024)
        self.assertIsNone(info.image_format)
        self.assertIsNone(info.image_mode)
        self.assertIsNone(info.image_size)
        self.assertIsNone(info.has_transparency)
        self.assertIsNone(info.is_valid_name)
        self.assertIsNone(info.name_parts)
    
    def test_trait_file_info_with_optional_fields(self):
        """Test TraitFileInfo with all optional fields set"""
        info = TraitFileInfo(
            file_path="/path/to/trait.png",
            file_name="trait.png",
            file_size=1024,
            image_format="PNG",
            image_mode="RGBA",
            image_size=(200, 200),
            has_transparency=True,
            is_valid_name=True,
            name_parts={"descriptive_name": "red-bg", "unique_id": "001"}
        )
        
        self.assertEqual(info.image_format, "PNG")
        self.assertEqual(info.image_mode, "RGBA")
        self.assertEqual(info.image_size, (200, 200))
        self.assertTrue(info.has_transparency)
        self.assertTrue(info.is_valid_name)
        self.assertEqual(info.name_parts["descriptive_name"], "red-bg")
        self.assertEqual(info.name_parts["unique_id"], "001")


class TestTraitFileValidator(unittest.TestCase):
    """Test TraitFileValidator class"""
    
    def setUp(self):
        """Set up test fixtures and temporary directory"""
        self.test_dir = tempfile.mkdtemp()
        self.validator = TraitFileValidator()
        self.strict_validator = TraitFileValidator(strict_mode=True)
        
        # Create test images with different properties
        self._create_test_images()
    
    def tearDown(self):
        """Clean up test files and temporary directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def _create_test_images(self):
        """Create various test images for validation testing"""
        # Valid PNG image with correct size and transparency
        self.valid_trait_path = os.path.join(self.test_dir, "trait-red-bg-001.png")
        self._create_png_image(self.valid_trait_path, (200, 200), "RGBA", has_transparency=True)
        
        # Valid PNG without transparency
        self.valid_no_transparency_path = os.path.join(self.test_dir, "trait-blue-bg-002.png")
        self._create_png_image(self.valid_no_transparency_path, (200, 200), "RGBA", has_transparency=False)
        
        # Wrong size image
        self.wrong_size_path = os.path.join(self.test_dir, "trait-green-bg-003.png")
        self._create_png_image(self.wrong_size_path, (100, 100), "RGBA")
        
        # Wrong format (JPEG)
        self.wrong_format_path = os.path.join(self.test_dir, "trait-yellow-bg-004.jpg")
        self._create_jpeg_image(self.wrong_format_path, (200, 200))
        
        # Wrong mode (RGB without transparency)
        self.wrong_mode_path = os.path.join(self.test_dir, "trait-purple-bg-005.png")
        self._create_png_image(self.wrong_mode_path, (200, 200), "RGB")
        
        # Invalid naming convention
        self.invalid_name_path = os.path.join(self.test_dir, "invalid-name.png")
        self._create_png_image(self.invalid_name_path, (200, 200), "RGBA")
        
        # Very large image
        self.large_image_path = os.path.join(self.test_dir, "trait-large-image-006.png")
        self._create_png_image(self.large_image_path, (1200, 1200), "RGBA")
        
        # Very small image
        self.small_image_path = os.path.join(self.test_dir, "trait-small-image-007.png")
        self._create_png_image(self.small_image_path, (30, 30), "RGBA")
        
        # Empty file
        self.empty_file_path = os.path.join(self.test_dir, "trait-empty-008.png")
        with open(self.empty_file_path, 'w') as f:
            pass  # Create empty file
    
    def _create_png_image(self, path: str, size: tuple, mode: str, has_transparency: bool = True):
        """Create a PNG image with specified properties"""
        if mode == "RGBA":
            color = (255, 0, 0, 255)
        elif mode == "RGB":
            color = (255, 0, 0)
        elif mode == "LA":
            color = (255, 255)
        elif mode == "L":
            color = 255
        else:
            color = (255, 0, 0, 255)
        
        img = Image.new(mode, size, color=color)
        
        if has_transparency and mode == "RGBA":
            # Add some transparent pixels
            draw = ImageDraw.Draw(img)
            draw.rectangle([50, 50, 150, 150], fill=(0, 0, 255, 128))
        elif not has_transparency and mode == "RGBA":
            # Make fully opaque
            img = Image.new("RGBA", size, color=(255, 0, 0, 255))
        
        img.save(path, "PNG")
    
    def _create_jpeg_image(self, path: str, size: tuple):
        """Create a JPEG image"""
        img = Image.new("RGB", size, color=(255, 255, 0))
        img.save(path, "JPEG")
    
    def test_validator_initialization(self):
        """Test TraitFileValidator initialization"""
        # Normal mode
        validator = TraitFileValidator()
        self.assertFalse(validator.strict_mode)
        self.assertEqual(len(validator.issues), 0)
        
        # Strict mode
        strict_validator = TraitFileValidator(strict_mode=True)
        self.assertTrue(strict_validator.strict_mode)
        self.assertEqual(len(strict_validator.issues), 0)
    
    def test_validate_valid_trait_file(self):
        """Test validation of a perfectly valid trait file"""
        result = self.validator.validate_file(self.valid_trait_path, (200, 200))
        
        self.assertTrue(result.is_valid)
        # Should only have info message about transparency (if any)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.warnings), 0)
    
    def test_validate_nonexistent_file(self):
        """Test validation of non-existent file"""
        nonexistent_path = os.path.join(self.test_dir, "does-not-exist.png")
        result = self.validator.validate_file(nonexistent_path)
        
        self.assertFalse(result.is_valid)
        self.assertTrue(len(result.errors) >= 1)
        
        # Should have file existence error
        existence_errors = [e for e in result.errors if e.category == "file_existence"]
        self.assertEqual(len(existence_errors), 1)
        self.assertIn("does not exist", existence_errors[0].message)
    
    def test_validate_wrong_file_extension(self):
        """Test validation of file with wrong extension"""
        result = self.validator.validate_file(self.wrong_format_path)
        
        self.assertFalse(result.is_valid)
        error_messages = [issue.message for issue in result.errors]
        self.assertTrue(any("Invalid file extension" in msg for msg in error_messages))
    
    def test_validate_wrong_dimensions(self):
        """Test validation of image with wrong dimensions"""
        result = self.validator.validate_file(self.wrong_size_path, (200, 200))
        
        self.assertFalse(result.is_valid)
        error_messages = [issue.message for issue in result.errors]
        self.assertTrue(any("does not match expected" in msg for msg in error_messages))
    
    def test_validate_wrong_image_mode(self):
        """Test validation of image without transparency support"""
        result = self.validator.validate_file(self.wrong_mode_path)
        
        self.assertFalse(result.is_valid)
        error_messages = [issue.message for issue in result.errors]
        self.assertTrue(any("does not support transparency" in msg for msg in error_messages))
    
    def test_validate_invalid_naming_convention(self):
        """Test validation of file with invalid naming convention"""
        result = self.validator.validate_file(self.invalid_name_path)
        
        self.assertFalse(result.is_valid)
        error_messages = [issue.message for issue in result.errors]
        self.assertTrue(any("Invalid filename format" in msg for msg in error_messages))
    
    def test_validate_empty_file(self):
        """Test validation of empty file"""
        result = self.validator.validate_file(self.empty_file_path)
        
        self.assertFalse(result.is_valid)
        error_messages = [issue.message for issue in result.errors]
        self.assertTrue(any("File is empty" in msg for msg in error_messages))
    
    def test_validate_large_image_warning(self):
        """Test validation generates warning for very large images"""
        result = self.validator.validate_file(self.large_image_path)
        
        # Should have warnings about large size
        warning_messages = [issue.message for issue in result.warnings]
        self.assertTrue(any("very large" in msg for msg in warning_messages))
    
    def test_validate_small_image_warning(self):
        """Test validation generates warning for very small images"""
        result = self.validator.validate_file(self.small_image_path)
        
        # Should have warnings about small size
        warning_messages = [issue.message for issue in result.warnings]
        self.assertTrue(any("very small" in msg for msg in warning_messages))
    
    def test_strict_mode_treats_warnings_as_errors(self):
        """Test that strict mode treats warnings as validation failures"""
        # In normal mode, warnings don't fail validation
        normal_result = self.validator.validate_file(self.large_image_path)
        
        # In strict mode, warnings cause validation failure
        strict_result = self.strict_validator.validate_file(self.large_image_path)
        if len(strict_result.warnings) > 0:
            self.assertFalse(strict_result.is_valid)
    
    def test_naming_convention_validation(self):
        """Test detailed naming convention validation"""
        # Valid name
        valid_name_path = os.path.join(self.test_dir, "trait-good-name-123.png")
        self._create_png_image(valid_name_path, (200, 200), "RGBA")
        result = self.validator.validate_file(valid_name_path)
        naming_errors = [issue for issue in result.errors if issue.category == "naming_convention"]
        self.assertEqual(len(naming_errors), 0)
        
        # Short descriptive name (should warn)
        short_name_path = os.path.join(self.test_dir, "trait-a-001.png")
        self._create_png_image(short_name_path, (200, 200), "RGBA")
        result = self.validator.validate_file(short_name_path)
        naming_warnings = [issue for issue in result.warnings if issue.category == "naming_convention"]
        self.assertTrue(len(naming_warnings) > 0)
        
        # Invalid ID format
        invalid_id_path = os.path.join(self.test_dir, "trait-test-12.png")
        self._create_png_image(invalid_id_path, (200, 200), "RGBA")
        result = self.validator.validate_file(invalid_id_path)
        naming_errors = [issue for issue in result.errors if issue.category == "naming_convention"]
        self.assertTrue(len(naming_errors) > 0)
        # Should have general naming convention error due to invalid ID format
        self.assertTrue(any("Invalid filename format" in error.message for error in naming_errors))


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        
        # Create some test files
        self.valid_file1 = os.path.join(self.test_dir, "trait-test-001.png")
        self.valid_file2 = os.path.join(self.test_dir, "trait-test-002.png")
        self.invalid_file = os.path.join(self.test_dir, "invalid-name.png")
        
        self._create_test_files()
    
    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def _create_test_files(self):
        """Create test files"""
        for file_path in [self.valid_file1, self.valid_file2, self.invalid_file]:
            img = Image.new("RGBA", (200, 200), color=(255, 0, 0, 255))
            img.save(file_path, "PNG")
    
    def test_validate_trait_file_function(self):
        """Test validate_trait_file convenience function"""
        # Valid file
        result = validate_trait_file(self.valid_file1)
        self.assertIsInstance(result, ValidationResult)
        
        # Test with custom parameters
        result = validate_trait_file(self.valid_file1, expected_size=(200, 200), strict_mode=True)
        self.assertIsInstance(result, ValidationResult)
        
        # Invalid file
        result = validate_trait_file(self.invalid_file)
        self.assertFalse(result.is_valid)
    
    def test_validate_multiple_trait_files_function(self):
        """Test validate_multiple_trait_files convenience function"""
        file_paths = [self.valid_file1, self.valid_file2, self.invalid_file]
        results = validate_multiple_trait_files(file_paths)
        
        self.assertIsInstance(results, dict)
        self.assertEqual(len(results), 3)
        
        # Check that all file paths are in results
        for file_path in file_paths:
            self.assertIn(str(file_path), results)
            self.assertIsInstance(results[str(file_path)], ValidationResult)
    
    def test_get_trait_validation_report_function(self):
        """Test get_trait_validation_report function"""
        result = validate_trait_file(self.invalid_file)
        
        # Test report generation
        report = get_trait_validation_report(result, self.invalid_file)
        self.assertIsInstance(report, str)
        self.assertIn("Trait File Validation:", report)
        
        # Test with valid file
        valid_result = validate_trait_file(self.valid_file1)
        valid_report = get_trait_validation_report(valid_result, self.valid_file1)
        self.assertIn("✅", valid_report)
        
        # Test without file path
        report_no_path = get_trait_validation_report(result)
        self.assertIsInstance(report_no_path, str)


if __name__ == '__main__':
    unittest.main()
