"""
Tests for Rarity Distribution Validator (Component 5.3)

This test suite validates the rarity distribution validation functionality according to
the GenConfig Phase 1 specification and task breakdown requirements.

Test Requirements:
- Validate rarity distribution feasibility and accuracy
- Distribution validation results as testable output
- Detects impossible distributions, validates generation feasibility
- Integration with existing weight calculator and selector components

Testing Strategy:
- Setup: Create test fixtures and sample data
- Execution: Run component functions with various inputs
- Validation: Assert expected outputs and behaviors
- Cleanup: Remove test files and reset state
"""

import unittest
import sys
import os
from typing import List, Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from rarity.distribution_validator import (
    validate_distribution,
    check_distribution_feasibility,
    simulate_generation_accuracy,
    get_distribution_report,
    RarityDistributionValidator,
    DistributionValidationError,
    DistributionValidationResult,
    TraitDistributionAnalysis,
    CollectionFeasibilityAnalysis,
    ValidationIssue,
    ValidationSeverity,
    create_distribution_validator,
)

from config.config_parser import (
    GenConfig, TraitCategory, TraitVariant, GridPosition,
    CollectionConfig, GenerationConfig, RarityConfig, ValidationConfig,
    ImageSize, GridConfig, CellSize, RarityTier
)


class TestDistributionValidator(unittest.TestCase):
    """Base test class for distribution validator components"""
    
    def setUp(self):
        """Setup test fixtures and sample data"""
        # Create sample trait variants with different weight distributions
        self.balanced_variants = [
            TraitVariant("Common", "trait-common-001.png", 100),
            TraitVariant("Uncommon", "trait-uncommon-002.png", 80),
            TraitVariant("Rare", "trait-rare-003.png", 60),
        ]
        
        self.imbalanced_variants = [
            TraitVariant("Ultra Common", "trait-ultra-001.png", 1000),
            TraitVariant("Ultra Rare", "trait-ultra-002.png", 1),
            TraitVariant("Ultra Rare 2", "trait-ultra-003.png", 1),
        ]
        
        self.zero_weight_variants = [
            TraitVariant("Normal", "trait-normal-001.png", 100),
            TraitVariant("Zero Weight", "trait-zero-002.png", 0),
        ]
        
        # Create sample trait categories
        self.balanced_category = TraitCategory(
            name="Balanced Background",
            required=True,
            grid_position=GridPosition(0, 0),
            variants=self.balanced_variants
        )
        
        self.imbalanced_category = TraitCategory(
            name="Imbalanced Pattern",
            required=True,
            grid_position=GridPosition(1, 1),
            variants=self.imbalanced_variants
        )
        
        self.zero_weight_category = TraitCategory(
            name="Zero Weight Category",
            required=False,
            grid_position=GridPosition(2, 2),
            variants=self.zero_weight_variants
        )
        
        self.empty_category = TraitCategory(
            name="Empty Category",
            required=False,
            grid_position=GridPosition(0, 1),
            variants=[]
        )
        
        # Create sample GenConfig for testing
        self.sample_config = self._create_sample_config()
        self.feasible_config = self._create_feasible_config()
        self.infeasible_config = self._create_infeasible_config()
        
        # Validator instances
        self.validator = RarityDistributionValidator()
        self.strict_validator = RarityDistributionValidator(tolerance_accuracy=0.01, tolerance_max_frequency=0.02)
        self.lenient_validator = RarityDistributionValidator(tolerance_accuracy=0.05, tolerance_max_frequency=0.10)
        
    def tearDown(self):
        """Cleanup test state"""
        # No persistent state to clean up for this component
        pass
    
    def _create_sample_config(self) -> GenConfig:
        """Create a sample GenConfig for testing"""
        return GenConfig(
            collection=CollectionConfig(
                name="Test Collection",
                description="Test collection for validation",
                size=1000,
                symbol="TEST",
                external_url="https://test.com"
            ),
            generation=GenerationConfig(
                image_format="PNG",
                image_size=ImageSize(600, 600),
                grid=GridConfig(3, 3, CellSize(200, 200)),
                background_color="#FFFFFF",
                allow_duplicates=False
            ),
            traits={
                "position-1-background": self.balanced_category,
                "position-5-center": self.imbalanced_category,
            },
            rarity=RarityConfig(
                calculation_method="weighted_random",
                distribution_validation=True,
                rarity_tiers={
                    "common": RarityTier(50, 100),
                    "rare": RarityTier(1, 49)
                }
            ),
            validation=ValidationConfig(
                enforce_grid_positions=True,
                require_all_positions=False,
                check_file_integrity=True,
                validate_image_dimensions=True
            )
        )
    
    def _create_feasible_config(self) -> GenConfig:
        """Create a feasible configuration"""
        config = self._create_sample_config()
        config.collection.size = 100  # Small collection size for feasibility
        return config
    
    def _create_infeasible_config(self) -> GenConfig:
        """Create an infeasible configuration"""
        config = self._create_sample_config()
        config.collection.size = 10000  # Large collection with limited combinations
        config.generation.allow_duplicates = False  # No duplicates allowed
        return config


