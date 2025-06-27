"""
Test suite for GenConfig Configuration Parser

This module tests the configuration parser functionality including loading,
parsing, validation, and data structure creation.
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config.config_parser import (
    ConfigurationParser,
    GenConfig,
    CollectionConfig,
    GenerationConfig,
    TraitCategory,
    RarityConfig,
    ValidationConfig,
    ConfigParseError,
    load_config,
    parse_config_dict,
    create_config_summary
)
from config.schema_validator import create_sample_config, SchemaValidationError
from utils.file_utils import safe_write_json


class TestConfigurationParser(unittest.TestCase):
    """Test cases for ConfigurationParser class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.parser = ConfigurationParser(validate_schema=True)
        self.parser_no_validation = ConfigurationParser(validate_schema=False)
        
        # Create sample valid configuration
        self.valid_config_data = create_sample_config()
        self.valid_config_path = self.temp_dir / "valid_config.json"
        safe_write_json(str(self.valid_config_path), self.valid_config_data)
        
        # Create invalid configuration for testing
        self.invalid_config_data = {
            "collection": {
                "name": "Test Collection",
                "description": "Test Description",
                "size": "invalid_size",  # Should be integer
                "symbol": "TEST",
                "external_url": "https://example.com"
            }
            # Missing required sections
        }
        self.invalid_config_path = self.temp_dir / "invalid_config.json"
        safe_write_json(str(self.invalid_config_path), self.invalid_config_data)
    
    def tearDown(self):
        """Clean up test fixtures"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_parser_initialization(self):
        """Test ConfigurationParser initialization"""
        # Test with validation enabled
        parser_with_validation = ConfigurationParser(validate_schema=True)
        self.assertTrue(parser_with_validation.validate_schema)
        
        # Test with validation disabled
        parser_without_validation = ConfigurationParser(validate_schema=False)
        self.assertFalse(parser_without_validation.validate_schema)
        
        # Test default initialization
        default_parser = ConfigurationParser()
        self.assertTrue(default_parser.validate_schema)
    
    def test_parse_valid_config_file(self):
        """Test parsing valid configuration file"""
        config = self.parser.parse_config_file(str(self.valid_config_path))
        
        # Verify return type
        self.assertIsInstance(config, GenConfig)
        
        # Verify config path was set
        self.assertEqual(config.config_path, str(self.valid_config_path.resolve()))
        
        # Verify collection data
        self.assertIsInstance(config.collection, CollectionConfig)
        self.assertEqual(config.collection.name, "Sample NFT Collection")
        self.assertEqual(config.collection.size, 1000)
        self.assertEqual(config.collection.symbol, "SAMPLE")
        
        # Verify generation data
        self.assertIsInstance(config.generation, GenerationConfig)
        self.assertEqual(config.generation.image_format, "PNG")
        self.assertEqual(config.generation.image_size.width, 600)
        self.assertEqual(config.generation.image_size.height, 600)
        self.assertEqual(config.generation.grid.rows, 3)
        self.assertEqual(config.generation.grid.columns, 3)
        
        # Verify traits data
        self.assertIsInstance(config.traits, dict)
        self.assertTrue(len(config.traits) > 0)
        
        # Verify at least one trait category
        first_trait = next(iter(config.traits.values()))
        self.assertIsInstance(first_trait, TraitCategory)
        self.assertTrue(len(first_trait.variants) > 0)
        
        # Verify rarity data
        self.assertIsInstance(config.rarity, RarityConfig)
        self.assertEqual(config.rarity.calculation_method, "weighted_random")
        
        # Verify validation data
        self.assertIsInstance(config.validation, ValidationConfig)
    
    def test_parse_config_data_directly(self):
        """Test parsing configuration data dictionary directly"""
        config = self.parser.parse_config_data(self.valid_config_data)
        
        # Verify return type
        self.assertIsInstance(config, GenConfig)
        
        # Config path should not be set when parsing data directly
        self.assertIsNone(config.config_path)
        
        # Verify basic structure
        self.assertIsInstance(config.collection, CollectionConfig)
        self.assertIsInstance(config.generation, GenerationConfig)
        self.assertIsInstance(config.traits, dict)
        self.assertIsInstance(config.rarity, RarityConfig)
        self.assertIsInstance(config.validation, ValidationConfig)
    
    def test_parse_invalid_config_with_validation(self):
        """Test parsing invalid configuration with schema validation enabled"""
        with self.assertRaises(SchemaValidationError):
            self.parser.parse_config_file(str(self.invalid_config_path))
    
    def test_parse_invalid_config_without_validation(self):
        """Test parsing invalid configuration with schema validation disabled"""
        with self.assertRaises(ConfigParseError):
            self.parser_no_validation.parse_config_file(str(self.invalid_config_path))
    
    def test_parse_nonexistent_file(self):
        """Test parsing non-existent configuration file"""
        nonexistent_path = self.temp_dir / "nonexistent.json"
        
        with self.assertRaises(ConfigParseError):
            self.parser.parse_config_file(str(nonexistent_path))
    
    def test_parse_malformed_json(self):
        """Test parsing malformed JSON file"""
        malformed_path = self.temp_dir / "malformed.json"
        with open(malformed_path, 'w') as f:
            f.write("{ invalid json content")
        
        with self.assertRaises(ConfigParseError):
            self.parser.parse_config_file(str(malformed_path))
    
    def test_gen_config_helper_methods(self):
        """Test GenConfig helper methods"""
        config = self.parser.parse_config_data(self.valid_config_data)
        
        # Test get_trait_by_position
        trait_position_1 = config.get_trait_by_position(1)
        if trait_position_1:
            self.assertEqual(trait_position_1.grid_position.row, 0)
            self.assertEqual(trait_position_1.grid_position.column, 0)
        
        # Test get_all_positions
        positions = config.get_all_positions()
        self.assertIsInstance(positions, list)
        self.assertTrue(all(isinstance(p, int) for p in positions))
        self.assertTrue(all(1 <= p <= 9 for p in positions))
        
        # Test is_complete_grid
        is_complete = config.is_complete_grid()
        self.assertIsInstance(is_complete, bool)
        
        # Test get_trait_counts
        trait_counts = config.get_trait_counts()
        self.assertIsInstance(trait_counts, dict)
        self.assertTrue(all(isinstance(count, int) for count in trait_counts.values()))
    
    def test_trait_variant_parsing(self):
        """Test parsing of trait variants with optional fields"""
        config = self.parser.parse_config_data(self.valid_config_data)
        
        # Find a trait with variants
        trait_category = next(iter(config.traits.values()))
        variant = trait_category.variants[0]
        
        # Verify required fields
        self.assertIsInstance(variant.name, str)
        self.assertIsInstance(variant.filename, str)
        self.assertIsInstance(variant.rarity_weight, int)
        
        # Optional fields may be None
        if variant.color_code is not None:
            self.assertIsInstance(variant.color_code, str)
        if variant.description is not None:
            self.assertIsInstance(variant.description, str)
    
    def test_rarity_tier_parsing(self):
        """Test parsing of rarity tier configuration"""
        config = self.parser.parse_config_data(self.valid_config_data)
        
        # Verify rarity tiers
        rarity_tiers = config.rarity.rarity_tiers
        self.assertIsInstance(rarity_tiers, dict)
        self.assertTrue(len(rarity_tiers) > 0)
        
        # Verify tier structure
        for tier_name, tier in rarity_tiers.items():
            self.assertIsInstance(tier_name, str)
            self.assertIsInstance(tier.min_weight, int)
            self.assertIsInstance(tier.max_weight, int)
            self.assertLessEqual(tier.min_weight, tier.max_weight)
    
    def test_grid_position_calculations(self):
        """Test grid position calculations and mappings"""
        config = self.parser.parse_config_data(self.valid_config_data)
        
        # Test position calculations
        for trait_key, trait in config.traits.items():
            row = trait.grid_position.row
            col = trait.grid_position.column
            
            # Verify valid grid coordinates
            self.assertIn(row, [0, 1, 2])
            self.assertIn(col, [0, 1, 2])
            
            # Verify position calculation
            calculated_position = row * 3 + col + 1
            self.assertIn(calculated_position, range(1, 10))


class TestConvenienceFunctions(unittest.TestCase):
    """Test cases for convenience functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.valid_config_data = create_sample_config()
        self.valid_config_path = self.temp_dir / "valid_config.json" 
        safe_write_json(str(self.valid_config_path), self.valid_config_data)
    
    def tearDown(self):
        """Clean up test fixtures"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_load_config_function(self):
        """Test load_config convenience function"""
        # Test with validation (default)
        config = load_config(str(self.valid_config_path))
        self.assertIsInstance(config, GenConfig)
        self.assertEqual(config.config_path, str(self.valid_config_path.resolve()))
        
        # Test without validation
        config_no_validation = load_config(str(self.valid_config_path), validate_schema=False)
        self.assertIsInstance(config_no_validation, GenConfig)
    
    def test_parse_config_dict_function(self):
        """Test parse_config_dict convenience function"""
        config = parse_config_dict(self.valid_config_data)
        self.assertIsInstance(config, GenConfig)
        self.assertIsNone(config.config_path)  # Should not be set for dictionary parsing
    
    def test_create_config_summary_function(self):
        """Test create_config_summary function"""
        config = parse_config_dict(self.valid_config_data)
        summary = create_config_summary(config)
        
        # Verify summary structure
        self.assertIsInstance(summary, dict)
        
        # Verify required keys
        required_keys = [
            "collection_name", "collection_size", "image_dimensions",
            "grid_dimensions", "cell_size", "trait_categories",
            "total_variants", "positions_used", "complete_grid",
            "rarity_calculation", "rarity_tiers", "validation_enabled"
        ]
        for key in required_keys:
            self.assertIn(key, summary)
        
        # Verify data types
        self.assertIsInstance(summary["collection_name"], str)
        self.assertIsInstance(summary["collection_size"], int)
        self.assertIsInstance(summary["trait_categories"], int)
        self.assertIsInstance(summary["total_variants"], int)
        self.assertIsInstance(summary["positions_used"], list)
        self.assertIsInstance(summary["complete_grid"], bool)
        self.assertIsInstance(summary["rarity_tiers"], list)
        self.assertIsInstance(summary["validation_enabled"], dict)


class TestDataStructures(unittest.TestCase):
    """Test cases for data structure classes"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.valid_config_data = create_sample_config()
        self.parser = ConfigurationParser(validate_schema=False)
    
    def test_collection_config_structure(self):
        """Test CollectionConfig data structure"""
        config = self.parser.parse_config_data(self.valid_config_data)
        collection = config.collection
        
        # Verify all required fields
        self.assertTrue(hasattr(collection, 'name'))
        self.assertTrue(hasattr(collection, 'description'))
        self.assertTrue(hasattr(collection, 'size'))
        self.assertTrue(hasattr(collection, 'symbol'))
        self.assertTrue(hasattr(collection, 'external_url'))
        
        # Verify data types
        self.assertIsInstance(collection.name, str)
        self.assertIsInstance(collection.description, str)
        self.assertIsInstance(collection.size, int)
        self.assertIsInstance(collection.symbol, str)
        self.assertIsInstance(collection.external_url, str)
    
    def test_generation_config_structure(self):
        """Test GenerationConfig data structure"""
        config = self.parser.parse_config_data(self.valid_config_data)
        generation = config.generation
        
        # Verify all required fields
        self.assertTrue(hasattr(generation, 'image_format'))
        self.assertTrue(hasattr(generation, 'image_size'))
        self.assertTrue(hasattr(generation, 'grid'))
        self.assertTrue(hasattr(generation, 'background_color'))
        self.assertTrue(hasattr(generation, 'allow_duplicates'))
        
        # Verify nested structures
        self.assertTrue(hasattr(generation.image_size, 'width'))
        self.assertTrue(hasattr(generation.image_size, 'height'))
        self.assertTrue(hasattr(generation.grid, 'rows'))
        self.assertTrue(hasattr(generation.grid, 'columns'))
        self.assertTrue(hasattr(generation.grid, 'cell_size'))
        self.assertTrue(hasattr(generation.grid.cell_size, 'width'))
        self.assertTrue(hasattr(generation.grid.cell_size, 'height'))
    
    def test_trait_category_structure(self):
        """Test TraitCategory data structure"""
        config = self.parser.parse_config_data(self.valid_config_data)
        
        # Get first trait category
        trait = next(iter(config.traits.values()))
        
        # Verify all required fields
        self.assertTrue(hasattr(trait, 'name'))
        self.assertTrue(hasattr(trait, 'required'))
        self.assertTrue(hasattr(trait, 'grid_position'))
        self.assertTrue(hasattr(trait, 'variants'))
        
        # Verify grid position structure
        self.assertTrue(hasattr(trait.grid_position, 'row'))
        self.assertTrue(hasattr(trait.grid_position, 'column'))
        
        # Verify variants list
        self.assertIsInstance(trait.variants, list)
        self.assertTrue(len(trait.variants) > 0)
        
        # Verify variant structure
        variant = trait.variants[0]
        self.assertTrue(hasattr(variant, 'name'))
        self.assertTrue(hasattr(variant, 'filename'))
        self.assertTrue(hasattr(variant, 'rarity_weight'))
        self.assertTrue(hasattr(variant, 'color_code'))
        self.assertTrue(hasattr(variant, 'description'))


