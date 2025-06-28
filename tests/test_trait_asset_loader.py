"""
Test suite for GenConfig Trait Asset Loader

Tests the efficient loading and caching of trait images.
Follows the testing strategy: Setup -> Execution -> Validation -> Cleanup
"""

import os
import tempfile
import shutil
import json
import time
from pathlib import Path
import pytest
import sys
from PIL import Image

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from traits.asset_loader import (
    TraitAssetLoader,
    TraitAssetCache,
    TraitAssetError,
    LoadedTraitAsset,
    CacheStats,
    CacheStrategy,
    create_asset_loader,
    load_trait_asset,
    get_asset_loader_report
)
from config.logic_validator import ValidationResult, ValidationSeverity
from infrastructure.directory_manager import create_collection_structure
from traits.directory_manager import create_trait_directories


class TestTraitAssetLoader:
    """Test cases for the Trait Asset Loader"""
    
    def setup_method(self):
        """Setup: Create test fixtures and sample data"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_collection = Path(self.temp_dir) / "test-collection"
        
        # Create collection structure
        create_collection_structure(str(self.test_collection))
        create_trait_directories(self.test_collection)
        
        # Create sample trait files for testing
        self._create_sample_trait_files()
        
        # Initialize loader
        self.loader = TraitAssetLoader(
            collection_root=self.test_collection,
            cache_size=10,
            cache_memory_mb=50
        )
    
    def teardown_method(self):
        """Cleanup: Remove test files and reset state"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _create_sample_trait_files(self):
        """Create sample trait files for testing"""
        trait_directories = [
            "position-1-background",
            "position-2-base",
            "position-3-accent"
        ]
        
        for trait_dir in trait_directories:
            dir_path = self.test_collection / "traits" / trait_dir
            
            # Create sample images
            sample_files = [
                f"trait-{trait_dir.split('-')[2]}-001.png",
                f"trait-{trait_dir.split('-')[2]}-002.png",
                f"trait-invalid-name.png"  # Invalid naming
            ]
            
            for filename in sample_files:
                file_path = dir_path / filename
                
                # Create a 200x200 RGBA image
                image = Image.new('RGBA', (200, 200), (255, 0, 0, 128))
                image.save(file_path, 'PNG')
    
    def test_loader_initialization(self):
        """Test: TraitAssetLoader initialization"""
        # Execution
        loader = TraitAssetLoader(
            collection_root=self.test_collection,
            cache_size=100,
            cache_memory_mb=256,
            cache_strategy=CacheStrategy.LRU
        )
        
        # Validation
        assert loader.collection_root == self.test_collection
        assert loader.traits_root == self.test_collection / "traits"
        assert loader.cache.max_size == 100
        assert loader.cache.max_memory_bytes == 256 * 1024 * 1024
        assert loader.cache.strategy == CacheStrategy.LRU
        assert loader.validate_on_load is True
    
    def test_load_single_trait_asset_success(self):
        """Test: Successfully loading a single trait asset"""
        # Setup
        trait_file = self.test_collection / "traits" / "position-1-background" / "trait-background-001.png"
        
        # Execution
        asset = self.loader.load_trait_asset(trait_file)
        
        # Validation
        assert asset is not None
        assert isinstance(asset, LoadedTraitAsset)
        assert asset.file_path == str(trait_file)
        assert asset.file_name == "trait-background-001.png"
        assert asset.trait_name == "background"
        assert asset.trait_id == "001"
        assert asset.image is not None
        assert asset.image_size == (200, 200)
        assert asset.file_size > 0
        assert asset.load_time > 0
        assert asset.memory_size > 0
        assert asset.access_count == 1
    
    def test_load_trait_asset_caching(self):
        """Test: Asset caching functionality"""
        # Setup
        trait_file = self.test_collection / "traits" / "position-1-background" / "trait-background-001.png"
        
        # Execution: Load twice
        asset1 = self.loader.load_trait_asset(trait_file)
        asset2 = self.loader.load_trait_asset(trait_file)
        
        # Validation
        assert asset1 is not None
        assert asset2 is not None
        assert asset1 is asset2  # Should be the same object from cache
        assert asset2.access_count == 2  # Access count should increment
        
        # Check cache statistics
        stats = self.loader.get_cache_statistics()
        assert stats['cache']['total_requests'] == 2
        assert stats['cache']['cache_hits'] == 1
        assert stats['cache']['cache_misses'] == 1
        assert stats['cache']['hit_rate'] == 50.0
    
    def test_load_trait_asset_missing_file(self):
        """Test: Loading non-existent file"""
        # Setup
        non_existent_file = self.test_collection / "traits" / "position-1-background" / "non-existent.png"
        
        # Execution
        asset = self.loader.load_trait_asset(non_existent_file)
        
        # Validation
        assert asset is None
        
        # Check loading statistics
        stats = self.loader.get_cache_statistics()
        assert stats['loading']['failed_loads'] > 0
        assert stats['loading']['success_rate'] < 100.0
    
    def test_load_trait_asset_without_validation(self):
        """Test: Loading asset without validation"""
        # Setup
        trait_file = self.test_collection / "traits" / "position-1-background" / "trait-background-001.png"
        loader_no_validate = TraitAssetLoader(
            collection_root=self.test_collection,
            validate_on_load=False
        )
        
        # Execution
        asset = loader_no_validate.load_trait_asset(trait_file)
        
        # Validation
        assert asset is not None
        assert isinstance(asset, LoadedTraitAsset)
        
        # Should have faster loading (no validation overhead)
        stats = loader_no_validate.get_cache_statistics()
        assert stats['loading']['validation_failures'] == 0
    
    def test_load_trait_assets_batch(self):
        """Test: Batch loading of multiple trait assets"""
        # Setup
        trait_files = [
            self.test_collection / "traits" / "position-1-background" / "trait-background-001.png",
            self.test_collection / "traits" / "position-1-background" / "trait-background-002.png",
            self.test_collection / "traits" / "position-2-base" / "trait-base-001.png"
        ]
        
        # Execution
        results = self.loader.load_trait_assets_batch(trait_files)
        
        # Validation
        assert len(results) == 3
        for file_path in trait_files:
            file_path_str = str(file_path)
            assert file_path_str in results
            asset = results[file_path_str]
            if asset:  # Only check if loading succeeded
                assert isinstance(asset, LoadedTraitAsset)
                assert asset.file_path == file_path_str
    
    def test_load_directory_assets(self):
        """Test: Loading all assets from a directory"""
        # Execution
        results = self.loader.load_directory_assets("position-1-background")
        
        # Validation
        assert isinstance(results, dict)
        assert len(results) > 0
        
        # Check that valid files were loaded
        loaded_count = sum(1 for asset in results.values() if asset is not None)
        assert loaded_count >= 2  # At least 2 valid files
    
    def test_load_directory_assets_nonexistent(self):
        """Test: Loading from non-existent directory"""
        # Execution
        results = self.loader.load_directory_assets("non-existent-directory")
        
        # Validation
        assert results == {}
    
    def test_load_all_assets(self):
        """Test: Loading all assets from all directories"""
        # Execution
        results = self.loader.load_all_assets()
        
        # Validation
        assert isinstance(results, dict)
        assert len(results) > 0
        
        # Should have results for multiple directories
        expected_dirs = ["position-1-background", "position-2-base", "position-3-accent"]
        for dir_name in expected_dirs:
            assert dir_name in results
            assert isinstance(results[dir_name], dict)
    
    def test_preload_assets_all(self):
        """Test: Preloading all assets"""
        # Execution
        result = self.loader.preload_assets()
        
        # Validation
        assert isinstance(result, ValidationResult)
        # Should have loaded some assets successfully
        
        # Check that cache has assets
        cache_stats = self.loader.get_cache_statistics()
        assert cache_stats['cache']['current_size'] > 0
        
        # Verify preload results in issues
        info_issues = [issue for issue in result.issues if issue.severity == ValidationSeverity.INFO]
        assert len(info_issues) >= 1  # Should have completion message
    
    def test_preload_assets_specific_directories(self):
        """Test: Preloading specific directories"""
        # Execution
        result = self.loader.preload_assets(["position-1-background", "position-2-base"])
        
        # Validation
        assert isinstance(result, ValidationResult)
        
        # Check cache size
        cache_stats = self.loader.get_cache_statistics()
        assert cache_stats['cache']['current_size'] > 0
    
    def test_get_cache_statistics(self):
        """Test: Retrieving cache statistics"""
        # Setup: Load some assets to generate statistics
        trait_file = self.test_collection / "traits" / "position-1-background" / "trait-background-001.png"
        self.loader.load_trait_asset(trait_file)
        self.loader.load_trait_asset(trait_file)  # Second access for cache hit
        
        # Execution
        stats = self.loader.get_cache_statistics()
        
        # Validation
        assert isinstance(stats, dict)
        assert 'cache' in stats
        assert 'loading' in stats
        
        # Cache stats
        cache_stats = stats['cache']
        assert cache_stats['total_requests'] >= 2
        assert cache_stats['cache_hits'] >= 1
        assert cache_stats['hit_rate'] >= 0.0
        assert cache_stats['current_size'] >= 1
        assert cache_stats['memory_usage_mb'] >= 0.0
        
        # Loading stats
        loading_stats = stats['loading']
        assert loading_stats['total_loads'] >= 1
        assert loading_stats['successful_loads'] >= 1
        assert loading_stats['success_rate'] >= 0.0
        assert loading_stats['average_load_time'] >= 0.0
    
    def test_clear_cache(self):
        """Test: Clearing the cache"""
        # Setup: Load some assets
        trait_file = self.test_collection / "traits" / "position-1-background" / "trait-background-001.png"
        self.loader.load_trait_asset(trait_file)
        
        # Verify cache has content
        stats_before = self.loader.get_cache_statistics()
        assert stats_before['cache']['current_size'] > 0
        
        # Execution
        self.loader.clear_cache()
        
        # Validation
        stats_after = self.loader.get_cache_statistics()
        assert stats_after['cache']['current_size'] == 0
        assert stats_after['cache']['memory_usage_mb'] == 0.0


