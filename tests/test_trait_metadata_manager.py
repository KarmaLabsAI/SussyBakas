"""
Tests for GenConfig Trait Metadata Manager

Tests the trait-specific metadata and properties management system
including JSON sidecar files, synchronization, and validation.
"""

import unittest
import tempfile
import shutil
import json
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from traits.metadata_manager import (
    TraitMetadataManager,
    TraitMetadata,
    MetadataError,
    MetadataSyncMode,
    MetadataValidationStats,
    load_trait_metadata,
    validate_metadata_consistency,
    sync_metadata,
    get_metadata_report
)
from config.logic_validator import ValidationResult, ValidationSeverity
from config.config_parser import GenConfig, TraitVariant, TraitCategory, GridPosition
from infrastructure.directory_manager import create_collection_structure


class TestTraitMetadata(unittest.TestCase):
    """Test the TraitMetadata data structure"""
    
    def test_trait_metadata_creation(self):
        """Test creating TraitMetadata objects"""
        metadata = TraitMetadata(
            name="Test Trait",
            filename="trait-test-001.png",
            rarity_weight=100,
            color_code="#FF0000",
            description="A test trait",
            category="Background",
            grid_position=(0, 0),
            tags=["test", "red"],
            artist="Test Artist"
        )
        
        self.assertEqual(metadata.name, "Test Trait")
        self.assertEqual(metadata.filename, "trait-test-001.png")
        self.assertEqual(metadata.rarity_weight, 100)
        self.assertEqual(metadata.color_code, "#FF0000")
        self.assertEqual(metadata.category, "Background")
        self.assertEqual(metadata.grid_position, (0, 0))
        self.assertEqual(metadata.tags, ["test", "red"])
    
    def test_trait_variant_conversion(self):
        """Test conversion to/from TraitVariant"""
        # Create from TraitVariant
        variant = TraitVariant(
            name="Test Variant",
            filename="trait-variant-001.png",
            rarity_weight=50,
            color_code="#00FF00",
            description="Test description"
        )
        
        metadata = TraitMetadata.from_trait_variant(
            variant, 
            category="Test Category", 
            grid_position=(1, 1)
        )
        
        self.assertEqual(metadata.name, variant.name)
        self.assertEqual(metadata.filename, variant.filename)
        self.assertEqual(metadata.rarity_weight, variant.rarity_weight)
        self.assertEqual(metadata.color_code, variant.color_code)
        self.assertEqual(metadata.description, variant.description)
        self.assertEqual(metadata.category, "Test Category")
        self.assertEqual(metadata.grid_position, (1, 1))
        
        # Convert back to TraitVariant
        converted_variant = metadata.to_trait_variant()
        
        self.assertEqual(converted_variant.name, variant.name)
        self.assertEqual(converted_variant.filename, variant.filename)
        self.assertEqual(converted_variant.rarity_weight, variant.rarity_weight)
        self.assertEqual(converted_variant.color_code, variant.color_code)
        self.assertEqual(converted_variant.description, variant.description)


