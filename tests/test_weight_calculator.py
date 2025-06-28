"""
Tests for Weight Calculator (Component 5.1)

This test suite validates the weight calculator functionality according to
the GenConfig Phase 1 specification and task breakdown requirements.

Test Requirements:
- Weights [100, 50, 25] = probabilities [57.1%, 28.6%, 14.3%]
- Accurate probability distributions for rarity weights
- Error handling for invalid inputs
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
import math

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from rarity.weight_calculator import (
    calculate_probabilities,
    calculate_trait_probabilities,
    WeightCalculator,
    WeightCalculationError,
    WeightCalculationResult,
    TraitProbabilityInfo,
    validate_weights,
    normalize_probabilities,
    get_cumulative_probabilities,
    create_weight_calculator,
)

from config.config_parser import TraitCategory, TraitVariant, GridPosition


class TestWeightCalculator(unittest.TestCase):
    """Base test class for weight calculator components"""
    
    def setUp(self):
        """Setup test fixtures and sample data"""
        # Core test data from task specification
        self.test_weights_basic = [100, 50, 25]
        self.expected_probabilities_basic = [0.571, 0.286, 0.143]  # 57.1%, 28.6%, 14.3%
        
        # Additional test cases
        self.test_weights_equal = [50, 50, 50]
        self.expected_probabilities_equal = [0.334, 0.333, 0.333]  # Equal distribution with rounding
        
        self.test_weights_extreme = [1000, 1, 1]
        self.expected_probabilities_extreme = [0.998, 0.001, 0.001]  # Extreme rarity
        
        self.test_weights_large = [100, 200, 300, 400, 500]
        
        # Invalid test data for error handling
        self.invalid_weights = [
            [-1, 50, 25],           # Negative weight
            [100, "50", 25],        # Non-integer weight
            [100, 50.5, 25],        # Float weight
            [100, None, 25],        # None weight
            [],                     # Empty list
            [0, 0, 0],             # All zero weights
        ]
        
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
        
        # Calculator instances
        self.calculator = WeightCalculator()
        self.calculator_precise = WeightCalculator(precision=4)
        self.calculator_no_validation = WeightCalculator(validate_inputs=False)
        
    def tearDown(self):
        """Cleanup test state"""
        # No persistent state to clean up for this component
        pass
    
    def assertProbabilitiesClose(self, actual: List[float], expected: List[float], delta: float = 0.001):
        """Helper method to assert probabilities are close within tolerance"""
        self.assertEqual(len(actual), len(expected))
        for i, (a, e) in enumerate(zip(actual, expected)):
            self.assertAlmostEqual(a, e, delta=delta, 
                                 msg=f"Probability at index {i}: expected {e}, got {a}")


class TestWeightCalculationResult(TestWeightCalculator):
    """Test WeightCalculationResult data structure"""
    
    def test_weight_calculation_result_creation(self):
        """Test creating WeightCalculationResult objects"""
        weights = [100, 50, 25]
        probabilities = [0.571, 0.286, 0.143]
        cumulative = [0.571, 0.857, 1.0]
        total_weight = 175
        
        result = WeightCalculationResult(weights, probabilities, total_weight, cumulative)
        
        self.assertEqual(result.weights, weights)
        self.assertEqual(result.probabilities, probabilities)
        self.assertEqual(result.total_weight, total_weight)
        self.assertEqual(result.cumulative_probabilities, cumulative)
    
    def test_get_probability_method(self):
        """Test get_probability method"""
        result = WeightCalculationResult([100, 50, 25], [0.571, 0.286, 0.143], 175, [0.571, 0.857, 1.0])
        
        self.assertEqual(result.get_probability(0), 0.571)
        self.assertEqual(result.get_probability(1), 0.286)
        self.assertEqual(result.get_probability(2), 0.143)
        
        with self.assertRaises(IndexError):
            result.get_probability(3)
        
        with self.assertRaises(IndexError):
            result.get_probability(-1)
    
    def test_get_cumulative_probability_method(self):
        """Test get_cumulative_probability method"""
        result = WeightCalculationResult([100, 50, 25], [0.571, 0.286, 0.143], 175, [0.571, 0.857, 1.0])
        
        self.assertEqual(result.get_cumulative_probability(0), 0.571)
        self.assertEqual(result.get_cumulative_probability(1), 0.857)
        self.assertEqual(result.get_cumulative_probability(2), 1.0)
        
        with self.assertRaises(IndexError):
            result.get_cumulative_probability(3)


class TestWeightCalculatorClass(TestWeightCalculator):
    """Test WeightCalculator class methods"""
    
    def test_core_probability_calculation(self):
        """Test core probability calculation per task specification"""
        # Test the specific requirement: Weights [100, 50, 25] = probabilities [57.1%, 28.6%, 14.3%]
        result = self.calculator.calculate_probabilities(self.test_weights_basic)
        
        self.assertIsInstance(result, WeightCalculationResult)
        self.assertEqual(result.weights, self.test_weights_basic)
        self.assertEqual(result.total_weight, 175)
        self.assertProbabilitiesClose(result.probabilities, self.expected_probabilities_basic)
    
    def test_equal_weights_distribution(self):
        """Test equal weight distribution"""
        result = self.calculator.calculate_probabilities(self.test_weights_equal)
        
        # Equal weights should result in approximately equal probabilities
        self.assertProbabilitiesClose(result.probabilities, self.expected_probabilities_equal)
        self.assertEqual(result.total_weight, 150)
    
    def test_extreme_weight_distribution(self):
        """Test extreme weight distribution"""
        result = self.calculator.calculate_probabilities(self.test_weights_extreme)
        
        self.assertProbabilitiesClose(result.probabilities, self.expected_probabilities_extreme)
        self.assertEqual(result.total_weight, 1002)
    
    def test_large_weight_set(self):
        """Test calculation with larger weight sets"""
        result = self.calculator.calculate_probabilities(self.test_weights_large)
        
        self.assertEqual(len(result.probabilities), 5)
        self.assertEqual(result.total_weight, 1500)
        self.assertAlmostEqual(sum(result.probabilities), 1.0, delta=0.001)
    
    def test_single_weight(self):
        """Test calculation with single weight"""
        result = self.calculator.calculate_probabilities([100])
        
        self.assertEqual(result.probabilities, [1.0])
        self.assertEqual(result.total_weight, 100)
        self.assertEqual(result.cumulative_probabilities, [1.0])
    
    def test_empty_weights(self):
        """Test calculation with empty weight list"""
        result = self.calculator.calculate_probabilities([])
        
        self.assertEqual(result.probabilities, [])
        self.assertEqual(result.total_weight, 0)
        self.assertEqual(result.cumulative_probabilities, [])
    
    def test_precision_settings(self):
        """Test different precision settings"""
        weights = [100, 50, 25]
        
        # Test default precision (3)
        result_default = self.calculator.calculate_probabilities(weights)
        self.assertEqual(len(str(result_default.probabilities[0]).split('.')[-1]), 3)
        
        # Test higher precision (4)
        result_precise = self.calculator_precise.calculate_probabilities(weights)
        self.assertEqual(len(str(result_precise.probabilities[0]).split('.')[-1]), 4)
    
    def test_probability_normalization(self):
        """Test that probabilities always sum to 1.0"""
        test_cases = [
            [100, 50, 25],
            [1, 1, 1],
            [1000, 1, 1],
            [33, 33, 34],
            [7, 11, 13, 17, 19],
        ]
        
        for weights in test_cases:
            with self.subTest(weights=weights):
                result = self.calculator.calculate_probabilities(weights)
                probability_sum = sum(result.probabilities)
                self.assertAlmostEqual(probability_sum, 1.0, delta=0.001)
    
    def test_cumulative_probabilities(self):
        """Test cumulative probability calculation"""
        result = self.calculator.calculate_probabilities([100, 50, 25])
        
        # Cumulative probabilities should be increasing
        for i in range(1, len(result.cumulative_probabilities)):
            self.assertGreaterEqual(result.cumulative_probabilities[i], 
                                  result.cumulative_probabilities[i-1])
        
        # Last cumulative probability should be 1.0
        self.assertEqual(result.cumulative_probabilities[-1], 1.0)


class TestTraitIntegration(TestWeightCalculator):
    """Test integration with trait category system"""
    
    def test_calculate_trait_probabilities(self):
        """Test calculating probabilities for trait category"""
        trait_probabilities = self.calculator.calculate_trait_probabilities(self.sample_trait_category)
        
        self.assertEqual(len(trait_probabilities), 3)
        
        # Check first trait probability info
        trait_info = trait_probabilities[0]
        self.assertIsInstance(trait_info, TraitProbabilityInfo)
        self.assertEqual(trait_info.category_name, "Background")
        self.assertEqual(trait_info.trait_name, "Red Background")
        self.assertEqual(trait_info.weight, 100)
        self.assertAlmostEqual(trait_info.probability, 0.571, delta=0.001)
        self.assertEqual(trait_info.index, 0)
    
    def test_empty_trait_category(self):
        """Test calculating probabilities for empty trait category"""
        empty_category = TraitCategory(
            name="Empty",
            required=False,
            grid_position=GridPosition(0, 0),
            variants=[]
        )
        
        trait_probabilities = self.calculator.calculate_trait_probabilities(empty_category)
        self.assertEqual(trait_probabilities, [])


class TestErrorHandling(TestWeightCalculator):
    """Test error handling and validation"""
    
    def test_invalid_weight_validation(self):
        """Test validation of invalid weights"""
        for invalid_weights in self.invalid_weights:
            with self.subTest(weights=invalid_weights):
                if invalid_weights == []:  # Empty list is valid
                    continue
                
                if invalid_weights == [0, 0, 0]:  # All zero weights should raise error
                    with self.assertRaises(WeightCalculationError):
                        self.calculator.calculate_probabilities(invalid_weights)
                else:
                    with self.assertRaises(WeightCalculationError):
                        self.calculator.calculate_probabilities(invalid_weights)


class TestConvenienceFunctions(TestWeightCalculator):
    """Test convenience functions"""
    
    def test_calculate_probabilities_function(self):
        """Test standalone calculate_probabilities function"""
        probabilities = calculate_probabilities(self.test_weights_basic)
        
        self.assertIsInstance(probabilities, list)
        self.assertEqual(len(probabilities), 3)
        self.assertProbabilitiesClose(probabilities, self.expected_probabilities_basic)
    
    def test_calculate_trait_probabilities_function(self):
        """Test standalone calculate_trait_probabilities function"""
        trait_probabilities = calculate_trait_probabilities(self.sample_trait_category)
        
        self.assertEqual(len(trait_probabilities), 3)
        self.assertIsInstance(trait_probabilities[0], TraitProbabilityInfo)
    
    def test_validate_weights_function(self):
        """Test validate_weights function"""
        # Valid weights
        self.assertTrue(validate_weights([100, 50, 25]))
        self.assertTrue(validate_weights([1, 1, 1]))
        self.assertTrue(validate_weights([]))
        
        # Invalid weights
        self.assertFalse(validate_weights([-1, 50, 25]))
        self.assertFalse(validate_weights([100, "50", 25]))
        self.assertFalse(validate_weights([100, None, 25]))
    
    def test_create_weight_calculator_function(self):
        """Test create_weight_calculator function"""
        calculator = create_weight_calculator(precision=4, validate_inputs=False)
        
        self.assertIsInstance(calculator, WeightCalculator)
        self.assertEqual(calculator.precision, 4)
        self.assertFalse(calculator.validate_inputs)


class TestIntegrationWorkflow(TestWeightCalculator):
    """Test complete workflow integration"""
    
    def test_complete_probability_workflow(self):
        """Test complete weight calculation workflow"""
        # Step 1: Create calculator
        calculator = create_weight_calculator(precision=3)
        
        # Step 2: Calculate probabilities
        result = calculator.calculate_probabilities(self.test_weights_basic)
        
        # Step 3: Validate results
        self.assertEqual(result.total_weight, 175)
        self.assertProbabilitiesClose(result.probabilities, self.expected_probabilities_basic)
        self.assertEqual(result.cumulative_probabilities[-1], 1.0)
        
        # Step 4: Test individual probability access
        self.assertAlmostEqual(result.get_probability(0), 0.571, delta=0.001)
        self.assertAlmostEqual(result.get_cumulative_probability(1), 0.857, delta=0.001)


if __name__ == '__main__':
    unittest.main() 