"""
Test suite for GenConfig Image Validator

Tests the validation of generated composite images for dimensions, format, 
file integrity, and image quality.
Follows the testing strategy: Setup -> Execution -> Validation -> Cleanup
"""

import os
import tempfile
import shutil
from pathlib import Path
import pytest
import sys
from PIL import Image
import hashlib

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from image.image_validator import (
    validate_image,
    validate_multiple_images,
    get_image_validation_report,
    create_image_validator,
    get_image_info,
    ImageValidator,
    ImageValidationInfo,
    ImageValidationMode,
    ImageValidationError
)
from config.logic_validator import ValidationResult, ValidationSeverity
from infrastructure.directory_manager import create_collection_structure


class TestImageValidationInfo:
    """Test cases for the ImageValidationInfo data structure"""
    
    def test_image_validation_info_creation(self):
        """Test: ImageValidationInfo creation and properties"""
        # Execution
        info = ImageValidationInfo(
            file_path="/test/image.png",
            file_name="image.png",
            file_size=1024000,
            total_pixels=360000,
            transparent_pixels=100000,
            opaque_pixels=260000
        )
        
        # Validation
        assert info.file_path == "/test/image.png"
        assert info.file_name == "image.png" 
        assert info.file_size == 1024000
        assert info.total_pixels == 360000
        assert abs(info.transparency_ratio - 0.278) < 0.01  # ~27.8%
        assert abs(info.opacity_ratio - 0.722) < 0.01      # ~72.2%
    
    def test_transparency_ratios_edge_cases(self):
        """Test: Transparency ratio calculations with edge cases"""
        # Test with zero pixels
        info = ImageValidationInfo("/test.png", "test.png", 0, total_pixels=0)
        assert info.transparency_ratio == 0.0
        assert info.opacity_ratio == 0.0
        
        # Test with all transparent
        info = ImageValidationInfo("/test.png", "test.png", 0, 
                                 total_pixels=100, transparent_pixels=100)
        assert info.transparency_ratio == 1.0
        assert info.opacity_ratio == 0.0