class TestTraitAssetCache:
    """Test cases for the TraitAssetCache"""
    
    def setup_method(self):
        """Setup: Create test cache"""
        self.cache = TraitAssetCache(
            max_size=3,
            max_memory_mb=1,
            strategy=CacheStrategy.LRU
        )
        
        # Create sample assets
        self.sample_assets = []
        for i in range(5):
            image = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
            asset = LoadedTraitAsset(
                file_path=f"/test/asset-{i}.png",
                file_name=f"asset-{i}.png",
                trait_name=f"asset-{i}",
                trait_id=f"{i:03d}",
                image=image,
                image_size=(100, 100),
                file_size=1000,
                load_time=0.1
            )
            self.sample_assets.append(asset)
    
    def teardown_method(self):
        """Cleanup: Clear cache"""
        self.cache.clear()
    
    def test_cache_initialization(self):
        """Test: Cache initialization"""
        # Execution
        cache = TraitAssetCache(
            max_size=100,
            max_memory_mb=256,
            strategy=CacheStrategy.SIZE_BASED
        )
        
        # Validation
        assert cache.max_size == 100
        assert cache.max_memory_bytes == 256 * 1024 * 1024
        assert cache.strategy == CacheStrategy.SIZE_BASED
        assert cache.stats.max_size == 100
        assert len(cache._cache) == 0
    
    def test_cache_put_and_get(self):
        """Test: Basic cache put and get operations"""
        # Setup
        asset = self.sample_assets[0]
        key = "test-key"
        
        # Execution
        put_result = self.cache.put(key, asset)
        retrieved_asset = self.cache.get(key)
        
        # Validation
        assert put_result is True
        assert retrieved_asset is not None
        assert retrieved_asset is asset
        assert retrieved_asset.access_count == 2  # 1 from put, 1 from get
        assert self.cache.stats.current_size == 1
        assert self.cache.stats.cache_hits == 1
        assert self.cache.stats.cache_misses == 0
    
    def test_cache_get_missing_key(self):
        """Test: Getting asset with missing key"""
        # Execution
        asset = self.cache.get("non-existent-key")
        
        # Validation
        assert asset is None
        assert self.cache.stats.cache_misses == 1
        assert self.cache.stats.cache_hits == 0
    
    def test_cache_lru_eviction(self):
        """Test: LRU cache eviction when size limit reached"""
        # Setup: Fill cache to capacity
        for i in range(3):
            self.cache.put(f"key-{i}", self.sample_assets[i])
        
        assert self.cache.stats.current_size == 3
        
        # Access key-1 to make it recently used
        self.cache.get("key-1")
        
        # Execution: Add one more asset (should evict key-0)
        self.cache.put("key-3", self.sample_assets[3])
        
        # Validation
        assert self.cache.stats.current_size == 3
        assert self.cache.stats.evictions == 1
        assert self.cache.get("key-0") is None  # Should be evicted
        assert self.cache.get("key-1") is not None  # Should still be there
        assert self.cache.get("key-2") is not None  # Should still be there
        assert self.cache.get("key-3") is not None  # Should be there
    
    def test_cache_remove(self):
        """Test: Removing asset from cache"""
        # Setup
        asset = self.sample_assets[0]
        key = "test-key"
        self.cache.put(key, asset)
        
        # Execution
        removed = self.cache.remove(key)
        retrieved = self.cache.get(key)
        
        # Validation
        assert removed is True
        assert retrieved is None
        assert self.cache.stats.current_size == 0
    
    def test_cache_remove_missing_key(self):
        """Test: Removing non-existent key"""
        # Execution
        removed = self.cache.remove("non-existent-key")
        
        # Validation
        assert removed is False
    
    def test_cache_clear(self):
        """Test: Clearing entire cache"""
        # Setup: Add some assets
        for i in range(2):
            self.cache.put(f"key-{i}", self.sample_assets[i])
        
        assert self.cache.stats.current_size == 2
        
        # Execution
        self.cache.clear()
        
        # Validation
        assert self.cache.stats.current_size == 0
        assert self.cache.stats.memory_usage_bytes == 0
        assert len(self.cache.get_keys()) == 0
    
    def test_cache_get_keys(self):
        """Test: Getting all cache keys"""
        # Setup
        keys = ["key-1", "key-2", "key-3"]
        for i, key in enumerate(keys):
            self.cache.put(key, self.sample_assets[i])
        
        # Execution
        retrieved_keys = self.cache.get_keys()
        
        # Validation
        assert len(retrieved_keys) == 3
        assert set(retrieved_keys) == set(keys)


