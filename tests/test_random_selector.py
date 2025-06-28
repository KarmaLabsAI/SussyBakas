"""
Tests for Weighted Random Selector (Component 5.2)

This test suite validates the weighted random selector functionality according to
the GenConfig Phase 1 specification and task breakdown requirements.

Test Requirements:
- Select traits based on weighted random distribution
- Statistically correct trait selection
- Selection frequency matches expected probabilities within tolerance
- Integration with existing trait configuration system

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
import statistics

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from rarity.random_selector import (
    select_weighted_random,
    select_trait_variant,
    analyze_selection_accuracy,
    WeightedRandomSelector,
    RandomSelectionError,
    SelectionResult,
    TraitSelectionResult,
    SelectionStatistics,
    create_weighted_random_selector,
)

from rarity.weight_calculator import WeightCalculator

from config.config_parser import TraitCategory, TraitVariant, GridPosition


class TestWeightedRandomSelector(unittest.TestCase):
    """Base test class for weighted random selector components"""
    
    def setUp(self):
        """Setup test fixtures and sample data"""
        # Test weights from Component 5.1 specification
        self.test_weights_basic = [100, 50, 25]
        self.expected_probabilities_basic = [0.571, 0.286, 0.143]
        
        # Additional test cases
        self.test_weights_equal = [50, 50, 50]
        self.test_weights_extreme = [1000, 1, 1]
        self.test_weights_large = [100, 200, 300, 400, 500]
        
        # Test items for selection
        self.test_items_basic = ['A', 'B', 'C']
        self.test_items_large = ['Item1', 'Item2', 'Item3', 'Item4', 'Item5']
        
        # Sample trait category for integration testing
        self.sample_trait_variants = [
            TraitVariant("Red Background", "trait-red-bg-001.png", 100, "#FF0000"),
            TraitVariant("Blue Background", "trait-blue-bg-002.png", 50, "#0000FF"),
            TraitVariant("Green Background", "trait-green-bg-003.png", 25, "#00FF00"),
        ]
        
        self.sample_trait_category = TraitCategory(
            name="Background",
            required=True,
            grid_position=GridPosition(0, 0),
            variants=self.sample_trait_variants
        )
        
        # Selector instances with fixed seed for reproducible testing
        self.selector = WeightedRandomSelector(seed=42)
        self.selector_no_seed = WeightedRandomSelector()
        
        # Statistical test parameters
        self.large_sample_size = 1000
        self.tolerance = 0.05  # 5% tolerance for statistical tests
        
    def tearDown(self):
        """Cleanup test state"""
        # Clear selection history
        self.selector.clear_selection_history()
        self.selector_no_seed.clear_selection_history()
    
    def assertSelectionWithinTolerance(self, actual_freq: float, expected_freq: float, tolerance: float = 0.05):
        """Helper method to assert selection frequency is within tolerance"""
        deviation = abs(actual_freq - expected_freq)
        self.assertLessEqual(deviation, tolerance, 
                           f"Selection frequency {actual_freq} deviates from expected {expected_freq} by {deviation}, exceeds tolerance {tolerance}")


class TestSelectionResult(TestWeightedRandomSelector):
    """Test SelectionResult data structure"""
    
    def test_selection_result_creation(self):
        """Test creating SelectionResult objects"""
        probabilities = [0.571, 0.286, 0.143]
        cumulative = [0.571, 0.857, 1.0]
        
        result = SelectionResult(
            selected_index=0,
            selected_item='A',
            random_value=0.3,
            probabilities=probabilities,
            cumulative_probabilities=cumulative
        )
        
        self.assertEqual(result.selected_index, 0)
        self.assertEqual(result.selected_item, 'A')
        self.assertEqual(result.random_value, 0.3)
        self.assertEqual(result.probabilities, probabilities)
        self.assertEqual(result.cumulative_probabilities, cumulative)
    
    def test_get_selection_info(self):
        """Test get_selection_info method"""
        result = SelectionResult(
            selected_index=1,
            selected_item='B',
            random_value=0.7,
            probabilities=[0.571, 0.286, 0.143],
            cumulative_probabilities=[0.571, 0.857, 1.0]
        )
        
        info = result.get_selection_info()
        
        self.assertIn('selected_index', info)
        self.assertIn('selected_item', info)
        self.assertIn('random_value', info)
        self.assertIn('selected_probability', info)
        self.assertIn('cumulative_range', info)
        
        self.assertEqual(info['selected_index'], 1)
        self.assertEqual(info['selected_item'], 'B')
        self.assertEqual(info['random_value'], 0.7)
        self.assertEqual(info['selected_probability'], 0.286)
        self.assertEqual(info['cumulative_range'], (0.571, 0.857))


class TestWeightedRandomSelectorClass(TestWeightedRandomSelector):
    """Test WeightedRandomSelector class methods"""
    
    def test_basic_weighted_selection(self):
        """Test basic weighted random selection functionality"""
        result = self.selector.select_weighted_random(self.test_weights_basic, self.test_items_basic)
        
        self.assertIsInstance(result, SelectionResult)
        self.assertIn(result.selected_index, [0, 1, 2])
        self.assertIn(result.selected_item, self.test_items_basic)
        self.assertTrue(0.0 <= result.random_value <= 1.0)
        self.assertEqual(len(result.probabilities), 3)
        self.assertEqual(len(result.cumulative_probabilities), 3)
    
    def test_selection_with_indices_only(self):
        """Test selection without providing items list"""
        result = self.selector.select_weighted_random(self.test_weights_basic)
        
        self.assertIsInstance(result, SelectionResult)
        self.assertIn(result.selected_index, [0, 1, 2])
        self.assertIn(result.selected_item, [0, 1, 2])  # Should be indices
        self.assertEqual(result.selected_item, result.selected_index)
    
    def test_reproducible_selection_with_seed(self):
        """Test that selection is reproducible with fixed seed"""
        selector1 = WeightedRandomSelector(seed=123)
        selector2 = WeightedRandomSelector(seed=123)
        
        result1 = selector1.select_weighted_random(self.test_weights_basic, self.test_items_basic)
        result2 = selector2.select_weighted_random(self.test_weights_basic, self.test_items_basic)
        
        self.assertEqual(result1.selected_index, result2.selected_index)
        self.assertEqual(result1.selected_item, result2.selected_item)
        self.assertEqual(result1.random_value, result2.random_value)
    
    def test_selection_history_tracking(self):
        """Test that selection history is properly tracked"""
        initial_history_length = len(self.selector.get_selection_history())
        
        # Perform multiple selections
        for _ in range(5):
            self.selector.select_weighted_random(self.test_weights_basic)
        
        history = self.selector.get_selection_history()
        self.assertEqual(len(history), initial_history_length + 5)
        
        # Clear history
        self.selector.clear_selection_history()
        self.assertEqual(len(self.selector.get_selection_history()), 0)
    
    def test_statistical_accuracy(self):
        """Test selection frequency matches expected probabilities within tolerance"""
        # Use larger sample size for statistical validation
        sample_size = 2000
        selection_counts = {0: 0, 1: 0, 2: 0}
        
        # Perform many selections with fixed seed for reproducible results
        selector = WeightedRandomSelector(seed=42)
        for _ in range(sample_size):
            result = selector.select_weighted_random(self.test_weights_basic)
            selection_counts[result.selected_index] += 1
        
        # Calculate actual frequencies
        actual_frequencies = {i: count / sample_size for i, count in selection_counts.items()}
        
        # Compare with expected frequencies (with tolerance)
        for i, expected_freq in enumerate(self.expected_probabilities_basic):
            actual_freq = actual_frequencies[i]
            self.assertSelectionWithinTolerance(actual_freq, expected_freq, self.tolerance)


class TestTraitIntegration(TestWeightedRandomSelector):
    """Test integration with trait category system"""
    
    def test_select_trait_variant(self):
        """Test selecting trait variant from category"""
        result = self.selector.select_trait_variant(self.sample_trait_category)
        
        self.assertIsInstance(result, TraitSelectionResult)
        self.assertIsInstance(result.selected_variant, TraitVariant)
        self.assertIn(result.selected_variant, self.sample_trait_variants)
        self.assertEqual(result.category_name, "Background")
        self.assertIn(result.selected_index, [0, 1, 2])
        self.assertTrue(0.0 <= result.random_value <= 1.0)
    
    def test_trait_selection_probabilities(self):
        """Test trait selection follows expected probabilities"""
        sample_size = 1500
        selection_counts = {0: 0, 1: 0, 2: 0}
        
        selector = WeightedRandomSelector(seed=42)
        for _ in range(sample_size):
            result = selector.select_trait_variant(self.sample_trait_category)
            selection_counts[result.selected_index] += 1
        
        # Validate frequencies match expected probabilities
        for i, expected_freq in enumerate(self.expected_probabilities_basic):
            actual_freq = selection_counts[i] / sample_size
            self.assertSelectionWithinTolerance(actual_freq, expected_freq, self.tolerance)
    
    def test_empty_trait_category(self):
        """Test error handling for empty trait category"""
        empty_category = TraitCategory(
            name="Empty",
            required=False,
            grid_position=GridPosition(0, 0),
            variants=[]
        )
        
        with self.assertRaises(RandomSelectionError):
            self.selector.select_trait_variant(empty_category)


class TestStatisticalAnalysis(TestWeightedRandomSelector):
    """Test statistical analysis functionality"""
    
    def test_analyze_selection_statistics(self):
        """Test selection statistics analysis"""
        stats = self.selector.analyze_selection_statistics(
            self.test_weights_basic, 
            sample_size=1000, 
            tolerance=0.05
        )
        
        self.assertIsInstance(stats, SelectionStatistics)
        self.assertEqual(stats.total_selections, 1000)
        self.assertEqual(len(stats.selection_counts), 3)
        self.assertEqual(len(stats.selection_frequencies), 3)
        self.assertEqual(len(stats.expected_frequencies), 3)
        self.assertEqual(len(stats.frequency_differences), 3)
        self.assertIsInstance(stats.max_deviation, float)
        self.assertIsInstance(stats.within_tolerance, bool)
        self.assertEqual(stats.tolerance, 0.05)
    
    def test_statistics_within_tolerance(self):
        """Test that statistics are within tolerance for known weights"""
        stats = self.selector.analyze_selection_statistics(
            self.test_weights_basic,
            sample_size=2000,
            tolerance=0.05
        )
        
        # Should be within tolerance for large sample size
        self.assertTrue(stats.within_tolerance, 
                       f"Statistics not within tolerance: max deviation {stats.max_deviation}, tolerance {stats.tolerance}")
        
        # Check individual frequencies
        for i, expected_freq in enumerate(self.expected_probabilities_basic):
            actual_freq = stats.selection_frequencies[i]
            self.assertSelectionWithinTolerance(actual_freq, expected_freq, 0.05)


class TestErrorHandling(TestWeightedRandomSelector):
    """Test error handling and validation"""
    
    def test_empty_weights_error(self):
        """Test error handling for empty weights"""
        with self.assertRaises(RandomSelectionError):
            self.selector.select_weighted_random([])
    
    def test_mismatched_items_weights_error(self):
        """Test error handling for mismatched items and weights counts"""
        with self.assertRaises(RandomSelectionError):
            self.selector.select_weighted_random([100, 50], ['A', 'B', 'C'])  # 2 weights, 3 items


class TestConvenienceFunctions(TestWeightedRandomSelector):
    """Test convenience functions"""
    
    def test_select_weighted_random_function(self):
        """Test standalone select_weighted_random function"""
        result = select_weighted_random(self.test_weights_basic, self.test_items_basic, seed=42)
        
        self.assertIsInstance(result, SelectionResult)
        self.assertIn(result.selected_item, self.test_items_basic)
    
    def test_select_trait_variant_function(self):
        """Test standalone select_trait_variant function"""
        result = select_trait_variant(self.sample_trait_category, seed=42)
        
        self.assertIsInstance(result, TraitSelectionResult)
        self.assertIn(result.selected_variant, self.sample_trait_variants)
    
    def test_analyze_selection_accuracy_function(self):
        """Test standalone analyze_selection_accuracy function"""
        stats = analyze_selection_accuracy(
            self.test_weights_basic,
            sample_size=1000,
            tolerance=0.05,
            seed=42
        )
        
        self.assertIsInstance(stats, SelectionStatistics)
        self.assertEqual(stats.total_selections, 1000)
    
    def test_create_weighted_random_selector_function(self):
        """Test create_weighted_random_selector function"""
        selector = create_weighted_random_selector(seed=42, precision=4)
        
        self.assertIsInstance(selector, WeightedRandomSelector)
        self.assertEqual(selector.weight_calculator.precision, 4)


class TestIntegrationWorkflow(TestWeightedRandomSelector):
    """Test complete workflow integration"""
    
    def test_complete_selection_workflow(self):
        """Test complete weighted selection workflow"""
        # Step 1: Create selector
        selector = create_weighted_random_selector(seed=42)
        
        # Step 2: Perform selection
        result = selector.select_weighted_random(self.test_weights_basic, self.test_items_basic)
        
        # Step 3: Validate result
        self.assertIsInstance(result, SelectionResult)
        self.assertIn(result.selected_item, self.test_items_basic)
        
        # Step 4: Get selection info
        info = result.get_selection_info()
        self.assertIn('selected_index', info)
        
        # Step 5: Check history
        history = selector.get_selection_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].selected_item, result.selected_item)


if __name__ == '__main__':
    unittest.main() 