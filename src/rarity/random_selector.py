"""
Weighted Random Selector (Component 5.2)

Selects traits based on weighted random distribution for the GenConfig 
generative NFT system. Uses probability calculations from Component 5.1
to perform statistically correct trait selection.

Selection Process:
1. Calculate probabilities from rarity weights
2. Generate random number (0.0 to 1.0)
3. Select trait based on cumulative probability ranges
4. Ensure statistical accuracy within tolerance
"""

import sys
import os
import random
from typing import List, Dict, Union, Optional, Any, Tuple
from dataclasses import dataclass
from collections import Counter

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.config_parser import GenConfig, TraitCategory, TraitVariant
from rarity.weight_calculator import (
    WeightCalculator, 
    WeightCalculationResult, 
    TraitProbabilityInfo,
    calculate_trait_probabilities,
    WeightCalculationError
)


class RandomSelectionError(Exception):
    """Exception raised for random selection errors"""
    pass


@dataclass 
class SelectionResult:
    """Result of a weighted random selection"""
    selected_index: int
    selected_item: Any
    random_value: float
    probabilities: List[float]
    cumulative_probabilities: List[float]
    
    def get_selection_info(self) -> Dict[str, Any]:
        """Get detailed information about the selection"""
        return {
            'selected_index': self.selected_index,
            'selected_item': self.selected_item,
            'random_value': self.random_value,
            'selected_probability': self.probabilities[self.selected_index],
            'cumulative_range': (
                self.cumulative_probabilities[self.selected_index - 1] if self.selected_index > 0 else 0.0,
                self.cumulative_probabilities[self.selected_index]
            )
        }


@dataclass
class TraitSelectionResult:
    """Result of trait selection from a category"""
    selected_variant: TraitVariant
    selected_index: int
    trait_probability_info: TraitProbabilityInfo
    random_value: float
    category_name: str


@dataclass
class SelectionStatistics:
    """Statistics about selection frequency and accuracy"""
    total_selections: int
    selection_counts: Dict[int, int]
    selection_frequencies: Dict[int, float]
    expected_frequencies: Dict[int, float]
    frequency_differences: Dict[int, float]
    max_deviation: float
    within_tolerance: bool
    tolerance: float