class TestEdgeCases(unittest.TestCase):
    """Test cases for edge cases and error conditions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.parser = ConfigurationParser(validate_schema=False)
    
    def tearDown(self):
        """Clean up test fixtures"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_empty_config_data(self):
        """Test parsing empty configuration data"""
        with self.assertRaises(ConfigParseError):
            self.parser.parse_config_data({})
    
    def test_missing_required_sections(self):
        """Test parsing configuration with missing required sections"""
        incomplete_config = {
            "collection": {
                "name": "Test",
                "description": "Test",
                "size": 100,
                "symbol": "TEST",
                "external_url": "https://example.com"
            }
            # Missing generation, traits, rarity, validation sections
        }
        
        with self.assertRaises(ConfigParseError):
            self.parser.parse_config_data(incomplete_config)
    
    def test_invalid_trait_structure(self):
        """Test parsing configuration with invalid trait structure"""
        invalid_config = create_sample_config()
        
        # Corrupt a trait entry
        first_trait_key = next(iter(invalid_config["traits"].keys()))
        del invalid_config["traits"][first_trait_key]["variants"]  # Remove required field
        
        with self.assertRaises(ConfigParseError):
            self.parser.parse_config_data(invalid_config)
    
    def test_zero_trait_categories(self):
        """Test configuration with no trait categories"""
        config_data = create_sample_config()
        config_data["traits"] = {}  # Empty traits section
        
        config = self.parser.parse_config_data(config_data)
        self.assertEqual(len(config.traits), 0)
        self.assertFalse(config.is_complete_grid())
        self.assertEqual(config.get_all_positions(), [])
    
    def test_single_trait_category(self):
        """Test configuration with single trait category"""
        config_data = create_sample_config()
        
        # Keep only first trait
        first_trait_key = next(iter(config_data["traits"].keys()))
        config_data["traits"] = {
            first_trait_key: config_data["traits"][first_trait_key]
        }
        
        config = self.parser.parse_config_data(config_data)
        self.assertEqual(len(config.traits), 1)
        self.assertFalse(config.is_complete_grid())  # Need all 9 positions
        self.assertEqual(len(config.get_all_positions()), 1)