class TestLoadedTraitAsset:
    """Test LoadedTraitAsset data structure"""
    
    def test_loaded_trait_asset_creation(self):
        """Test: Creating LoadedTraitAsset"""
        # Setup
        image = Image.new('RGBA', (200, 200), (255, 0, 0, 128))
        
        # Execution
        asset = LoadedTraitAsset(
            file_path="/test/trait-bg-001.png",
            file_name="trait-bg-001.png",
            trait_name="bg",
            trait_id="001",
            image=image,
            image_size=(200, 200),
            file_size=1024,
            load_time=0.05
        )
        
        # Validation
        assert asset.file_path == "/test/trait-bg-001.png"
        assert asset.trait_name == "bg"
        assert asset.trait_id == "001"
        assert asset.image_size == (200, 200)
        assert asset.memory_size > 0  # Should calculate memory usage
        assert asset.access_count == 0
        assert asset.last_accessed > 0
    
    def test_loaded_trait_asset_touch(self):
        """Test: Touch functionality for access tracking"""
        # Setup
        image = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
        asset = LoadedTraitAsset(
            file_path="/test/asset.png",
            file_name="asset.png",
            trait_name="test",
            trait_id="001",
            image=image,
            image_size=(100, 100),
            file_size=100,
            load_time=0.01
        )
        
        initial_access_time = asset.last_accessed
        initial_access_count = asset.access_count
        
        # Execution
        time.sleep(0.01)  # Small delay to ensure time difference
        asset.touch()
        
        # Validation
        assert asset.last_accessed > initial_access_time
        assert asset.access_count == initial_access_count + 1