class TestImageValidator:
    """Test cases for the ImageValidator class"""
    
    def setup_method(self):
        """Setup: Create test fixtures and sample data"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_dir = Path(self.temp_dir) / "test-images"
        self.test_dir.mkdir(exist_ok=True)
        
        # Create test images
        self._create_test_images()
        
        # Initialize validator
        self.validator = ImageValidator()
    
    def teardown_method(self):
        """Cleanup: Remove test files and reset state"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _create_test_images(self):
        """Create various test images for validation"""
        # Valid 600x600 RGBA PNG
        self.valid_image_path = self.test_dir / "valid_composite.png"
        valid_image = Image.new('RGBA', (600, 600), (255, 255, 255, 255))
        # Add some content to make it more realistic
        for x in range(0, 600, 100):
            for y in range(0, 600, 100):
                for px in range(x, min(x+50, 600)):
                    for py in range(y, min(y+50, 600)):
                        valid_image.putpixel((px, py), (255, 0, 0, 128))
        valid_image.save(self.valid_image_path, 'PNG')
        
        # Invalid size image (300x300)
        self.invalid_size_path = self.test_dir / "invalid_size.png"
        invalid_size = Image.new('RGBA', (300, 300), (255, 255, 255, 255))
        invalid_size.save(self.invalid_size_path, 'PNG')
        
        # Invalid format (JPEG)
        self.invalid_format_path = self.test_dir / "invalid_format.jpg"
        invalid_format = Image.new('RGB', (600, 600), (255, 255, 255))
        invalid_format.save(self.invalid_format_path, 'JPEG')
        
        # RGB mode (valid but not preferred)
        self.rgb_mode_path = self.test_dir / "rgb_mode.png"
        rgb_image = Image.new('RGB', (600, 600), (255, 255, 255))
        rgb_image.save(self.rgb_mode_path, 'PNG')
        
        # Completely transparent image  
        self.transparent_path = self.test_dir / "transparent.png"
        transparent = Image.new('RGBA', (600, 600), (255, 255, 255, 0))
        transparent.save(self.transparent_path, 'PNG')
        
        # Very small file
        self.tiny_image_path = self.test_dir / "tiny.png"
        tiny = Image.new('RGBA', (600, 600), (255, 255, 255, 255))
        # Save with maximum compression to make it small
        tiny.save(self.tiny_image_path, 'PNG', optimize=True)
        
        # Non-existent file path
        self.nonexistent_path = self.test_dir / "does_not_exist.png"
    
    def test_validator_initialization_default(self):
        """Test: ImageValidator initialization with default parameters"""
        # Execution
        validator = ImageValidator()
        
        # Validation
        assert validator.validation_mode == ImageValidationMode.NORMAL
        assert validator.expected_size == (600, 600)
        assert validator.calculate_hash is True
        assert validator.check_quality_metrics is True
    
    def test_validator_initialization_custom(self):
        """Test: ImageValidator initialization with custom parameters"""
        # Execution
        validator = ImageValidator(
            validation_mode=ImageValidationMode.STRICT,
            expected_size=(800, 800),
            calculate_hash=False,
            check_quality_metrics=False
        )
        
        # Validation
        assert validator.validation_mode == ImageValidationMode.STRICT
        assert validator.expected_size == (800, 800)
        assert validator.calculate_hash is False
        assert validator.check_quality_metrics is False
    
    def test_validate_valid_image_success(self):
        """Test: Successfully validating a valid composite image"""
        # Execution
        result = self.validator.validate_image(self.valid_image_path)
        
        # Validation
        assert result.is_valid is True
        assert len([i for i in result.issues if i.severity == ValidationSeverity.ERROR]) == 0
        # May have info messages but no errors
    
    def test_validate_invalid_size_failure(self):
        """Test: Validation fails for incorrect image dimensions"""
        # Execution
        result = self.validator.validate_image(self.invalid_size_path)
        
        # Validation
        assert result.is_valid is False
        error_messages = [i.message for i in result.issues if i.severity == ValidationSeverity.ERROR]
        assert any("Invalid dimensions" in msg for msg in error_messages)
    
    def test_validate_invalid_format_failure(self):
        """Test: Validation fails for incorrect file format"""
        # Execution
        result = self.validator.validate_image(self.invalid_format_path)
        
        # Validation
        assert result.is_valid is False
        error_messages = [i.message for i in result.issues if i.severity == ValidationSeverity.ERROR]
        assert any("Invalid image format" in msg for msg in error_messages)
    
    def test_validate_nonexistent_file_failure(self):
        """Test: Validation fails for non-existent file"""
        # Execution
        result = self.validator.validate_image(self.nonexistent_path)
        
        # Validation
        assert result.is_valid is False
        error_messages = [i.message for i in result.issues if i.severity == ValidationSeverity.ERROR]
        assert any("does not exist" in msg for msg in error_messages)
    
    def test_validate_rgb_mode_warning(self):
        """Test: RGB mode generates warning but passes validation"""
        # Execution
        result = self.validator.validate_image(self.rgb_mode_path)
        
        # Validation - Should pass with warnings in normal mode
        assert result.is_valid is True
        warning_messages = [i.message for i in result.issues if i.severity == ValidationSeverity.WARNING]
        assert any("RGBA" in msg and "preferred" in msg for msg in warning_messages)
    
    def test_validate_transparent_image_warning(self):
        """Test: Completely transparent image generates quality warning"""
        # Execution
        result = self.validator.validate_image(self.transparent_path)
        
        # Validation
        warning_messages = [i.message for i in result.issues if i.severity == ValidationSeverity.WARNING]
        assert any("completely transparent" in msg for msg in warning_messages)
    
    def test_validation_modes_strict(self):
        """Test: Strict validation mode treats warnings as failures"""
        # Setup
        strict_validator = ImageValidator(validation_mode=ImageValidationMode.STRICT)
        
        # Execution
        result = strict_validator.validate_image(self.rgb_mode_path)
        
        # Validation - Should fail in strict mode due to warnings
        assert result.is_valid is False
    
    def test_validation_modes_permissive(self):
        """Test: Permissive validation mode ignores warnings"""
        # Setup
        permissive_validator = ImageValidator(validation_mode=ImageValidationMode.PERMISSIVE)
        
        # Execution
        result = permissive_validator.validate_image(self.rgb_mode_path)
        
        # Validation - Should pass in permissive mode despite warnings
        assert result.is_valid is True
    
    def test_custom_expected_size(self):
        """Test: Validation with custom expected dimensions"""
        # Setup
        custom_validator = ImageValidator(expected_size=(300, 300))
        
        # Execution - Valid image should now fail with custom size
        result1 = custom_validator.validate_image(self.valid_image_path)
        result2 = custom_validator.validate_image(self.invalid_size_path)
        
        # Validation
        assert result1.is_valid is False  # 600x600 fails for 300x300 expectation
        assert result2.is_valid is True   # 300x300 passes for 300x300 expectation
    
    def test_image_corruption_detection(self):
        """Test: Detection of corrupted image data"""
        # Setup - Create a file with invalid image data
        corrupted_path = self.test_dir / "corrupted.png"
        with open(corrupted_path, 'wb') as f:
            f.write(b"This is not a valid PNG file")
        
        # Execution
        result = self.validator.validate_image(corrupted_path)
        
        # Validation
        assert result.is_valid is False
        error_messages = [i.message for i in result.issues if i.severity == ValidationSeverity.ERROR]
        assert any("not a valid image" in msg or "corrupted" in msg for msg in error_messages)


