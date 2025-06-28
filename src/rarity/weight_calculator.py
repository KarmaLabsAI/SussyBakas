"""
Weight Calculator (Component 5.1)

Calculates selection probabilities from rarity weights for the GenConfig 
generative NFT system. Provides weighted random distribution calculations
and trait probability computations.

Example Weight Calculation:
- Weights [100, 50, 25] = Total 175
- Probabilities [57.1%, 28.6%, 14.3%] = [100/175, 50/175, 25/175]
"""

import sys
import os
from typing import List, Dict, Union, Optional, Any, Tuple
from dataclasses import dataclass
import math

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.config_parser import GenConfig, TraitCategory, TraitVariant


class WeightCalculationError(Exception):
    """Exception raised for weight calculation errors"""
    pass


@dataclass
class WeightCalculationResult:
    """Result of weight calculation operations"""
    weights: List[int]
    probabilities: List[float]
    total_weight: int
    cumulative_probabilities: List[float]
    
    def get_probability(self, index: int) -> float:
        """Get probability for specific index"""
        if 0 <= index < len(self.probabilities):
            return self.probabilities[index]
        raise IndexError(f"Index {index} out of range for {len(self.probabilities)} probabilities")
    
    def get_cumulative_probability(self, index: int) -> float:
        """Get cumulative probability up to specific index"""
        if 0 <= index < len(self.cumulative_probabilities):
            return self.cumulative_probabilities[index]
        raise IndexError(f"Index {index} out of range for {len(self.cumulative_probabilities)} cumulative probabilities")


@dataclass
class TraitProbabilityInfo:
    """Information about trait probability calculations"""
    category_name: str
    trait_name: str
    weight: int
    probability: float
    cumulative_probability: float
    index: int


class WeightCalculator:
    """
    Main weight calculator class for converting rarity weights to probabilities
    """
    
    def __init__(self, precision: int = 3, validate_inputs: bool = True):
        """
        Initialize weight calculator
        
        Args:
            precision: Decimal precision for probability calculations
            validate_inputs: Whether to validate input weights
        """
        self.precision = precision
        self.validate_inputs = validate_inputs
    
    def calculate_probabilities(self, weights: List[int]) -> WeightCalculationResult:
        """
        Calculate selection probabilities from rarity weights
        
        Args:
            weights: List of integer weights for each trait variant
            
        Returns:
            WeightCalculationResult: Complete calculation results
            
        Raises:
            WeightCalculationError: If weight calculation fails
            
        Examples:
            >>> calculator = WeightCalculator()
            >>> result = calculator.calculate_probabilities([100, 50, 25])
            >>> result.probabilities
            [0.571, 0.286, 0.143]
        """
        if self.validate_inputs:
            self._validate_weights(weights)
        
        if not weights:
            return WeightCalculationResult([], [], 0, [])
        
        # Calculate total weight
        total_weight = sum(weights)
        
        if total_weight == 0:
            raise WeightCalculationError("Total weight cannot be zero")
        
        # Calculate individual probabilities
        probabilities = []
        for weight in weights:
            probability = round(weight / total_weight, self.precision)
            probabilities.append(probability)
        
        # Normalize probabilities to ensure they sum to 1.0
        probabilities = self._normalize_probabilities(probabilities)
        
        # Calculate cumulative probabilities
        cumulative_probabilities = self._calculate_cumulative_probabilities(probabilities)
        
        return WeightCalculationResult(
            weights=weights.copy(),
            probabilities=probabilities,
            total_weight=total_weight,
            cumulative_probabilities=cumulative_probabilities
        )
    
    def calculate_trait_probabilities(self, trait_category: TraitCategory) -> List[TraitProbabilityInfo]:
        """
        Calculate probabilities for all variants in a trait category
        
        Args:
            trait_category: TraitCategory object with variants
            
        Returns:
            List[TraitProbabilityInfo]: Probability information for each variant
            
        Raises:
            WeightCalculationError: If calculation fails
        """
        if not trait_category.variants:
            return []
        
        # Extract weights from trait variants
        weights = [variant.rarity_weight for variant in trait_category.variants]
        
        # Calculate probabilities
        result = self.calculate_probabilities(weights)
        
        # Create trait probability info objects
        trait_probabilities = []
        for i, variant in enumerate(trait_category.variants):
            trait_info = TraitProbabilityInfo(
                category_name=trait_category.name,
                trait_name=variant.name,
                weight=variant.rarity_weight,
                probability=result.probabilities[i],
                cumulative_probability=result.cumulative_probabilities[i],
                index=i
            )
            trait_probabilities.append(trait_info)
        
        return trait_probabilities
    
    def calculate_collection_probabilities(self, config: GenConfig) -> Dict[str, List[TraitProbabilityInfo]]:
        """
        Calculate probabilities for all trait categories in a collection
        
        Args:
            config: GenConfig object with trait categories
            
        Returns:
            Dict[str, List[TraitProbabilityInfo]]: Probabilities by category
        """
        collection_probabilities = {}
        
        for trait_key, trait_category in config.traits.items():
            trait_probabilities = self.calculate_trait_probabilities(trait_category)
            collection_probabilities[trait_key] = trait_probabilities
        
        return collection_probabilities
    
    def get_calculation_summary(self, weights: List[int]) -> Dict[str, Any]:
        """
        Get detailed summary of weight calculation
        
        Args:
            weights: List of weights to analyze
            
        Returns:
            Dict[str, Any]: Detailed calculation summary
        """
        result = self.calculate_probabilities(weights)
        
        return {
            'input_weights': weights,
            'total_weight': result.total_weight,
            'probabilities': result.probabilities,
            'cumulative_probabilities': result.cumulative_probabilities,
            'min_probability': min(result.probabilities) if result.probabilities else 0,
            'max_probability': max(result.probabilities) if result.probabilities else 0,
            'weight_count': len(weights),
            'precision': self.precision,
            'probability_sum': sum(result.probabilities)
        }
    
    def _validate_weights(self, weights: List[int]) -> None:
        """Validate input weights"""
        if not isinstance(weights, list):
            raise WeightCalculationError(f"Weights must be a list, got {type(weights)}")
        
        for i, weight in enumerate(weights):
            if not isinstance(weight, int):
                raise WeightCalculationError(f"Weight at index {i} must be an integer, got {type(weight)}")
            
            if weight < 0:
                raise WeightCalculationError(f"Weight at index {i} cannot be negative: {weight}")
    
    def _normalize_probabilities(self, probabilities: List[float]) -> List[float]:
        """Normalize probabilities to ensure they sum to 1.0"""
        if not probabilities:
            return []
        
        total = sum(probabilities)
        if total == 0:
            # If all probabilities are 0, distribute equally
            equal_prob = round(1.0 / len(probabilities), self.precision)
            return [equal_prob] * len(probabilities)
        
        # Normalize and round
        normalized = []
        for prob in probabilities:
            normalized.append(round(prob / total, self.precision))
        
        # Adjust for rounding errors to ensure sum = 1.0
        current_sum = sum(normalized)
        if current_sum != 1.0:
            # Adjust the largest probability to make sum = 1.0
            max_index = normalized.index(max(normalized))
            adjustment = round(1.0 - current_sum, self.precision)
            normalized[max_index] = round(normalized[max_index] + adjustment, self.precision)
        
        return normalized
    
    def _calculate_cumulative_probabilities(self, probabilities: List[float]) -> List[float]:
        """Calculate cumulative probability distribution"""
        if not probabilities:
            return []
        
        cumulative = []
        running_sum = 0.0
        
        for prob in probabilities:
            running_sum += prob
            cumulative.append(round(running_sum, self.precision))
        
        # Ensure the last cumulative probability is exactly 1.0
        if cumulative and cumulative[-1] != 1.0:
            cumulative[-1] = 1.0
        
        return cumulative


