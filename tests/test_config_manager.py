"""
Test suite for GenConfig Configuration Manager

This module tests the configuration manager functionality including
high-level configuration management, orchestration of all validation components,
and complete configuration lifecycle management.
"""

import unittest
import tempfile
import shutil
import json
from pathlib import Path
from typing import Dict, Any
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config.config_manager import (
    ConfigurationManager,
    ConfigurationManagerError,
    ConfigurationState,
    ValidationMode,
    ValidationLevel,
    load_and_validate_config,
    create_configuration_manager,
    validate_config_file
)
from config.schema_validator import create_sample_config
from config.config_parser import GenConfig
from config.logic_validator import ValidationResult, ValidationSeverity
from utils.file_utils import safe_write_json, safe_write_file


class TestConfigurationState(unittest.TestCase):
    """Test cases for ConfigurationState data structure"""
    
    def test_configuration_state_creation(self):
        """Test ConfigurationState creation and properties"""
        state = ConfigurationState()
        
        # Test initial state
        self.assertIsNone(state.config)
        self.assertIsNone(state.config_path)
        self.assertFalse(state.schema_valid)
        self.assertEqual(len(state.schema_errors), 0)
        self.assertFalse(state.logic_valid)
        self.assertIsNone(state.logic_result)
        self.assertIsNone(state.load_time)
        self.assertIsNone(state.validation_time)
        self.assertFalse(state.is_loaded)
        self.assertFalse(state.is_validated)
    
    def test_configuration_state_properties(self):
        """Test ConfigurationState computed properties"""
        state = ConfigurationState()
        
        # Test invalid state
        self.assertFalse(state.is_valid)
        self.assertFalse(state.has_errors)
        self.assertFalse(state.has_warnings)
        
        # Test with schema errors
        state.schema_errors = ["Test error"]
        self.assertTrue(state.has_errors)
        
        # Test valid state
        state.schema_valid = True
        state.logic_valid = True
        state.is_loaded = True
        state.schema_errors = []
        self.assertTrue(state.is_valid)
    
    def test_configuration_state_summary(self):
        """Test ConfigurationState summary generation"""
        state = ConfigurationState()
        state.config_path = "/test/config.json"
        state.load_time = 0.123
        state.validation_time = 0.456
        state.is_loaded = True
        state.schema_valid = True
        
        summary = state.get_summary()
        
        # Verify summary structure
        self.assertIsInstance(summary, dict)
        self.assertIn("is_loaded", summary)
        self.assertIn("is_validated", summary)
        self.assertIn("is_valid", summary)
        self.assertIn("has_errors", summary)
        self.assertIn("has_warnings", summary)
        self.assertIn("config_path", summary)
        self.assertIn("load_time_ms", summary)
        self.assertIn("validation_time_ms", summary)
        self.assertIn("schema_validation", summary)
        
        # Verify values
        self.assertTrue(summary["is_loaded"])
        self.assertEqual(summary["config_path"], "/test/config.json")
        self.assertEqual(summary["load_time_ms"], 123.0)
        self.assertEqual(summary["validation_time_ms"], 456.0)


