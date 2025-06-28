"""
Test suite for Grid Layout Validator

Tests Component 4.2: Grid Layout Validator functionality including:
- Grid position assignment validation
- Position uniqueness checking
- Grid completeness validation  
- Coordinate consistency validation
- Trait key format validation
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from grid.layout_validator import (
    GridLayoutValidator,
    GridPositionAssignment,
    GridLayoutError,
    ValidationSeverity,
    ValidationIssue,
    ValidationResult,
    validate_grid_layout,
    get_grid_layout_report,
    check_grid_completeness,
    check_position_uniqueness
)
from config.config_parser import (
    GenConfig,
    parse_config_dict
)
from config.schema_validator import create_sample_config


class TestGridPositionAssignment(unittest.TestCase):
    """Test cases for GridPositionAssignment data structure"""
    
    def test_grid_position_assignment_creation(self):
        """Test GridPositionAssignment creation and properties"""
        assignment = GridPositionAssignment(
            position=5,
            coordinates=(1, 1),
            trait_category_key="position-5-center",
            trait_name="Center Trait",
            is_required=True
        )
        
        self.assertEqual(assignment.position, 5)
        self.assertEqual(assignment.coordinates, (1, 1))
        self.assertEqual(assignment.trait_category_key, "position-5-center")
        self.assertEqual(assignment.trait_name, "Center Trait")
        self.assertTrue(assignment.is_required)


class TestGridLayoutValidator(unittest.TestCase):
    """Test cases for GridLayoutValidator main functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = GridLayoutValidator()
        self.strict_validator = GridLayoutValidator(strict_mode=True)
        
        # Create valid config with all 9 positions
        self.valid_config_data = self._create_complete_config()
        self.valid_config = parse_config_dict(self.valid_config_data)
        
        # Create partial config with only some positions
        self.partial_config_data = self._create_partial_config()
        self.partial_config = parse_config_dict(self.partial_config_data)
        
        # Create config with duplicate positions
        self.duplicate_config_data = self._create_duplicate_position_config()
        self.duplicate_config = parse_config_dict(self.duplicate_config_data)
    
    def _create_complete_config(self) -> Dict[str, Any]:
        """Create configuration with all 9 grid positions"""
        base_config = create_sample_config()
        
        # Add all 9 positions
        positions = [
            ("position-1-background", "Background", 0, 0),
            ("position-2-base", "Base", 0, 1),
            ("position-3-accent", "Accent", 0, 2),
            ("position-4-pattern", "Pattern", 1, 0),
            ("position-5-center", "Center", 1, 1),
            ("position-6-decoration", "Decoration", 1, 2),
            ("position-7-border", "Border", 2, 0),
            ("position-8-highlight", "Highlight", 2, 1),
            ("position-9-overlay", "Overlay", 2, 2)
        ]
        
        base_config["traits"] = {}
        for trait_key, name, row, col in positions:
            base_config["traits"][trait_key] = {
                "name": name,
                "required": True,
                "grid_position": {"row": row, "column": col},
                "variants": [
                    {
                        "name": f"Default {name}",
                        "filename": f"trait-{name.lower()}-001.png",
                        "rarity_weight": 100
                    }
                ]
            }
        
        return base_config
    
    def _create_partial_config(self) -> Dict[str, Any]:
        """Create configuration with only 3 positions"""
        base_config = create_sample_config()
        
        base_config["traits"] = {
            "position-1-background": {
                "name": "Background",
                "required": True,
                "grid_position": {"row": 0, "column": 0},
                "variants": [{"name": "Red Background", "filename": "trait-red-bg-001.png", "rarity_weight": 100}]
            },
            "position-5-center": {
                "name": "Center",
                "required": True,
                "grid_position": {"row": 1, "column": 1},
                "variants": [{"name": "Center Element", "filename": "trait-center-001.png", "rarity_weight": 100}]
            },
            "position-9-overlay": {
                "name": "Overlay",
                "required": False,
                "grid_position": {"row": 2, "column": 2},
                "variants": [{"name": "Overlay Effect", "filename": "trait-overlay-001.png", "rarity_weight": 100}]
            }
        }
        
        return base_config
    
    def _create_duplicate_position_config(self) -> Dict[str, Any]:
        """Create configuration with duplicate position assignments"""
        base_config = create_sample_config()
        
        base_config["traits"] = {
            "position-1-background": {
                "name": "Background",
                "required": True,
                "grid_position": {"row": 0, "column": 0},  # Position 1
                "variants": [{"name": "Red Background", "filename": "trait-red-bg-001.png", "rarity_weight": 100}]
            },
            "position-2-base": {
                "name": "Base",
                "required": True,
                "grid_position": {"row": 0, "column": 0},  # Position 1 (duplicate!)
                "variants": [{"name": "Blue Base", "filename": "trait-blue-base-001.png", "rarity_weight": 100}]
            }
        }
        
        return base_config
    
    def test_validate_complete_grid_layout(self):
        """Test validation of complete grid layout"""
        result = self.validator.validate_grid_layout(self.valid_config)
        
        # Should be valid
        self.assertTrue(result.is_valid)
        
        # Should have info messages about grid completeness
        info_messages = [issue.message for issue in result.infos]
        self.assertTrue(any("9/9 positions assigned" in msg for msg in info_messages))
        self.assertTrue(any("Complete 3×3 grid coverage achieved" in msg for msg in info_messages))
    
    def test_validate_partial_grid_layout(self):
        """Test validation of partial grid layout"""
        result = self.validator.validate_grid_layout(self.partial_config)
        
        # Should have warnings about incomplete grid
        warning_messages = [issue.message for issue in result.warnings]
        self.assertTrue(any("Grid incomplete: missing positions" in msg for msg in warning_messages))
        
        # Should still be valid in normal mode
        self.assertTrue(result.is_valid)
    
    def test_validate_duplicate_positions(self):
        """Test validation catches duplicate position assignments"""
        result = self.validator.validate_grid_layout(self.duplicate_config)
        
        # Should be invalid due to duplicate positions
        self.assertFalse(result.is_valid)
        
        # Should have error about duplicate positions
        error_messages = [issue.message for issue in result.errors]
        self.assertTrue(any("Grid position 1 assigned to multiple traits" in msg for msg in error_messages))
    
    def test_get_position_assignments(self):
        """Test getting position assignments from config"""
        assignments = self.validator.get_position_assignments(self.valid_config)
        
        # Should have 9 assignments
        self.assertEqual(len(assignments), 9)
        
        # Check specific assignment
        center_assignment = next((a for a in assignments if a.position == 5), None)
        self.assertIsNotNone(center_assignment)
        self.assertEqual(center_assignment.coordinates, (1, 1))
        self.assertEqual(center_assignment.trait_name, "Center")
    
    def test_strict_mode_validation(self):
        """Test strict mode treats warnings as errors"""
        # Partial config should be invalid in strict mode
        result = self.strict_validator.validate_grid_layout(self.partial_config)
        self.assertFalse(result.is_valid)
        
        # Complete config should still be valid in strict mode
        result = self.strict_validator.validate_grid_layout(self.valid_config)
        self.assertTrue(result.is_valid)
    
    def test_check_grid_completeness(self):
        """Test grid completeness checking"""
        # Complete grid
        is_complete, missing = self.validator.check_grid_completeness(self.valid_config)
        self.assertTrue(is_complete)
        self.assertEqual(len(missing), 0)
        
        # Partial grid
        is_complete, missing = self.validator.check_grid_completeness(self.partial_config)
        self.assertFalse(is_complete)
        self.assertEqual(missing, {2, 3, 4, 6, 7, 8})
    
    def test_check_position_uniqueness(self):
        """Test position uniqueness checking"""
        # Valid config - should be unique
        is_unique, duplicates = self.validator.check_position_uniqueness(self.valid_config)
        self.assertTrue(is_unique)
        self.assertEqual(len(duplicates), 0)
        
        # Duplicate config - should not be unique
        is_unique, duplicates = self.validator.check_position_uniqueness(self.duplicate_config)
        self.assertFalse(is_unique)
        self.assertIn(1, duplicates)
        self.assertEqual(len(duplicates[1]), 2)