class TestConvenienceFunctions:
    """Test cases for convenience functions"""
    
    def setup_method(self):
        """Setup: Create test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_dir = Path(self.temp_dir) / "test-images"
        self.test_dir.mkdir(exist_ok=True)
        
        # Create a valid test image
        self.valid_image_path = self.test_dir / "valid.png"
        valid_image = Image.new('RGBA', (600, 600), (255, 255, 255, 128))
        valid_image.save(self.valid_image_path, 'PNG')
        
        # Create an invalid test image
        self.invalid_image_path = self.test_dir / "invalid.png"
        invalid_image = Image.new('RGBA', (300, 300), (255, 255, 255, 128))
        invalid_image.save(self.invalid_image_path, 'PNG')
    
    def teardown_method(self):
        """Cleanup: Remove test files"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_validate_image_convenience_function(self):
        """Test: validate_image convenience function"""
        # Execution
        result_valid = validate_image(self.valid_image_path)
        result_invalid = validate_image(self.invalid_image_path)
        
        # Validation
        assert result_valid.is_valid is True
        assert result_invalid.is_valid is False
    
    def test_validate_multiple_images(self):
        """Test: validate_multiple_images function"""
        # Execution
        results = validate_multiple_images([
            self.valid_image_path,
            self.invalid_image_path
        ])
        
        # Validation
        assert len(results) == 2
        assert results[str(self.valid_image_path)].is_valid is True
        assert results[str(self.invalid_image_path)].is_valid is False
    
    def test_get_image_validation_report_passed(self):
        """Test: Generate report for passed validation"""
        # Setup
        result = validate_image(self.valid_image_path)
        
        # Execution
        report = get_image_validation_report(result, str(self.valid_image_path))
        
        # Validation
        assert "✅" in report
        assert str(self.valid_image_path) in report
    
    def test_get_image_validation_report_failed(self):
        """Test: Generate report for failed validation"""
        # Setup
        result = validate_image(self.invalid_image_path)
        
        # Execution
        report = get_image_validation_report(result, str(self.invalid_image_path))
        
        # Validation
        assert "❌" in report
        assert "Invalid dimensions" in report
        assert str(self.invalid_image_path) in report
    
    def test_create_image_validator_function(self):
        """Test: create_image_validator convenience function"""
        # Execution
        validator = create_image_validator(
            expected_size=(800, 800),
            validation_mode=ImageValidationMode.STRICT
        )
        
        # Validation
        assert isinstance(validator, ImageValidator)
        assert validator.expected_size == (800, 800)
        assert validator.validation_mode == ImageValidationMode.STRICT
    
    def test_get_image_info_function(self):
        """Test: get_image_info convenience function"""
        # Execution
        info = get_image_info(self.valid_image_path)
        
        # Validation
        assert isinstance(info, ImageValidationInfo)
        assert info.file_path == str(self.valid_image_path)
        assert info.image_size == (600, 600)
        assert info.image_mode == 'RGBA'
        assert info.image_format == 'PNG'
        assert info.total_pixels == 360000  # 600 * 600