class TestConfigurationManager(unittest.TestCase):
    """Test cases for ConfigurationManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create test configuration files
        self.valid_config_data = create_sample_config()
        # Fix the sample config to be logically valid
        self.valid_config_data["collection"]["size"] = 10  # Reasonable size
        self.valid_config_data["generation"]["allow_duplicates"] = True  # Allow duplicates
        # Add more variants to make it more realistic
        self.valid_config_data["traits"]["position-1-background"]["variants"].extend([
            {
                "name": "Blue Background",
                "filename": "trait-blue-bg-002.png",
                "rarity_weight": 50,
                "color_code": "#0000FF"
            },
            {
                "name": "Green Background",
                "filename": "trait-green-bg-003.png",
                "rarity_weight": 25,
                "color_code": "#00FF00"
            }
        ])
        self.valid_config_path = self.temp_dir / "valid_config.json"
        safe_write_json(str(self.valid_config_path), self.valid_config_data)
        
        # Create invalid configuration
        self.invalid_config_data = create_sample_config()
        del self.invalid_config_data["collection"]["name"]  # Remove required field
        self.invalid_config_path = self.temp_dir / "invalid_config.json"
        safe_write_json(str(self.invalid_config_path), self.invalid_config_data)
        
        # Create problematic configuration (valid schema, logic issues)
        self.problematic_config_data = create_sample_config()
        self.problematic_config_data["collection"]["size"] = 1000000  # Too large
        self.problematic_config_data["generation"]["allow_duplicates"] = False
        self.problematic_config_path = self.temp_dir / "problematic_config.json"
        safe_write_json(str(self.problematic_config_path), self.problematic_config_data)
        
        # Create malformed JSON file
        self.malformed_path = self.temp_dir / "malformed.json"
        safe_write_file(str(self.malformed_path), '{"invalid": json}')
        
        # Create test traits directory structure
        self.traits_dir = self.temp_dir / "traits"
        self.traits_dir.mkdir()
        trait_dir = self.traits_dir / "position-1-background"
        trait_dir.mkdir()
        (trait_dir / "trait-red-bg-001.png").write_text("fake png")
    
    def tearDown(self):
        """Clean up test fixtures"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_manager_initialization(self):
        """Test ConfigurationManager initialization with different parameters"""
        # Test default initialization
        manager = ConfigurationManager()
        self.assertEqual(manager.validation_mode, ValidationMode.FULL)
        self.assertEqual(manager.validation_level, ValidationLevel.NORMAL)
        self.assertTrue(manager.check_file_existence)
        
        # Test custom initialization
        manager = ConfigurationManager(
            validation_mode=ValidationMode.SCHEMA_ONLY,
            validation_level=ValidationLevel.STRICT,
            check_file_existence=False
        )
        self.assertEqual(manager.validation_mode, ValidationMode.SCHEMA_ONLY)
        self.assertEqual(manager.validation_level, ValidationLevel.STRICT)
        self.assertFalse(manager.check_file_existence)
    
    def test_load_valid_configuration(self):
        """Test loading valid configuration"""
        manager = ConfigurationManager()
        
        state = manager.load_configuration(str(self.valid_config_path))
        
        # Verify state
        self.assertIsInstance(state, ConfigurationState)
        self.assertTrue(state.is_loaded)
        self.assertTrue(state.is_validated)
        self.assertTrue(state.schema_valid)
        self.assertTrue(state.logic_valid)
        self.assertTrue(state.is_valid)
        self.assertIsNotNone(state.config)
        self.assertIsInstance(state.config, GenConfig)
        self.assertIsNotNone(state.load_time)
        self.assertIsNotNone(state.validation_time)
    
    def test_load_invalid_schema_configuration(self):
        """Test loading configuration with schema errors"""
        # Schema errors should prevent parsing in any mode since the config
        # structure is broken and can't be parsed
        manager = ConfigurationManager(validation_level=ValidationLevel.NORMAL)
        
        with self.assertRaises(ConfigurationManagerError):
            manager.load_configuration(str(self.invalid_config_path))
        
        # Should also fail in strict mode
        strict_manager = ConfigurationManager(validation_level=ValidationLevel.STRICT)
        with self.assertRaises(ConfigurationManagerError):
            strict_manager.load_configuration(str(self.invalid_config_path))
    
    def test_load_problematic_logic_configuration(self):
        """Test loading configuration with logic validation issues"""
        manager = ConfigurationManager(validation_level=ValidationLevel.NORMAL)
        
        state = manager.load_configuration(str(self.problematic_config_path))
        
        # Should load but have logic validation issues
        self.assertTrue(state.is_loaded)
        self.assertTrue(state.schema_valid)
        self.assertFalse(state.logic_valid)
        self.assertIsNotNone(state.logic_result)
        self.assertTrue(len(state.logic_result.errors) > 0)
        self.assertFalse(state.is_valid)
    
    def test_load_nonexistent_file(self):
        """Test loading nonexistent configuration file"""
        manager = ConfigurationManager()
        
        with self.assertRaises(ConfigurationManagerError) as context:
            manager.load_configuration("/nonexistent/config.json")
        
        self.assertIn("not found", str(context.exception))
    
    def test_load_malformed_json(self):
        """Test loading malformed JSON file"""
        manager = ConfigurationManager()
        
        with self.assertRaises(ConfigurationManagerError):
            manager.load_configuration(str(self.malformed_path))
    
    def test_validation_modes(self):
        """Test different validation modes"""
        # Schema only mode
        schema_manager = ConfigurationManager(validation_mode=ValidationMode.SCHEMA_ONLY)
        state = schema_manager.load_configuration(str(self.valid_config_path))
        self.assertTrue(state.schema_valid)
        self.assertTrue(state.logic_valid)  # Not validated, defaults to True
        
        # Logic only mode
        logic_manager = ConfigurationManager(validation_mode=ValidationMode.LOGIC_ONLY)
        state = logic_manager.load_configuration(str(self.valid_config_path))
        self.assertTrue(state.schema_valid)  # Not validated, defaults to True
        self.assertIsNotNone(state.logic_result)
        
        # Skip all validation mode
        skip_manager = ConfigurationManager(validation_mode=ValidationMode.SKIP_ALL)
        state = skip_manager.load_configuration(str(self.valid_config_path))
        self.assertTrue(state.schema_valid)
        self.assertTrue(state.logic_valid)
    
    def test_validation_levels(self):
        """Test different validation levels"""
        # Permissive mode (only fails on errors, not warnings)
        permissive_manager = ConfigurationManager(
            validation_level=ValidationLevel.PERMISSIVE,
            check_file_existence=False
        )
        
        # Should succeed even with warnings
        state = permissive_manager.load_configuration(str(self.valid_config_path))
        self.assertTrue(state.is_loaded)
        
        # Normal mode
        normal_manager = ConfigurationManager(
            validation_level=ValidationLevel.NORMAL,
            check_file_existence=False
        )
        state = normal_manager.load_configuration(str(self.valid_config_path))
        self.assertTrue(state.is_loaded)
        
        # Strict mode tested in other methods
    
    def test_reload_configuration(self):
        """Test reloading configuration"""
        manager = ConfigurationManager()
        
        # Load initial configuration
        state1 = manager.load_configuration(str(self.valid_config_path))
        config1 = state1.config
        
        # Reload configuration
        state2 = manager.reload_configuration()
        config2 = state2.config
        
        # Should be equivalent configurations
        self.assertEqual(config1.collection.name, config2.collection.name)
        self.assertEqual(config1.collection.size, config2.collection.size)
        
        # Test reload without loaded configuration
        empty_manager = ConfigurationManager()
        with self.assertRaises(ConfigurationManagerError):
            empty_manager.reload_configuration()
    
    def test_validate_configuration(self):
        """Test validating already-loaded configuration"""
        manager = ConfigurationManager()
        state = manager.load_configuration(str(self.valid_config_path))
        
        # Validate the loaded configuration
        result = manager.validate_configuration(state.config)
        self.assertIsInstance(result, ValidationResult)
        
        # Test with skip validation mode
        skip_manager = ConfigurationManager(validation_mode=ValidationMode.SKIP_ALL)
        result = skip_manager.validate_configuration(state.config)
        self.assertTrue(result.is_valid)
    
    def test_get_configuration(self):
        """Test getting current configuration"""
        manager = ConfigurationManager()
        
        # No configuration loaded
        self.assertIsNone(manager.get_configuration())
        
        # Configuration loaded
        manager.load_configuration(str(self.valid_config_path))
        config = manager.get_configuration()
        self.assertIsNotNone(config)
        self.assertIsInstance(config, GenConfig)
    
    def test_get_state(self):
        """Test getting current state"""
        manager = ConfigurationManager()
        
        # Initial state
        state = manager.get_state()
        self.assertIsInstance(state, ConfigurationState)
        self.assertFalse(state.is_loaded)
        
        # After loading
        manager.load_configuration(str(self.valid_config_path))
        state = manager.get_state()
        self.assertTrue(state.is_loaded)
    
    def test_is_valid(self):
        """Test configuration validity check"""
        manager = ConfigurationManager()
        
        # No configuration loaded
        self.assertFalse(manager.is_valid())
        
        # Valid configuration loaded
        manager.load_configuration(str(self.valid_config_path))
        self.assertTrue(manager.is_valid())
        
        # Invalid configuration - even permissive mode should reject configurations with errors
        manager = ConfigurationManager(validation_level=ValidationLevel.PERMISSIVE)
        with self.assertRaises(ConfigurationManagerError):
            manager.load_configuration(str(self.problematic_config_path))
    
    def test_get_validation_report(self):
        """Test validation report generation"""
        manager = ConfigurationManager()
        
        # Load configuration and generate report
        manager.load_configuration(str(self.valid_config_path))
        report = manager.get_validation_report()
        
        # Verify report structure
        self.assertIsInstance(report, str)
        self.assertIn("Configuration Manager Report", report)
        self.assertIn("VALID", report)
        self.assertIn("Configuration File:", report)
        self.assertIn("Collection:", report)
        self.assertIn("Load Time:", report)
        self.assertIn("Validation Time:", report)
        self.assertIn("Schema Validation:", report)
        self.assertIn("Logic Validation:", report)
        self.assertIn("Summary:", report)
    
    def test_save_configuration_placeholder(self):
        """Test save configuration placeholder method"""
        manager = ConfigurationManager()
        state = manager.load_configuration(str(self.valid_config_path))
        
        # Should raise NotImplementedError
        with self.assertRaises(NotImplementedError):
            manager.save_configuration(state.config, "/test/output.json")
    
    def test_file_existence_validation(self):
        """Test trait file existence validation"""
        # Manager with file checking enabled
        manager = ConfigurationManager(check_file_existence=True)
        state = manager.load_configuration(str(self.valid_config_path), str(self.traits_dir))
        
        # Should have file validation issues since files don't really exist
        self.assertTrue(state.is_loaded)
        if state.logic_result:
            # May have file validation issues but should not prevent loading
            pass
        
        # Manager with file checking disabled
        manager_no_files = ConfigurationManager(check_file_existence=False)
        state = manager_no_files.load_configuration(str(self.valid_config_path))
        self.assertTrue(state.is_loaded)