class WeightedRandomSelector:
    """
    Main weighted random selector class for trait selection based on probabilities
    """
    
    def __init__(self, weight_calculator: Optional[WeightCalculator] = None, seed: Optional[int] = None):
        """
        Initialize weighted random selector
        
        Args:
            weight_calculator: WeightCalculator instance for probability calculations
            seed: Random seed for reproducible results (None for random)
        """
        self.weight_calculator = weight_calculator or WeightCalculator()
        self.random = random.Random(seed)
        self.selection_history: List[SelectionResult] = []
    
    def select_weighted_random(self, weights: List[int], items: Optional[List[Any]] = None) -> SelectionResult:
        """
        Select item using weighted random distribution
        
        Args:
            weights: List of weights for each item
            items: Optional list of items to select from (uses indices if None)
            
        Returns:
            SelectionResult: Complete selection result information
            
        Raises:
            RandomSelectionError: If selection fails
            
        Examples:
            >>> selector = WeightedRandomSelector(seed=42)
            >>> result = selector.select_weighted_random([100, 50, 25], ['A', 'B', 'C'])
            >>> result.selected_item
            'A'  # Most likely due to highest weight
        """
        if not weights:
            raise RandomSelectionError("Cannot select from empty weights list")
        
        # Calculate probabilities using weight calculator
        calc_result = self.weight_calculator.calculate_probabilities(weights)
        
        if not calc_result.probabilities:
            raise RandomSelectionError("Failed to calculate probabilities from weights")
        
        # Use items list or create indices
        selection_items = items if items is not None else list(range(len(weights)))
        
        if len(selection_items) != len(weights):
            raise RandomSelectionError(f"Items count ({len(selection_items)}) must match weights count ({len(weights)})")
        
        # Generate random number and select based on cumulative probabilities
        random_value = self.random.random()
        selected_index = self._select_by_cumulative_probability(random_value, calc_result.cumulative_probabilities)
        
        # Create selection result
        result = SelectionResult(
            selected_index=selected_index,
            selected_item=selection_items[selected_index],
            random_value=random_value,
            probabilities=calc_result.probabilities,
            cumulative_probabilities=calc_result.cumulative_probabilities
        )
        
        # Store in history for statistics
        self.selection_history.append(result)
        
        return result
    
    def select_trait_variant(self, trait_category: TraitCategory) -> TraitSelectionResult:
        """
        Select trait variant from a trait category based on rarity weights
        
        Args:
            trait_category: TraitCategory with variants to select from
            
        Returns:
            TraitSelectionResult: Complete trait selection result
            
        Raises:
            RandomSelectionError: If trait selection fails
        """
        if not trait_category.variants:
            raise RandomSelectionError(f"Trait category '{trait_category.name}' has no variants to select from")
        
        # Calculate trait probabilities
        trait_probabilities = self.weight_calculator.calculate_trait_probabilities(trait_category)
        
        # Extract weights and variants
        weights = [variant.rarity_weight for variant in trait_category.variants]
        variants = trait_category.variants
        
        # Perform weighted selection
        selection_result = self.select_weighted_random(weights, variants)
        
        # Create trait-specific result
        trait_result = TraitSelectionResult(
            selected_variant=selection_result.selected_item,
            selected_index=selection_result.selected_index,
            trait_probability_info=trait_probabilities[selection_result.selected_index],
            random_value=selection_result.random_value,
            category_name=trait_category.name
        )
        
        return trait_result
    
    def select_collection_traits(self, config: GenConfig) -> Dict[str, TraitSelectionResult]:
        """
        Select traits for all categories in a collection
        
        Args:
            config: GenConfig object with trait categories
            
        Returns:
            Dict[str, TraitSelectionResult]: Selected traits by category key
        """
        collection_selections = {}
        
        for trait_key, trait_category in config.traits.items():
            trait_selection = self.select_trait_variant(trait_category)
            collection_selections[trait_key] = trait_selection
        
        return collection_selections
    
    def select_multiple(self, weights: List[int], count: int, items: Optional[List[Any]] = None, 
                       allow_duplicates: bool = True) -> List[SelectionResult]:
        """
        Perform multiple weighted random selections
        
        Args:
            weights: List of weights for each item
            count: Number of selections to perform
            items: Optional list of items to select from
            allow_duplicates: Whether to allow selecting the same item multiple times
            
        Returns:
            List[SelectionResult]: List of selection results
            
        Raises:
            RandomSelectionError: If multiple selection fails
        """
        if count <= 0:
            raise RandomSelectionError("Selection count must be positive")
        
        if not allow_duplicates and count > len(weights):
            raise RandomSelectionError(f"Cannot select {count} unique items from {len(weights)} options")
        
        selections = []
        remaining_weights = weights.copy()
        remaining_items = items.copy() if items else list(range(len(weights)))
        
        for _ in range(count):
            if not remaining_weights:
                break
            
            # Perform selection
            result = self.select_weighted_random(remaining_weights, remaining_items)
            selections.append(result)
            
            # Remove selected item if duplicates not allowed
            if not allow_duplicates:
                selected_idx = result.selected_index
                remaining_weights.pop(selected_idx)
                remaining_items.pop(selected_idx)
        
        return selections
    
    def analyze_selection_statistics(self, weights: List[int], sample_size: int = 1000, 
                                   tolerance: float = 0.05) -> SelectionStatistics:
        """
        Analyze selection statistics by performing multiple selections
        
        Args:
            weights: List of weights to test
            sample_size: Number of selections to perform for analysis
            tolerance: Acceptable deviation from expected frequency (as ratio)
            
        Returns:
            SelectionStatistics: Statistical analysis of selection accuracy
        """
        if sample_size <= 0:
            raise RandomSelectionError("Sample size must be positive")
        
        # Calculate expected probabilities
        calc_result = self.weight_calculator.calculate_probabilities(weights)
        expected_probs = calc_result.probabilities
        
        # Perform multiple selections
        selections = []
        for _ in range(sample_size):
            result = self.select_weighted_random(weights)
            selections.append(result.selected_index)
        
        # Count selections
        selection_counts = Counter(selections)
        
        # Calculate frequencies and deviations
        selection_frequencies = {}
        expected_frequencies = {}
        frequency_differences = {}
        
        for i in range(len(weights)):
            count = selection_counts.get(i, 0)
            actual_freq = count / sample_size
            expected_freq = expected_probs[i]
            
            selection_frequencies[i] = actual_freq
            expected_frequencies[i] = expected_freq
            frequency_differences[i] = abs(actual_freq - expected_freq)
        
        # Calculate maximum deviation and tolerance check
        max_deviation = max(frequency_differences.values()) if frequency_differences else 0.0
        within_tolerance = max_deviation <= tolerance
        
        return SelectionStatistics(
            total_selections=sample_size,
            selection_counts=dict(selection_counts),
            selection_frequencies=selection_frequencies,
            expected_frequencies=expected_frequencies,
            frequency_differences=frequency_differences,
            max_deviation=max_deviation,
            within_tolerance=within_tolerance,
            tolerance=tolerance
        )
    
    def get_selection_history(self) -> List[SelectionResult]:
        """Get history of all selections made by this selector"""
        return self.selection_history.copy()
    
    def clear_selection_history(self) -> None:
        """Clear the selection history"""
        self.selection_history.clear()
    
    def set_seed(self, seed: Optional[int]) -> None:
        """Set random seed for reproducible results"""
        self.random = random.Random(seed)
    
    def _select_by_cumulative_probability(self, random_value: float, cumulative_probs: List[float]) -> int:
        """
        Select index based on random value and cumulative probabilities
        
        Args:
            random_value: Random value between 0.0 and 1.0
            cumulative_probs: List of cumulative probabilities
            
        Returns:
            int: Selected index
        """
        if not 0.0 <= random_value <= 1.0:
            raise RandomSelectionError(f"Random value must be between 0.0 and 1.0, got {random_value}")
        
        if not cumulative_probs:
            raise RandomSelectionError("Cumulative probabilities list cannot be empty")
        
        # Find first cumulative probability greater than random value
        for i, cumulative_prob in enumerate(cumulative_probs):
            if random_value <= cumulative_prob:
                return i
        
        # Fallback to last index (should not happen with proper cumulative probabilities)
        return len(cumulative_probs) - 1