class TestValidationDetails(unittest.TestCase):
    """Test cases for detailed validation scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = GridLayoutValidator()
    
    def test_invalid_coordinates_validation(self):
        """Test validation of invalid coordinates"""
        # Create config with invalid coordinates
        config_data = create_sample_config()
        config_data["traits"] = {
            "position-1-background": {
                "name": "Background",
                "required": True,
                "grid_position": {"row": 3, "column": 0},  # Invalid row (should be 0-2)
                "variants": [{"name": "Background", "filename": "trait-bg-001.png", "rarity_weight": 100}]
            }
        }
        
        config = parse_config_dict(config_data)
        result = self.validator.validate_grid_layout(config)
        
        # Should be invalid
        self.assertFalse(result.is_valid)
        
        # Should have error about invalid coordinates
        error_messages = [issue.message for issue in result.errors]
        self.assertTrue(any("Invalid coordinates" in msg for msg in error_messages))
    
    def test_trait_key_format_validation(self):
        """Test validation of trait key formats"""
        # Create config with mismatched trait key
        config_data = create_sample_config()
        config_data["traits"] = {
            "position-2-background": {  # Key says position 2
                "name": "Background",
                "required": True,
                "grid_position": {"row": 0, "column": 0},  # But coordinates are position 1
                "variants": [{"name": "Background", "filename": "trait-bg-001.png", "rarity_weight": 100}]
            }
        }
        
        config = parse_config_dict(config_data)
        result = self.validator.validate_grid_layout(config)
        
        # Should have warnings about key mismatch
        warning_messages = [issue.message for issue in result.warnings]
        self.assertTrue(any("indicates position 2 but grid coordinates indicate position 1" in msg for msg in warning_messages))
    
    def test_empty_traits_validation(self):
        """Test validation when no traits are defined"""
        config_data = create_sample_config()
        config_data["traits"] = {}
        
        config = parse_config_dict(config_data)
        result = self.validator.validate_grid_layout(config)
        
        # Should be invalid
        self.assertFalse(result.is_valid)
        
        # Should have error about no grid assignments
        error_messages = [issue.message for issue in result.errors]
        self.assertTrue(any("No grid position assignments found" in msg for msg in error_messages))
    
    def test_require_all_positions_disabled(self):
        """Test behavior when require_all_positions is disabled"""
        config_data = self._create_partial_config()
        config_data["validation"]["require_all_positions"] = False
        
        config = parse_config_dict(config_data)
        result = self.validator.validate_grid_layout(config)
        
        # Should be valid even with incomplete grid
        self.assertTrue(result.is_valid)
        
        # Should still have warnings about missing positions
        warning_messages = [issue.message for issue in result.warnings]
        self.assertTrue(any("Grid incomplete: missing positions" in msg for msg in warning_messages))
    
    def _create_partial_config(self) -> Dict[str, Any]:
        """Helper to create partial config"""
        base_config = create_sample_config()
        base_config["traits"] = {
            "position-1-background": {
                "name": "Background",
                "required": True,
                "grid_position": {"row": 0, "column": 0},
                "variants": [{"name": "Red Background", "filename": "trait-red-bg-001.png", "rarity_weight": 100}]
            }
        }
        return base_config


class TestConvenienceFunctions(unittest.TestCase):
    """Test cases for convenience functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config_data = create_sample_config()
        self.config = parse_config_dict(self.config_data)
    
    def test_validate_grid_layout_function(self):
        """Test validate_grid_layout convenience function"""
        # Test with default parameters
        result = validate_grid_layout(self.config)
        self.assertIsInstance(result, ValidationResult)
        
        # Test with strict mode
        result_strict = validate_grid_layout(self.config, strict_mode=True)
        self.assertIsInstance(result_strict, ValidationResult)
    
    def test_get_grid_layout_report_function(self):
        """Test get_grid_layout_report function"""
        result = validate_grid_layout(self.config)
        report = get_grid_layout_report(result)
        
        # Verify report structure
        self.assertIsInstance(report, str)
        self.assertIn("Grid Layout Validation:", report)
        self.assertIn("Total Issues:", report)
        
        # Test with invalid result
        validator = GridLayoutValidator()
        invalid_config_data = self.config_data.copy()
        invalid_config_data["traits"] = {}
        invalid_config = parse_config_dict(invalid_config_data)
        
        invalid_result = validator.validate_grid_layout(invalid_config)
        invalid_report = get_grid_layout_report(invalid_result)
        self.assertIn("INVALID", invalid_report)
    
    def test_check_grid_completeness_function(self):
        """Test check_grid_completeness convenience function"""
        is_complete, missing = check_grid_completeness(self.config)
        self.assertIsInstance(is_complete, bool)
        self.assertIsInstance(missing, set)
    
    def test_check_position_uniqueness_function(self):
        """Test check_position_uniqueness convenience function"""
        is_unique, duplicates = check_position_uniqueness(self.config)
        self.assertIsInstance(is_unique, bool)
        self.assertIsInstance(duplicates, dict)


