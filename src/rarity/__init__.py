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

__all__ = [
    # Main functions
    'calculate_probabilities',
    'calculate_trait_probabilities',
    
    # Classes
    'WeightCalculator',
    
    # Exceptions
    'WeightCalculationError',
    
    # Utility functions
    'validate_weights',
    'normalize_probabilities',
    'get_cumulative_probabilities',
    'create_weight_calculator',
] 