class TestTraitMetadataManager(unittest.TestCase):
    """Test the main TraitMetadataManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.collection_root = Path(self.test_dir) / "test_collection"
        
        # Create collection structure
        create_collection_structure(str(self.collection_root))
        
        # Initialize manager
        self.manager = TraitMetadataManager(self.collection_root)
        
        # Create sample config
        self._create_sample_config()
        
        # Create sample trait images
        self._create_sample_traits()
    
    def tearDown(self):
        """Clean up test files"""
        shutil.rmtree(self.test_dir)
    
    def _create_sample_config(self):
        """Create a sample configuration file"""
        config_data = {
            "collection": {
                "name": "Test Collection",
                "description": "A test collection",
                "size": 100,
                "symbol": "TEST",
                "external_url": "https://example.com"
            },
            "generation": {
                "image_format": "PNG",
                "image_size": {"width": 600, "height": 600},
                "grid": {
                    "rows": 3,
                    "columns": 3,
                    "cell_size": {"width": 200, "height": 200}
                },
                "background_color": "#FFFFFF",
                "allow_duplicates": False
            },
            "traits": {
                "position-1-background": {
                    "name": "Background",
                    "required": True,
                    "grid_position": {"row": 0, "column": 0},
                    "variants": [
                        {
                            "name": "Red Background",
                            "filename": "trait-red-bg-001.png",
                            "rarity_weight": 100,
                            "color_code": "#FF0000"
                        },
                        {
                            "name": "Blue Background",
                            "filename": "trait-blue-bg-002.png",
                            "rarity_weight": 50,
                            "color_code": "#0000FF"
                        }
                    ]
                },
                "position-5-center": {
                    "name": "Center",
                    "required": True,
                    "grid_position": {"row": 1, "column": 1},
                    "variants": [
                        {
                            "name": "Circle Center",
                            "filename": "trait-circle-001.png",
                            "rarity_weight": 75,
                            "color_code": "#00FF00"
                        }
                    ]
                }
            },
            "rarity": {
                "calculation_method": "weighted_random",
                "distribution_validation": True,
                "rarity_tiers": {
                    "common": {"min_weight": 76, "max_weight": 100},
                    "uncommon": {"min_weight": 51, "max_weight": 75},
                    "rare": {"min_weight": 26, "max_weight": 50},
                    "epic": {"min_weight": 11, "max_weight": 25},
                    "legendary": {"min_weight": 1, "max_weight": 10}
                }
            },
            "validation": {
                "enforce_grid_positions": True,
                "require_all_positions": False,
                "check_file_integrity": True,
                "validate_image_dimensions": True
            }
        }
        
        config_path = self.collection_root / "config.json"
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def _create_sample_traits(self):
        """Create sample trait images"""
        # Create trait images
        trait_files = [
            ("position-1-background", "trait-red-bg-001.png"),
            ("position-1-background", "trait-blue-bg-002.png"),
            ("position-5-center", "trait-circle-001.png")
        ]
        
        for category, filename in trait_files:
            trait_dir = self.collection_root / "traits" / category
            trait_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a simple colored square
            img = Image.new('RGBA', (200, 200), (255, 0, 0, 128))
            img.save(trait_dir / filename, "PNG")
    
    def test_manager_initialization(self):
        """Test manager initialization"""
        self.assertEqual(self.manager.collection_root, self.collection_root)
        self.assertEqual(self.manager.traits_root, self.collection_root / "traits")
        self.assertEqual(self.manager.config_path, self.collection_root / "config.json")
    
    def test_save_and_load_metadata(self):
        """Test saving and loading metadata files"""
        # Create test metadata
        metadata = TraitMetadata(
            name="Test Trait",
            filename="trait-test-001.png",
            rarity_weight=100,
            color_code="#FF0000",
            description="A test trait",
            category="Background",
            grid_position=(0, 0),
            tags=["test", "red"],
            artist="Test Artist",
            custom_properties={"texture": "smooth", "style": "modern"}
        )
        
        # Set metadata path
        metadata_path = self.collection_root / "traits" / "position-1-background" / "trait-test-001.json"
        metadata.metadata_path = str(metadata_path)
        
        # Save metadata
        success = self.manager.save_trait_metadata(metadata)
        self.assertTrue(success)
        self.assertTrue(metadata_path.exists())
        
        # Load metadata
        loaded_metadata = self.manager.load_trait_metadata(metadata_path)
        
        # Verify loaded data
        self.assertEqual(loaded_metadata.name, metadata.name)
        self.assertEqual(loaded_metadata.filename, metadata.filename)
        self.assertEqual(loaded_metadata.rarity_weight, metadata.rarity_weight)
        self.assertEqual(loaded_metadata.color_code, metadata.color_code)
        self.assertEqual(loaded_metadata.description, metadata.description)
        self.assertEqual(loaded_metadata.category, metadata.category)
        self.assertEqual(loaded_metadata.grid_position, metadata.grid_position)
        self.assertEqual(loaded_metadata.tags, metadata.tags)
        self.assertEqual(loaded_metadata.artist, metadata.artist)
        self.assertEqual(loaded_metadata.custom_properties, metadata.custom_properties)
    
    def test_create_metadata_from_config(self):
        """Test creating metadata from configuration"""
        # Load config
        from config.config_parser import ConfigurationParser
        parser = ConfigurationParser()
        config = parser.parse_config_file(str(self.manager.config_path))
        
        # Create metadata from config
        metadata_by_category = self.manager.create_metadata_from_config(config)
        
        # Verify structure
        self.assertIn("position-1-background", metadata_by_category)
        self.assertIn("position-5-center", metadata_by_category)
        
        # Check background variants
        bg_metadata = metadata_by_category["position-1-background"]
        self.assertEqual(len(bg_metadata), 2)
        
        red_bg = next((m for m in bg_metadata if m.name == "Red Background"), None)
        self.assertIsNotNone(red_bg)
        self.assertEqual(red_bg.filename, "trait-red-bg-001.png")
        self.assertEqual(red_bg.rarity_weight, 100)
        self.assertEqual(red_bg.color_code, "#FF0000")
        self.assertEqual(red_bg.category, "Background")
        self.assertEqual(red_bg.grid_position, (0, 0))
        
        # Check paths are set correctly
        expected_image_path = str(self.collection_root / "traits" / "position-1-background" / "trait-red-bg-001.png")
        expected_metadata_path = str(self.collection_root / "traits" / "position-1-background" / "trait-red-bg-001.json")
        self.assertEqual(red_bg.image_path, expected_image_path)
        self.assertEqual(red_bg.metadata_path, expected_metadata_path)
    
    def test_scan_metadata_files(self):
        """Test scanning for existing metadata files"""
        # Create some metadata files
        bg_dir = self.collection_root / "traits" / "position-1-background"
        
        metadata1 = {
            "name": "Red Background",
            "filename": "trait-red-bg-001.png",
            "rarity_weight": 100,
            "color_code": "#FF0000",
            "category": "Background",
            "grid_position": [0, 0],
            "_genconfig_version": "1.0",
            "_metadata_type": "trait"
        }
        
        metadata2 = {
            "name": "Blue Background",
            "filename": "trait-blue-bg-002.png",
            "rarity_weight": 50,
            "color_code": "#0000FF",
            "category": "Background",
            "grid_position": [0, 0],
            "_genconfig_version": "1.0",
            "_metadata_type": "trait"
        }
        
        with open(bg_dir / "trait-red-bg-001.json", 'w') as f:
            json.dump(metadata1, f)
        
        with open(bg_dir / "trait-blue-bg-002.json", 'w') as f:
            json.dump(metadata2, f)
        
        # Scan metadata files
        scanned_metadata = self.manager.scan_metadata_files()
        
        # Verify results
        self.assertIn("position-1-background", scanned_metadata)
        bg_metadata = scanned_metadata["position-1-background"]
        self.assertEqual(len(bg_metadata), 2)
        
        # Check one of the loaded metadata objects
        red_metadata = next((m for m in bg_metadata if m.name == "Red Background"), None)
        self.assertIsNotNone(red_metadata)
        self.assertEqual(red_metadata.filename, "trait-red-bg-001.png")
        self.assertEqual(red_metadata.rarity_weight, 100)
    
    def test_validate_metadata_consistency(self):
        """Test metadata consistency validation"""
        # Run validation on empty metadata (should find missing files)
        result = self.manager.validate_metadata_consistency()
        
        # Should be valid (no errors) but have info messages about missing metadata
        self.assertTrue(result.is_valid)
        
        # Should have missing metadata issues
        missing_issues = [issue for issue in result.issues if issue.category == "missing_metadata"]
        self.assertTrue(len(missing_issues) > 0)
        
        # Create metadata files with conflicts
        bg_dir = self.collection_root / "traits" / "position-1-background"
        
        # Create metadata with different name than config
        conflicting_metadata = {
            "name": "Different Name",  # Config has "Red Background"
            "filename": "trait-red-bg-001.png",
            "rarity_weight": 200,  # Config has 100
            "color_code": "#00FF00",  # Config has "#FF0000"
            "category": "Background",
            "grid_position": [0, 0]
        }
        
        with open(bg_dir / "trait-red-bg-001.json", 'w') as f:
            json.dump(conflicting_metadata, f)
        
        # Run validation again
        result = self.manager.validate_metadata_consistency()
        
        # Should still be valid but have conflict warnings
        self.assertTrue(result.is_valid)
        
        # Should have metadata conflict issues
        conflict_issues = [issue for issue in result.issues if issue.category == "metadata_conflict"]
        self.assertTrue(len(conflict_issues) > 0)
    
    def test_sync_metadata_config_to_files(self):
        """Test synchronizing metadata from config to files"""
        # Sync metadata from config to files
        result = self.manager.sync_metadata(MetadataSyncMode.CONFIG_TO_FILES)
        
        # Should be successful
        self.assertTrue(result.is_valid)
        
        # Check that metadata files were created
        bg_dir = self.collection_root / "traits" / "position-1-background"
        center_dir = self.collection_root / "traits" / "position-5-center"
        
        self.assertTrue((bg_dir / "trait-red-bg-001.json").exists())
        self.assertTrue((bg_dir / "trait-blue-bg-002.json").exists())
        self.assertTrue((center_dir / "trait-circle-001.json").exists())
        
        # Verify content of one metadata file
        with open(bg_dir / "trait-red-bg-001.json", 'r') as f:
            metadata = json.load(f)
        
        self.assertEqual(metadata["name"], "Red Background")
        self.assertEqual(metadata["filename"], "trait-red-bg-001.png")
        self.assertEqual(metadata["rarity_weight"], 100)
        self.assertEqual(metadata["color_code"], "#FF0000")
    
    def test_create_metadata_template(self):
        """Test creating metadata templates"""
        template = self.manager.create_metadata_template(
            trait_name="Template Trait",
            filename="trait-template-001.png",
            category="Test Category",
            grid_position=(2, 2),
            rarity_weight=75,
            tags=["template", "test"],
            artist="Template Artist"
        )
        
        self.assertEqual(template.name, "Template Trait")
        self.assertEqual(template.filename, "trait-template-001.png")
        self.assertEqual(template.category, "Test Category")
        self.assertEqual(template.grid_position, (2, 2))
        self.assertEqual(template.rarity_weight, 75)
        self.assertEqual(template.tags, ["template", "test"])
        self.assertEqual(template.artist, "Template Artist")


class TestMetadataValidationStats(unittest.TestCase):
    """Test the MetadataValidationStats data structure"""
    
    def test_stats_creation(self):
        """Test creating validation stats"""
        stats = MetadataValidationStats(
            total_files=10,
            valid_metadata=8,
            invalid_metadata=1,
            missing_metadata=1,
            config_sync_issues=2,
            property_conflicts=1
        )
        
        self.assertEqual(stats.total_files, 10)
        self.assertEqual(stats.valid_metadata, 8)
        self.assertEqual(stats.invalid_metadata, 1)
        self.assertEqual(stats.missing_metadata, 1)
        self.assertEqual(stats.config_sync_issues, 2)
        self.assertEqual(stats.property_conflicts, 1)


class TestConvenienceFunctions(unittest.TestCase):
    """Test the module-level convenience functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.collection_root = Path(self.test_dir) / "test_collection"
        
        # Create collection structure
        create_collection_structure(str(self.collection_root))
        
        # Create sample config (minimal)
        config_data = {
            "collection": {
                "name": "Test Collection",
                "description": "A test collection",
                "size": 10,
                "symbol": "TEST",
                "external_url": "https://example.com"
            },
            "generation": {
                "image_format": "PNG",
                "image_size": {"width": 600, "height": 600},
                "grid": {
                    "rows": 3,
                    "columns": 3,
                    "cell_size": {"width": 200, "height": 200}
                },
                "background_color": "#FFFFFF",
                "allow_duplicates": False
            },
            "traits": {
                "position-1-background": {
                    "name": "Background",
                    "required": True,
                    "grid_position": {"row": 0, "column": 0},
                    "variants": [
                        {
                            "name": "Test Background",
                            "filename": "trait-test-bg-001.png",
                            "rarity_weight": 100
                        }
                    ]
                }
            },
            "rarity": {
                "calculation_method": "weighted_random",
                "distribution_validation": True,
                "rarity_tiers": {
                    "common": {"min_weight": 76, "max_weight": 100},
                    "uncommon": {"min_weight": 51, "max_weight": 75},
                    "rare": {"min_weight": 26, "max_weight": 50},
                    "epic": {"min_weight": 11, "max_weight": 25},
                    "legendary": {"min_weight": 1, "max_weight": 10}
                }
            },
            "validation": {
                "enforce_grid_positions": True,
                "require_all_positions": False,
                "check_file_integrity": True,
                "validate_image_dimensions": True
            }
        }
        
        config_path = self.collection_root / "config.json"
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def tearDown(self):
        """Clean up test files"""
        shutil.rmtree(self.test_dir)
    
    def test_validate_metadata_consistency_function(self):
        """Test the convenience validation function"""
        result = validate_metadata_consistency(self.collection_root)
        
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)
    
    def test_sync_metadata_function(self):
        """Test the convenience sync function"""
        result = sync_metadata(self.collection_root, MetadataSyncMode.CONFIG_TO_FILES)
        
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)
    
    def test_get_metadata_report_function(self):
        """Test the convenience report function"""
        report = get_metadata_report(self.collection_root)
        
        self.assertIsInstance(report, str)
        self.assertIn("Trait Metadata Summary", report)
        self.assertIn("Collection Root", report)
    
    def test_load_trait_metadata_function(self):
        """Test the convenience load function"""
        # Create a metadata file first
        bg_dir = self.collection_root / "traits" / "position-1-background"
        bg_dir.mkdir(parents=True, exist_ok=True)
        
        metadata_data = {
            "name": "Test Metadata",
            "filename": "trait-test-001.png",
            "rarity_weight": 100,
            "category": "Background",
            "grid_position": [0, 0]
        }
        
        metadata_path = bg_dir / "trait-test-001.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata_data, f)
        
        # Load using convenience function
        metadata = load_trait_metadata(metadata_path)
        
        self.assertIsInstance(metadata, TraitMetadata)
        self.assertEqual(metadata.name, "Test Metadata")
        self.assertEqual(metadata.filename, "trait-test-001.png")