# Convenience functions for easier usage
def select_weighted_random(weights: List[int], items: Optional[List[Any]] = None, 
                          seed: Optional[int] = None) -> SelectionResult:
    """
    Perform weighted random selection with weights
    
    Args:
        weights: List of weights for selection
        items: Optional list of items to select from
        seed: Optional random seed for reproducible results
        
    Returns:
        SelectionResult: Selection result
        
    Examples:
        >>> result = select_weighted_random([100, 50, 25], ['A', 'B', 'C'])
        >>> result.selected_item  # Most likely 'A' due to highest weight
    """
    selector = WeightedRandomSelector(seed=seed)
    return selector.select_weighted_random(weights, items)


def select_trait_variant(trait_category: TraitCategory, seed: Optional[int] = None) -> TraitSelectionResult:
    """
    Select trait variant from category based on rarity weights
    
    Args:
        trait_category: TraitCategory to select from
        seed: Optional random seed for reproducible results
        
    Returns:
        TraitSelectionResult: Trait selection result
    """
    selector = WeightedRandomSelector(seed=seed)
    return selector.select_trait_variant(trait_category)


def analyze_selection_accuracy(weights: List[int], sample_size: int = 1000, 
                             tolerance: float = 0.05, seed: Optional[int] = None) -> SelectionStatistics:
    """
    Analyze selection accuracy by testing multiple selections
    
    Args:
        weights: List of weights to test
        sample_size: Number of test selections
        tolerance: Acceptable deviation from expected frequency
        seed: Optional random seed for reproducible results
        
    Returns:
        SelectionStatistics: Statistical analysis results
    """
    selector = WeightedRandomSelector(seed=seed)
    return selector.analyze_selection_statistics(weights, sample_size, tolerance)


def create_weighted_random_selector(seed: Optional[int] = None, 
                                   precision: int = 3) -> WeightedRandomSelector:
    """
    Create a WeightedRandomSelector instance with specified settings
    
    Args:
        seed: Random seed for reproducible results
        precision: Decimal precision for probability calculations
        
    Returns:
        WeightedRandomSelector: Configured selector instance
    """
    weight_calculator = WeightCalculator(precision=precision)
    return WeightedRandomSelector(weight_calculator=weight_calculator, seed=seed) 