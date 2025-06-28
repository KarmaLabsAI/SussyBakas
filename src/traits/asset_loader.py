"""
GenConfig Trait Asset Loader

This module provides efficient loading and caching of trait images for the GenConfig system.
It handles image loading, memory management, and provides fast access to trait assets
while gracefully handling missing or corrupted files.
"""

import os
import sys
import time
import weakref
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import OrderedDict
from PIL import Image
import threading

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.logic_validator import ValidationResult, ValidationIssue, ValidationSeverity
from utils.file_utils import validate_file_exists, get_file_size, FileOperationError
from .trait_validator import validate_trait_file
from .directory_manager import TraitDirectoryManager, TraitFileEntry


class TraitAssetError(Exception):
    """Custom exception for trait asset loading errors"""
    pass


class CacheStrategy(Enum):
    """Cache eviction strategies"""
    LRU = "lru"  # Least Recently Used
    SIZE_BASED = "size_based"  # Based on memory size
    FIFO = "fifo"  # First In, First Out


@dataclass
class CacheStats:
    """Statistics about cache performance"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    evictions: int = 0
    current_size: int = 0
    max_size: int = 0
    memory_usage_bytes: int = 0
    max_memory_bytes: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as percentage"""
        if self.total_requests == 0:
            return 0.0
        return (self.cache_hits / self.total_requests) * 100.0
    
    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate as percentage"""
        return 100.0 - self.hit_rate


@dataclass
class LoadedTraitAsset:
    """Container for a loaded trait asset"""
    file_path: str
    file_name: str
    trait_name: str
    trait_id: str
    image: Image.Image
    image_size: Tuple[int, int]
    file_size: int
    load_time: float
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    memory_size: int = 0
    
    def __post_init__(self):
        """Calculate memory usage after initialization"""
        if self.image:
            # Estimate memory usage: width * height * channels * bytes_per_channel
            width, height = self.image.size
            channels = len(self.image.getbands()) if hasattr(self.image, 'getbands') else 4
            self.memory_size = width * height * channels
    
    def touch(self):
        """Update access time and count"""
        self.last_accessed = time.time()
        self.access_count += 1


class TraitAssetCache:
    """
    High-performance cache for trait assets with multiple eviction strategies
    """
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 512,
                 strategy: CacheStrategy = CacheStrategy.LRU):
        """
        Initialize trait asset cache
        
        Args:
            max_size: Maximum number of assets to cache
            max_memory_mb: Maximum memory usage in MB
            strategy: Cache eviction strategy
        """
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.strategy = strategy
        
        # Thread-safe cache storage
        self._cache: OrderedDict[str, LoadedTraitAsset] = OrderedDict()
        self._lock = threading.RLock()
        
        # Cache statistics
        self.stats = CacheStats(
            max_size=max_size,
            max_memory_bytes=self.max_memory_bytes
        )
        
        # Weak references to notify on eviction
        self._eviction_callbacks: Set[weakref.ref] = set()
    
    def get(self, key: str) -> Optional[LoadedTraitAsset]:
        """
        Get asset from cache
        
        Args:
            key: Cache key (typically file path)
            
        Returns:
            LoadedTraitAsset if found, None otherwise
        """
        with self._lock:
            self.stats.total_requests += 1
            
            if key in self._cache:
                asset = self._cache[key]
                asset.touch()
                
                # Move to end for LRU strategy
                if self.strategy == CacheStrategy.LRU:
                    self._cache.move_to_end(key)
                
                self.stats.cache_hits += 1
                return asset
            else:
                self.stats.cache_misses += 1
                return None
    
    def put(self, key: str, asset: LoadedTraitAsset) -> bool:
        """
        Add asset to cache
        
        Args:
            key: Cache key
            asset: Asset to cache
            
        Returns:
            bool: True if added successfully
        """
        with self._lock:
            # Check if we need to evict before adding
            while self._should_evict(asset):
                if not self._evict_one():
                    return False  # Cannot evict anything
            
            # Add to cache
            self._cache[key] = asset
            self.stats.current_size = len(self._cache)
            self.stats.memory_usage_bytes += asset.memory_size
            
            return True
    
    def remove(self, key: str) -> bool:
        """
        Remove asset from cache
        
        Args:
            key: Cache key to remove
            
        Returns:
            bool: True if removed
        """
        with self._lock:
            if key in self._cache:
                asset = self._cache.pop(key)
                self.stats.current_size = len(self._cache)
                self.stats.memory_usage_bytes -= asset.memory_size
                return True
            return False
    
    def clear(self):
        """Clear all cached assets"""
        with self._lock:
            self._cache.clear()
            self.stats.current_size = 0
            self.stats.memory_usage_bytes = 0
    
    def get_keys(self) -> List[str]:
        """Get all cache keys"""
        with self._lock:
            return list(self._cache.keys())
    
    def _should_evict(self, new_asset: LoadedTraitAsset) -> bool:
        """Check if eviction is needed before adding new asset"""
        return (
            len(self._cache) >= self.max_size or
            self.stats.memory_usage_bytes + new_asset.memory_size > self.max_memory_bytes
        )
    
    def _evict_one(self) -> bool:
        """Evict one asset based on strategy"""
        if not self._cache:
            return False
        
        key_to_evict = None
        
        if self.strategy == CacheStrategy.LRU:
            # Remove least recently used (first item in OrderedDict)
            key_to_evict = next(iter(self._cache))
        
        elif self.strategy == CacheStrategy.FIFO:
            # Remove first inserted (first item in OrderedDict)
            key_to_evict = next(iter(self._cache))
        
        elif self.strategy == CacheStrategy.SIZE_BASED:
            # Remove largest asset by memory usage
            largest_key = max(self._cache.keys(), 
                            key=lambda k: self._cache[k].memory_size)
            key_to_evict = largest_key
        
        if key_to_evict:
            asset = self._cache.pop(key_to_evict)
            self.stats.current_size = len(self._cache)
            self.stats.memory_usage_bytes -= asset.memory_size
            self.stats.evictions += 1
            
            # Notify eviction callbacks
            self._notify_eviction(key_to_evict, asset)
            return True
        
        return False
    
    def _notify_eviction(self, key: str, asset: LoadedTraitAsset):
        """Notify registered callbacks about eviction"""
        dead_refs = set()
        for callback_ref in self._eviction_callbacks:
            callback = callback_ref()
            if callback is None:
                dead_refs.add(callback_ref)
            else:
                try:
                    callback(key, asset)
                except Exception:
                    pass  # Ignore callback errors
        
        # Clean up dead references
        self._eviction_callbacks -= dead_refs


class TraitAssetLoader:
    """
    Efficient trait asset loader with caching and validation
    
    Provides:
    - Fast image loading with validation
    - Memory-efficient caching with multiple strategies
    - Graceful error handling for missing/corrupted files
    - Integration with existing trait management components
    - Performance monitoring and statistics
    """
    
    def __init__(self, collection_root: Union[str, Path], 
                 cache_size: int = 1000, cache_memory_mb: int = 512,
                 cache_strategy: CacheStrategy = CacheStrategy.LRU,
                 validate_on_load: bool = True):
        """
        Initialize trait asset loader
        
        Args:
            collection_root: Root path of the GenConfig collection
            cache_size: Maximum number of assets to cache
            cache_memory_mb: Maximum cache memory usage in MB
            cache_strategy: Cache eviction strategy
            validate_on_load: Whether to validate images when loading
        """
        self.collection_root = Path(collection_root)
        self.traits_root = self.collection_root / "traits"
        self.validate_on_load = validate_on_load
        
        # Initialize cache
        self.cache = TraitAssetCache(
            max_size=cache_size,
            max_memory_mb=cache_memory_mb,
            strategy=cache_strategy
        )
        
        # Directory manager for trait discovery
        self.directory_manager = TraitDirectoryManager(collection_root)
        
        # Loading statistics
        self.load_stats = {
            'total_loads': 0,
            'successful_loads': 0,
            'failed_loads': 0,
            'validation_failures': 0,
            'total_load_time': 0.0
        }
    
    def load_trait_asset(self, file_path: Union[str, Path], 
                        validate: Optional[bool] = None) -> Optional[LoadedTraitAsset]:
        """
        Load a single trait asset with caching
        
        Args:
            file_path: Path to the trait image file
            validate: Whether to validate the image (overrides instance setting)
            
        Returns:
            LoadedTraitAsset if successful, None if failed
        """
        file_path_str = str(file_path)
        
        # Check cache first
        cached_asset = self.cache.get(file_path_str)
        if cached_asset:
            return cached_asset
        
        # Load from disk
        return self._load_from_disk(file_path_str, validate)
    
    def load_trait_assets_batch(self, file_paths: List[Union[str, Path]], 
                               validate: Optional[bool] = None) -> Dict[str, Optional[LoadedTraitAsset]]:
        """
        Load multiple trait assets efficiently
        
        Args:
            file_paths: List of paths to trait image files
            validate: Whether to validate images
            
        Returns:
            Dict mapping file paths to loaded assets (None if failed)
        """
        results = {}
        
        for file_path in file_paths:
            file_path_str = str(file_path)
            results[file_path_str] = self.load_trait_asset(file_path_str, validate)
        
        return results
    
    def load_directory_assets(self, directory_name: str, 
                             validate: Optional[bool] = None) -> Dict[str, Optional[LoadedTraitAsset]]:
        """
        Load all trait assets from a specific directory
        
        Args:
            directory_name: Name of trait directory (e.g., "position-1-background")
            validate: Whether to validate images
            
        Returns:
            Dict mapping file paths to loaded assets
        """
        directory_info = self.directory_manager.scan_trait_directories()
        
        if directory_name not in directory_info:
            return {}
        
        dir_info = directory_info[directory_name]
        file_paths = [entry.file_path for entry in dir_info.trait_files]
        
        return self.load_trait_assets_batch(file_paths, validate)
    
    def load_all_assets(self, validate: Optional[bool] = None) -> Dict[str, Dict[str, Optional[LoadedTraitAsset]]]:
        """
        Load all trait assets from all directories
        
        Args:
            validate: Whether to validate images
            
        Returns:
            Dict mapping directory names to file path -> asset mappings
        """
        directory_info = self.directory_manager.scan_trait_directories()
        results = {}
        
        for directory_name in directory_info:
            results[directory_name] = self.load_directory_assets(directory_name, validate)
        
        return results
    
    def preload_assets(self, directory_names: Optional[List[str]] = None) -> ValidationResult:
        """
        Preload assets into cache for better performance
        
        Args:
            directory_names: Specific directories to preload, or None for all
            
        Returns:
            ValidationResult: Results of preloading operation
        """
        issues = []
        loaded_count = 0
        failed_count = 0
        
        try:
            directory_info = self.directory_manager.scan_trait_directories()
            
            # Determine which directories to process
            if directory_names is None:
                directories_to_process = list(directory_info.keys())
            else:
                directories_to_process = [d for d in directory_names if d in directory_info]
            
            for directory_name in directories_to_process:
                dir_info = directory_info[directory_name]
                
                for file_entry in dir_info.trait_files:
                    if file_entry.is_valid_name:
                        asset = self.load_trait_asset(file_entry.file_path)
                        if asset:
                            loaded_count += 1
                        else:
                            failed_count += 1
                            issues.append(ValidationIssue(
                                ValidationSeverity.WARNING,
                                "preload_failed",
                                f"Failed to preload asset: {file_entry.file_path}",
                                file_entry.file_path,
                                "Check file integrity and permissions"
                            ))
            
            issues.append(ValidationIssue(
                ValidationSeverity.INFO,
                "preload_complete",
                f"Preloaded {loaded_count} assets, {failed_count} failures",
                str(self.traits_root),
                None
            ))
            
            return ValidationResult(is_valid=failed_count == 0, issues=issues)
            
        except Exception as e:
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                "preload_error",
                f"Error during preloading: {str(e)}",
                str(self.traits_root),
                "Check system logs for detailed error information"
            ))
            return ValidationResult(is_valid=False, issues=issues)
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive cache and loading statistics
        
        Returns:
            Dict with cache and loading statistics
        """
        return {
            'cache': {
                'total_requests': self.cache.stats.total_requests,
                'cache_hits': self.cache.stats.cache_hits,
                'cache_misses': self.cache.stats.cache_misses,
                'hit_rate': self.cache.stats.hit_rate,
                'miss_rate': self.cache.stats.miss_rate,
                'evictions': self.cache.stats.evictions,
                'current_size': self.cache.stats.current_size,
                'max_size': self.cache.stats.max_size,
                'memory_usage_mb': self.cache.stats.memory_usage_bytes / (1024 * 1024),
                'max_memory_mb': self.cache.stats.max_memory_bytes / (1024 * 1024),
                'memory_utilization': (self.cache.stats.memory_usage_bytes / 
                                     max(self.cache.stats.max_memory_bytes, 1)) * 100.0
            },
            'loading': {
                'total_loads': self.load_stats['total_loads'],
                'successful_loads': self.load_stats['successful_loads'],
                'failed_loads': self.load_stats['failed_loads'],
                'validation_failures': self.load_stats['validation_failures'],
                'success_rate': (self.load_stats['successful_loads'] / 
                               max(self.load_stats['total_loads'], 1)) * 100.0,
                'average_load_time': (self.load_stats['total_load_time'] / 
                                    max(self.load_stats['total_loads'], 1))
            }
        }
    
    def clear_cache(self):
        """Clear all cached assets"""
        self.cache.clear()
    
    def _load_from_disk(self, file_path: str, validate: Optional[bool] = None) -> Optional[LoadedTraitAsset]:
        """Load trait asset from disk with validation and caching"""
        start_time = time.time()
        self.load_stats['total_loads'] += 1
        
        try:
            # Check if file exists
            if not validate_file_exists(file_path):
                self.load_stats['failed_loads'] += 1
                return None
            
            # Validate if requested
            should_validate = validate if validate is not None else self.validate_on_load
            if should_validate:
                validation_result = validate_trait_file(file_path)
                if not validation_result.is_valid:
                    self.load_stats['validation_failures'] += 1
                    self.load_stats['failed_loads'] += 1
                    return None
            
            # Load image
            try:
                image = Image.open(file_path)
                # Convert to RGBA for consistency
                if image.mode != 'RGBA':
                    image = image.convert('RGBA')
            except Exception as e:
                self.load_stats['failed_loads'] += 1
                return None
            
            # Extract trait information from filename
            file_name = Path(file_path).name
            trait_name, trait_id = self._parse_trait_filename(file_name)
            
            # Get file size
            try:
                file_size = get_file_size(file_path)
            except FileOperationError:
                file_size = 0
            
            # Create asset
            load_time = time.time() - start_time
            asset = LoadedTraitAsset(
                file_path=file_path,
                file_name=file_name,
                trait_name=trait_name,
                trait_id=trait_id,
                image=image,
                image_size=image.size,
                file_size=file_size,
                load_time=load_time
            )
            
            # Add to cache
            if self.cache.put(file_path, asset):
                self.load_stats['successful_loads'] += 1
                self.load_stats['total_load_time'] += load_time
                return asset
            else:
                # Cache full, but still return the asset
                self.load_stats['successful_loads'] += 1
                self.load_stats['total_load_time'] += load_time
                return asset
                
        except Exception as e:
            self.load_stats['failed_loads'] += 1
            return None
    
    def _parse_trait_filename(self, filename: str) -> Tuple[str, str]:
        """Parse trait name and ID from filename"""
        # Remove extension
        name_without_ext = filename.rsplit('.', 1)[0]
        
        # Try to match pattern: trait-{name}-{id}
        if name_without_ext.startswith('trait-') and name_without_ext.count('-') >= 2:
            parts = name_without_ext.split('-')
            if len(parts) >= 3:
                trait_id = parts[-1]
                trait_name = '-'.join(parts[1:-1])
                return trait_name, trait_id
        
        # Fallback: use whole name
        return name_without_ext, "000"