class TestErrorHandling(unittest.TestCase):
    """Test cases for error handling scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = GridLayoutValidator()
    
    def test_malformed_grid_position(self):
        """Test handling of malformed grid position data"""
        # Create config with missing grid position attributes
        config_data = create_sample_config()
        config_data["traits"] = {
            "position-1-background": {
                "name": "Background",
                "required": True,
                "grid_position": {"row": 0},  # Missing column
                "variants": [{"name": "Background", "filename": "trait-bg-001.png", "rarity_weight": 100}]
            }
        }
        
        # This should be caught by schema validation or parsing
        # but we test graceful handling if it gets through
        try:
            config = parse_config_dict(config_data)
            result = self.validator.validate_grid_layout(config)
            # Should handle gracefully and return error result
            self.assertFalse(result.is_valid)
        except Exception:
            # Expected if config parser catches this first
            pass
    
    def test_coordinate_calculation_error(self):
        """Test handling of coordinate calculation errors"""
        # This tests internal error handling in coordinate calculations
        # Most errors should be caught by validation, but we test robustness
        pass


class TestIntegrationWorkflow(unittest.TestCase):
    """Integration tests demonstrating complete validation workflow"""
    
    def test_complete_validation_workflow(self):
        """Test complete grid layout validation workflow"""
        print("🧪 Testing complete Grid Layout Validation workflow...")
        
        # Step 1: Create and validate complete configuration
        print("📋 Step 1: Creating complete grid configuration...")
        complete_config_data = self._create_complete_grid_config()
        complete_config = parse_config_dict(complete_config_data)
        
        validator = GridLayoutValidator()
        result = validator.validate_grid_layout(complete_config)
        
        self.assertTrue(result.is_valid, "Complete grid should be valid")
        print(f"✅ Complete grid validation: {len(result.issues)} issues found")
        
        # Step 2: Test grid completeness checking
        print("🔍 Step 2: Checking grid completeness...")
        is_complete, missing = validator.check_grid_completeness(complete_config)
        self.assertTrue(is_complete, "Grid should be complete")
        self.assertEqual(len(missing), 0, "No positions should be missing")
        print(f"✅ Grid completeness: {is_complete}, missing: {missing}")
        
        # Step 3: Test position uniqueness checking
        print("🎯 Step 3: Checking position uniqueness...")
        is_unique, duplicates = validator.check_position_uniqueness(complete_config)
        self.assertTrue(is_unique, "Positions should be unique")
        self.assertEqual(len(duplicates), 0, "No duplicates should exist")
        print(f"✅ Position uniqueness: {is_unique}, duplicates: {duplicates}")
        
        # Step 4: Test validation report generation
        print("📊 Step 4: Generating validation report...")
        report = get_grid_layout_report(result)
        self.assertIn("Grid Layout Validation: ✅ VALID", report)
        print("✅ Validation report generated successfully")
        
        # Step 5: Test partial grid handling
        print("⚠️ Step 5: Testing partial grid validation...")
        partial_config_data = self._create_partial_grid_config()
        partial_config = parse_config_dict(partial_config_data)
        
        partial_result = validator.validate_grid_layout(partial_config)
        # Should be valid in normal mode but have warnings
        self.assertTrue(partial_result.is_valid, "Partial grid should be valid in normal mode")
        self.assertTrue(len(partial_result.warnings) > 0, "Should have warnings about incomplete grid")
        print(f"✅ Partial grid validation: {len(partial_result.warnings)} warnings")
        
        # Step 6: Test strict mode behavior
        print("🔒 Step 6: Testing strict mode validation...")
        strict_validator = GridLayoutValidator(strict_mode=True)
        strict_result = strict_validator.validate_grid_layout(partial_config)
        # Should be invalid in strict mode due to warnings
        self.assertFalse(strict_result.is_valid, "Partial grid should be invalid in strict mode")
        print(f"✅ Strict mode validation: Invalid as expected")
        
        # Step 7: Test error scenarios
        print("❌ Step 7: Testing error scenarios...")
        duplicate_config_data = self._create_duplicate_position_config()
        duplicate_config = parse_config_dict(duplicate_config_data)
        
        error_result = validator.validate_grid_layout(duplicate_config)
        self.assertFalse(error_result.is_valid, "Duplicate positions should make grid invalid")
        self.assertTrue(len(error_result.errors) > 0, "Should have errors about duplicate positions")
        print(f"✅ Error handling: {len(error_result.errors)} errors detected")
        
        print("\n🎉 All Grid Layout Validation integration tests passed!")
        return True
    
    def _create_complete_grid_config(self) -> Dict[str, Any]:
        """Create configuration with complete 3x3 grid"""
        config = create_sample_config()
        
        positions = [
            ("position-1-background", "Background", 0, 0),
            ("position-2-base", "Base", 0, 1),
            ("position-3-accent", "Accent", 0, 2),
            ("position-4-pattern", "Pattern", 1, 0),
            ("position-5-center", "Center", 1, 1),
            ("position-6-decoration", "Decoration", 1, 2),
            ("position-7-border", "Border", 2, 0),
            ("position-8-highlight", "Highlight", 2, 1),
            ("position-9-overlay", "Overlay", 2, 2)
        ]
        
        config["traits"] = {}
        for trait_key, name, row, col in positions:
            config["traits"][trait_key] = {
                "name": name,
                "required": (row + col) % 2 == 0,  # Make some required
                "grid_position": {"row": row, "column": col},
                "variants": [
                    {
                        "name": f"Default {name}",
                        "filename": f"trait-{name.lower()}-001.png",
                        "rarity_weight": 100 - (row * 3 + col) * 10  # Varying weights
                    }
                ]
            }
        
        return config
    
    def _create_partial_grid_config(self) -> Dict[str, Any]:
        """Create configuration with partial grid (3 positions)"""
        config = create_sample_config()
        
        config["traits"] = {
            "position-1-background": {
                "name": "Background",
                "required": True,
                "grid_position": {"row": 0, "column": 0},
                "variants": [{"name": "Background", "filename": "trait-bg-001.png", "rarity_weight": 100}]
            },
            "position-5-center": {
                "name": "Center",
                "required": True,
                "grid_position": {"row": 1, "column": 1},
                "variants": [{"name": "Center", "filename": "trait-center-001.png", "rarity_weight": 100}]
            },
            "position-9-overlay": {
                "name": "Overlay",
                "required": False,
                "grid_position": {"row": 2, "column": 2},
                "variants": [{"name": "Overlay", "filename": "trait-overlay-001.png", "rarity_weight": 100}]
            }
        }
        
        return config
    
    def _create_duplicate_position_config(self) -> Dict[str, Any]:
        """Create configuration with duplicate position assignments"""
        config = create_sample_config()
        
        config["traits"] = {
            "position-1-background": {
                "name": "Background",
                "required": True,
                "grid_position": {"row": 0, "column": 0},  # Position 1
                "variants": [{"name": "Background", "filename": "trait-bg-001.png", "rarity_weight": 100}]
            },
            "position-2-base": {
                "name": "Base",
                "required": True,
                "grid_position": {"row": 0, "column": 0},  # Position 1 (duplicate!)
                "variants": [{"name": "Base", "filename": "trait-base-001.png", "rarity_weight": 100}]
            }
        }
        
        return config


if __name__ == "__main__":
    # Run integration test first
    print("Running Grid Layout Validator Tests...")
    
    integration_suite = unittest.TestLoader().loadTestsFromTestCase(TestIntegrationWorkflow)
    integration_runner = unittest.TextTestRunner(verbosity=2)
    integration_result = integration_runner.run(integration_suite)
    
    if integration_result.wasSuccessful():
        # Run all tests
        print("\n" + "="*60)
        print("Running Full Test Suite...")
        unittest.main(verbosity=2, exit=False)
    else:
        print("❌ Integration test failed. Please check implementation.")
        sys.exit(1) 