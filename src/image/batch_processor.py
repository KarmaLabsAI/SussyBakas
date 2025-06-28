"""
GenConfig Batch Image Processor

High-performance batch processing module for GenConfig system.
Handles large batches efficiently with memory management and progress tracking.
"""

import os
import sys
import gc
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import hashlib
import tempfile
from PIL import Image
import psutil

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.file_utils import validate_file_exists, ensure_directory_exists, get_file_size
from image.image_utils import ImageUtilities, ImageProcessingResult, ResizeMethod, ImageFormat, TransparencyMode


class BatchProcessingError(Exception):
    """Custom exception for batch processing errors"""
    pass


class ProcessingMode(Enum):
    """Batch processing execution modes"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    ADAPTIVE = "adaptive"


class BatchOperation(Enum):
    """Supported batch operations"""
    RESIZE = "resize"
    CONVERT_FORMAT = "convert_format"
    HANDLE_TRANSPARENCY = "handle_transparency"
    STANDARDIZE_TRAIT = "standardize_trait"
    OPTIMIZE = "optimize"
    CREATE_THUMBNAILS = "create_thumbnails"


@dataclass
class BatchProcessingConfig:
    """Configuration for batch processing operations"""
    operation: BatchOperation
    processing_mode: ProcessingMode = ProcessingMode.ADAPTIVE
    chunk_size: int = 50
    max_workers: Optional[int] = None
    memory_limit_mb: float = 1024.0
    enable_progress_tracking: bool = True
    enable_resumable: bool = True
    output_naming_pattern: str = "{stem}{ext}"
    overwrite_existing: bool = False
    operation_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchProgress:
    """Batch processing progress information"""
    total_items: int = 0
    completed_items: int = 0
    failed_items: int = 0
    skipped_items: int = 0
    current_chunk: int = 0
    total_chunks: int = 0
    start_time: float = 0.0
    processing_rate_per_second: float = 0.0
    current_memory_usage_mb: float = 0.0
    peak_memory_usage_mb: float = 0.0
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_items == 0:
            return 0.0
        return (self.completed_items / self.total_items) * 100.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        processed = self.completed_items + self.failed_items
        if processed == 0:
            return 0.0
        return (self.completed_items / processed) * 100.0


@dataclass
class BatchResult:
    """Result of batch processing operation"""
    success: bool
    config: BatchProcessingConfig
    progress: BatchProgress
    results: Dict[str, ImageProcessingResult] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    total_processing_time: float = 0.0
    total_file_size_processed: int = 0
    output_paths: List[str] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        return {
            "total_items": self.progress.total_items,
            "completed": self.progress.completed_items,
            "failed": self.progress.failed_items,
            "success_rate": f"{self.progress.success_rate:.1f}%",
            "completion": f"{self.progress.completion_percentage:.1f}%",
            "processing_time": f"{self.total_processing_time:.2f}s",
            "processing_rate": f"{self.progress.processing_rate_per_second:.2f} items/sec",
            "peak_memory": f"{self.progress.peak_memory_usage_mb:.2f} MB"
        }


class ProgressCallback:
    """Callback interface for progress monitoring"""
    
    def __init__(self, callback_func: Optional[Callable[[BatchProgress], None]] = None):
        self.callback_func = callback_func
        
    def update(self, progress: BatchProgress) -> None:
        """Update progress"""
        if self.callback_func:
            self.callback_func(progress)
    
    def log_progress(self, progress: BatchProgress) -> None:
        """Default progress logging"""
        print(f"Progress: {progress.completion_percentage:.1f}% "
              f"({progress.completed_items}/{progress.total_items}) "
              f"- {progress.processing_rate_per_second:.1f} items/sec")


class BatchImageProcessor:
    """
    High-performance batch image processor for GenConfig operations
    
    Features:
    - Memory-efficient processing with chunking
    - Parallel processing support
    - Progress tracking and monitoring
    - Adaptive processing mode selection
    """
    
    def __init__(self, temp_dir: Optional[str] = None):
        """Initialize batch processor"""
        self.image_utils = ImageUtilities()
        self.temp_dir = Path(temp_dir or tempfile.gettempdir()) / "genconfig_batch"
        ensure_directory_exists(str(self.temp_dir))
        
        # Processing state
        self._stop_requested = False
        
        # Memory monitoring
        try:
            self.process = psutil.Process()
        except Exception:
            self.process = None
    
    def process_batch(self,
                     input_paths: List[Union[str, Path]],
                     output_dir: Union[str, Path],
                     config: BatchProcessingConfig,
                     progress_callback: Optional[ProgressCallback] = None) -> BatchResult:
        """
        Process a batch of images with specified configuration
        
        Args:
            input_paths: List of input image file paths
            output_dir: Output directory for processed images
            config: Batch processing configuration
            progress_callback: Optional progress callback for monitoring
            
        Returns:
            BatchResult: Comprehensive batch processing results
        """
        # Initialize result object
        result = BatchResult(
            success=False,
            config=config,
            progress=BatchProgress()
        )
        
        try:
            # Setup progress tracking
            result.progress.start_time = time.time()
            result.progress.total_items = len(input_paths)
            
            # Create output directory
            output_dir_path = Path(output_dir)
            ensure_directory_exists(str(output_dir_path))
            
            # Determine optimal processing mode
            actual_mode = self._determine_processing_mode(config, input_paths)
            
            # Calculate chunks
            chunks = self._create_chunks(input_paths, config.chunk_size)
            result.progress.total_chunks = len(chunks)
            
            # Initialize progress callback
            if progress_callback is None:
                progress_callback = ProgressCallback()
            
            # Process chunks
            for chunk_idx, chunk in enumerate(chunks):
                if self._stop_requested:
                    break
                
                result.progress.current_chunk = chunk_idx + 1
                
                # Process current chunk
                chunk_results = self._process_chunk(
                    chunk, output_dir_path, config, actual_mode
                )
                
                # Update results
                for path, chunk_result in chunk_results.items():
                    result.results[path] = chunk_result
                    if chunk_result.success:
                        result.progress.completed_items += 1
                        if chunk_result.output_path:
                            result.output_paths.append(chunk_result.output_path)
                    else:
                        result.progress.failed_items += 1
                        result.errors.extend(chunk_result.errors)
                
                # Update progress metrics
                self._update_progress_metrics(result.progress)
                
                # Check memory usage
                current_memory = self._get_memory_usage_mb()
                result.progress.current_memory_usage_mb = current_memory
                result.progress.peak_memory_usage_mb = max(
                    result.progress.peak_memory_usage_mb, current_memory
                )
                
                # Memory management
                if current_memory > config.memory_limit_mb:
                    gc.collect()
                    current_memory = self._get_memory_usage_mb()
                    if current_memory > config.memory_limit_mb:
                        result.warnings.append(
                            f"Memory usage ({current_memory:.1f} MB) exceeds limit"
                        )
                
                # Update progress
                if config.enable_progress_tracking:
                    progress_callback.update(result.progress)
            
            # Calculate final statistics
            result.total_processing_time = time.time() - result.progress.start_time
            result.total_file_size_processed = sum(
                res.file_size_bytes for res in result.results.values() if res.success
            )
            
            # Generate statistics
            result.statistics = self._generate_statistics(result)
            
            # Determine overall success
            result.success = result.progress.failed_items == 0 and not self._stop_requested
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Batch processing failed: {str(e)}")
        
        finally:
            self._stop_requested = False
        
        return result
    
    def stop_processing(self) -> None:
        """Request to stop current batch processing"""
        self._stop_requested = True
    
    def estimate_processing_time(self,
                               input_paths: List[Union[str, Path]],
                               config: BatchProcessingConfig,
                               sample_size: int = 10) -> Dict[str, float]:
        """Estimate processing time for a batch"""
        if not input_paths:
            return {"total": 0.0, "per_item": 0.0}
        
        # Take sample of images
        sample_paths = input_paths[:min(sample_size, len(input_paths))]
        
        # Create temporary output directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Time sample processing
            start_time = time.time()
            sample_results = self._process_chunk(
                sample_paths, Path(temp_dir), config, ProcessingMode.SEQUENTIAL
            )
            sample_time = time.time() - start_time
        
        # Calculate timing estimates
        successful_samples = sum(1 for r in sample_results.values() if r.success)
        if successful_samples == 0:
            return {"total": 0.0, "per_item": 0.0}
        
        per_item_time = sample_time / successful_samples
        total_estimated_time = per_item_time * len(input_paths)
        
        return {
            "total": total_estimated_time,
            "per_item": per_item_time
        }
    
    def _determine_processing_mode(self, config: BatchProcessingConfig,
                                 input_paths: List[Union[str, Path]]) -> ProcessingMode:
        """Determine optimal processing mode"""
        if config.processing_mode != ProcessingMode.ADAPTIVE:
            return config.processing_mode
        
        # Adaptive mode logic
        num_items = len(input_paths)
        cpu_count = os.cpu_count() or 1
        
        # For small batches, use sequential
        if num_items < 10:
            return ProcessingMode.SEQUENTIAL
        
        # For larger batches with multi-core systems, use parallel
        if num_items >= 10 and cpu_count >= 2:
            return ProcessingMode.PARALLEL
        
        # Default to sequential
        return ProcessingMode.SEQUENTIAL
    
    def _create_chunks(self, input_paths: List[Union[str, Path]], 
                      chunk_size: int) -> List[List[Union[str, Path]]]:
        """Create chunks from input paths"""
        chunks = []
        for i in range(0, len(input_paths), chunk_size):
            chunks.append(input_paths[i:i + chunk_size])
        return chunks
    
    def _process_chunk(self, chunk: List[Union[str, Path]], output_dir: Path,
                      config: BatchProcessingConfig, mode: ProcessingMode) -> Dict[str, ImageProcessingResult]:
        """Process a single chunk of images"""
        if mode == ProcessingMode.PARALLEL:
            return self._process_chunk_parallel(chunk, output_dir, config)
        else:
            return self._process_chunk_sequential(chunk, output_dir, config)
    
    def _process_chunk_sequential(self, chunk: List[Union[str, Path]], output_dir: Path,
                                config: BatchProcessingConfig) -> Dict[str, ImageProcessingResult]:
        """Process chunk sequentially"""
        results = {}
        for input_path in chunk:
            if self._stop_requested:
                break
            results[str(input_path)] = self._process_single_image(input_path, output_dir, config)
        return results
    
    def _process_chunk_parallel(self, chunk: List[Union[str, Path]], output_dir: Path,
                              config: BatchProcessingConfig) -> Dict[str, ImageProcessingResult]:
        """Process chunk using thread-based parallelism"""
        results = {}
        max_workers = config.max_workers or min(len(chunk), os.cpu_count() or 1)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(self._process_single_image, path, output_dir, config): str(path)
                for path in chunk
            }
            
            for future in as_completed(future_to_path):
                if self._stop_requested:
                    break
                path = future_to_path[future]
                try:
                    results[path] = future.result()
                except Exception as e:
                    error_result = ImageProcessingResult(success=False, input_path=path)
                    error_result.errors.append(f"Processing failed: {str(e)}")
                    results[path] = error_result
        
        return results
    
    def _process_single_image(self, input_path: Union[str, Path], output_dir: Path,
                            config: BatchProcessingConfig) -> ImageProcessingResult:
        """Process a single image"""
        input_path_obj = Path(input_path)
        
        # Generate output path
        output_path = self._generate_output_path(input_path_obj, output_dir, config)
        
        # Skip if output exists and overwrite is disabled
        if output_path.exists() and not config.overwrite_existing:
            result = ImageProcessingResult(
                success=True,
                input_path=str(input_path),
                output_path=str(output_path)
            )
            result.warnings.append("Output file already exists, skipping")
            return result
        
        # Perform the specified operation
        try:
            if config.operation == BatchOperation.RESIZE:
                return self._perform_resize(input_path, output_path, config.operation_params)
            elif config.operation == BatchOperation.CONVERT_FORMAT:
                return self._perform_format_conversion(input_path, output_path, config.operation_params)
            elif config.operation == BatchOperation.HANDLE_TRANSPARENCY:
                return self._perform_transparency_handling(input_path, output_path, config.operation_params)
            elif config.operation == BatchOperation.STANDARDIZE_TRAIT:
                return self._perform_trait_standardization(input_path, output_path, config.operation_params)
            elif config.operation == BatchOperation.OPTIMIZE:
                return self._perform_optimization(input_path, output_path, config.operation_params)
            elif config.operation == BatchOperation.CREATE_THUMBNAILS:
                return self._perform_thumbnail_creation(input_path, output_path, config.operation_params)
            else:
                raise BatchProcessingError(f"Unsupported operation: {config.operation}")
                
        except Exception as e:
            result = ImageProcessingResult(success=False, input_path=str(input_path))
            result.errors.append(f"Operation failed: {str(e)}")
            return result
    
    def _generate_output_path(self, input_path: Path, output_dir: Path,
                            config: BatchProcessingConfig) -> Path:
        """Generate output file path"""
        stem = input_path.stem
        ext = input_path.suffix
        
        # Handle format conversion
        if config.operation == BatchOperation.CONVERT_FORMAT:
            target_format = config.operation_params.get("target_format", "PNG")
            ext = f".{target_format.lower()}"
        
        filename = config.output_naming_pattern.format(stem=stem, ext=ext)
        return output_dir / filename
    
    def _perform_resize(self, input_path: Union[str, Path], output_path: Path,
                       params: Dict[str, Any]) -> ImageProcessingResult:
        """Perform image resize operation"""
        target_size = params.get("target_size", (200, 200))
        method = ResizeMethod[params.get("method", "LANCZOS").upper()]
        
        return self.image_utils.resize_image(
            input_path, output_path, target_size, method
        )
    
    def _perform_format_conversion(self, input_path: Union[str, Path], output_path: Path,
                                 params: Dict[str, Any]) -> ImageProcessingResult:
        """Perform image format conversion"""
        target_format = ImageFormat[params.get("target_format", "PNG").upper()]
        quality = params.get("quality")
        
        return self.image_utils.convert_format(
            input_path, output_path, target_format, quality
        )
    
    def _perform_transparency_handling(self, input_path: Union[str, Path], output_path: Path,
                                     params: Dict[str, Any]) -> ImageProcessingResult:
        """Perform transparency handling operation"""
        mode = TransparencyMode[params.get("mode", "PRESERVE").upper()]
        
        return self.image_utils.handle_transparency(
            input_path, output_path, mode
        )
    
    def _perform_trait_standardization(self, input_path: Union[str, Path], output_path: Path,
                                     params: Dict[str, Any]) -> ImageProcessingResult:
        """Perform trait standardization (resize to 200x200 PNG)"""
        # First resize to trait size
        resize_result = self.image_utils.resize_image(
            input_path, output_path, (200, 200), ResizeMethod.LANCZOS
        )
        
        if not resize_result.success:
            return resize_result
        
        # Then ensure PNG format
        if not str(output_path).lower().endswith('.png'):
            png_path = output_path.with_suffix('.png')
            format_result = self.image_utils.convert_format(
                output_path, png_path, ImageFormat.PNG
            )
            if format_result.success:
                output_path.unlink()
                format_result.output_path = str(png_path)
            return format_result
        
        return resize_result
    
    def _perform_optimization(self, input_path: Union[str, Path], output_path: Path,
                            params: Dict[str, Any]) -> ImageProcessingResult:
        """Perform image optimization"""
        max_file_size = params.get("max_file_size")
        target_format = params.get("target_format")
        
        target_format_enum = None
        if target_format:
            target_format_enum = ImageFormat[target_format.upper()]
        
        return self.image_utils.optimize_image(
            input_path, output_path, max_file_size, target_format_enum
        )
    
    def _perform_thumbnail_creation(self, input_path: Union[str, Path], output_path: Path,
                                  params: Dict[str, Any]) -> ImageProcessingResult:
        """Perform thumbnail creation"""
        thumbnail_size = params.get("thumbnail_size", (150, 150))
        
        return self.image_utils.create_thumbnail(
            input_path, output_path, thumbnail_size
        )
    
    def _update_progress_metrics(self, progress: BatchProgress) -> None:
        """Update progress timing and rate metrics"""
        elapsed = time.time() - progress.start_time if progress.start_time > 0 else 0
        if elapsed > 0:
            progress.processing_rate_per_second = progress.completed_items / elapsed
    
    def _get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB"""
        try:
            if self.process:
                return self.process.memory_info().rss / (1024 * 1024)
        except Exception:
            pass
        return 0.0
    
    def _generate_statistics(self, result: BatchResult) -> Dict[str, Any]:
        """Generate comprehensive statistics"""
        successful_results = [r for r in result.results.values() if r.success]
        
        return {
            "processing_summary": {
                "total_items": result.progress.total_items,
                "successful": len(successful_results),
                "failed": result.progress.failed_items,
                "success_rate": result.progress.success_rate
            },
            "timing": {
                "total_time": result.total_processing_time,
                "processing_rate": result.progress.processing_rate_per_second
            },
            "memory": {
                "peak_usage_mb": result.progress.peak_memory_usage_mb
            },
            "operations": {
                "operation_type": result.config.operation.value,
                "processing_mode": result.config.processing_mode.value,
                "chunk_size": result.config.chunk_size
            }
        }