class TestCacheStrategy:
    """Test different cache strategies"""
    
    def test_cache_strategy_enum(self):
        """Test: CacheStrategy enum values"""
        # Validation
        assert CacheStrategy.LRU.value == "lru"
        assert CacheStrategy.SIZE_BASED.value == "size_based"
        assert CacheStrategy.FIFO.value == "fifo"


class TestCacheStats:
    """Test cache statistics"""
    
    def test_cache_stats_creation(self):
        """Test: Creating CacheStats"""
        # Execution
        stats = CacheStats(
            total_requests=100,
            cache_hits=75,
            cache_misses=25,
            max_size=1000
        )
        
        # Validation
        assert stats.hit_rate == 75.0
        assert stats.miss_rate == 25.0
    
    def test_cache_stats_zero_requests(self):
        """Test: Cache stats with zero requests"""
        # Execution
        stats = CacheStats()
        
        # Validation
        assert stats.hit_rate == 0.0
        assert stats.miss_rate == 100.0


class TestTraitAssetLoaderConvenienceFunctions:
    """Test convenience functions"""
    
    def setup_method(self):
        """Setup: Create test collection"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_collection = Path(self.temp_dir) / "test-collection"
        create_collection_structure(str(self.test_collection))
        create_trait_directories(self.test_collection)
        
        # Create sample trait file
        trait_dir = self.test_collection / "traits" / "position-1-background"
        trait_file = trait_dir / "trait-background-001.png"
        image = Image.new('RGBA', (200, 200), (255, 0, 0, 128))
        image.save(trait_file, 'PNG')
        
        self.trait_file = trait_file
    
    def teardown_method(self):
        """Cleanup: Remove test files"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_create_asset_loader_function(self):
        """Test: create_asset_loader convenience function"""
        # Execution
        loader = create_asset_loader(
            collection_root=self.test_collection,
            cache_size=500,
            cache_memory_mb=128,
            cache_strategy=CacheStrategy.SIZE_BASED
        )
        
        # Validation
        assert isinstance(loader, TraitAssetLoader)
        assert loader.collection_root == self.test_collection
        assert loader.cache.max_size == 500
        assert loader.cache.strategy == CacheStrategy.SIZE_BASED
    
    def test_load_trait_asset_function(self):
        """Test: load_trait_asset convenience function"""
        # Execution
        asset = load_trait_asset(self.test_collection, self.trait_file)
        
        # Validation
        assert asset is not None
        assert isinstance(asset, LoadedTraitAsset)
        assert asset.file_path == str(self.trait_file)
    
    def test_get_asset_loader_report_function(self):
        """Test: get_asset_loader_report convenience function"""
        # Setup: Create loader and load some assets
        loader = TraitAssetLoader(self.test_collection)
        loader.load_trait_asset(self.trait_file)
        
        # Execution
        report = get_asset_loader_report(loader)
        
        # Validation
        assert isinstance(report, str)
        assert "Trait Asset Loader Report" in report
        assert "Cache Statistics" in report
        assert "Loading Statistics" in report
        assert str(self.test_collection) in report