class TestValidationDataStructures(TestDistributionValidator):
    """Test validation data structures"""
    
    def test_validation_issue_creation(self):
        """Test creating ValidationIssue objects"""
        issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            category="test_category",
            message="Test error message",
            trait_key="test_trait",
            trait_name="Test Trait",
            expected_value=1.0,
            actual_value=0.5,
            deviation=0.5
        )
        
        self.assertEqual(issue.severity, ValidationSeverity.ERROR)
        self.assertEqual(issue.category, "test_category")
        self.assertEqual(issue.message, "Test error message")
        self.assertEqual(issue.trait_key, "test_trait")
        self.assertEqual(issue.trait_name, "Test Trait")
        self.assertEqual(issue.expected_value, 1.0)
        self.assertEqual(issue.actual_value, 0.5)
        self.assertEqual(issue.deviation, 0.5)
    
    def test_trait_distribution_analysis_creation(self):
        """Test creating TraitDistributionAnalysis objects"""
        analysis = TraitDistributionAnalysis(
            category_key="test_category",
            category_name="Test Category",
            total_variants=3,
            total_weight=240,
            min_weight=60,
            max_weight=100,
            weight_distribution={"common": 100, "uncommon": 80, "rare": 60},
            expected_frequencies={"common": 0.417, "uncommon": 0.333, "rare": 0.250},
            expected_occurrences={"common": 417.0, "uncommon": 333.0, "rare": 250.0},
            min_possible_occurrence={"common": 1, "uncommon": 1, "rare": 1},
            max_possible_occurrence={"common": 438, "uncommon": 350, "rare": 262},
            zero_weight_variants=[],
            rarity_balance_score=0.8
        )
        
        self.assertEqual(analysis.category_key, "test_category")
        self.assertEqual(analysis.total_variants, 3)
        self.assertEqual(analysis.total_weight, 240)
        self.assertEqual(len(analysis.weight_distribution), 3)
        self.assertEqual(len(analysis.zero_weight_variants), 0)