class TestIntegrationWorkflow(unittest.TestCase):
    """Integration tests for complete parser workflow"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_data = create_sample_config()
        self.config_path = self.temp_dir / "integration_config.json"
        safe_write_json(str(self.config_path), self.config_data)
    
    def tearDown(self):
        """Clean up test fixtures"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_complete_parsing_workflow(self):
        """Test complete configuration parsing workflow"""
        # Step 1: Load configuration with validation
        config = load_config(str(self.config_path), validate_schema=True)
        
        # Step 2: Verify structure is complete
        self.assertIsInstance(config, GenConfig)
        self.assertTrue(len(config.traits) > 0)
        
        # Step 3: Create summary
        summary = create_config_summary(config)
        self.assertIsInstance(summary, dict)
        
        # Step 4: Test helper methods
        positions = config.get_all_positions()
        trait_counts = config.get_trait_counts()
        
        # Step 5: Verify data consistency
        self.assertEqual(len(positions), len(config.traits))
        self.assertEqual(len(trait_counts), len(config.traits))
        
        # Step 6: Test position lookups
        for position in positions:
            trait = config.get_trait_by_position(position)
            self.assertIsNotNone(trait)
    
    def test_parser_error_handling(self):
        """Test parser error handling across different scenarios"""
        parser = ConfigurationParser(validate_schema=True)
        
        # Test 1: Non-existent file
        with self.assertRaises(ConfigParseError):
            parser.parse_config_file("/nonexistent/path/config.json")
        
        # Test 2: Invalid JSON
        invalid_json_path = self.temp_dir / "invalid.json"
        with open(invalid_json_path, 'w') as f:
            f.write("{ invalid: json }")
        
        with self.assertRaises(ConfigParseError):
            parser.parse_config_file(str(invalid_json_path))
        
        # Test 3: Schema validation failure (actual schema issues)
        invalid_config = {"invalid": "structure"}
        invalid_config_path = self.temp_dir / "invalid_schema.json"
        safe_write_json(str(invalid_config_path), invalid_config)
        
        with self.assertRaises(SchemaValidationError):
            parser.parse_config_file(str(invalid_config_path))


if __name__ == '__main__':
    unittest.main() 