class TestErrorHandling:
    """Test cases for error handling and edge cases"""
    
    def test_image_validation_error_exception(self):
        """Test: ImageValidationError exception"""
        # Execution & Validation
        with pytest.raises(ImageValidationError) as exc_info:
            raise ImageValidationError("Test validation error")
        
        assert str(exc_info.value) == "Test validation error"
    
    def test_validator_with_inaccessible_file(self):
        """Test: Handling of files with permission issues"""
        # Note: This test may be platform-dependent
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create a file path that doesn't exist
            nonexistent_path = Path(temp_dir) / "nonexistent" / "deep" / "path.png"
            
            # Execution
            validator = ImageValidator()
            result = validator.validate_image(nonexistent_path)
            
            # Validation
            assert result.is_valid is False
            assert len(result.issues) > 0
            
        finally:
            shutil.rmtree(temp_dir)


def test_integration_workflow():
    """
    Integration test: Complete workflow from image creation to validation
    
    Tests the full integration workflow following the testing strategy:
    Setup -> Execution -> Validation -> Cleanup
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Setup: Create complete test environment
        test_collection = Path(temp_dir) / "integration-test"
        output_dir = Path(temp_dir) / "output"
        
        create_collection_structure(str(test_collection))
        output_dir.mkdir(exist_ok=True)
        
        # Create test composite image
        perfect_image_path = output_dir / "perfect_composite.png"
        perfect_image = Image.new('RGBA', (600, 600), (255, 255, 255, 255))
        # Add layered content to simulate real composite
        for layer in range(3):
            for x in range(layer * 200, (layer + 1) * 200):
                for y in range(layer * 200, (layer + 1) * 200):
                    if (x + y) % 20 == 0:  # Create pattern
                        perfect_image.putpixel((x, y), (255, 0, 0, 128 + layer * 40))
        perfect_image.save(perfect_image_path, 'PNG')
        
        # Execution: Validate using different approaches
        
        # 1. Individual validation
        result = validate_image(perfect_image_path)
        
        # 2. Batch validation
        batch_results = validate_multiple_images([perfect_image_path])
        
        # 3. Get detailed info
        image_info = get_image_info(perfect_image_path)
        
        # Validation: Verify all validation results
        assert result.is_valid is True
        assert batch_results[str(perfect_image_path)].is_valid is True
        assert image_info.image_size == (600, 600)
        assert image_info.image_mode == 'RGBA'
        assert image_info.total_pixels == 360000
        
        # Generate and verify report
        report = get_image_validation_report(result, str(perfect_image_path))
        assert len(report) > 0
        assert "✅" in report
        
        print("✅ Integration test passed: All image validation operations successful")
        print(f"   • Image validation: {result.is_valid}")
        print(f"   • Batch validation: {len(batch_results)} images processed")
        print(f"   • Image info: All metadata extracted correctly")
        
    finally:
        # Cleanup: Remove test directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir) 