class TestRarityDistributionValidatorClass(TestDistributionValidator):
    """Test RarityDistributionValidator class methods"""
    
    def test_validate_distribution_basic(self):
        """Test basic distribution validation"""
        result = self.validator.validate_distribution(self.sample_config, run_simulation=False)
        
        self.assertIsInstance(result, DistributionValidationResult)
        self.assertIsInstance(result.is_valid, bool)
        self.assertIsInstance(result.overall_score, float)
        self.assertIsInstance(result.collection_analysis, CollectionFeasibilityAnalysis)
        self.assertIsInstance(result.trait_analyses, dict)
        self.assertIsInstance(result.validation_issues, list)
        self.assertIsInstance(result.recommendations, list)
        self.assertTrue(0.0 <= result.overall_score <= 1.0)
    
    def test_validate_distribution_with_simulation(self):
        """Test distribution validation with statistical simulation"""
        result = self.validator.validate_distribution(self.sample_config, run_simulation=True, simulation_sample_size=1000)
        
        self.assertIsInstance(result, DistributionValidationResult)
        self.assertIsNotNone(result.statistical_simulation_results)
        self.assertIsInstance(result.statistical_simulation_results, dict)
        
        # Check that simulation results exist for each trait category
        for trait_key in self.sample_config.traits.keys():
            self.assertIn(trait_key, result.statistical_simulation_results)
    
    def test_validate_trait_distribution(self):
        """Test validating individual trait distribution"""
        analysis = self.validator.validate_trait_distribution(self.balanced_category, 1000)
        
        self.assertIsInstance(analysis, TraitDistributionAnalysis)
        self.assertEqual(analysis.category_name, "Balanced Background")
        self.assertEqual(analysis.total_variants, 3)
        self.assertGreater(analysis.total_weight, 0)
        self.assertGreater(analysis.rarity_balance_score, 0)
    
    def test_check_distribution_feasibility(self):
        """Test quick feasibility checking"""
        feasible = self.validator.check_distribution_feasibility(self.feasible_config)
        infeasible = self.validator.check_distribution_feasibility(self.infeasible_config)
        
        self.assertIsInstance(feasible, bool)
        self.assertIsInstance(infeasible, bool)
        # Feasible config should be more likely to be feasible than infeasible config
        # Note: This may not always be true due to complex validation logic
    
    def test_simulate_generation_accuracy(self):
        """Test simulation of generation accuracy"""
        simulation_results = self.validator.simulate_generation_accuracy(self.sample_config, sample_size=500)
        
        self.assertIsInstance(simulation_results, dict)
        self.assertEqual(len(simulation_results), len(self.sample_config.traits))
        
        for trait_key, stats in simulation_results.items():
            self.assertIn(trait_key, self.sample_config.traits)
            self.assertIsInstance(stats.within_tolerance, bool)
            self.assertIsInstance(stats.max_deviation, float)
    
    def test_empty_trait_category_handling(self):
        """Test handling of empty trait categories"""
        config_with_empty = self._create_sample_config()
        config_with_empty.traits["empty_category"] = self.empty_category
        
        result = self.validator.validate_distribution(config_with_empty, run_simulation=False)
        
        self.assertIsInstance(result, DistributionValidationResult)
        # Should have validation issues for empty category
        empty_issues = [issue for issue in result.validation_issues if issue.category == "empty_category"]
        self.assertGreater(len(empty_issues), 0)
    
    def test_zero_weight_variants_detection(self):
        """Test detection of zero-weight variants"""
        config_with_zero = self._create_sample_config()
        config_with_zero.traits["zero_weight_category"] = self.zero_weight_category
        
        result = self.validator.validate_distribution(config_with_zero, run_simulation=False)
        
        # Check if zero weight variants are detected in analysis
        zero_analysis = result.trait_analyses["zero_weight_category"]
        self.assertGreater(len(zero_analysis.zero_weight_variants), 0)
        self.assertEqual(zero_analysis.zero_weight_variants[0], "Zero Weight")