class TestErrorHandling(unittest.TestCase):
    """Test error handling in metadata management"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.collection_root = Path(self.test_dir) / "test_collection"
        self.manager = TraitMetadataManager(self.collection_root)
    
    def tearDown(self):
        """Clean up test files"""
        shutil.rmtree(self.test_dir)
    
    def test_load_nonexistent_metadata(self):
        """Test loading non-existent metadata file"""
        nonexistent_path = self.collection_root / "nonexistent.json"
        
        with self.assertRaises(MetadataError):
            self.manager.load_trait_metadata(nonexistent_path)
    
    def test_load_invalid_json(self):
        """Test loading invalid JSON metadata"""
        invalid_json_path = self.collection_root / "invalid.json"
        invalid_json_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write invalid JSON
        with open(invalid_json_path, 'w') as f:
            f.write("{invalid json content")
        
        with self.assertRaises(MetadataError):
            self.manager.load_trait_metadata(invalid_json_path)
    
    def test_save_metadata_without_path(self):
        """Test saving metadata without specifying path"""
        metadata = TraitMetadata(
            name="Test",
            filename="test.png",
            rarity_weight=100
        )
        
        # No metadata_path set
        with self.assertRaises(MetadataError):
            self.manager.save_trait_metadata(metadata)
    
    def test_validation_without_config(self):
        """Test validation when config file doesn't exist"""
        # Collection root doesn't have a config.json
        result = self.manager.validate_metadata_consistency()
        
        # Should return error result
        self.assertFalse(result.is_valid)
        error_issues = [issue for issue in result.issues if issue.severity == ValidationSeverity.ERROR]
        self.assertTrue(len(error_issues) > 0)


