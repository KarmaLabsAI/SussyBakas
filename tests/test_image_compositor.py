"""
Test suite for GenConfig Image Compositor

Tests the combining of multiple trait images into single composite images.
Follows the testing strategy: Setup -> Execution -> Validation -> Cleanup
"""

import os
import tempfile
import shutil
import time
from pathlib import Path
import pytest
import sys
from PIL import Image

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from image.compositor import (
    ImageCompositor,
    CompositeImageResult,
    ImageCompositionError,
    create_composite,
    validate_composite_inputs
)
from infrastructure.directory_manager import create_collection_structure
from traits.directory_manager import create_trait_directories


class TestImageCompositor:
    """Test cases for the Image Compositor class"""
    
    def setup_method(self):
        """Setup: Create test fixtures and sample data"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_collection = Path(self.temp_dir) / "test-collection"
        self.output_dir = Path(self.temp_dir) / "output"
        
        # Create collection structure
        create_collection_structure(str(self.test_collection))
        create_trait_directories(self.test_collection)
        self.output_dir.mkdir(exist_ok=True)
        
        # Create sample trait files for testing
        self._create_sample_trait_files()
        
        # Initialize compositor
        self.compositor = ImageCompositor()
    
    def teardown_method(self):
        """Cleanup: Remove test files and reset state"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _create_sample_trait_files(self):
        """Create sample trait files for testing"""
        trait_data = [
            (1, "background", (255, 0, 0, 128)),   # Red background
            (5, "center", (255, 0, 255, 255)),     # Magenta center (opaque)
            (9, "overlay", (128, 0, 255, 128))     # Purple overlay
        ]
        
        self.trait_files = {}
        
        for position, category, color in trait_data:
            trait_dir = f"position-{position}-{category}"
            dir_path = self.test_collection / "traits" / trait_dir
            
            filename = f"trait-{category}-001.png"
            file_path = dir_path / filename
            
            # Create a 200x200 RGBA image
            image = Image.new('RGBA', (200, 200), color)
            image.save(file_path, 'PNG')
            self.trait_files[position] = str(file_path)
    
    def test_compositor_initialization_default(self):
        """Test: ImageCompositor initialization with default parameters"""
        # Execution
        compositor = ImageCompositor()
        
        # Validation
        assert compositor.final_size == (600, 600)
        assert compositor.cell_size == (200, 200)
        assert compositor.background_color == "#FFFFFF"
        assert compositor.output_format == "PNG"
    
    def test_create_composite_from_files_success(self):
        """Test: Successfully creating composite from trait files"""
        # Setup
        output_path = self.output_dir / "test_composite.png"
        
        # Execution
        result = self.compositor.create_composite_from_files(self.trait_files, str(output_path))
        
        # Validation
        assert result.success is True
        assert result.output_path == str(output_path.resolve())
        assert result.final_size == (600, 600)
        assert result.cell_size == (200, 200)
        assert result.composition_time > 0
        assert len(result.traits_used) == 3
        assert result.total_layers == 3
        assert len(result.errors) == 0
        assert result.file_size_bytes > 0
        
        # Verify output file exists and is valid
        assert output_path.exists()
        composite_image = Image.open(output_path)
        assert composite_image.size == (600, 600)
        assert composite_image.mode == 'RGBA'


def test_create_composite_convenience_function():
    """Test: create_composite convenience function"""
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Setup
        test_collection = Path(temp_dir) / "test-collection"
        output_dir = Path(temp_dir) / "output"
        
        create_collection_structure(str(test_collection))
        create_trait_directories(test_collection)
        output_dir.mkdir(exist_ok=True)
        
        # Create sample trait file
        trait_path = test_collection / "traits" / "position-1-background" / "trait-background-001.png"
        image = Image.new('RGBA', (200, 200), (255, 0, 0, 128))
        image.save(trait_path, 'PNG')
        
        output_path = output_dir / "convenience_test.png"
        trait_files = {1: str(trait_path)}
        
        # Execution
        success = create_composite(trait_files, str(output_path))
        
        # Validation
        assert success is True
        assert output_path.exists()
        
        # Verify image properties
        composite = Image.open(output_path)
        assert composite.size == (600, 600)
        assert composite.mode == 'RGBA'
        
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
