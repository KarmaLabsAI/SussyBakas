"""
Tests for Grid Template Generator - Component 4.3

This module contains comprehensive tests for the grid template generation functionality,
ensuring correct 600×600 template creation with 200×200 cells per task specification.
"""

import unittest
import tempfile
from pathlib import Path
from PIL import Image
import os

from src.grid.template_generator import (
    GridTemplateGenerator,
    GridTemplateDimensions,
    GridTemplateStyle,
    GridTemplateError,
    generate_grid_template,
    create_standard_template,
    get_template_info,
    validate_template_config
)


class TestGridTemplateDimensions(unittest.TestCase):
    """Test GridTemplateDimensions data structure"""
    
    def test_default_dimensions(self):
        """Test default dimensions are correct"""
        dimensions = GridTemplateDimensions()
        
        self.assertEqual(dimensions.image_width, 600)
        self.assertEqual(dimensions.image_height, 600)
        self.assertEqual(dimensions.cell_width, 200)
        self.assertEqual(dimensions.cell_height, 200)
    
    def test_custom_dimensions(self):
        """Test custom dimensions"""
        dimensions = GridTemplateDimensions(
            image_width=900,
            image_height=900,
            cell_width=300,
            cell_height=300
        )
        
        self.assertEqual(dimensions.image_width, 900)
        self.assertEqual(dimensions.image_height, 900)
        self.assertEqual(dimensions.cell_width, 300)
        self.assertEqual(dimensions.cell_height, 300)
    
    def test_dimension_validation_width_mismatch(self):
        """Test dimension validation fails for width mismatch"""
        with self.assertRaises(ValueError) as context:
            GridTemplateDimensions(
                image_width=700,  # Should be 600 (200*3)
                image_height=600,
                cell_width=200,
                cell_height=200
            )
        
        self.assertIn("Image width 700 must equal cell_width * 3", str(context.exception))
    
    def test_dimension_validation_height_mismatch(self):
        """Test dimension validation fails for height mismatch"""
        with self.assertRaises(ValueError) as context:
            GridTemplateDimensions(
                image_width=600,
                image_height=700,  # Should be 600 (200*3)
                cell_width=200,
                cell_height=200
            )
        
        self.assertIn("Image height 700 must equal cell_height * 3", str(context.exception))


class TestGridTemplateStyle(unittest.TestCase):
    """Test GridTemplateStyle data structure"""
    
    def test_default_style(self):
        """Test default style configuration"""
        style = GridTemplateStyle()
        
        self.assertEqual(style.background_color, (255, 255, 255, 255))
        self.assertEqual(style.grid_line_color, (200, 200, 200, 255))
        self.assertEqual(style.text_color, (100, 100, 100, 255))
        self.assertEqual(style.border_color, (150, 150, 150, 255))
        self.assertEqual(style.grid_line_width, 2)
        self.assertEqual(style.border_width, 3)
        self.assertEqual(style.font_size, 24)
        self.assertTrue(style.show_position_numbers)
        self.assertTrue(style.show_category_labels)
        self.assertFalse(style.show_coordinates)
    
    def test_custom_style(self):
        """Test custom style configuration"""
        style = GridTemplateStyle(
            background_color=(0, 0, 0, 255),
            grid_line_color=(255, 0, 0, 255),
            text_color=(255, 255, 255, 255),
            font_size=32,
            show_coordinates=True
        )
        
        self.assertEqual(style.background_color, (0, 0, 0, 255))
        self.assertEqual(style.grid_line_color, (255, 0, 0, 255))
        self.assertEqual(style.text_color, (255, 255, 255, 255))
        self.assertEqual(style.font_size, 32)
        self.assertTrue(style.show_coordinates)