class TestTraitAssetLoaderErrorHandling:
    """Test error handling and edge cases"""
    
    def setup_method(self):
        """Setup: Create test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_collection = Path(self.temp_dir) / "test-collection"
    
    def teardown_method(self):
        """Cleanup: Remove test files"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_loader_with_nonexistent_collection(self):
        """Test: Loader with non-existent collection root"""
        # Execution
        loader = TraitAssetLoader("/non/existent/path")
        asset = loader.load_trait_asset("/non/existent/file.png")
        
        # Validation
        assert asset is None
        
        # Check loading statistics
        stats = loader.get_cache_statistics()
        assert stats['loading']['failed_loads'] > 0
    
    def test_trait_asset_error_exception(self):
        """Test: TraitAssetError exception"""
        # Execution & Validation
        with pytest.raises(TraitAssetError):
            raise TraitAssetError("Test error message")
    
    def test_parse_trait_filename_edge_cases(self):
        """Test: Edge cases in trait filename parsing"""
        # Setup
        loader = TraitAssetLoader(self.test_collection)
        
        # Test cases
        test_cases = [
            ("trait-red-bg-001.png", ("red-bg", "001")),
            ("trait-complex-name-with-dashes-123.png", ("complex-name-with-dashes", "123")),
            ("invalid-filename.png", ("invalid-filename", "000")),
            ("trait.png", ("trait", "000")),
            ("trait-name.png", ("trait-name", "000"))
        ]
        
        for filename, expected in test_cases:
            # Execution
            trait_name, trait_id = loader._parse_trait_filename(filename)
            
            # Validation
            assert (trait_name, trait_id) == expected


def test_integration_workflow():
    """
    Integration test: Complete asset loading workflow
    Tests: Setup -> Execution -> Validation -> Cleanup
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Setup
        collection_root = Path(temp_dir) / "integration-test"
        create_collection_structure(str(collection_root))
        create_trait_directories(collection_root)
        
        # Create sample trait files
        trait_dir = collection_root / "traits" / "position-1-background"
        for i in range(3):
            trait_file = trait_dir / f"trait-bg-{i:03d}.png"
            image = Image.new('RGBA', (200, 200), (255, i * 50, 0, 128))
            image.save(trait_file, 'PNG')
        
        # Execution: Create loader and test full workflow
        loader = TraitAssetLoader(
            collection_root=collection_root,
            cache_size=10,
            cache_memory_mb=50
        )
        
        # Load individual asset
        asset = loader.load_trait_asset(trait_dir / "trait-bg-001.png")
        assert asset is not None
        
        # Load directory assets
        dir_assets = loader.load_directory_assets("position-1-background")
        assert len(dir_assets) >= 3
        
        # Preload assets
        preload_result = loader.preload_assets(["position-1-background"])
        assert preload_result.is_valid
        
        # Check statistics
        stats = loader.get_cache_statistics()
        assert stats['cache']['current_size'] > 0
        assert stats['loading']['total_loads'] > 0
        assert stats['loading']['success_rate'] > 0
        
        # Generate report
        report = get_asset_loader_report(loader)
        assert len(report) > 100
        
        # Clear cache
        loader.clear_cache()
        final_stats = loader.get_cache_statistics()
        assert final_stats['cache']['current_size'] == 0
        
        # Integration test successful
        assert True
        
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir) 