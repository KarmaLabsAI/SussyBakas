"""
Test suite for GenConfig Schema Validation Suite

Tests the comprehensive validation system that coordinates all validation components
to ensure complete configuration validation per GenConfig specification.
"""

import unittest
import tempfile
import json
import os
from pathlib import Path
from PIL import Image
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from validation.schema_suite import (
    SchemaValidationSuite,
    ComprehensiveValidationResult,
    ValidationPhase,
    ValidationMode,
    PhaseResult,
    validate_config_comprehensive,
    get_comprehensive_validation_report
)
from config.logic_validator import ValidationSeverity


class TestSchemaValidationSuite(unittest.TestCase):
    """Test the SchemaValidationSuite class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_path = self.temp_dir / "config.json"
        self.traits_dir = self.temp_dir / "traits"
        
        # Create valid configuration
        self.valid_config = {
            "collection": {
                "name": "Test Collection",
                "description": "A test NFT collection",
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
                            "rarity_weight": 100
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
                            "filename": "trait-circle-center-001.png",
                            "rarity_weight": 50
                        }
                    ]
                }
            },
            "rarity": {
                "calculation_method": "weighted_random",
                "distribution_validation": True,
                "rarity_tiers": {
                    "common": {"min_weight": 50, "max_weight": 100},
                    "uncommon": {"min_weight": 25, "max_weight": 49},
                    "rare": {"min_weight": 10, "max_weight": 24},
                    "epic": {"min_weight": 5, "max_weight": 9},
                    "legendary": {"min_weight": 1, "max_weight": 4}
                }
            },
            "validation": {
                "enforce_grid_positions": True,
                "require_all_positions": False,
                "check_file_integrity": True,
                "validate_image_dimensions": True
            }
        }
        
        # Create test trait files
        self._create_test_trait_files()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def _create_test_trait_files(self):
        """Create test trait files"""
        # Create trait directories
        pos1_dir = self.traits_dir / "position-1-background"
        pos5_dir = self.traits_dir / "position-5-center"
        pos1_dir.mkdir(parents=True)
        pos5_dir.mkdir(parents=True)
        
        # Create 200x200 test images
        for dir_path, filename in [
            (pos1_dir, "trait-red-bg-001.png"),
            (pos5_dir, "trait-circle-center-001.png")
        ]:
            img = Image.new('RGBA', (200, 200), (255, 0, 0, 255))
            img.save(dir_path / filename)
    
    def _write_config(self, config_data):
        """Write config data to test file"""
        with open(self.config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def test_suite_initialization(self):
        """Test suite initialization with different modes"""
        # Test default mode
        suite = SchemaValidationSuite()
        self.assertEqual(suite.validation_mode, ValidationMode.STANDARD)
        
        # Test specific modes
        for mode in ValidationMode:
            suite = SchemaValidationSuite(mode)
            self.assertEqual(suite.validation_mode, mode)
            self.assertIsNotNone(suite.config_parser)
            self.assertIsNotNone(suite.logic_validator)
            self.assertIsNotNone(suite.trait_validator)
    
    def test_minimal_validation_mode(self):
        """Test minimal validation mode (schema only)"""
        self._write_config(self.valid_config)
        
        suite = SchemaValidationSuite(ValidationMode.MINIMAL)
        result = suite.validate_configuration(self.config_path)
        
        self.assertIsInstance(result, ComprehensiveValidationResult)
        self.assertEqual(result.validation_mode, ValidationMode.MINIMAL)
        self.assertIn(ValidationPhase.SCHEMA, result.phase_results)
        
        # Should only have schema phase
        self.assertEqual(len(result.phase_results), 1)
        self.assertTrue(result.overall_success)
    
    def test_standard_validation_mode(self):
        """Test standard validation mode (schema + logic)"""
        self._write_config(self.valid_config)
        
        suite = SchemaValidationSuite(ValidationMode.STANDARD)
        result = suite.validate_configuration(self.config_path)
        
        self.assertEqual(result.validation_mode, ValidationMode.STANDARD)
        self.assertIn(ValidationPhase.SCHEMA, result.phase_results)
        self.assertIn(ValidationPhase.PARSING, result.phase_results)
        self.assertIn(ValidationPhase.LOGIC, result.phase_results)
        
        # Should have schema, parsing, and logic phases
        self.assertGreaterEqual(len(result.phase_results), 3)
        self.assertTrue(result.overall_success)
    
    def test_comprehensive_validation_mode(self):
        """Test comprehensive validation mode (all phases)"""
        self._write_config(self.valid_config)
        
        suite = SchemaValidationSuite(ValidationMode.COMPREHENSIVE)
        result = suite.validate_configuration(self.config_path, self.traits_dir)
        
        self.assertEqual(result.validation_mode, ValidationMode.COMPREHENSIVE)
        self.assertIn(ValidationPhase.SCHEMA, result.phase_results)
        self.assertIn(ValidationPhase.PARSING, result.phase_results)
        self.assertIn(ValidationPhase.LOGIC, result.phase_results)
        self.assertIn(ValidationPhase.TRAITS, result.phase_results)
        self.assertIn(ValidationPhase.INTEGRATION, result.phase_results)
        
        # Should have all phases
        self.assertEqual(len(result.phase_results), 5)
    
    def test_strict_validation_mode(self):
        """Test strict validation mode (comprehensive with strict logic)"""
        self._write_config(self.valid_config)
        
        suite = SchemaValidationSuite(ValidationMode.STRICT)
        result = suite.validate_configuration(self.config_path, self.traits_dir)
        
        self.assertEqual(result.validation_mode, ValidationMode.STRICT)
        # Should have strict mode enabled in logic validator
        self.assertTrue(suite.logic_validator.strict_mode)
    
    def test_invalid_schema_handling(self):
        """Test handling of invalid schema"""
        invalid_config = {"invalid": "config"}
        self._write_config(invalid_config)
        
        suite = SchemaValidationSuite()
        result = suite.validate_configuration(self.config_path)
        
        self.assertFalse(result.overall_success)
        self.assertIn(ValidationPhase.SCHEMA, result.phase_results)
        self.assertFalse(result.phase_results[ValidationPhase.SCHEMA].success)
        self.assertGreater(len(result.errors), 0)
    
    def test_parsing_error_handling(self):
        """Test handling of parsing errors"""
        # Create invalid JSON
        with open(self.config_path, 'w') as f:
            f.write("{ invalid json }")
        
        suite = SchemaValidationSuite()
        result = suite.validate_configuration(self.config_path)
        
        self.assertFalse(result.overall_success)
        # Should fail at schema or parsing phase
        has_error = any(not phase_result.success for phase_result in result.phase_results.values())
        self.assertTrue(has_error)
    
    def test_logic_validation_errors(self):
        """Test logic validation error detection"""
        # Create config with logic errors (duplicate grid positions)
        invalid_config = self.valid_config.copy()
        invalid_config["traits"]["position-2-duplicate"] = {
            "name": "Duplicate",
            "required": True,
            "grid_position": {"row": 0, "column": 0},  # Same as position-1
            "variants": [
                {
                    "name": "Duplicate Trait",
                    "filename": "trait-duplicate-001.png",
                    "rarity_weight": 50
                }
            ]
        }
        self._write_config(invalid_config)
        
        suite = SchemaValidationSuite(ValidationMode.STANDARD)
        result = suite.validate_configuration(self.config_path)
        
        self.assertFalse(result.overall_success)
        self.assertIn(ValidationPhase.LOGIC, result.phase_results)
        logic_result = result.phase_results[ValidationPhase.LOGIC]
        self.assertFalse(logic_result.success)
        self.assertGreater(len(logic_result.issues), 0)
    
    def test_trait_file_validation(self):
        """Test trait file validation phase"""
        self._write_config(self.valid_config)
        
        suite = SchemaValidationSuite(ValidationMode.COMPREHENSIVE)
        result = suite.validate_configuration(self.config_path, self.traits_dir)
        
        self.assertIn(ValidationPhase.TRAITS, result.phase_results)
        traits_result = result.phase_results[ValidationPhase.TRAITS]
        
        # Should validate existing trait files
        self.assertIn("validated_files", traits_result.details)
        self.assertGreaterEqual(traits_result.details["validated_files"], 2)
    
    def test_integration_validation(self):
        """Test integration validation phase"""
        self._write_config(self.valid_config)
        
        suite = SchemaValidationSuite(ValidationMode.COMPREHENSIVE)
        result = suite.validate_configuration(self.config_path, self.traits_dir)
        
        self.assertIn(ValidationPhase.INTEGRATION, result.phase_results)
        integration_result = result.phase_results[ValidationPhase.INTEGRATION]
        
        # Should have integration checks
        self.assertIn("integration_checks", integration_result.details)
        checks = integration_result.details["integration_checks"]
        self.assertIn("dimension_consistency", checks)
        self.assertIn("rarity_distribution", checks)
    
    def test_phase_timing(self):
        """Test that phase timing is recorded"""
        self._write_config(self.valid_config)
        
        suite = SchemaValidationSuite()
        result = suite.validate_configuration(self.config_path)
        
        # Check that timing is recorded
        self.assertGreater(result.total_duration_ms, 0)
        
        for phase_result in result.phase_results.values():
            self.assertGreaterEqual(phase_result.duration_ms, 0)
    
    def test_result_properties(self):
        """Test ComprehensiveValidationResult properties"""
        self._write_config(self.valid_config)
        
        suite = SchemaValidationSuite()
        result = suite.validate_configuration(self.config_path)
        
        # Test property access
        all_issues = result.all_issues
        errors = result.errors
        warnings = result.warnings
        infos = result.infos
        
        self.assertIsInstance(all_issues, list)
        self.assertIsInstance(errors, list)
        self.assertIsInstance(warnings, list)
        self.assertIsInstance(infos, list)
        
        # Test summary
        summary = result.get_summary()
        self.assertIn("overall_success", summary)
        self.assertIn("validation_mode", summary)
        self.assertIn("total_duration_ms", summary)
        self.assertIn("phases_executed", summary)
        
        # Test phase summary
        if ValidationPhase.SCHEMA in result.phase_results:
            phase_summary = result.get_phase_summary(ValidationPhase.SCHEMA)
            self.assertIsNotNone(phase_summary)
            self.assertIn("phase", phase_summary)
            self.assertIn("success", phase_summary)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_path = self.temp_dir / "config.json"
        
        # Create minimal valid config
        valid_config = {
            "collection": {
                "name": "Test Collection",
                "description": "A test NFT collection",
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
                            "name": "Red Background",
                            "filename": "trait-red-bg-001.png",
                            "rarity_weight": 100
                        }
                    ]
                }
            },
            "rarity": {
                "calculation_method": "weighted_random",
                "distribution_validation": True,
                "rarity_tiers": {
                    "common": {"min_weight": 50, "max_weight": 100},
                    "uncommon": {"min_weight": 25, "max_weight": 49},
                    "rare": {"min_weight": 10, "max_weight": 24},
                    "epic": {"min_weight": 5, "max_weight": 9},
                    "legendary": {"min_weight": 1, "max_weight": 4}
                }
            },
            "validation": {
                "enforce_grid_positions": True,
                "require_all_positions": False,
                "check_file_integrity": True,
                "validate_image_dimensions": True
            }
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(valid_config, f, indent=2)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_validate_config_comprehensive(self):
        """Test validate_config_comprehensive convenience function"""
        result = validate_config_comprehensive(self.config_path)
        
        self.assertIsInstance(result, ComprehensiveValidationResult)
        self.assertEqual(result.validation_mode, ValidationMode.STANDARD)
        
        # Test with different mode
        result = validate_config_comprehensive(
            self.config_path, 
            validation_mode=ValidationMode.MINIMAL
        )
        self.assertEqual(result.validation_mode, ValidationMode.MINIMAL)
    
    def test_get_comprehensive_validation_report(self):
        """Test validation report generation"""
        result = validate_config_comprehensive(self.config_path)
        report = get_comprehensive_validation_report(result)
        
        self.assertIsInstance(report, str)
        self.assertIn("GENCONFIG COMPREHENSIVE VALIDATION REPORT", report)
        self.assertIn("Overall Status:", report)
        self.assertIn("VALIDATION PHASES:", report)
        
        # Test report with errors
        # Create config with issues
        invalid_config = {"invalid": "config"}
        invalid_path = self.temp_dir / "invalid.json"
        with open(invalid_path, 'w') as f:
            json.dump(invalid_config, f)
        
        result = validate_config_comprehensive(invalid_path)
        report = get_comprehensive_validation_report(result)
        
        self.assertIn("❌ FAILED", report)
        self.assertIn("ISSUE SUMMARY:", report)
        self.assertIn("RECOMMENDATIONS:", report)


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_nonexistent_config_file(self):
        """Test handling of non-existent config file"""
        nonexistent_path = self.temp_dir / "nonexistent.json"
        
        suite = SchemaValidationSuite()
        result = suite.validate_configuration(nonexistent_path)
        
        self.assertFalse(result.overall_success)
        self.assertGreater(len(result.errors), 0)
    
    def test_empty_config_file(self):
        """Test handling of empty config file"""
        empty_path = self.temp_dir / "empty.json"
        empty_path.write_text("")
        
        suite = SchemaValidationSuite()
        result = suite.validate_configuration(empty_path)
        
        self.assertFalse(result.overall_success)
    
    def test_malformed_json(self):
        """Test handling of malformed JSON"""
        malformed_path = self.temp_dir / "malformed.json"
        malformed_path.write_text("{ invalid json content")
        
        suite = SchemaValidationSuite()
        result = suite.validate_configuration(malformed_path)
        
        self.assertFalse(result.overall_success)
    
    def test_missing_traits_directory(self):
        """Test handling of missing traits directory"""
        config = {
            "collection": {
                "name": "Test",
                "description": "Test",
                "size": 10,
                "symbol": "TEST",
                "external_url": "https://example.com"
            },
            "generation": {
                "image_format": "PNG",
                "image_size": {"width": 600, "height": 600},
                "grid": {"rows": 3, "columns": 3, "cell_size": {"width": 200, "height": 200}},
                "background_color": "#FFFFFF",
                "allow_duplicates": False
            },
            "traits": {
                "position-1-background": {
                    "name": "Background",
                    "required": True,
                    "grid_position": {"row": 0, "column": 0},
                    "variants": [{"name": "Test", "filename": "trait-test-001.png", "rarity_weight": 100}]
                }
            },
            "rarity": {
                "calculation_method": "weighted_random",
                "distribution_validation": True,
                "rarity_tiers": {
                    "common": {"min_weight": 50, "max_weight": 100},
                    "uncommon": {"min_weight": 25, "max_weight": 49},
                    "rare": {"min_weight": 10, "max_weight": 24},
                    "epic": {"min_weight": 5, "max_weight": 9},
                    "legendary": {"min_weight": 1, "max_weight": 4}
                }
            },
            "validation": {
                "enforce_grid_positions": True,
                "require_all_positions": False,
                "check_file_integrity": True,
                "validate_image_dimensions": True
            }
        }
        
        config_path = self.temp_dir / "config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        nonexistent_traits = self.temp_dir / "nonexistent_traits"
        
        suite = SchemaValidationSuite(ValidationMode.COMPREHENSIVE)
        result = suite.validate_configuration(config_path, nonexistent_traits)
        
        # Should handle missing traits directory gracefully
        self.assertIn(ValidationPhase.TRAITS, result.phase_results)


if __name__ == '__main__':
    unittest.main() 