# Convenience functions for easier usage
def calculate_probabilities(weights: List[int], precision: int = 3) -> List[float]:
    """
    Calculate selection probabilities from rarity weights
    
    Args:
        weights: List of integer weights
        precision: Decimal precision for calculations
        
    Returns:
        List[float]: Probability for each weight
        
    Examples:
        >>> calculate_probabilities([100, 50, 25])
        [0.571, 0.286, 0.143]
    """
    calculator = WeightCalculator(precision=precision)
    result = calculator.calculate_probabilities(weights)
    return result.probabilities


def calculate_trait_probabilities(trait_category: TraitCategory) -> List[TraitProbabilityInfo]:
    """
    Calculate probabilities for trait category variants
    
    Args:
        trait_category: TraitCategory with variants
        
    Returns:
        List[TraitProbabilityInfo]: Probability information for each variant
    """
    calculator = WeightCalculator()
    return calculator.calculate_trait_probabilities(trait_category)


def validate_weights(weights: List[int]) -> bool:
    """
    Validate that weights are valid for probability calculation
    
    Args:
        weights: List of weights to validate
        
    Returns:
        bool: True if weights are valid, False otherwise
    """
    try:
        calculator = WeightCalculator(validate_inputs=True)
        calculator._validate_weights(weights)
        return True
    except WeightCalculationError:
        return False


def normalize_probabilities(probabilities: List[float], precision: int = 3) -> List[float]:
    """
    Normalize probabilities to ensure they sum to 1.0
    
    Args:
        probabilities: List of probabilities to normalize
        precision: Decimal precision for calculations
        
    Returns:
        List[float]: Normalized probabilities
    """
    calculator = WeightCalculator(precision=precision)
    return calculator._normalize_probabilities(probabilities)


def get_cumulative_probabilities(probabilities: List[float], precision: int = 3) -> List[float]:
    """
    Calculate cumulative probability distribution
    
    Args:
        probabilities: List of individual probabilities
        precision: Decimal precision for calculations
        
    Returns:
        List[float]: Cumulative probabilities
    """
    calculator = WeightCalculator(precision=precision)
    return calculator._calculate_cumulative_probabilities(probabilities)


def create_weight_calculator(precision: int = 3, validate_inputs: bool = True) -> WeightCalculator:
    """
    Create a WeightCalculator instance with specified settings
    
    Args:
        precision: Decimal precision for calculations
        validate_inputs: Whether to validate input weights
        
    Returns:
        WeightCalculator: Configured calculator instance
    """
    return WeightCalculator(precision=precision, validate_inputs=validate_inputs) 