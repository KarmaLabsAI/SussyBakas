"""
Tests for Collection Feasibility Checker (Component 5.4)

This test suite validates the collection feasibility checking functionality according to
the GenConfig Phase 1 specification and task breakdown requirements.

Test Requirements:
- Validate collection size against available trait combinations
- Feasibility analysis and warnings as testable output
- Correctly calculates maximum unique combinations
- Integration with existing configuration system

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

from rarity.feasibility_checker import (
    check_collection_feasibility,
    calculate_max_unique_combinations,
    is_collection_size_feasible,
    suggest_optimal_collection_size,
    get_feasibility_report,
    CollectionFeasibilityChecker,
    FeasibilityCheckError,
    CollectionFeasibilityResult,
    CombinationSpaceAnalysis,
    CategoryCombinationAnalysis,
    FeasibilityWarning,
    FeasibilityLevel,
    WarningType,
    FeasibilityRecommendations,
    create_feasibility_checker,
)

from config.config_parser import (
    GenConfig, TraitCategory, TraitVariant, GridPosition,
    CollectionConfig, GenerationConfig, RarityConfig, ValidationConfig,
    ImageSize, GridConfig, CellSize, RarityTier
)


class TestFeasibilityChecker(unittest.TestCase):
    """Base test class for feasibility checker components"""
    
    def setUp(self):
        """Setup test fixtures and sample data"""
        # Create sample trait variants with different counts
        self.small_variants = [
            TraitVariant("Variant 1", "trait-v1-001.png", 100),
            TraitVariant("Variant 2", "trait-v2-002.png", 50),
        ]
        
        self.medium_variants = [
            TraitVariant("Variant A", "trait-va-001.png", 100),
            TraitVariant("Variant B", "trait-vb-002.png", 80),
            TraitVariant("Variant C", "trait-vc-003.png", 60),
        ]
        
        self.large_variants = [
            TraitVariant("Option 1", "trait-o1-001.png", 100),
            TraitVariant("Option 2", "trait-o2-002.png", 80),
            TraitVariant("Option 3", "trait-o3-003.png", 60),
            TraitVariant("Option 4", "trait-o4-004.png", 40),
            TraitVariant("Option 5", "trait-o5-005.png", 20),
        ]
        
        # Create sample trait categories
        self.small_category = TraitCategory(
            name="Small Category",
            required=True,
            grid_position=GridPosition(0, 0),
            variants=self.small_variants
        )
        
        self.medium_category = TraitCategory(
            name="Medium Category",
            required=True,
            grid_position=GridPosition(1, 1),
            variants=self.medium_variants
        )
        
        self.large_category = TraitCategory(
            name="Large Category",
            required=False,
            grid_position=GridPosition(2, 2),
            variants=self.large_variants
        )
        
        self.empty_category = TraitCategory(
            name="Empty Category",
            required=False,
            grid_position=GridPosition(0, 1),
            variants=[]
        )
        
        self.single_variant_category = TraitCategory(
            name="Single Variant",
            required=True,
            grid_position=GridPosition(1, 0),
            variants=[TraitVariant("Only One", "trait-only-001.png", 100)]
        )
        
        # Create sample configurations
        self.feasible_config = self._create_feasible_config()
        self.challenging_config = self._create_challenging_config()
        self.infeasible_config = self._create_infeasible_config()
        self.optimal_config = self._create_optimal_config()
        
        # Checker instances
        self.checker = CollectionFeasibilityChecker()
        
    def tearDown(self):
        """Cleanup test state"""
        # No persistent state to clean up for this component
        pass
    
    def _create_feasible_config(self) -> GenConfig:
        """Create a feasible configuration"""
        return GenConfig(
            collection=CollectionConfig(
                name="Feasible Collection",
                description="Test collection for feasibility",
                size=15,  # 2 * 3 * 5 = 30 max combinations, 50% utilization
                symbol="FEAS",
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
                "position-1-background": self.small_category,
                "position-5-center": self.medium_category,
                "position-9-overlay": self.large_category,
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
    
    def _create_challenging_config(self) -> GenConfig:
        """Create a challenging configuration"""
        config = self._create_feasible_config()
        config.collection.size = 28  # 93% utilization
        return config
    
    def _create_infeasible_config(self) -> GenConfig:
        """Create an infeasible configuration"""
        config = self._create_feasible_config()
        config.collection.size = 50  # Exceeds 30 max combinations
        return config
    
    def _create_optimal_config(self) -> GenConfig:
        """Create an optimal configuration"""
        config = self._create_feasible_config()
        config.collection.size = 10  # 33% utilization
        return config


class TestFeasibilityDataStructures(TestFeasibilityChecker):
    """Test feasibility data structures"""
    
    def test_feasibility_warning_creation(self):
        """Test creating FeasibilityWarning objects"""
        warning = FeasibilityWarning(
            warning_type=WarningType.HIGH_UTILIZATION,
            severity="high",
            message="Test warning message",
            category_key="test_category",
            category_name="Test Category",
            affected_value=90,
            recommended_value=70,
            recommendation="Test recommendation"
        )
        
        self.assertEqual(warning.warning_type, WarningType.HIGH_UTILIZATION)
        self.assertEqual(warning.severity, "high")
        self.assertEqual(warning.message, "Test warning message")
        self.assertEqual(warning.category_key, "test_category")
        self.assertEqual(warning.affected_value, 90)
    
    def test_combination_space_analysis_creation(self):
        """Test creating CombinationSpaceAnalysis objects"""
        analysis = CombinationSpaceAnalysis(
            total_possible_combinations=1000,
            collection_size=700,
            utilization_ratio=0.7,
            utilization_percentage=70.0,
            requires_duplicates=False,
            combination_efficiency_score=0.85,
            category_analyses={}
        )
        
        self.assertEqual(analysis.total_possible_combinations, 1000)
        self.assertEqual(analysis.collection_size, 700)
        self.assertAlmostEqual(analysis.utilization_ratio, 0.7)
        self.assertFalse(analysis.requires_duplicates)
    
    def test_feasibility_level_enum(self):
        """Test FeasibilityLevel enum values"""
        self.assertEqual(FeasibilityLevel.OPTIMAL.value, "optimal")
        self.assertEqual(FeasibilityLevel.FEASIBLE.value, "feasible")
        self.assertEqual(FeasibilityLevel.CHALLENGING.value, "challenging")
        self.assertEqual(FeasibilityLevel.INFEASIBLE.value, "infeasible")


class TestCollectionFeasibilityCheckerClass(TestFeasibilityChecker):
    """Test CollectionFeasibilityChecker class methods"""
    
    def test_check_feasibility_basic(self):
        """Test basic feasibility checking"""
        result = self.checker.check_feasibility(self.feasible_config)
        
        self.assertIsInstance(result, CollectionFeasibilityResult)
        self.assertIsInstance(result.is_feasible, bool)
        self.assertIsInstance(result.feasibility_level, FeasibilityLevel)
        self.assertIsInstance(result.combination_analysis, CombinationSpaceAnalysis)
        self.assertIsInstance(result.warnings, list)
        self.assertIsInstance(result.recommendations, FeasibilityRecommendations)
        self.assertGreater(result.max_unique_combinations, 0)
    
    def test_calculate_max_combinations(self):
        """Test calculating maximum combinations"""
        max_combinations = self.checker.calculate_max_combinations(self.feasible_config)
        
        # Expected: 2 * 3 * 5 = 30 combinations
        self.assertEqual(max_combinations, 30)
    
    def test_calculate_max_combinations_with_empty_category(self):
        """Test max combinations with empty category"""
        config_with_empty = self._create_feasible_config()
        config_with_empty.traits["empty_category"] = self.empty_category
        
        max_combinations = self.checker.calculate_max_combinations(config_with_empty)
        
        # Should be 0 if any category is empty
        self.assertEqual(max_combinations, 0)
    
    def test_check_collection_size_feasibility(self):
        """Test quick feasibility checking"""
        feasible = self.checker.check_collection_size_feasibility(self.feasible_config)
        infeasible = self.checker.check_collection_size_feasibility(self.infeasible_config)
        
        self.assertIsInstance(feasible, bool)
        self.assertIsInstance(infeasible, bool)
        self.assertTrue(feasible)  # Should be feasible
        self.assertFalse(infeasible)  # Should be infeasible
    
    def test_suggest_optimal_collection_size(self):
        """Test optimal collection size suggestion"""
        optimal_size = self.checker.suggest_optimal_collection_size(self.feasible_config)
        
        # Expected: 70% of 30 = 21
        expected_optimal = int(30 * 0.7)
        self.assertEqual(optimal_size, expected_optimal)
    
    def test_get_collection_size_recommendations(self):
        """Test collection size recommendations"""
        recommendations = self.checker.get_collection_size_recommendations(self.feasible_config)
        
        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0)
        self.assertTrue(all(isinstance(size, int) for size in recommendations))
        self.assertEqual(recommendations, sorted(recommendations))  # Should be sorted
    
    def test_feasibility_levels(self):
        """Test different feasibility levels"""
        optimal_result = self.checker.check_feasibility(self.optimal_config)
        feasible_result = self.checker.check_feasibility(self.feasible_config)
        challenging_result = self.checker.check_feasibility(self.challenging_config)
        infeasible_result = self.checker.check_feasibility(self.infeasible_config)
        
        self.assertEqual(optimal_result.feasibility_level, FeasibilityLevel.OPTIMAL)
        self.assertEqual(feasible_result.feasibility_level, FeasibilityLevel.OPTIMAL)  # 50% utilization is optimal
        self.assertEqual(challenging_result.feasibility_level, FeasibilityLevel.CHALLENGING)
        self.assertEqual(infeasible_result.feasibility_level, FeasibilityLevel.INFEASIBLE)


class TestMaxCombinationsCalculation(TestFeasibilityChecker):
    """Test maximum combinations calculation logic"""
    
    def test_simple_combination_calculation(self):
        """Test simple combination calculation"""
        # 2 variants in each of 2 categories = 4 combinations
        simple_config = self._create_feasible_config()
        simple_config.traits = {
            "category1": self.small_category,
            "category2": self.small_category,
        }
        
        max_combinations = self.checker.calculate_max_combinations(simple_config)
        self.assertEqual(max_combinations, 4)  # 2 * 2 = 4
    
    def test_complex_combination_calculation(self):
        """Test complex combination calculation"""
        # Expected: 2 * 3 * 5 = 30 combinations
        max_combinations = self.checker.calculate_max_combinations(self.feasible_config)
        self.assertEqual(max_combinations, 30)
    
    def test_single_category_combinations(self):
        """Test combinations with single category"""
        single_config = self._create_feasible_config()
        single_config.traits = {"single": self.medium_category}
        
        max_combinations = self.checker.calculate_max_combinations(single_config)
        self.assertEqual(max_combinations, 3)  # Only one category with 3 variants
    
    def test_no_traits_combinations(self):
        """Test combinations with no traits"""
        empty_config = self._create_feasible_config()
        empty_config.traits = {}
        
        max_combinations = self.checker.calculate_max_combinations(empty_config)
        self.assertEqual(max_combinations, 0)


class TestFeasibilityWarnings(TestFeasibilityChecker):
    """Test feasibility warning generation"""
    
    def test_insufficient_combinations_warning(self):
        """Test insufficient combinations warning"""
        result = self.checker.check_feasibility(self.infeasible_config)
        
        insufficient_warnings = [w for w in result.warnings 
                               if w.warning_type == WarningType.INSUFFICIENT_COMBINATIONS]
        self.assertGreater(len(insufficient_warnings), 0)
        
        warning = insufficient_warnings[0]
        self.assertEqual(warning.severity, "critical")
        self.assertIn("exceeds maximum unique combinations", warning.message)
    
    def test_high_utilization_warning(self):
        """Test high utilization warning"""
        result = self.checker.check_feasibility(self.challenging_config)
        
        utilization_warnings = [w for w in result.warnings 
                              if w.warning_type == WarningType.HIGH_UTILIZATION]
        self.assertGreater(len(utilization_warnings), 0)
        
        warning = utilization_warnings[0]
        self.assertIn(warning.severity, ["medium", "high"])
        self.assertIn("utilization", warning.message.lower())
    
    def test_empty_category_warning(self):
        """Test empty category warning"""
        config_with_empty = self._create_feasible_config()
        config_with_empty.traits["empty"] = self.empty_category
        
        result = self.checker.check_feasibility(config_with_empty)
        
        empty_warnings = [w for w in result.warnings 
                         if w.warning_type == WarningType.EMPTY_CATEGORIES]
        self.assertGreater(len(empty_warnings), 0)
        
        warning = empty_warnings[0]
        self.assertEqual(warning.severity, "critical")
        self.assertIn("no variants", warning.message)
    
    def test_single_variant_warning(self):
        """Test single variant category warning"""
        config_with_single = self._create_feasible_config()
        config_with_single.traits["single"] = self.single_variant_category
        
        result = self.checker.check_feasibility(config_with_single)
        
        single_warnings = [w for w in result.warnings 
                          if w.warning_type == WarningType.SINGLE_VARIANT_CATEGORIES]
        self.assertGreater(len(single_warnings), 0)
        
        warning = single_warnings[0]
        self.assertEqual(warning.severity, "medium")
        self.assertIn("only one variant", warning.message)


class TestFeasibilityRecommendations(TestFeasibilityChecker):
    """Test feasibility recommendation generation"""
    
    def test_optimal_size_recommendation(self):
        """Test optimal size recommendation"""
        result = self.checker.check_feasibility(self.challenging_config)
        
        # Should recommend optimal size different from current
        if result.recommendations.optimal_collection_size:
            self.assertNotEqual(result.recommendations.optimal_collection_size, 
                              self.challenging_config.collection.size)
    
    def test_suggested_collection_sizes(self):
        """Test suggested collection sizes"""
        result = self.checker.check_feasibility(self.feasible_config)
        
        suggested = result.recommendations.suggested_collection_sizes
        self.assertIsInstance(suggested, list)
        self.assertGreater(len(suggested), 0)
        self.assertEqual(suggested, sorted(suggested))
    
    def test_variant_recommendations(self):
        """Test variant count recommendations"""
        config_with_issues = self._create_feasible_config()
        config_with_issues.traits["empty"] = self.empty_category
        config_with_issues.traits["single"] = self.single_variant_category
        
        result = self.checker.check_feasibility(config_with_issues)
        
        variant_recs = result.recommendations.variant_recommendations
        self.assertIn("empty", variant_recs)
        self.assertIn("single", variant_recs)
        self.assertEqual(variant_recs["empty"], 3)  # Suggest at least 3 variants
        self.assertEqual(variant_recs["single"], 3)


class TestErrorHandling(TestFeasibilityChecker):
    """Test error handling and validation"""
    
    def test_feasibility_check_error(self):
        """Test FeasibilityCheckError exception"""
        # This test verifies the exception exists and can be raised
        with self.assertRaises(FeasibilityCheckError):
            raise FeasibilityCheckError("Test error message")
    
    def test_invalid_config_handling(self):
        """Test handling of invalid configurations"""
        # Test with None config should raise error
        with self.assertRaises(FeasibilityCheckError):
            self.checker.check_feasibility(None)


class TestConvenienceFunctions(TestFeasibilityChecker):
    """Test convenience functions"""
    
    def test_check_collection_feasibility_function(self):
        """Test standalone check_collection_feasibility function"""
        result = check_collection_feasibility(self.feasible_config)
        
        self.assertIsInstance(result, CollectionFeasibilityResult)
        self.assertIsInstance(result.is_feasible, bool)
    
    def test_calculate_max_unique_combinations_function(self):
        """Test standalone calculate_max_unique_combinations function"""
        max_combinations = calculate_max_unique_combinations(self.feasible_config)
        
        self.assertIsInstance(max_combinations, int)
        self.assertEqual(max_combinations, 30)  # Expected for feasible_config
    
    def test_is_collection_size_feasible_function(self):
        """Test standalone is_collection_size_feasible function"""
        feasible = is_collection_size_feasible(self.feasible_config)
        infeasible = is_collection_size_feasible(self.infeasible_config)
        
        self.assertIsInstance(feasible, bool)
        self.assertIsInstance(infeasible, bool)
        self.assertTrue(feasible)
        self.assertFalse(infeasible)
    
    def test_suggest_optimal_collection_size_function(self):
        """Test standalone suggest_optimal_collection_size function"""
        optimal_size = suggest_optimal_collection_size(self.feasible_config)
        
        self.assertIsInstance(optimal_size, int)
        self.assertGreater(optimal_size, 0)
    
    def test_get_feasibility_report_function(self):
        """Test get_feasibility_report function"""
        result = check_collection_feasibility(self.feasible_config)
        report = get_feasibility_report(result)
        
        self.assertIsInstance(report, str)
        self.assertIn("Collection Feasibility Analysis Report", report)
        self.assertIn("Combination Space Analysis:", report)
    
    def test_create_feasibility_checker_function(self):
        """Test create_feasibility_checker function"""
        checker = create_feasibility_checker(optimal_threshold=0.6, challenging_threshold=0.8)
        
        self.assertIsInstance(checker, CollectionFeasibilityChecker)
        self.assertAlmostEqual(checker.optimal_threshold, 0.6)
        self.assertAlmostEqual(checker.challenging_threshold, 0.8)


class TestIntegrationWorkflow(TestFeasibilityChecker):
    """Test complete workflow integration"""
    
    def test_complete_feasibility_workflow(self):
        """Test complete feasibility workflow"""
        # Step 1: Create checker
        checker = create_feasibility_checker(optimal_threshold=0.7, challenging_threshold=0.9)
        
        # Step 2: Check feasibility
        result = checker.check_feasibility(self.feasible_config)
        
        # Step 3: Validate result structure
        self.assertIsInstance(result, CollectionFeasibilityResult)
        self.assertIsInstance(result.is_feasible, bool)
        self.assertGreater(result.max_unique_combinations, 0)
        
        # Step 4: Generate report
        report = get_feasibility_report(result)
        self.assertIsInstance(report, str)
        self.assertIn("Feasibility Analysis Report", report)
        
        # Step 5: Check specific calculations
        max_combinations = calculate_max_unique_combinations(self.feasible_config)
        self.assertEqual(max_combinations, result.max_unique_combinations)
    
    def test_task_breakdown_requirements(self):
        """Test specific task breakdown requirements"""
        # Task: Validate collection size against available trait combinations
        result = check_collection_feasibility(self.feasible_config)
        
        # Testable Output: Feasibility analysis and warnings
        self.assertIsInstance(result, CollectionFeasibilityResult)
        self.assertIsInstance(result.warnings, list)
        self.assertIsInstance(result.combination_analysis, CombinationSpaceAnalysis)
        
        # Test: Correctly calculates maximum unique combinations
        max_combinations = calculate_max_unique_combinations(self.feasible_config)
        expected_combinations = 2 * 3 * 5  # small * medium * large categories
        self.assertEqual(max_combinations, expected_combinations)
        
        # Validate feasibility analysis accuracy
        self.assertEqual(result.max_unique_combinations, max_combinations)
        self.assertEqual(result.collection_size, self.feasible_config.collection.size)
    
    def test_edge_cases_and_boundary_conditions(self):
        """Test edge cases and boundary conditions"""
        # Test with exactly maximum combinations
        exact_config = self._create_feasible_config()
        exact_config.collection.size = 30  # Exactly max combinations
        
        result = check_collection_feasibility(exact_config)
        self.assertFalse(result.is_feasible)  # 100% utilization is not feasible
        self.assertEqual(result.feasibility_level, FeasibilityLevel.INFEASIBLE)  # 100% utilization is infeasible
        
        # Test with single combination possible
        single_config = self._create_feasible_config()
        single_config.traits = {"single": self.single_variant_category}
        single_config.collection.size = 1
        
        result = check_collection_feasibility(single_config)
        self.assertTrue(result.is_feasible)
        self.assertEqual(result.feasibility_level, FeasibilityLevel.CHALLENGING)  # Small collections can use 100%
        self.assertEqual(result.max_unique_combinations, 1)
    
    def test_integration_with_existing_components(self):
        """Test integration with existing configuration components"""
        # This test validates that the feasibility checker works with existing GenConfig
        # structures from the configuration parser
        
        # Test with all trait categories from feasible config
        for trait_key, trait_category in self.feasible_config.traits.items():
            self.assertIsInstance(trait_category, TraitCategory)
            self.assertIsInstance(trait_category.variants, list)
            self.assertGreater(len(trait_category.variants), 0)
        
        # Test that feasibility checker correctly processes the config
        result = check_collection_feasibility(self.feasible_config)
        
        # Validate that all categories are analyzed
        self.assertEqual(len(result.combination_analysis.category_analyses), 
                        len(self.feasible_config.traits))
        
        # Validate category analysis data
        for trait_key in self.feasible_config.traits.keys():
            self.assertIn(trait_key, result.combination_analysis.category_analyses)
            category_analysis = result.combination_analysis.category_analyses[trait_key]
            self.assertIsInstance(category_analysis, CategoryCombinationAnalysis)


if __name__ == '__main__':
    unittest.main() 