# Convenience functions
def create_asset_loader(collection_root: Union[str, Path], 
                       cache_size: int = 1000, cache_memory_mb: int = 512,
                       cache_strategy: CacheStrategy = CacheStrategy.LRU) -> TraitAssetLoader:
    """
    Create a trait asset loader with specified configuration
    
    Args:
        collection_root: Root path of the GenConfig collection
        cache_size: Maximum number of assets to cache
        cache_memory_mb: Maximum cache memory usage in MB
        cache_strategy: Cache eviction strategy
        
    Returns:
        TraitAssetLoader: Configured asset loader
    """
    return TraitAssetLoader(
        collection_root=collection_root,
        cache_size=cache_size,
        cache_memory_mb=cache_memory_mb,
        cache_strategy=cache_strategy
    )


def load_trait_asset(collection_root: Union[str, Path], 
                    file_path: Union[str, Path]) -> Optional[LoadedTraitAsset]:
    """
    Convenience function to load a single trait asset
    
    Args:
        collection_root: Root path of the GenConfig collection
        file_path: Path to the trait image file
        
    Returns:
        LoadedTraitAsset if successful, None if failed
    """
    loader = TraitAssetLoader(collection_root)
    return loader.load_trait_asset(file_path)


def get_asset_loader_report(loader: TraitAssetLoader) -> str:
    """
    Generate a comprehensive report of asset loader performance
    
    Args:
        loader: TraitAssetLoader instance
        
    Returns:
        String containing formatted report
    """
    stats = loader.get_cache_statistics()
    
    report_lines = [
        "=== Trait Asset Loader Report ===",
        f"Collection Root: {loader.collection_root}",
        "",
        "📊 Cache Statistics:",
        f"  Total Requests: {stats['cache']['total_requests']}",
        f"  Cache Hits: {stats['cache']['cache_hits']}",
        f"  Cache Misses: {stats['cache']['cache_misses']}",
        f"  Hit Rate: {stats['cache']['hit_rate']:.1f}%",
        f"  Miss Rate: {stats['cache']['miss_rate']:.1f}%",
        f"  Evictions: {stats['cache']['evictions']}",
        f"  Current Size: {stats['cache']['current_size']}/{stats['cache']['max_size']}",
        f"  Memory Usage: {stats['cache']['memory_usage_mb']:.1f}/{stats['cache']['max_memory_mb']:.1f} MB",
        f"  Memory Utilization: {stats['cache']['memory_utilization']:.1f}%",
        "",
        "📈 Loading Statistics:",
        f"  Total Loads: {stats['loading']['total_loads']}",
        f"  Successful Loads: {stats['loading']['successful_loads']}",
        f"  Failed Loads: {stats['loading']['failed_loads']}",
        f"  Validation Failures: {stats['loading']['validation_failures']}",
        f"  Success Rate: {stats['loading']['success_rate']:.1f}%",
        f"  Average Load Time: {stats['loading']['average_load_time']:.3f}s"
    ]
    
    return "\n".join(report_lines) 