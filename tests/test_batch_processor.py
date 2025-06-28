"""
Test suite for GenConfig Batch Image Processor

Tests the high-performance batch processing functionality including memory management,
progress tracking, parallel processing, and comprehensive error handling.
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path
from PIL import Image
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from image.batch_processor import (
    BatchImageProcessor,
    BatchProcessingConfig,
    BatchProgress,
    BatchResult,
    ProgressCallback,
    ProcessingMode,
    BatchOperation,
    BatchProcessingError,
    batch_resize_images,
    batch_convert_format,
    batch_standardize_traits
)


class TestBatchProcessingConfig(unittest.TestCase):
    """Test BatchProcessingConfig class"""
    
    def test_config_creation(self):
        """Test configuration creation with defaults"""
        config = BatchProcessingConfig(operation=BatchOperation.RESIZE)
        
        self.assertEqual(config.operation, BatchOperation.RESIZE)
        self.assertEqual(config.processing_mode, ProcessingMode.ADAPTIVE)
        self.assertEqual(config.chunk_size, 50)
        self.assertIsNone(config.max_workers)
        self.assertEqual(config.memory_limit_mb, 1024.0)
        self.assertTrue(config.enable_progress_tracking)
        self.assertTrue(config.enable_resumable)
        self.assertEqual(config.output_naming_pattern, "{stem}{ext}")
        self.assertFalse(config.overwrite_existing)
        self.assertEqual(config.operation_params, {})


class TestBatchProgress(unittest.TestCase):
    """Test BatchProgress class"""
    
    def test_progress_creation(self):
        """Test progress creation with defaults"""
        progress = BatchProgress()
        
        self.assertEqual(progress.total_items, 0)
        self.assertEqual(progress.completed_items, 0)
        self.assertEqual(progress.failed_items, 0)
        self.assertEqual(progress.skipped_items, 0)
        self.assertEqual(progress.current_chunk, 0)
        self.assertEqual(progress.total_chunks, 0)
        self.assertEqual(progress.start_time, 0.0)
        self.assertEqual(progress.processing_rate_per_second, 0.0)
    
    def test_completion_percentage(self):
        """Test completion percentage calculation"""
        progress = BatchProgress()
        
        # Test with no items
        self.assertEqual(progress.completion_percentage, 0.0)
        
        # Test with partial completion
        progress.total_items = 100
        progress.completed_items = 25
        self.assertEqual(progress.completion_percentage, 25.0)
        
        # Test with full completion
        progress.completed_items = 100
        self.assertEqual(progress.completion_percentage, 100.0)
    
    def test_success_rate(self):
        """Test success rate calculation"""
        progress = BatchProgress()
        
        # Test with no processed items
        self.assertEqual(progress.success_rate, 0.0)
        
        # Test with mixed results
        progress.completed_items = 80
        progress.failed_items = 20
        self.assertEqual(progress.success_rate, 80.0)
        
        # Test with all successful
        progress.failed_items = 0
        self.assertEqual(progress.success_rate, 100.0)


class TestBatchImageProcessor(unittest.TestCase):
    """Test BatchImageProcessor class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.input_dir = Path(self.test_dir) / "input"
        self.output_dir = Path(self.test_dir) / "output"
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
        # Create test images
        self.test_images = []
        for i in range(5):
            image_path = self.input_dir / f"test_image_{i}.png"
            # Create a simple 100x100 red image
            img = Image.new('RGB', (100, 100), color='red')
            img.save(image_path)
            self.test_images.append(str(image_path))
        
        self.processor = BatchImageProcessor(temp_dir=self.test_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_processor_initialization(self):
        """Test processor initialization"""
        self.assertIsNotNone(self.processor.image_utils)
        self.assertTrue(self.processor.temp_dir.exists())
        self.assertFalse(self.processor._stop_requested)
    
    def test_batch_resize_processing(self):
        """Test batch resize processing"""
        config = BatchProcessingConfig(
            operation=BatchOperation.RESIZE,
            processing_mode=ProcessingMode.SEQUENTIAL,
            chunk_size=3,
            operation_params={
                "target_size": (50, 50),
                "method": "LANCZOS"
            }
        )
        
        result = self.processor.process_batch(
            self.test_images, self.output_dir, config
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.progress.total_items, 5)
        self.assertEqual(result.progress.completed_items, 5)
        self.assertEqual(result.progress.failed_items, 0)
        self.assertEqual(len(result.output_paths), 5)
        
        # Verify output files exist and have correct dimensions
        for output_path in result.output_paths:
            self.assertTrue(Path(output_path).exists())
            with Image.open(output_path) as img:
                self.assertEqual(img.size, (50, 50))
    
    def test_batch_format_conversion(self):
        """Test batch format conversion"""
        config = BatchProcessingConfig(
            operation=BatchOperation.CONVERT_FORMAT,
            processing_mode=ProcessingMode.SEQUENTIAL,
            operation_params={
                "target_format": "JPEG",
                "quality": 90
            }
        )
        
        result = self.processor.process_batch(
            self.test_images, self.output_dir, config
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.progress.completed_items, 5)
        
        # Verify output files have JPEG format
        for output_path in result.output_paths:
            self.assertTrue(output_path.endswith('.jpeg'))
            with Image.open(output_path) as img:
                self.assertEqual(img.format, 'JPEG')
    
    def test_batch_trait_standardization(self):
        """Test batch trait standardization"""
        config = BatchProcessingConfig(
            operation=BatchOperation.STANDARDIZE_TRAIT,
            processing_mode=ProcessingMode.SEQUENTIAL
        )
        
        result = self.processor.process_batch(
            self.test_images, self.output_dir, config
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.progress.completed_items, 5)
        
        # Verify output files are 200x200 PNG
        for output_path in result.output_paths:
            self.assertTrue(output_path.endswith('.png'))
            with Image.open(output_path) as img:
                self.assertEqual(img.size, (200, 200))
                self.assertEqual(img.format, 'PNG')
    
    def test_parallel_processing(self):
        """Test parallel processing mode"""
        config = BatchProcessingConfig(
            operation=BatchOperation.RESIZE,
            processing_mode=ProcessingMode.PARALLEL,
            max_workers=2,
            operation_params={
                "target_size": (75, 75),
                "method": "LANCZOS"
            }
        )
        
        result = self.processor.process_batch(
            self.test_images, self.output_dir, config
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.progress.completed_items, 5)
        self.assertEqual(len(result.output_paths), 5)
    
    def test_progress_tracking(self):
        """Test progress tracking during processing"""
        progress_updates = []
        
        def track_progress(progress):
            progress_updates.append({
                'completed': progress.completed_items,
                'total': progress.total_items,
                'percentage': progress.completion_percentage
            })
        
        callback = ProgressCallback(track_progress)
        
        config = BatchProcessingConfig(
            operation=BatchOperation.RESIZE,
            processing_mode=ProcessingMode.SEQUENTIAL,
            chunk_size=2,
            operation_params={"target_size": (50, 50)}
        )
        
        result = self.processor.process_batch(
            self.test_images, self.output_dir, config, callback
        )
        
        self.assertTrue(result.success)
        self.assertTrue(len(progress_updates) > 0)
        
        # Check that progress was tracked
        final_update = progress_updates[-1]
        self.assertEqual(final_update['completed'], 5)
        self.assertEqual(final_update['total'], 5)
        self.assertEqual(final_update['percentage'], 100.0)
    
    def test_error_handling(self):
        """Test error handling for invalid inputs"""
        # Create config with non-existent input files
        invalid_paths = ["/non/existent/file1.png", "/non/existent/file2.png"]
        
        config = BatchProcessingConfig(
            operation=BatchOperation.RESIZE,
            operation_params={"target_size": (50, 50)}
        )
        
        result = self.processor.process_batch(
            invalid_paths, self.output_dir, config
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.progress.failed_items, 2)
        self.assertTrue(len(result.errors) > 0)
    
    def test_memory_monitoring(self):
        """Test memory usage monitoring"""
        config = BatchProcessingConfig(
            operation=BatchOperation.RESIZE,
            memory_limit_mb=1.0,  # Very low limit to trigger warnings
            operation_params={"target_size": (50, 50)}
        )
        
        result = self.processor.process_batch(
            self.test_images, self.output_dir, config
        )
        
        # Should complete but may have memory warnings
        self.assertTrue(result.success)
        self.assertGreaterEqual(result.progress.peak_memory_usage_mb, 0)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions for batch operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.input_dir = Path(self.test_dir) / "input"
        self.output_dir = Path(self.test_dir) / "output"
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
        # Create test images
        self.test_images = []
        for i in range(3):
            image_path = self.input_dir / f"test_{i}.png"
            img = Image.new('RGB', (100, 100), color='blue')
            img.save(image_path)
            self.test_images.append(str(image_path))
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_batch_resize_images_function(self):
        """Test batch_resize_images convenience function"""
        result = batch_resize_images(
            self.test_images,
            self.output_dir,
            target_size=(75, 75),
            method="bilinear",
            chunk_size=2
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.progress.completed_items, 3)
        
        # Verify output
        for output_path in result.output_paths:
            with Image.open(output_path) as img:
                self.assertEqual(img.size, (75, 75))
    
    def test_batch_convert_format_function(self):
        """Test batch_convert_format convenience function"""
        result = batch_convert_format(
            self.test_images,
            self.output_dir,
            target_format="JPEG",
            quality=85,
            chunk_size=2
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.progress.completed_items, 3)
        
        # Verify output format
        for output_path in result.output_paths:
            self.assertTrue(output_path.endswith('.jpeg'))
            with Image.open(output_path) as img:
                self.assertEqual(img.format, 'JPEG')
    
    def test_batch_standardize_traits_function(self):
        """Test batch_standardize_traits convenience function"""
        result = batch_standardize_traits(
            self.test_images,
            self.output_dir,
            chunk_size=2
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.progress.completed_items, 3)
        
        # Verify trait standardization
        for output_path in result.output_paths:
            self.assertTrue(output_path.endswith('.png'))
            with Image.open(output_path) as img:
                self.assertEqual(img.size, (200, 200))
                self.assertEqual(img.format, 'PNG')


if __name__ == '__main__':
    unittest.main()