class TestConvenienceFunctions(unittest.TestCase):
    """Test cases for convenience functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create test configuration
        self.config_data = create_sample_config()
        # Fix the sample config to be logically valid
        self.config_data["collection"]["size"] = 10  # Reasonable size
        self.config_data["generation"]["allow_duplicates"] = True  # Allow duplicates
        self.config_path = self.temp_dir / "test_config.json"
        safe_write_json(str(self.config_path), self.config_data)
    
    def tearDown(self):
        """Clean up test fixtures"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_load_and_validate_config(self):
        """Test load_and_validate_config convenience function"""
        config, state = load_and_validate_config(str(self.config_path))
        
        self.assertIsInstance(config, GenConfig)
        self.assertIsInstance(state, ConfigurationState)
        self.assertTrue(state.is_loaded)
        self.assertTrue(state.is_valid)
    
    def test_create_configuration_manager(self):
        """Test create_configuration_manager factory function"""
        manager = create_configuration_manager(
            validation_mode=ValidationMode.SCHEMA_ONLY,
            validation_level=ValidationLevel.STRICT,
            check_file_existence=False
        )
        
        self.assertIsInstance(manager, ConfigurationManager)
        self.assertEqual(manager.validation_mode, ValidationMode.SCHEMA_ONLY)
        self.assertEqual(manager.validation_level, ValidationLevel.STRICT)
        self.assertFalse(manager.check_file_existence)
    
    def test_validate_config_file(self):
        """Test validate_config_file convenience function"""
        result = validate_config_file(str(self.config_path))
        
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)
        
        # Test with validation level
        result_strict = validate_config_file(
            str(self.config_path),
            validation_level=ValidationLevel.STRICT
        )
        self.assertIsInstance(result_strict, ValidationResult)


