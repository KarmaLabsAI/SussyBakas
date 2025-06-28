"""
GenConfig Rarity Engine Package

This package provides weight-based trait selection and distribution functionality
for the GenConfig generative NFT system.
"""

from .weight_calculator import (
    calculate_probabilities,
    calculate_trait_probabilities,
    WeightCalculator,
    WeightCalculationError,
    validate_weights,
    normalize_probabilities,
    get_cumulative_probabilities,
    create_weight_calculator,
)

from .random_selector import (
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

__all__ = [
    # Weight Calculator functions
    'calculate_probabilities',
    'calculate_trait_probabilities',
    
    # Random Selector functions
    'select_weighted_random',
    'select_trait_variant',
    'analyze_selection_accuracy',
    
    # Classes
    'WeightCalculator',
    'WeightedRandomSelector',
    'SelectionResult',
    'TraitSelectionResult',
    'SelectionStatistics',
    
    # Exceptions
    'WeightCalculationError',
    'RandomSelectionError',
    
    # Utility functions
    'validate_weights',
    'normalize_probabilities',
    'get_cumulative_probabilities',
    'create_weight_calculator',
    'create_weighted_random_selector',
] 