# Convenience functions for common batch operations

def batch_resize_images(input_paths: List[Union[str, Path]],
                       output_dir: Union[str, Path],
                       target_size: Tuple[int, int] = (200, 200),
                       method: str = "lanczos",
                       chunk_size: int = 50,
                       progress_callback: Optional[Callable] = None) -> BatchResult:
    """Batch resize images to target size"""
    config = BatchProcessingConfig(
        operation=BatchOperation.RESIZE,
        chunk_size=chunk_size,
        operation_params={
            "target_size": target_size,
            "method": method.upper()
        }
    )
    
    processor = BatchImageProcessor()
    callback = ProgressCallback(progress_callback) if progress_callback else None
    
    return processor.process_batch(input_paths, output_dir, config, callback)


def batch_convert_format(input_paths: List[Union[str, Path]],
                        output_dir: Union[str, Path],
                        target_format: str = "PNG",
                        quality: Optional[int] = None,
                        chunk_size: int = 50,
                        progress_callback: Optional[Callable] = None) -> BatchResult:
    """Batch convert images to target format"""
    config = BatchProcessingConfig(
        operation=BatchOperation.CONVERT_FORMAT,
        chunk_size=chunk_size,
        operation_params={
            "target_format": target_format.upper(),
            "quality": quality
        }
    )
    
    processor = BatchImageProcessor()
    callback = ProgressCallback(progress_callback) if progress_callback else None
    
    return processor.process_batch(input_paths, output_dir, config, callback)


def batch_standardize_traits(input_paths: List[Union[str, Path]],
                            output_dir: Union[str, Path],
                            chunk_size: int = 50,
                            progress_callback: Optional[Callable] = None) -> BatchResult:
    """Batch standardize trait images to GenConfig specifications"""
    config = BatchProcessingConfig(
        operation=BatchOperation.STANDARDIZE_TRAIT,
        chunk_size=chunk_size
    )
    
    processor = BatchImageProcessor()
    callback = ProgressCallback(progress_callback) if progress_callback else None
    
    return processor.process_batch(input_paths, output_dir, config, callback)