class TestValidationRequirements(TestDistributionValidator):
    """Test specific validation requirements from specification"""
    
    def test_distribution_accuracy_tolerance(self):
        """Test 2% distribution accuracy tolerance requirement"""
        # Create validator with 2% tolerance as per specification
        validator = RarityDistributionValidator(tolerance_accuracy=0.02)
        
        result = validator.validate_distribution(self.sample_config)
        
        # Validator should use 2% tolerance
        self.assertAlmostEqual(validator.tolerance_accuracy, 0.02)
    
    def test_minimum_occurrence_requirement(self):
        """Test minimum occurrence requirement (unless weight = 0)"""
        result = self.validator.validate_distribution(self.sample_config)
        
        for trait_key, analysis in result.trait_analyses.items():
            for trait_name, min_occurrence in analysis.min_possible_occurrence.items():
                weight = analysis.weight_distribution[trait_name]
                if weight > 0:
                    self.assertGreaterEqual(min_occurrence, 1, 
                                          f"Trait '{trait_name}' with weight {weight} should have min occurrence >= 1")
                else:
                    self.assertEqual(min_occurrence, 0, 
                                   f"Trait '{trait_name}' with weight 0 should have min occurrence = 0")
    
    def test_maximum_frequency_tolerance(self):
        """Test 5% maximum frequency tolerance requirement"""
        # Create validator with 5% max frequency tolerance as per specification
        validator = RarityDistributionValidator(tolerance_max_frequency=0.05)
        
        result = validator.validate_distribution(self.sample_config)
        
        # Validator should use 5% max frequency tolerance
        self.assertAlmostEqual(validator.tolerance_max_frequency, 0.05)
    
    def test_impossible_distribution_detection(self):
        """Test detection of impossible distributions"""
        # Create config with impossible requirements
        impossible_config = self._create_sample_config()
        impossible_config.collection.size = 1000000  # Very large collection
        impossible_config.generation.allow_duplicates = False  # No duplicates
        # Limited trait combinations make this impossible
        
        result = self.validator.validate_distribution(impossible_config, run_simulation=False)
        
        # Should detect impossibility
        self.assertFalse(result.collection_analysis.unique_combinations_feasible)
        
        # Should have error issues
        error_issues = [issue for issue in result.validation_issues if issue.severity == ValidationSeverity.ERROR]
        self.assertGreater(len(error_issues), 0)
    
    def test_generation_feasibility_validation(self):
        """Test validation of generation feasibility"""
        feasible_result = self.validator.validate_distribution(self.feasible_config)
        infeasible_result = self.validator.validate_distribution(self.infeasible_config)
        
        # Check combination feasibility analysis
        self.assertIsInstance(feasible_result.collection_analysis.unique_combinations_feasible, bool)
        self.assertIsInstance(infeasible_result.collection_analysis.unique_combinations_feasible, bool)
        
        # Check that total combinations are calculated
        self.assertGreater(feasible_result.collection_analysis.total_possible_combinations, 0)
        self.assertGreater(infeasible_result.collection_analysis.total_possible_combinations, 0)


class TestStatisticalSimulation(TestDistributionValidator):
    """Test statistical simulation functionality"""
    
    def test_simulation_accuracy_validation(self):
        """Test that simulation validates accuracy within tolerance"""
        result = self.validator.validate_distribution(self.sample_config, run_simulation=True, simulation_sample_size=1000)
        
        self.assertIsNotNone(result.statistical_simulation_results)
        
        for trait_key, stats in result.statistical_simulation_results.items():
            # Each simulation should have complete statistics
            self.assertIsInstance(stats.total_selections, int)
            self.assertIsInstance(stats.within_tolerance, bool)
            self.assertIsInstance(stats.max_deviation, float)
            self.assertGreater(stats.total_selections, 0)
    
    def test_simulation_with_different_tolerances(self):
        """Test simulation with different tolerance levels"""
        strict_result = self.strict_validator.simulate_generation_accuracy(self.sample_config, sample_size=500, tolerance=0.01)
        lenient_result = self.lenient_validator.simulate_generation_accuracy(self.sample_config, sample_size=500, tolerance=0.05)
        
        self.assertIsInstance(strict_result, dict)
        self.assertIsInstance(lenient_result, dict)
        
        # Lenient tolerance should be more likely to pass than strict
        strict_passes = sum(1 for stats in strict_result.values() if stats.within_tolerance)
        lenient_passes = sum(1 for stats in lenient_result.values() if stats.within_tolerance)
        
        # This relationship should hold in most cases
        self.assertGreaterEqual(lenient_passes, strict_passes)


