"""
Test suite for GenConfig Configuration Logic Validator

This module tests the configuration logic validator functionality including
logical consistency validation, constraint checking, and business rule validation.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config.logic_validator import (
    ConfigurationLogicValidator,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    ConfigurationLogicError,
    validate_config_logic,
    get_validation_report
)
from config.config_parser import (
    GenConfig,
    CollectionConfig,
    GenerationConfig,
    ImageSize,
    GridConfig,
    CellSize,
    TraitCategory,
    TraitVariant,
    GridPosition,
    RarityConfig,
    RarityTier,
    ValidationConfig
)
from config.schema_validator import create_sample_config
from config.config_parser import parse_config_dict
from utils.file_utils import safe_write_file


class TestValidationStructures(unittest.TestCase):
    """Test cases for validation data structures"""
    
    def test_validation_issue_creation(self):
        """Test ValidationIssue creation and properties"""
        issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            category="test_category",
            message="Test message",
            path="test.path",
            suggestion="Test suggestion"
        )
        
        self.assertEqual(issue.severity, ValidationSeverity.ERROR)
        self.assertEqual(issue.category, "test_category")
        self.assertEqual(issue.message, "Test message")
        self.assertEqual(issue.path, "test.path")
        self.assertEqual(issue.suggestion, "Test suggestion")
    
    def test_validation_result_properties(self):
        """Test ValidationResult properties and methods"""
        issues = [
            ValidationIssue(ValidationSeverity.ERROR, "category1", "Error message"),
            ValidationIssue(ValidationSeverity.WARNING, "category2", "Warning message"),
            ValidationIssue(ValidationSeverity.INFO, "category3", "Info message"),
            ValidationIssue(ValidationSeverity.ERROR, "category1", "Another error")
        ]
        
        result = ValidationResult(is_valid=False, issues=issues)
        
        # Test basic properties
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.issues), 4)
        
        # Test filtered properties
        self.assertEqual(len(result.errors), 2)
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(len(result.infos), 1)
        
        # Test summary
        summary = result.get_summary()
        self.assertEqual(summary["total_issues"], 4)
        self.assertEqual(summary["errors"], 2)
        self.assertEqual(summary["warnings"], 1)
        self.assertEqual(summary["infos"], 1)
        self.assertIn("category1", summary["categories"])
        self.assertIn("category2", summary["categories"])
        self.assertIn("category3", summary["categories"])


class TestConfigurationLogicValidator(unittest.TestCase):
    """Test cases for ConfigurationLogicValidator class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.validator = ConfigurationLogicValidator(check_file_existence=False)
        self.strict_validator = ConfigurationLogicValidator(strict_mode=True)
        
        # Create valid test configuration
        config_data = create_sample_config()
        self.valid_config = parse_config_dict(config_data)
        
        # Create configuration with known issues
        self.invalid_config = self._create_invalid_config()
    
    def tearDown(self):
        """Clean up test fixtures"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def _create_invalid_config(self) -> GenConfig:
        """Create configuration with known validation issues"""
        return GenConfig(
            collection=CollectionConfig(
                name="",  # Empty name - should trigger error
                description="",  # Empty description - should trigger warning
                size=-5,  # Invalid size - should trigger error
                symbol="invalid",  # Lowercase symbol - should trigger warning
                external_url="https://example.com"
            ),
            generation=GenerationConfig(
                image_format="PNG",
                image_size=ImageSize(width=500, height=500),  # Mismatched dimensions
                grid=GridConfig(
                    rows=3,
                    columns=3,
                    cell_size=CellSize(width=200, height=200)  # Should be 600x600 total
                ),
                background_color="#FFFFFF",
                allow_duplicates=False
            ),
            traits={
                "position-1-background": TraitCategory(
                    name="Background",
                    required=True,
                    grid_position=GridPosition(row=0, column=0),
                    variants=[]  # Empty variants - should trigger error
                ),
                "position-2-base": TraitCategory(
                    name="Base",
                    required=True,
                    grid_position=GridPosition(row=0, column=0),  # Duplicate position
                    variants=[
                        TraitVariant(
                            name="Variant1",
                            filename="file1.png",
                            rarity_weight=0  # Invalid weight
                        )
                    ]
                )
            },
            rarity=RarityConfig(
                calculation_method="weighted_random",
                distribution_validation=True,
                rarity_tiers={
                    "common": RarityTier(min_weight=100, max_weight=50),  # Invalid range
                    "rare": RarityTier(min_weight=25, max_weight=75)  # Overlapping range
                }
            ),
            validation=ValidationConfig(
                enforce_grid_positions=True,
                require_all_positions=True,
                check_file_integrity=True,
                validate_image_dimensions=True
            )
        )
    
    def test_validator_initialization(self):
        """Test ConfigurationLogicValidator initialization"""
        # Test default initialization
        default_validator = ConfigurationLogicValidator()
        self.assertTrue(default_validator.check_file_existence)
        self.assertFalse(default_validator.strict_mode)
        
        # Test custom initialization
        custom_validator = ConfigurationLogicValidator(
            check_file_existence=False,
            strict_mode=True
        )
        self.assertFalse(custom_validator.check_file_existence)
        self.assertTrue(custom_validator.strict_mode)
    
    def test_validate_valid_config(self):
        """Test validation of valid configuration"""
        # Create a better test config with more variants to avoid feasibility issues
        better_config = GenConfig(
            collection=CollectionConfig("Test", "Valid test config", 10, "TEST", "https://example.com"),
            generation=GenerationConfig(
                "PNG",
                ImageSize(600, 600),
                GridConfig(3, 3, CellSize(200, 200)),
                "#FFFFFF",
                True  # Allow duplicates to avoid feasibility issues
            ),
            traits={
                "position-1-background": TraitCategory(
                    "Background",
                    True,
                    GridPosition(0, 0),
                    [
                        TraitVariant("Red", "red.png", 100),
                        TraitVariant("Blue", "blue.png", 50),
                        TraitVariant("Green", "green.png", 25)
                    ]
                )
            },
            rarity=RarityConfig(
                "weighted_random",
                True,
                {
                    "common": RarityTier(50, 100),
                    "uncommon": RarityTier(25, 49),
                    "rare": RarityTier(1, 24)
                }
            ),
            validation=ValidationConfig(True, False, True, True)
        )
        
        result = self.validator.validate_config(better_config)
        
        self.assertIsInstance(result, ValidationResult)
        
        # Should have no errors
        self.assertEqual(len(result.errors), 0)
    
    def test_validate_invalid_config(self):
        """Test validation of invalid configuration"""
        result = self.validator.validate_config(self.invalid_config)
        
        self.assertIsInstance(result, ValidationResult)
        self.assertFalse(result.is_valid)
        self.assertTrue(len(result.errors) > 0)
        
        # Check for expected error categories
        error_categories = [issue.category for issue in result.errors]
        self.assertIn("collection_constraints", error_categories)
        self.assertIn("dimension_consistency", error_categories)
        self.assertIn("grid_consistency", error_categories)
        self.assertIn("trait_requirements", error_categories)
    
    def test_strict_mode(self):
        """Test strict mode behavior"""
        # Create config that would pass normally but has warnings
        config_with_warnings = GenConfig(
            collection=CollectionConfig(
                name="Test Collection",
                description="",  # Empty description - warning
                size=1000,
                symbol="test",  # Lowercase - warning
                external_url="https://example.com"
            ),
            generation=GenerationConfig(
                image_format="PNG",
                image_size=ImageSize(width=600, height=600),
                grid=GridConfig(
                    rows=3,
                    columns=3,
                    cell_size=CellSize(width=200, height=200)
                ),
                background_color="#FFFFFF",
                allow_duplicates=False
            ),
            traits={
                "position-1-background": TraitCategory(
                    name="Background",
                    required=True,
                    grid_position=GridPosition(row=0, column=0),
                    variants=[
                        TraitVariant(
                            name="Red Background",
                            filename="red.png",
                            rarity_weight=100
                        )
                    ]
                )
            },
            rarity=RarityConfig(
                calculation_method="weighted_random",
                distribution_validation=True,
                rarity_tiers={
                    "common": RarityTier(min_weight=50, max_weight=100)
                }
            ),
            validation=ValidationConfig(
                enforce_grid_positions=True,
                require_all_positions=False,
                check_file_integrity=True,
                validate_image_dimensions=True
            )
        )
        
        # Normal mode should pass despite warnings
        normal_result = self.validator.validate_config(config_with_warnings)
        
        # Strict mode should fail due to warnings
        strict_result = self.strict_validator.validate_config(config_with_warnings)
        
        # Normal mode should be valid if no errors
        if len(normal_result.errors) == 0:
            self.assertTrue(normal_result.is_valid)
        
        # Strict mode should be invalid if any warnings
        if len(strict_result.warnings) > 0:
            self.assertFalse(strict_result.is_valid)
    
    def test_grid_consistency_validation(self):
        """Test grid consistency validation"""
        # Test duplicate positions
        config = GenConfig(
            collection=CollectionConfig("Test", "Test", 100, "TEST", "https://example.com"),
            generation=GenerationConfig(
                "PNG",
                ImageSize(600, 600),
                GridConfig(3, 3, CellSize(200, 200)),
                "#FFFFFF",
                False
            ),
            traits={
                "position-1-background": TraitCategory(
                    "Background",
                    True,
                    GridPosition(0, 0),
                    [TraitVariant("Var1", "file1.png", 100)]
                ),
                "position-5-center": TraitCategory(
                    "Center", 
                    True,
                    GridPosition(0, 0),  # Duplicate position
                    [TraitVariant("Var2", "file2.png", 100)]
                )
            },
            rarity=RarityConfig("weighted_random", True, {"common": RarityTier(50, 100)}),
            validation=ValidationConfig(True, False, True, True)
        )
        
        result = self.validator.validate_config(config)
        
        # Should have grid consistency errors
        grid_errors = [issue for issue in result.errors if issue.category == "grid_consistency"]
        self.assertTrue(len(grid_errors) > 0)
    
    def test_dimension_consistency_validation(self):
        """Test dimension consistency validation"""
        # Test mismatched dimensions
        config = GenConfig(
            collection=CollectionConfig("Test", "Test", 100, "TEST", "https://example.com"),
            generation=GenerationConfig(
                "PNG",
                ImageSize(500, 500),  # Wrong size
                GridConfig(3, 3, CellSize(200, 200)),  # Should be 600x600
                "#FFFFFF",
                False
            ),
            traits={
                "position-1-background": TraitCategory(
                    "Background",
                    True,
                    GridPosition(0, 0),
                    [TraitVariant("Var1", "file1.png", 100)]
                )
            },
            rarity=RarityConfig("weighted_random", True, {"common": RarityTier(50, 100)}),
            validation=ValidationConfig(True, False, True, True)
        )
        
        result = self.validator.validate_config(config)
        
        # Should have dimension consistency errors
        dimension_errors = [issue for issue in result.errors if issue.category == "dimension_consistency"]
        self.assertTrue(len(dimension_errors) > 0)
    
    def test_collection_constraints_validation(self):
        """Test collection constraints validation"""
        # Test invalid collection size
        config = GenConfig(
            collection=CollectionConfig("", "Test", -10, "test", "https://example.com"),
            generation=GenerationConfig(
                "PNG",
                ImageSize(600, 600),
                GridConfig(3, 3, CellSize(200, 200)),
                "#FFFFFF",
                False
            ),
            traits={
                "position-1-background": TraitCategory(
                    "Background",
                    True,
                    GridPosition(0, 0),
                    [TraitVariant("Var1", "file1.png", 100)]
                )
            },
            rarity=RarityConfig("weighted_random", True, {"common": RarityTier(50, 100)}),
            validation=ValidationConfig(True, False, True, True)
        )
        
        result = self.validator.validate_config(config)
        
        # Should have collection constraint errors
        collection_errors = [issue for issue in result.errors if issue.category == "collection_constraints"]
        self.assertTrue(len(collection_errors) > 0)
    
    def test_rarity_logic_validation(self):
        """Test rarity logic validation"""
        # Test invalid rarity tiers
        config = GenConfig(
            collection=CollectionConfig("Test", "Test", 100, "TEST", "https://example.com"),
            generation=GenerationConfig(
                "PNG",
                ImageSize(600, 600),
                GridConfig(3, 3, CellSize(200, 200)),
                "#FFFFFF",
                False
            ),
            traits={
                "position-1-background": TraitCategory(
                    "Background",
                    True,
                    GridPosition(0, 0),
                    [TraitVariant("Var1", "file1.png", 500)]  # Weight outside tiers
                )
            },
            rarity=RarityConfig(
                "weighted_random",
                True,
                {
                    "common": RarityTier(100, 50),  # Invalid range
                    "rare": RarityTier(25, 75)  # Overlapping
                }
            ),
            validation=ValidationConfig(True, False, True, True)
        )
        
        result = self.validator.validate_config(config)
        
        # Should have rarity logic errors or warnings
        rarity_issues = [issue for issue in result.issues if issue.category == "rarity_logic"]
        self.assertTrue(len(rarity_issues) > 0)
    
    def test_trait_requirements_validation(self):
        """Test trait requirements validation"""
        # Test empty variants and duplicate names
        config = GenConfig(
            collection=CollectionConfig("Test", "Test", 100, "TEST", "https://example.com"),
            generation=GenerationConfig(
                "PNG",
                ImageSize(600, 600),
                GridConfig(3, 3, CellSize(200, 200)),
                "#FFFFFF",
                False
            ),
            traits={
                "position-1-background": TraitCategory(
                    "Background",
                    True,
                    GridPosition(0, 0),
                    []  # Empty variants
                ),
                "position-2-base": TraitCategory(
                    "Base",
                    True,
                    GridPosition(0, 1),
                    [
                        TraitVariant("Duplicate", "file1.png", 100),
                        TraitVariant("Duplicate", "file2.png", 100)  # Duplicate name
                    ]
                )
            },
            rarity=RarityConfig("weighted_random", True, {"common": RarityTier(50, 100)}),
            validation=ValidationConfig(True, False, True, True)
        )
        
        result = self.validator.validate_config(config)
        
        # Should have trait requirement errors
        trait_errors = [issue for issue in result.errors if issue.category == "trait_requirements"]
        self.assertTrue(len(trait_errors) > 0)
    
    def test_generation_feasibility_validation(self):
        """Test generation feasibility validation"""
        # Test collection size exceeding combinations
        config = GenConfig(
            collection=CollectionConfig("Test", "Test", 100, "TEST", "https://example.com"),
            generation=GenerationConfig(
                "PNG",
                ImageSize(600, 600),
                GridConfig(3, 3, CellSize(200, 200)),
                "#FFFFFF",
                False  # No duplicates allowed
            ),
            traits={
                "position-1-background": TraitCategory(
                    "Background",
                    True,
                    GridPosition(0, 0),
                    [
                        TraitVariant("Var1", "file1.png", 100),
                        TraitVariant("Var2", "file2.png", 100)
                    ]  # Only 2 variants, max 2 combinations
                )
            },
            rarity=RarityConfig("weighted_random", True, {"common": RarityTier(50, 100)}),
            validation=ValidationConfig(True, False, True, True)
        )
        
        result = self.validator.validate_config(config)
        
        # Should have generation feasibility error
        feasibility_errors = [issue for issue in result.errors if issue.category == "generation_feasibility"]
        self.assertTrue(len(feasibility_errors) > 0)


class TestFileValidation(unittest.TestCase):
    """Test cases for file-based validation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create test trait files
        self.traits_dir = self.temp_dir / "traits"
        self.traits_dir.mkdir()
        
        trait_dir = self.traits_dir / "position-1-background"
        trait_dir.mkdir()
        
        # Create a dummy PNG file (not a real image, but enough for testing)
        test_file = trait_dir / "test-trait.png"
        safe_write_file(str(test_file), "FAKE PNG CONTENT")
        
        # Create config for testing
        config_data = create_sample_config()
        self.config = parse_config_dict(config_data)
        
        self.validator = ConfigurationLogicValidator(check_file_existence=True)
    
    def tearDown(self):
        """Clean up test fixtures"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_file_existence_validation(self):
        """Test trait file existence validation"""
        # Test with non-existent traits directory
        result = self.validator.validate_config(self.config, "/nonexistent/path")
        
        # Should have file validation errors
        file_errors = [issue for issue in result.errors if issue.category == "file_validation"]
        self.assertTrue(len(file_errors) > 0)
    
    def test_missing_trait_files(self):
        """Test validation with missing trait files"""
        # Create config with files that don't exist
        config = GenConfig(
            collection=CollectionConfig("Test", "Test", 100, "TEST", "https://example.com"),
            generation=GenerationConfig(
                "PNG",
                ImageSize(600, 600),
                GridConfig(3, 3, CellSize(200, 200)),
                "#FFFFFF",
                False
            ),
            traits={
                "position-1-background": TraitCategory(
                    "Background",
                    True,
                    GridPosition(0, 0),
                    [TraitVariant("Missing", "nonexistent.png", 100)]
                )
            },
            rarity=RarityConfig("weighted_random", True, {"common": RarityTier(50, 100)}),
            validation=ValidationConfig(True, False, True, True)
        )
        
        result = self.validator.validate_config(config, str(self.traits_dir))
        
        # Should have file validation errors for missing files
        file_errors = [issue for issue in result.errors if issue.category == "file_validation"]
        self.assertTrue(len(file_errors) > 0)


class TestConvenienceFunctions(unittest.TestCase):
    """Test cases for convenience functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        config_data = create_sample_config()
        self.config = parse_config_dict(config_data)
    
    def test_validate_config_logic_function(self):
        """Test validate_config_logic convenience function"""
        # Test with default parameters
        result = validate_config_logic(self.config)
        self.assertIsInstance(result, ValidationResult)
        
        # Test with custom parameters
        result_strict = validate_config_logic(
            self.config,
            check_file_existence=False,
            strict_mode=True
        )
        self.assertIsInstance(result_strict, ValidationResult)
    
    def test_get_validation_report_function(self):
        """Test get_validation_report function"""
        # Create result with various issue types
        issues = [
            ValidationIssue(ValidationSeverity.ERROR, "test", "Error message", "path.error"),
            ValidationIssue(ValidationSeverity.WARNING, "test", "Warning message", "path.warning", "Fix suggestion"),
            ValidationIssue(ValidationSeverity.INFO, "test", "Info message")
        ]
        result = ValidationResult(is_valid=False, issues=issues)
        
        report = get_validation_report(result)
        
        # Verify report structure
        self.assertIsInstance(report, str)
        self.assertIn("INVALID", report)
        self.assertIn("ERROR", report)
        self.assertIn("WARNING", report)
        self.assertIn("Info message", report)
        self.assertIn("Fix suggestion", report)
        
        # Test valid result
        valid_result = ValidationResult(is_valid=True, issues=[])
        valid_report = get_validation_report(valid_result)
        self.assertIn("VALID", valid_report)


