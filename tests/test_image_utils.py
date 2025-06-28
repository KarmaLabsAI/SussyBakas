"""
Test suite for GenConfig Image Utilities (Component 6.3)

Tests for image processing operations including resize, format conversion,
transparency handling, and other image manipulation utilities.
"""

import unittest
import tempfile
import shutil
import os
from pathlib import Path
from PIL import Image, ImageDraw

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from image.image_utils import (
    resize_image,
    convert_image_format,
    handle_image_transparency,
    get_image_info,
    standardize_trait_image,
    batch_process_images
)


class TestImageUtils(unittest.TestCase):
    """Test cases for image utilities module"""
    
    def setUp(self):
        """Set up test fixtures and temporary directory"""
        # Setup
        self.test_dir = Path(tempfile.mkdtemp())
        self.output_dir = self.test_dir / "output"
        self.output_dir.mkdir(exist_ok=True)
        
        # Create test images
        self._create_test_images()
    
    def tearDown(self):
        """Clean up test files and temporary directory"""
        # Cleanup
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def _create_test_images(self):
        """Create various test images for processing"""
        # Standard RGBA image (200x200)
        self.rgba_image_path = self.test_dir / "test_rgba.png"
        rgba_img = Image.new('RGBA', (200, 200), (255, 0, 0, 255))
        # Add some transparency
        draw = ImageDraw.Draw(rgba_img)
        draw.rectangle([50, 50, 150, 150], fill=(0, 255, 0, 128))
        rgba_img.save(self.rgba_image_path, 'PNG')
        
        # RGB image (300x300) - larger size for resize testing
        self.rgb_image_path = self.test_dir / "test_rgb.png"
        rgb_img = Image.new('RGB', (300, 300), (0, 0, 255))
        rgb_img.save(self.rgb_image_path, 'PNG')
        
        # Small image (100x100) for upscaling tests
        self.small_image_path = self.test_dir / "test_small.png"
        small_img = Image.new('RGBA', (100, 100), (255, 255, 0, 255))
        small_img.save(self.small_image_path, 'PNG')
        
        # JPEG image for format conversion testing
        self.jpeg_image_path = self.test_dir / "test_image.jpg"
        jpeg_img = Image.new('RGB', (400, 400), (255, 128, 0))
        jpeg_img.save(self.jpeg_image_path, 'JPEG')
    
    def test_resize_image_basic(self):
        """Test: Basic image resizing functionality"""
        # Setup
        output_path = self.output_dir / "resized_basic.png"
        target_size = (150, 150)
        
        # Execution
        result = resize_image(self.rgba_image_path, output_path, target_size)
        
        # Validation
        assert result is True
        assert output_path.exists()
        
        with Image.open(output_path) as resized_img:
            assert resized_img.size == target_size
    
    def test_resize_image_methods(self):
        """Test: Different resize methods"""
        methods = ["nearest", "bilinear", "bicubic", "lanczos"]
        target_size = (100, 100)
        
        for method in methods:
            with self.subTest(method=method):
                # Setup
                output_path = self.output_dir / f"resized_{method}.png"
                
                # Execution
                result = resize_image(self.rgb_image_path, output_path, target_size, method)
                
                # Validation
                assert result is True
                assert output_path.exists()
                
                with Image.open(output_path) as resized_img:
                    assert resized_img.size == target_size
    
    def test_resize_image_nonexistent_file(self):
        """Test: Resize with non-existent input file"""
        # Setup
        nonexistent_path = self.test_dir / "nonexistent.png"
        output_path = self.output_dir / "should_not_exist.png"
        
        # Execution
        result = resize_image(nonexistent_path, output_path, (100, 100))
        
        # Validation
        assert result is False
        assert not output_path.exists()
    
    def test_convert_image_format_png_to_jpeg(self):
        """Test: Convert PNG to JPEG format"""
        # Setup
        output_path = self.output_dir / "converted_to_jpeg.jpg"
        
        # Execution
        result = convert_image_format(self.rgb_image_path, output_path, "JPEG")
        
        # Validation
        assert result is True
        assert output_path.exists()
        
        with Image.open(output_path) as converted_img:
            assert converted_img.format == "JPEG"
    
    def test_convert_image_format_rgba_to_jpeg(self):
        """Test: Convert RGBA image to JPEG (transparency should be handled)"""
        # Setup
        output_path = self.output_dir / "rgba_to_jpeg.jpg"
        
        # Execution
        result = convert_image_format(self.rgba_image_path, output_path, "JPEG")
        
        # Validation
        assert result is True
        assert output_path.exists()
        
        with Image.open(output_path) as converted_img:
            assert converted_img.format == "JPEG"
            assert converted_img.mode == "RGB"  # Transparency should be removed
    
    def test_convert_image_format_nonexistent_file(self):
        """Test: Convert non-existent file"""
        # Setup
        nonexistent_path = self.test_dir / "nonexistent.png"
        output_path = self.output_dir / "should_not_exist.jpg"
        
        # Execution
        result = convert_image_format(nonexistent_path, output_path, "JPEG")
        
        # Validation
        assert result is False
        assert not output_path.exists()
    
    def test_handle_transparency_preserve(self):
        """Test: Preserve existing transparency"""
        # Setup
        output_path = self.output_dir / "transparency_preserved.png"
        
        # Execution
        result = handle_image_transparency(self.rgba_image_path, output_path, "preserve")
        
        # Validation
        assert result is True
        assert output_path.exists()
        
        with Image.open(output_path) as processed_img:
            assert processed_img.mode == "RGBA"
    
    def test_handle_transparency_remove(self):
        """Test: Remove transparency from image"""
        # Setup
        output_path = self.output_dir / "transparency_removed.png"
        
        # Execution
        result = handle_image_transparency(self.rgba_image_path, output_path, "remove")
        
        # Validation
        assert result is True
        assert output_path.exists()
        
        with Image.open(output_path) as processed_img:
            assert processed_img.mode == "RGB"
    
    def test_handle_transparency_add(self):
        """Test: Add transparency to RGB image"""
        # Setup
        output_path = self.output_dir / "transparency_added.png"
        
        # Execution
        result = handle_image_transparency(self.rgb_image_path, output_path, "add")
        
        # Validation
        assert result is True
        assert output_path.exists()
        
        with Image.open(output_path) as processed_img:
            assert processed_img.mode == "RGBA"
    
    def test_get_image_info_valid_image(self):
        """Test: Get information about valid image"""
        # Execution
        info = get_image_info(self.rgba_image_path)
        
        # Validation
        assert "error" not in info
        assert info["size"] == (200, 200)
        assert info["format"] == "PNG"
        assert info["mode"] == "RGBA"
        assert info["has_transparency"] is True
        assert info["file_size"] > 0
    
    def test_get_image_info_nonexistent_file(self):
        """Test: Get info for non-existent file"""
        # Setup
        nonexistent_path = self.test_dir / "nonexistent.png"
        
        # Execution
        info = get_image_info(nonexistent_path)
        
        # Validation
        assert "error" in info
        assert info["error"] == "File not found"
    
    def test_standardize_trait_image_success(self):
        """Test: Successfully standardize trait image"""
        # Setup
        output_path = self.output_dir / "standardized_trait.png"
        
        # Execution
        result = standardize_trait_image(self.rgb_image_path, output_path)
        
        # Validation
        assert result is True
        assert output_path.exists()
        
        with Image.open(output_path) as standardized_img:
            assert standardized_img.size == (200, 200)  # GenConfig trait size
    
    def test_standardize_trait_image_nonexistent_file(self):
        """Test: Standardize non-existent file"""
        # Setup
        nonexistent_path = self.test_dir / "nonexistent.png"
        output_path = self.output_dir / "should_not_exist.png"
        
        # Execution
        result = standardize_trait_image(nonexistent_path, output_path)
        
        # Validation
        assert result is False
        assert not output_path.exists()
    
    def test_batch_process_images_resize(self):
        """Test: Batch resize multiple images"""
        # Setup
        input_paths = [self.rgba_image_path, self.rgb_image_path]
        batch_output_dir = self.output_dir / "batch_resize"
        
        # Execution
        results = batch_process_images(
            input_paths, batch_output_dir, "resize", 
            target_size=(150, 150), method="lanczos"
        )
        
        # Validation
        assert len(results) == 2
        for input_path in input_paths:
            assert results[str(input_path)] is True
        
        # Check output files exist and have correct size
        for input_path in input_paths:
            output_file = batch_output_dir / Path(input_path).name
            assert output_file.exists()
            
            with Image.open(output_file) as img:
                assert img.size == (150, 150)
    
    def test_batch_process_images_convert(self):
        """Test: Batch convert multiple images"""
        # Setup
        input_paths = [self.rgba_image_path, self.rgb_image_path]
        batch_output_dir = self.output_dir / "batch_convert"
        
        # Execution
        results = batch_process_images(
            input_paths, batch_output_dir, "convert", 
            target_format="JPEG"
        )
        
        # Validation
        assert len(results) == 2
        for input_path in input_paths:
            assert results[str(input_path)] is True
    
    def test_batch_process_images_invalid_operation(self):
        """Test: Batch process with invalid operation"""
        # Setup
        input_paths = [self.rgba_image_path]
        batch_output_dir = self.output_dir / "batch_invalid"
        
        # Execution
        results = batch_process_images(
            input_paths, batch_output_dir, "invalid_operation"
        )
        
        # Validation
        assert len(results) == 1
        assert results[str(self.rgba_image_path)] is False


if __name__ == "__main__":
    unittest.main() 