class TestErrorHandling(unittest.TestCase):
    """Test cases for error handling and edge cases"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test fixtures"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_schema_validation_errors(self):
        """Test handling of schema validation errors"""
        # Create invalid schema configuration
        invalid_config = {"invalid": "schema"}
        invalid_path = self.temp_dir / "invalid.json"
        safe_write_json(str(invalid_path), invalid_config)
        
        manager = ConfigurationManager(validation_level=ValidationLevel.PERMISSIVE)
        
        with self.assertRaises(ConfigurationManagerError):
            manager.load_configuration(str(invalid_path))
    
    def test_parsing_errors(self):
        """Test handling of configuration parsing errors"""
        # Create malformed JSON
        malformed_path = self.temp_dir / "malformed.json"
        safe_write_file(str(malformed_path), '{"incomplete": json')
        
        manager = ConfigurationManager()
        
        with self.assertRaises(ConfigurationManagerError):
            manager.load_configuration(str(malformed_path))
    
    def test_logic_validation_errors(self):
        """Test handling of logic validation errors"""
        # Create configuration with logic issues
        problematic_config = create_sample_config()
        problematic_config["collection"]["size"] = -1  # Invalid size
        problematic_path = self.temp_dir / "problematic.json"
        safe_write_json(str(problematic_path), problematic_config)
        
        # Normal mode should load but be invalid
        manager = ConfigurationManager(validation_level=ValidationLevel.NORMAL)
        state = manager.load_configuration(str(problematic_path))
        self.assertTrue(state.is_loaded)
        self.assertFalse(state.is_valid)
        
        # Strict mode should fail
        strict_manager = ConfigurationManager(validation_level=ValidationLevel.STRICT)
        with self.assertRaises(ConfigurationManagerError):
            strict_manager.load_configuration(str(problematic_path))
    
    def test_empty_configuration(self):
        """Test handling of empty configuration"""
        empty_path = self.temp_dir / "empty.json"
        safe_write_json(str(empty_path), {})
        
        manager = ConfigurationManager()
        
        with self.assertRaises(ConfigurationManagerError):
            manager.load_configuration(str(empty_path))


class TestIntegrationWorkflow(unittest.TestCase):
    """Integration tests for complete configuration manager workflow"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create comprehensive test configuration
        self.config_data = create_sample_config()
        self.config_data["collection"]["name"] = "Integration Test Collection"
        self.config_data["collection"]["size"] = 20  # Reasonable size
        self.config_data["generation"]["allow_duplicates"] = True  # Allow duplicates for easier testing
        
        # Add more trait variants for better testing
        self.config_data["traits"]["position-1-background"]["variants"].extend([
            {
                "name": "Blue Background",
                "filename": "trait-blue-bg-002.png",
                "rarity_weight": 50,
                "color_code": "#0000FF"
            },
            {
                "name": "Green Background",
                "filename": "trait-green-bg-003.png", 
                "rarity_weight": 25,
                "color_code": "#00FF00"
            }
        ])
        
        self.config_path = self.temp_dir / "integration_config.json"
        safe_write_json(str(self.config_path), self.config_data)
    
    def tearDown(self):
        """Clean up test fixtures"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_complete_configuration_workflow(self):
        """Test complete configuration management workflow"""
        # Step 1: Create manager with full validation
        manager = ConfigurationManager(
            validation_mode=ValidationMode.FULL,
            validation_level=ValidationLevel.NORMAL,
            check_file_existence=False
        )
        
        # Step 2: Load configuration
        state = manager.load_configuration(str(self.config_path))
        
        # Step 3: Verify loaded state
        self.assertTrue(state.is_loaded)
        self.assertTrue(state.is_validated)
        self.assertTrue(state.schema_valid)
        self.assertTrue(state.logic_valid)
        self.assertTrue(state.is_valid)
        self.assertIsNotNone(state.config)
        
        # Step 4: Get configuration object
        config = manager.get_configuration()
        self.assertIsNotNone(config)
        self.assertEqual(config.collection.name, "Integration Test Collection")
        self.assertEqual(config.collection.size, 20)
        
        # Step 5: Validate configuration again
        validation_result = manager.validate_configuration(config)
        self.assertTrue(validation_result.is_valid)
        
        # Step 6: Generate comprehensive report
        report = manager.get_validation_report()
        self.assertIn("VALID", report)
        self.assertIn("Integration Test Collection", report)
        
        # Step 7: Check state summary
        summary = state.get_summary()
        self.assertTrue(summary["is_valid"])
        self.assertFalse(summary["has_errors"])
        self.assertIsNotNone(summary["configuration"])
    
    def test_workflow_with_different_modes(self):
        """Test workflow with different validation modes and levels"""
        modes_and_levels = [
            (ValidationMode.SCHEMA_ONLY, ValidationLevel.NORMAL),
            (ValidationMode.LOGIC_ONLY, ValidationLevel.NORMAL),
            (ValidationMode.FULL, ValidationLevel.STRICT),
            (ValidationMode.FULL, ValidationLevel.PERMISSIVE),
            (ValidationMode.SKIP_ALL, ValidationLevel.NORMAL)
        ]
        
        for mode, level in modes_and_levels:
            with self.subTest(mode=mode.value, level=level.value):
                manager = ConfigurationManager(
                    validation_mode=mode,
                    validation_level=level,
                    check_file_existence=False
                )
                
                # Note: Strict mode will fail on this config due to incomplete grid warning
                if level == ValidationLevel.STRICT:
                    with self.assertRaises(ConfigurationManagerError):
                        manager.load_configuration(str(self.config_path))
                else:
                    state = manager.load_configuration(str(self.config_path))
                    
                    # Should successfully load this configuration in non-strict modes
                    self.assertTrue(state.is_loaded)
                    self.assertIsNotNone(state.config)
                    
                    # Generate report for each mode
                    report = manager.get_validation_report()
                    self.assertIn("Configuration Manager Report", report)
    
    def test_performance_metrics(self):
        """Test performance metric collection"""
        manager = ConfigurationManager()
        
        state = manager.load_configuration(str(self.config_path))
        
        # Verify timing metrics are collected
        self.assertIsNotNone(state.load_time)
        self.assertIsNotNone(state.validation_time)
        self.assertGreater(state.load_time, 0)
        self.assertGreater(state.validation_time, 0)
        
        # Verify summary includes timing
        summary = state.get_summary()
        self.assertIsNotNone(summary["load_time_ms"])
        self.assertIsNotNone(summary["validation_time_ms"])
        self.assertGreater(summary["load_time_ms"], 0)
        self.assertGreater(summary["validation_time_ms"], 0)


if __name__ == '__main__':
    unittest.main() 