class TestValidationCategories(unittest.TestCase):
    """Test cases for specific validation categories"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.validator = ConfigurationLogicValidator(check_file_existence=False)
    
    def test_edge_case_configurations(self):
        """Test validation of edge case configurations"""
        # Test minimal configuration
        minimal_config = GenConfig(
            collection=CollectionConfig("Min", "Minimal config", 1, "MIN", "https://example.com"),
            generation=GenerationConfig(
                "PNG",
                ImageSize(300, 300),
                GridConfig(3, 3, CellSize(100, 100)),
                "#FFFFFF",
                True
            ),
            traits={},  # No traits
            rarity=RarityConfig("weighted_random", True, {}),  # No tiers
            validation=ValidationConfig(False, False, False, False)
        )
        
        result = self.validator.validate_config(minimal_config)
        
        # Should identify issues with empty traits and rarity tiers
        self.assertFalse(result.is_valid)
    
    def test_boundary_values(self):
        """Test validation with boundary values"""
        # Test with extreme values
        extreme_config = GenConfig(
            collection=CollectionConfig("Extreme", "Test", 1000000, "EXTREME", "https://example.com"),
            generation=GenerationConfig(
                "PNG",
                ImageSize(6000, 6000),  # Very large
                GridConfig(3, 3, CellSize(2000, 2000)),
                "#FFFFFF",
                False
            ),
            traits={
                "position-1-background": TraitCategory(
                    "Background",
                    True,
                    GridPosition(0, 0),
                    [TraitVariant("Var1", "file1.png", 10000)]  # Very high weight
                )
            },
            rarity=RarityConfig("weighted_random", True, {"common": RarityTier(1, 10000)}),
            validation=ValidationConfig(True, False, True, True)
        )
        
        result = self.validator.validate_config(extreme_config)
        
        # Should have warnings about extreme values
        warnings = result.warnings
        self.assertTrue(len(warnings) > 0)


class TestIntegrationWorkflow(unittest.TestCase):
    """Integration tests for complete validation workflow"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        config_data = create_sample_config()
        self.config = parse_config_dict(config_data)
    
    def tearDown(self):
        """Clean up test fixtures"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_complete_validation_workflow(self):
        """Test complete configuration validation workflow"""
        # Step 1: Create validator
        validator = ConfigurationLogicValidator(
            check_file_existence=False,
            strict_mode=False
        )
        
        # Step 2: Validate configuration
        result = validator.validate_config(self.config)
        
        # Step 3: Verify result structure
        self.assertIsInstance(result, ValidationResult)
        self.assertIsInstance(result.issues, list)
        
        # Step 4: Generate report
        report = get_validation_report(result)
        self.assertIsInstance(report, str)
        
        # Step 5: Check summary
        summary = result.get_summary()
        self.assertIsInstance(summary, dict)
        self.assertIn("is_valid", summary)
        self.assertIn("total_issues", summary)
    
    def test_validation_with_all_checks(self):
        """Test validation with all validation checks enabled"""
        # Create comprehensive configuration
        comprehensive_config = GenConfig(
            collection=CollectionConfig("Comprehensive", "Full test config", 1000, "COMP", "https://example.com"),
            generation=GenerationConfig(
                "PNG",
                ImageSize(600, 600),
                GridConfig(3, 3, CellSize(200, 200)),
                "#FFFFFF",
                False
            ),
            traits={
                f"position-{i+1}-test": TraitCategory(
                    f"Test{i+1}",
                    True,
                    GridPosition(i // 3, i % 3),
                    [
                        TraitVariant(f"Variant{j+1}", f"file{i+1}_{j+1}.png", (j+1) * 10)
                        for j in range(3)
                    ]
                )
                for i in range(9)  # All 9 positions
            },
            rarity=RarityConfig(
                "weighted_random",
                True,
                {
                    "common": RarityTier(20, 30),
                    "uncommon": RarityTier(10, 19),
                    "rare": RarityTier(1, 9)
                }
            ),
            validation=ValidationConfig(True, True, True, True)
        )
        
        validator = ConfigurationLogicValidator(check_file_existence=False)
        result = validator.validate_config(comprehensive_config)
        
        # Should pass most validations for a well-structured config
        self.assertTrue(len(result.errors) == 0 or result.is_valid)


if __name__ == '__main__':
    unittest.main() 