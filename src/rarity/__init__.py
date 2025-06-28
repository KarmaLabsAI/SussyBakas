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

from .distribution_validator import (
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

from .feasibility_checker import (
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

__all__ = [
    # Weight Calculator functions
    'calculate_probabilities',
    'calculate_trait_probabilities',
    
    # Random Selector functions
    'select_weighted_random',
    'select_trait_variant',
    'analyze_selection_accuracy',
    
    # Distribution Validator functions
    'validate_distribution',
    'check_distribution_feasibility',
    'simulate_generation_accuracy',
    'get_distribution_report',
    
    # Feasibility Checker functions
    'check_collection_feasibility',
    'calculate_max_unique_combinations',
    'is_collection_size_feasible',
    'suggest_optimal_collection_size',
    'get_feasibility_report',
    
    # Classes
    'WeightCalculator',
    'WeightedRandomSelector',
    'RarityDistributionValidator',
    'CollectionFeasibilityChecker',
    'SelectionResult',
    'TraitSelectionResult',
    'SelectionStatistics',
    'DistributionValidationResult',
    'TraitDistributionAnalysis',
    'CollectionFeasibilityAnalysis',
    'CollectionFeasibilityResult',
    'CombinationSpaceAnalysis',
    'CategoryCombinationAnalysis',
    'ValidationIssue',
    'ValidationSeverity',
    'FeasibilityWarning',
    'FeasibilityLevel',
    'WarningType',
    'FeasibilityRecommendations',
    
    # Exceptions
    'WeightCalculationError',
    'RandomSelectionError',
    'DistributionValidationError',
    'FeasibilityCheckError',
    
    # Utility functions
    'validate_weights',
    'normalize_probabilities',
    'get_cumulative_probabilities',
    'create_weight_calculator',
    'create_weighted_random_selector',
    'create_distribution_validator',
    'create_feasibility_checker',
] 