class TestIntegrationWorkflow(unittest.TestCase):
    """Test complete integration workflow"""
    
    def setUp(self):
        """Set up complete test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.collection_root = Path(self.test_dir) / "test_collection"
        
        # Create collection structure
        create_collection_structure(str(self.collection_root))
        
        # Create a complete, valid configuration
        self._create_complete_config()
        
        # Create trait images
        self._create_trait_images()
        
        # Initialize manager
        self.manager = TraitMetadataManager(self.collection_root)
    
    def tearDown(self):
        """Clean up test files"""
        shutil.rmtree(self.test_dir)
    
    def _create_complete_config(self):
        """Create a complete configuration file"""
        config_data = {
            "collection": {
                "name": "Integration Test Collection",
                "description": "A complete test collection",
                "size": 50,
                "symbol": "INTEG",
                "external_url": "https://example.com/integration"
            },
            "generation": {
                "image_format": "PNG",
                "image_size": {"width": 600, "height": 600},
                "grid": {
                    "rows": 3,
                    "columns": 3,
                    "cell_size": {"width": 200, "height": 200}
                },
                "background_color": "#F0F0F0",
                "allow_duplicates": False
            },
            "traits": {
                "position-1-background": {
                    "name": "Background",
                    "required": True,
                    "grid_position": {"row": 0, "column": 0},
                    "variants": [
                        {
                            "name": "Sky Background",
                            "filename": "trait-sky-bg-001.png",
                            "rarity_weight": 100,
                            "color_code": "#87CEEB",
                            "description": "A beautiful sky background"
                        },
                        {
                            "name": "Forest Background",
                            "filename": "trait-forest-bg-002.png",
                            "rarity_weight": 75,
                            "color_code": "#228B22"
                        }
                    ]
                },
                "position-5-center": {
                    "name": "Center Element",
                    "required": True,
                    "grid_position": {"row": 1, "column": 1},
                    "variants": [
                        {
                            "name": "Golden Star",
                            "filename": "trait-star-001.png",
                            "rarity_weight": 50,
                            "color_code": "#FFD700",
                            "description": "A shining golden star"
                        },
                        {
                            "name": "Crystal Gem",
                            "filename": "trait-gem-002.png",
                            "rarity_weight": 25,
                            "color_code": "#E0E0E0"
                        }
                    ]
                }
            },
            "rarity": {
                "calculation_method": "weighted_random",
                "distribution_validation": True,
                "rarity_tiers": {
                    "common": {"min_weight": 75, "max_weight": 100},
                    "uncommon": {"min_weight": 50, "max_weight": 74},
                    "rare": {"min_weight": 25, "max_weight": 49}
                }
            },
            "validation": {
                "enforce_grid_positions": True,
                "require_all_positions": False,
                "check_file_integrity": True,
                "validate_image_dimensions": True
            }
        }
        
        config_path = self.collection_root / "config.json"
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def _create_trait_images(self):
        """Create trait image files"""
        trait_files = [
            ("position-1-background", "trait-sky-bg-001.png", (135, 206, 235)),
            ("position-1-background", "trait-forest-bg-002.png", (34, 139, 34)),
            ("position-5-center", "trait-star-001.png", (255, 215, 0)),
            ("position-5-center", "trait-gem-002.png", (224, 224, 224))
        ]
        
        for category, filename, color in trait_files:
            trait_dir = self.collection_root / "traits" / category
            trait_dir.mkdir(parents=True, exist_ok=True)
            
            # Create trait image
            img = Image.new('RGBA', (200, 200), (*color, 200))
            draw = ImageDraw.Draw(img)
            
            # Add some visual distinction
            if "star" in filename:
                # Draw a star-like shape
                draw.polygon([(100, 50), (120, 90), (160, 90), (130, 120), 
                             (140, 160), (100, 140), (60, 160), (70, 120), 
                             (40, 90), (80, 90)], fill=(*color, 255))
            elif "gem" in filename:
                # Draw a diamond shape
                draw.polygon([(100, 60), (140, 100), (100, 140), (60, 100)], 
                           fill=(*color, 255))
            
            img.save(trait_dir / filename, "PNG")
    
    def test_complete_metadata_workflow(self):
        """Test complete metadata management workflow"""
        # Step 1: Initial validation (should show missing metadata)
        initial_result = self.manager.validate_metadata_consistency()
        self.assertTrue(initial_result.is_valid)
        
        # Should have missing metadata notifications
        missing_issues = [issue for issue in initial_result.issues 
                         if issue.category == "missing_metadata"]
        self.assertTrue(len(missing_issues) > 0)
        
        # Step 2: Sync metadata from config to files
        sync_result = self.manager.sync_metadata(MetadataSyncMode.CONFIG_TO_FILES)
        self.assertTrue(sync_result.is_valid)
        
        # Verify metadata files were created
        bg_dir = self.collection_root / "traits" / "position-1-background"
        center_dir = self.collection_root / "traits" / "position-5-center"
        
        expected_files = [
            bg_dir / "trait-sky-bg-001.json",
            bg_dir / "trait-forest-bg-002.json",
            center_dir / "trait-star-001.json",
            center_dir / "trait-gem-002.json"
        ]
        
        for file_path in expected_files:
            self.assertTrue(file_path.exists(), f"Metadata file not created: {file_path}")
        
        # Step 3: Validate after sync (should be clean)
        post_sync_result = self.manager.validate_metadata_consistency()
        self.assertTrue(post_sync_result.is_valid)
        
        # Should have no missing metadata issues now
        missing_issues = [issue for issue in post_sync_result.issues 
                         if issue.category == "missing_metadata"]
        self.assertEqual(len(missing_issues), 0)
        
        # Step 4: Test metadata summary
        summary = self.manager.get_metadata_summary()
        self.assertIn("Integration Test Collection", summary)
        self.assertIn("**Metadata Files**: 4", summary)
        self.assertIn("✅", summary)  # Should show successful status
        
        # Step 5: Modify a metadata file and test conflict detection
        star_metadata_path = center_dir / "trait-star-001.json"
        with open(star_metadata_path, 'r') as f:
            metadata = json.load(f)
        
        # Change some properties to create conflicts
        metadata["name"] = "Modified Star Name"
        metadata["rarity_weight"] = 999
        metadata["color_code"] = "#123456"
        
        with open(star_metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Step 6: Validate with conflicts
        conflict_result = self.manager.validate_metadata_consistency()
        self.assertTrue(conflict_result.is_valid)  # Still valid, but has warnings
        
        # Should detect conflicts
        conflict_issues = [issue for issue in conflict_result.issues 
                          if issue.category == "metadata_conflict"]
        self.assertTrue(len(conflict_issues) > 0)
        
        # Step 7: Resolve conflicts with merge sync
        merge_result = self.manager.sync_metadata(MetadataSyncMode.MERGE_FAVOR_CONFIG)
        self.assertTrue(merge_result.is_valid)
        
        # Step 8: Final validation should be clean
        final_result = self.manager.validate_metadata_consistency()
        self.assertTrue(final_result.is_valid)
        
        conflict_issues = [issue for issue in final_result.issues 
                          if issue.category == "metadata_conflict"]
        self.assertEqual(len(conflict_issues), 0)


if __name__ == "__main__":
    unittest.main() 