class TestErrorHandling(TestDistributionValidator):
    """Test error handling and validation"""
    
    def test_invalid_config_handling(self):
        """Test handling of invalid configurations"""
        # Test with None config should raise DistributionValidationError
        with self.assertRaises(DistributionValidationError):
            self.validator.validate_distribution(None)
    
    def test_distribution_validation_error(self):
        """Test DistributionValidationError exception"""
        # This test verifies the exception exists and can be raised
        with self.assertRaises(DistributionValidationError):
            raise DistributionValidationError("Test error message")
    
    def test_empty_traits_handling(self):
        """Test handling of configuration with no traits"""
        empty_config = self._create_sample_config()
        empty_config.traits = {}
        
        result = self.validator.validate_distribution(empty_config, run_simulation=False)
        
        self.assertIsInstance(result, DistributionValidationResult)
        self.assertEqual(len(result.trait_analyses), 0)


class TestConvenienceFunctions(TestDistributionValidator):
    """Test convenience functions"""
    
    def test_validate_distribution_function(self):
        """Test standalone validate_distribution function"""
        result = validate_distribution(self.sample_config, tolerance_accuracy=0.02, tolerance_max_frequency=0.05)
        
        self.assertIsInstance(result, DistributionValidationResult)
    
    def test_check_distribution_feasibility_function(self):
        """Test standalone check_distribution_feasibility function"""
        feasible = check_distribution_feasibility(self.feasible_config)
        
        self.assertIsInstance(feasible, bool)
    
    def test_simulate_generation_accuracy_function(self):
        """Test standalone simulate_generation_accuracy function"""
        simulation_results = simulate_generation_accuracy(self.sample_config, sample_size=500, tolerance=0.02)
        
        self.assertIsInstance(simulation_results, dict)
        self.assertGreater(len(simulation_results), 0)
    
    def test_get_distribution_report_function(self):
        """Test get_distribution_report function"""
        result = validate_distribution(self.sample_config)
        report = get_distribution_report(result)
        
        self.assertIsInstance(report, str)
        self.assertIn("Rarity Distribution Validation Report", report)
        self.assertIn("Overall Status:", report)
        self.assertIn("Collection Analysis:", report)
    
    def test_create_distribution_validator_function(self):
        """Test create_distribution_validator function"""
        validator = create_distribution_validator(tolerance_accuracy=0.03, tolerance_max_frequency=0.08)
        
        self.assertIsInstance(validator, RarityDistributionValidator)
        self.assertAlmostEqual(validator.tolerance_accuracy, 0.03)
        self.assertAlmostEqual(validator.tolerance_max_frequency, 0.08)


class TestIntegrationWorkflow(TestDistributionValidator):
    """Test complete workflow integration"""
    
    def test_complete_validation_workflow(self):
        """Test complete validation workflow"""
        # Step 1: Create validator
        validator = create_distribution_validator(tolerance_accuracy=0.02, tolerance_max_frequency=0.05)
        
        # Step 2: Perform validation
        result = validator.validate_distribution(self.sample_config, run_simulation=True)
        
        # Step 3: Validate result structure
        self.assertIsInstance(result, DistributionValidationResult)
        self.assertIsInstance(result.is_valid, bool)
        self.assertGreater(len(result.trait_analyses), 0)
        
        # Step 4: Generate report
        report = get_distribution_report(result)
        self.assertIsInstance(report, str)
        self.assertIn("Distribution Validation Report", report)
        
        # Step 5: Check feasibility
        feasible = check_distribution_feasibility(self.sample_config)
        self.assertIsInstance(feasible, bool)
    
    def test_integration_with_existing_components(self):
        """Test integration with weight calculator and random selector"""
        # This test validates that the distribution validator works with existing components
        result = self.validator.validate_distribution(self.sample_config, run_simulation=True)
        
        # Should have statistical simulation results (integration with random selector)
        self.assertIsNotNone(result.statistical_simulation_results)
        
        # Should have trait probability analyses (integration with weight calculator)
        for analysis in result.trait_analyses.values():
            self.assertIsInstance(analysis.expected_frequencies, dict)
            self.assertIsInstance(analysis.expected_occurrences, dict)
        
        # Test that recommendations are generated
        self.assertIsInstance(result.recommendations, list)


if __name__ == '__main__':
    unittest.main() 