class TestGridTemplateGenerator(unittest.TestCase):
    """Test main GridTemplateGenerator functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_output_path = Path(self.temp_dir) / "test-template.png"
        self.generator = GridTemplateGenerator()
    
    def tearDown(self):
        """Clean up test files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_generator_initialization_default(self):
        """Test generator initialization with defaults"""
        generator = GridTemplateGenerator()
        
        self.assertIsInstance(generator.dimensions, GridTemplateDimensions)
        self.assertIsInstance(generator.style, GridTemplateStyle)
        self.assertEqual(generator.dimensions.image_width, 600)
        self.assertEqual(generator.dimensions.image_height, 600)
    
    def test_generator_initialization_custom(self):
        """Test generator initialization with custom parameters"""
        dimensions = GridTemplateDimensions(900, 900, 300, 300)
        style = GridTemplateStyle(font_size=32)
        
        generator = GridTemplateGenerator(dimensions=dimensions, style=style)
        
        self.assertEqual(generator.dimensions.image_width, 900)
        self.assertEqual(generator.style.font_size, 32)
    
    def test_default_categories(self):
        """Test default category mapping"""
        expected_categories = {
            1: "Background",
            2: "Base", 
            3: "Accent",
            4: "Pattern",
            5: "Center",
            6: "Decoration",
            7: "Border",
            8: "Highlight",
            9: "Overlay"
        }
        
        self.assertEqual(GridTemplateGenerator.DEFAULT_CATEGORIES, expected_categories)
    
    def test_generate_template_default(self):
        """Test template generation with default settings"""
        success = self.generator.generate_template(self.test_output_path)
        
        self.assertTrue(success)
        self.assertTrue(self.test_output_path.exists())
        self.assertTrue(self.test_output_path.is_file())
        
        # Verify image properties
        with Image.open(self.test_output_path) as img:
            self.assertEqual(img.size, (600, 600))
            self.assertEqual(img.format, "PNG")
            self.assertEqual(img.mode, "RGBA")
    
    def test_generate_template_custom_categories(self):
        """Test template generation with custom categories"""
        custom_categories = {
            1: "Custom1", 2: "Custom2", 3: "Custom3",
            4: "Custom4", 5: "Custom5", 6: "Custom6",
            7: "Custom7", 8: "Custom8", 9: "Custom9"
        }
        
        success = self.generator.generate_template(
            self.test_output_path, 
            categories=custom_categories
        )
        
        self.assertTrue(success)
        self.assertTrue(self.test_output_path.exists())
    
    def test_generate_template_no_guides(self):
        """Test template generation without guides"""
        success = self.generator.generate_template(
            self.test_output_path,
            include_guides=False
        )
        
        self.assertTrue(success)
        self.assertTrue(self.test_output_path.exists())
    
    def test_generate_template_creates_directory(self):
        """Test that template generation creates output directory"""
        nested_path = Path(self.temp_dir) / "nested" / "directory" / "template.png"
        
        success = self.generator.generate_template(nested_path)
        
        self.assertTrue(success)
        self.assertTrue(nested_path.exists())
        self.assertTrue(nested_path.parent.exists())
    
    def test_create_template_data(self):
        """Test in-memory template creation"""
        template_image = self.generator.create_template_data()
        
        self.assertIsInstance(template_image, Image.Image)
        self.assertEqual(template_image.size, (600, 600))
        self.assertEqual(template_image.mode, "RGBA")
    
    def test_create_template_data_custom_categories(self):
        """Test in-memory template creation with custom categories"""
        custom_categories = {i: f"Test{i}" for i in range(1, 10)}
        
        template_image = self.generator.create_template_data(
            categories=custom_categories,
            include_guides=False
        )
        
        self.assertIsInstance(template_image, Image.Image)
        self.assertEqual(template_image.size, (600, 600))
    
    def test_generate_template_error_handling(self):
        """Test error handling in template generation"""
        # Test with invalid output path (permission denied simulation)
        invalid_path = "/root/invalid/path/template.png"
        
        with self.assertRaises(GridTemplateError):
            self.generator.generate_template(invalid_path)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_output_path = Path(self.temp_dir) / "convenience-template.png"
    
    def tearDown(self):
        """Clean up test files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_generate_grid_template_default(self):
        """Test convenience function with default parameters"""
        success = generate_grid_template(self.test_output_path)
        
        self.assertTrue(success)
        self.assertTrue(self.test_output_path.exists())
        
        # Verify standard dimensions
        with Image.open(self.test_output_path) as img:
            self.assertEqual(img.size, (600, 600))
    
    def test_generate_grid_template_custom_size(self):
        """Test convenience function with custom size"""
        success = generate_grid_template(
            self.test_output_path,
            image_size=(900, 900),
            cell_size=(300, 300)
        )
        
        self.assertTrue(success)
        self.assertTrue(self.test_output_path.exists())
        
        # Verify custom dimensions
        with Image.open(self.test_output_path) as img:
            self.assertEqual(img.size, (900, 900))
    
    def test_generate_grid_template_custom_categories(self):
        """Test convenience function with custom categories"""
        custom_categories = {i: f"Cat{i}" for i in range(1, 10)}
        
        success = generate_grid_template(
            self.test_output_path,
            categories=custom_categories
        )
        
        self.assertTrue(success)
        self.assertTrue(self.test_output_path.exists())
    
    def test_generate_grid_template_no_guides(self):
        """Test convenience function without guides"""
        success = generate_grid_template(
            self.test_output_path,
            include_guides=False
        )
        
        self.assertTrue(success)
        self.assertTrue(self.test_output_path.exists())
    
    def test_generate_grid_template_error_handling(self):
        """Test convenience function error handling"""
        # Test with invalid dimensions
        success = generate_grid_template(
            self.test_output_path,
            image_size=(500, 500),  # Not divisible by 3
            cell_size=(200, 200)
        )
        
        self.assertFalse(success)
    
    def test_create_standard_template(self):
        """Test standard template creation function"""
        success = create_standard_template(self.test_output_path)
        
        self.assertTrue(success)
        self.assertTrue(self.test_output_path.exists())
        
        # Verify it's the standard 600×600 template
        with Image.open(self.test_output_path) as img:
            self.assertEqual(img.size, (600, 600))
    
    def test_get_template_info_default(self):
        """Test template info with default dimensions"""
        info = get_template_info()
        
        expected_info = {
            "image_size": (600, 600),
            "cell_size": (200, 200),
            "grid_dimensions": (3, 3),
            "total_cells": 9,
            "categories": GridTemplateGenerator.DEFAULT_CATEGORIES.copy()
        }
        
        self.assertEqual(info, expected_info)
    
    def test_get_template_info_custom(self):
        """Test template info with custom dimensions"""
        custom_dimensions = GridTemplateDimensions(900, 900, 300, 300)
        info = get_template_info(custom_dimensions)
        
        self.assertEqual(info["image_size"], (900, 900))
        self.assertEqual(info["cell_size"], (300, 300))
        self.assertEqual(info["grid_dimensions"], (3, 3))
        self.assertEqual(info["total_cells"], 9)
    
    def test_validate_template_config_valid(self):
        """Test template config validation with valid parameters"""
        is_valid, errors = validate_template_config((600, 600), (200, 200))
        
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_template_config_invalid_dimensions(self):
        """Test template config validation with invalid dimensions"""
        is_valid, errors = validate_template_config((500, 600), (200, 200))
        
        self.assertFalse(is_valid)
        self.assertTrue(any("Image width 500 must equal cell_width * 3" in error for error in errors))
    
    def test_validate_template_config_negative_dimensions(self):
        """Test template config validation with negative dimensions"""
        is_valid, errors = validate_template_config((-100, 600), (200, 200))
        
        self.assertFalse(is_valid)
        self.assertTrue(any("Image dimensions must be positive" in error for error in errors))
    
    def test_validate_template_config_too_large(self):
        """Test template config validation with oversized dimensions"""
        is_valid, errors = validate_template_config((6000, 6000), (2000, 2000))
        
        self.assertFalse(is_valid)
        self.assertTrue(any("Image dimensions should not exceed 5000×5000" in error for error in errors))
    
    def test_validate_template_config_too_small(self):
        """Test template config validation with undersized cells"""
        is_valid, errors = validate_template_config((120, 120), (40, 40))
        
        self.assertFalse(is_valid)
        self.assertTrue(any("Cell dimensions should be at least 50×50" in error for error in errors))


class TestIntegrationWorkflow(unittest.TestCase):
    """Test complete workflow integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.templates_dir = Path(self.temp_dir) / "templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)
    
    def tearDown(self):
        """Clean up test files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_complete_template_generation_workflow(self):
        """Test complete template generation workflow per task specification"""
        print("🚀 Testing Component 4.3: Grid Template Generator workflow...")
        
        # Step 1: Generate standard template
        standard_template_path = self.templates_dir / "standard-template.png"
        print("📝 Generating standard 600×600 template...")
        
        success = create_standard_template(standard_template_path)
        self.assertTrue(success, "Failed to generate standard template")
        self.assertTrue(standard_template_path.exists(), "Standard template file not created")
        print("✅ Standard template generated successfully")
        
        # Step 2: Verify template dimensions per specification
        print("📏 Verifying template dimensions (600×600 with 200×200 cells)...")
        with Image.open(standard_template_path) as img:
            self.assertEqual(img.size, (600, 600), "Template image size incorrect")
            self.assertEqual(img.format, "PNG", "Template format should be PNG")
            self.assertEqual(img.mode, "RGBA", "Template should support transparency")
        print("✅ Template dimensions verified: 600×600 PNG with RGBA")
        
        # Step 3: Generate custom template with different styling
        custom_template_path = self.templates_dir / "custom-template.png"
        print("🎨 Generating custom template with styling options...")
        
        custom_dimensions = GridTemplateDimensions(900, 900, 300, 300)
        custom_style = GridTemplateStyle(
            background_color=(240, 240, 240, 255),
            grid_line_color=(150, 150, 150, 255),
            show_coordinates=True,
            font_size=28
        )
        
        generator = GridTemplateGenerator(custom_dimensions, custom_style)
        success = generator.generate_template(custom_template_path)
        self.assertTrue(success, "Failed to generate custom template")
        print("✅ Custom template generated successfully")
        
        # Step 4: Verify custom template properties
        print("🔍 Verifying custom template properties...")
        with Image.open(custom_template_path) as img:
            self.assertEqual(img.size, (900, 900), "Custom template size incorrect")
        print("✅ Custom template verified: 900×900")
        
        # Step 5: Test in-memory template creation
        print("💾 Testing in-memory template creation...")
        template_image = generator.create_template_data()
        self.assertIsInstance(template_image, Image.Image)
        self.assertEqual(template_image.size, (900, 900))
        print("✅ In-memory template creation successful")
        
        # Step 6: Test configuration validation
        print("⚙️ Testing template configuration validation...")
        
        # Valid config
        is_valid, errors = validate_template_config((600, 600), (200, 200))
        self.assertTrue(is_valid, f"Valid config marked as invalid: {errors}")
        
        # Invalid config
        is_valid, errors = validate_template_config((500, 600), (200, 200))
        self.assertFalse(is_valid, "Invalid config marked as valid")
        self.assertTrue(len(errors) > 0, "No validation errors reported")
        print("✅ Configuration validation working correctly")
        
        # Step 7: Test template info generation
        print("📊 Testing template information generation...")
        info = get_template_info()
        self.assertEqual(info["image_size"], (600, 600))
        self.assertEqual(info["cell_size"], (200, 200))
        self.assertEqual(info["total_cells"], 9)
        self.assertEqual(len(info["categories"]), 9)
        print("✅ Template info generation verified")
        
        # Step 8: Verify file sizes are reasonable
        print("📁 Verifying template file sizes...")
        standard_size = standard_template_path.stat().st_size
        custom_size = custom_template_path.stat().st_size
        
        self.assertGreater(standard_size, 1000, "Standard template file too small")
        self.assertGreater(custom_size, 1000, "Custom template file too small")
        self.assertLess(standard_size, 500000, "Standard template file too large")  # 500KB limit
        self.assertLess(custom_size, 1000000, "Custom template file too large")     # 1MB limit
        
        print(f"✅ File sizes verified - Standard: {standard_size} bytes, Custom: {custom_size} bytes")
        
        print("\n🎉 All Component 4.3 tests passed! Grid Template Generator working correctly.")
        return True


class TestErrorHandling(unittest.TestCase):
    """Test error handling scenarios"""
    
    def test_grid_template_error_exception(self):
        """Test GridTemplateError exception"""
        error = GridTemplateError("Test error message")
        self.assertIsInstance(error, Exception)
        self.assertEqual(str(error), "Test error message")
    
    def test_invalid_dimensions_error(self):
        """Test error handling for invalid dimensions"""
        with self.assertRaises(ValueError):
            GridTemplateDimensions(500, 600, 200, 200)  # Width mismatch
    
    def test_generator_with_invalid_dimensions(self):
        """Test generator initialization with invalid dimensions"""
        with self.assertRaises(ValueError):
            invalid_dimensions = GridTemplateDimensions(400, 600, 200, 200)
            GridTemplateGenerator(dimensions=invalid_dimensions)


if __name__ == "__main__":
    # Run all tests
    unittest.main(verbosity=2) 