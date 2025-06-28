"""
Collection Feasibility Checker (Component 5.4)

Validates collection size against available trait combinations for the GenConfig 
generative NFT system. Ensures requested collection sizes are achievable given
the available trait variants and configuration constraints.

Key Functionality:
- Calculate maximum possible unique combinations from trait categories
- Compare against requested collection size for feasibility validation
- Provide warnings and recommendations for collection optimization
- Analyze combination space efficiency and utilization
- Handle edge cases and configuration constraints
"""

import sys
import os
import math
from typing import List, Dict, Union, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.config_parser import GenConfig, TraitCategory, TraitVariant


class FeasibilityCheckError(Exception):
    """Exception raised for feasibility checking errors"""
    pass


class FeasibilityLevel(Enum):
    """Feasibility levels for collection generation"""
    OPTIMAL = "optimal"        # Collection size well within combination space
    FEASIBLE = "feasible"      # Collection size achievable but may require careful generation
    CHALLENGING = "challenging" # Collection size near maximum combinations, may be difficult
    INFEASIBLE = "infeasible"  # Collection size exceeds available combinations


class WarningType(Enum):
    """Types of feasibility warnings"""
    INSUFFICIENT_COMBINATIONS = "insufficient_combinations"
    HIGH_UTILIZATION = "high_utilization"
    DUPLICATE_REQUIREMENT = "duplicate_requirement"
    EMPTY_CATEGORIES = "empty_categories"
    SINGLE_VARIANT_CATEGORIES = "single_variant_categories"
    UNEVEN_DISTRIBUTION = "uneven_distribution"
    LARGE_COLLECTION_SIZE = "large_collection_size"


@dataclass
class FeasibilityWarning:
    """Individual feasibility warning"""
    warning_type: WarningType
    severity: str  # "low", "medium", "high", "critical"
    message: str
    category_key: Optional[str] = None
    category_name: Optional[str] = None
    affected_value: Optional[int] = None
    recommended_value: Optional[int] = None
    recommendation: Optional[str] = None


@dataclass
class CategoryCombinationAnalysis:
    """Analysis of combination space for a trait category"""
    category_key: str
    category_name: str
    variant_count: int
    is_empty: bool
    is_single_variant: bool
    is_required: bool
    contribution_to_combinations: int
    category_utilization_ratio: float


@dataclass
class CombinationSpaceAnalysis:
    """Analysis of overall combination space"""
    total_possible_combinations: int
    collection_size: int
    utilization_ratio: float
    utilization_percentage: float
    requires_duplicates: bool
    combination_efficiency_score: float
    category_analyses: Dict[str, CategoryCombinationAnalysis]


@dataclass
class FeasibilityRecommendations:
    """Recommendations for improving collection feasibility"""
    optimal_collection_size: Optional[int]
    suggested_collection_sizes: List[int]
    variant_recommendations: Dict[str, int]  # category -> suggested variant count
    configuration_changes: List[str]
    optimization_suggestions: List[str]


@dataclass
class CollectionFeasibilityResult:
    """Complete collection feasibility analysis result"""
    is_feasible: bool
    feasibility_level: FeasibilityLevel
    combination_analysis: CombinationSpaceAnalysis
    warnings: List[FeasibilityWarning]
    recommendations: FeasibilityRecommendations
    max_unique_combinations: int
    collection_size: int
    allows_duplicates: bool


class CollectionFeasibilityChecker:
    """
    Main collection feasibility checker for validating collection size against trait combinations
    """
    
    def __init__(self, optimal_utilization_threshold: float = 0.7, 
                 challenging_utilization_threshold: float = 0.9):
        """
        Initialize collection feasibility checker
        
        Args:
            optimal_utilization_threshold: Threshold below which collection is considered optimal (default 70%)
            challenging_utilization_threshold: Threshold above which collection becomes challenging (default 90%)
        """
        self.optimal_threshold = optimal_utilization_threshold
        self.challenging_threshold = challenging_utilization_threshold
        self.warnings: List[FeasibilityWarning] = []
    
    def check_feasibility(self, config: GenConfig) -> CollectionFeasibilityResult:
        """
        Check collection feasibility against available trait combinations
        
        Args:
            config: GenConfig object with trait categories and collection settings
            
        Returns:
            CollectionFeasibilityResult: Complete feasibility analysis
            
        Raises:
            FeasibilityCheckError: If feasibility checking fails
        """
        self.warnings.clear()
        
        try:
            # Analyze combination space
            combination_analysis = self._analyze_combination_space(config)
            
            # Determine feasibility level
            feasibility_level = self._determine_feasibility_level(combination_analysis)
            
            # Generate warnings
            self._generate_feasibility_warnings(config, combination_analysis)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(config, combination_analysis)
            
            # Determine overall feasibility
            is_feasible = self._determine_overall_feasibility(combination_analysis, config)
            
            return CollectionFeasibilityResult(
                is_feasible=is_feasible,
                feasibility_level=feasibility_level,
                combination_analysis=combination_analysis,
                warnings=self.warnings.copy(),
                recommendations=recommendations,
                max_unique_combinations=combination_analysis.total_possible_combinations,
                collection_size=config.collection.size,
                allows_duplicates=config.generation.allow_duplicates
            )
            
        except Exception as e:
            raise FeasibilityCheckError(f"Feasibility check failed: {str(e)}") from e
    
    def calculate_max_combinations(self, config: GenConfig) -> int:
        """
        Calculate maximum possible unique combinations from trait categories
        
        Args:
            config: GenConfig object with trait categories
            
        Returns:
            int: Maximum possible unique combinations
        """
        if not config.traits:
            return 0
        
        total_combinations = 1
        for trait_category in config.traits.values():
            variant_count = len(trait_category.variants)
            if variant_count == 0:
                return 0  # No combinations possible if any category is empty
            total_combinations *= variant_count
        
        return total_combinations
    
    def check_collection_size_feasibility(self, config: GenConfig) -> bool:
        """
        Quick check if collection size is feasible
        
        Args:
            config: GenConfig object to check
            
        Returns:
            bool: True if collection size is feasible
        """
        try:
            result = self.check_feasibility(config)
            return result.is_feasible
        except FeasibilityCheckError:
            return False
    
    def suggest_optimal_collection_size(self, config: GenConfig) -> int:
        """
        Suggest optimal collection size based on combination space
        
        Args:
            config: GenConfig object with trait categories
            
        Returns:
            int: Suggested optimal collection size
        """
        max_combinations = self.calculate_max_combinations(config)
        if max_combinations == 0:
            return 0
        
        # Optimal size is typically 50-70% of max combinations
        optimal_size = int(max_combinations * self.optimal_threshold)
        return max(1, optimal_size)
    
    def get_collection_size_recommendations(self, config: GenConfig) -> List[int]:
        """
        Get recommended collection sizes for different scenarios
        
        Args:
            config: GenConfig object with trait categories
            
        Returns:
            List[int]: List of recommended collection sizes
        """
        max_combinations = self.calculate_max_combinations(config)
        if max_combinations == 0:
            return []
        
        recommendations = []
        
        # Small collection (10% of max)
        small_size = max(1, int(max_combinations * 0.1))
        recommendations.append(small_size)
        
        # Medium collection (30% of max)
        medium_size = max(1, int(max_combinations * 0.3))
        if medium_size != small_size:
            recommendations.append(medium_size)
        
        # Optimal collection (70% of max)
        optimal_size = max(1, int(max_combinations * self.optimal_threshold))
        if optimal_size not in recommendations:
            recommendations.append(optimal_size)
        
        # Challenging collection (90% of max)
        challenging_size = max(1, int(max_combinations * self.challenging_threshold))
        if challenging_size not in recommendations and challenging_size != optimal_size:
            recommendations.append(challenging_size)
        
        # Maximum unique collection
        if max_combinations not in recommendations:
            recommendations.append(max_combinations)
        
        return sorted(recommendations)
    
    def _analyze_combination_space(self, config: GenConfig) -> CombinationSpaceAnalysis:
        """Analyze the combination space for the collection"""
        total_combinations = self.calculate_max_combinations(config)
        collection_size = config.collection.size
        
        # Calculate utilization metrics
        if total_combinations > 0:
            utilization_ratio = collection_size / total_combinations
            utilization_percentage = utilization_ratio * 100
        else:
            utilization_ratio = float('inf')
            utilization_percentage = float('inf')
        
        requires_duplicates = (collection_size > total_combinations and 
                             not config.generation.allow_duplicates) or total_combinations == 0
        
        # Calculate efficiency score
        efficiency_score = self._calculate_combination_efficiency_score(config, total_combinations, collection_size)
        
        # Analyze individual categories
        category_analyses = {}
        for trait_key, trait_category in config.traits.items():
            category_analysis = self._analyze_category_combinations(trait_key, trait_category, total_combinations)
            category_analyses[trait_key] = category_analysis
        
        return CombinationSpaceAnalysis(
            total_possible_combinations=total_combinations,
            collection_size=collection_size,
            utilization_ratio=utilization_ratio,
            utilization_percentage=utilization_percentage,
            requires_duplicates=requires_duplicates,
            combination_efficiency_score=efficiency_score,
            category_analyses=category_analyses
        )
    
    def _analyze_category_combinations(self, trait_key: str, trait_category: TraitCategory, 
                                     total_combinations: int) -> CategoryCombinationAnalysis:
        """Analyze combination contribution for individual category"""
        variant_count = len(trait_category.variants)
        is_empty = variant_count == 0
        is_single_variant = variant_count == 1
        
        # Calculate contribution (how many combinations this category enables)
        if variant_count > 0 and total_combinations > 0:
            contribution = total_combinations // variant_count if variant_count > 0 else 0
            utilization_ratio = contribution / total_combinations if total_combinations > 0 else 0
        else:
            contribution = 0
            utilization_ratio = 0
        
        return CategoryCombinationAnalysis(
            category_key=trait_key,
            category_name=trait_category.name,
            variant_count=variant_count,
            is_empty=is_empty,
            is_single_variant=is_single_variant,
            is_required=trait_category.required,
            contribution_to_combinations=contribution,
            category_utilization_ratio=utilization_ratio
        )
    
    def _determine_feasibility_level(self, analysis: CombinationSpaceAnalysis) -> FeasibilityLevel:
        """Determine feasibility level based on utilization ratio"""
        if analysis.total_possible_combinations == 0:
            return FeasibilityLevel.INFEASIBLE
        
        if analysis.requires_duplicates:
            return FeasibilityLevel.INFEASIBLE
        
        if analysis.utilization_ratio <= self.optimal_threshold:
            return FeasibilityLevel.OPTIMAL
        elif analysis.utilization_ratio <= self.challenging_threshold:
            return FeasibilityLevel.FEASIBLE
        elif analysis.utilization_ratio < 1.0:
            return FeasibilityLevel.CHALLENGING
        elif analysis.utilization_ratio == 1.0 and analysis.collection_size <= 10:
            return FeasibilityLevel.CHALLENGING  # Allow small collections to use 100%
        else:
            return FeasibilityLevel.INFEASIBLE
    
    def _generate_feasibility_warnings(self, config: GenConfig, analysis: CombinationSpaceAnalysis) -> None:
        """Generate warnings based on feasibility analysis"""
        # Insufficient combinations warning
        if analysis.requires_duplicates:
            self.warnings.append(FeasibilityWarning(
                WarningType.INSUFFICIENT_COMBINATIONS,
                "critical",
                f"Collection size ({analysis.collection_size:,}) exceeds maximum unique combinations ({analysis.total_possible_combinations:,})",
                affected_value=analysis.collection_size,
                recommended_value=analysis.total_possible_combinations,
                recommendation="Reduce collection size or add more trait variants to increase combination space"
            ))
        
        # High utilization warning
        elif analysis.utilization_ratio > self.challenging_threshold:
            self.warnings.append(FeasibilityWarning(
                WarningType.HIGH_UTILIZATION,
                "high" if analysis.utilization_ratio > 0.95 else "medium",
                f"High combination space utilization ({analysis.utilization_percentage:.1f}%) may make generation challenging",
                affected_value=int(analysis.utilization_percentage),
                recommended_value=int(self.optimal_threshold * 100),
                recommendation="Consider reducing collection size for more reliable generation"
            ))
        
        # Duplicate requirement warning
        if config.collection.size > analysis.total_possible_combinations and config.generation.allow_duplicates:
            self.warnings.append(FeasibilityWarning(
                WarningType.DUPLICATE_REQUIREMENT,
                "medium",
                f"Collection will require duplicate combinations due to limited trait variants",
                recommendation="Add more trait variants to avoid duplicates"
            ))
        
        # Empty categories warning
        empty_categories = [cat for cat in analysis.category_analyses.values() if cat.is_empty]
        if empty_categories:
            for category in empty_categories:
                self.warnings.append(FeasibilityWarning(
                    WarningType.EMPTY_CATEGORIES,
                    "critical",
                    f"Trait category '{category.category_name}' has no variants",
                    category_key=category.category_key,
                    category_name=category.category_name,
                    recommendation="Add trait variants to enable collection generation"
                ))
        
        # Single variant categories warning
        single_variant_categories = [cat for cat in analysis.category_analyses.values() 
                                   if cat.is_single_variant and not cat.is_empty]
        if single_variant_categories:
            for category in single_variant_categories:
                self.warnings.append(FeasibilityWarning(
                    WarningType.SINGLE_VARIANT_CATEGORIES,
                    "medium",
                    f"Trait category '{category.category_name}' has only one variant, limiting combinations",
                    category_key=category.category_key,
                    category_name=category.category_name,
                    recommendation="Add more variants to increase trait diversity"
                ))
        
        # Large collection size warning
        if config.collection.size > 50000:
            self.warnings.append(FeasibilityWarning(
                WarningType.LARGE_COLLECTION_SIZE,
                "medium",
                f"Large collection size ({config.collection.size:,}) may require significant generation time",
                affected_value=config.collection.size,
                recommendation="Consider generating in batches or optimizing generation pipeline"
            ))
    
    def _generate_recommendations(self, config: GenConfig, analysis: CombinationSpaceAnalysis) -> FeasibilityRecommendations:
        """Generate recommendations for improving feasibility"""
        optimal_size = self.suggest_optimal_collection_size(config)
        suggested_sizes = self.get_collection_size_recommendations(config)
        
        # Variant recommendations
        variant_recommendations = {}
        for trait_key, category_analysis in analysis.category_analyses.items():
            if category_analysis.is_empty:
                variant_recommendations[trait_key] = 3  # Suggest at least 3 variants
            elif category_analysis.is_single_variant:
                variant_recommendations[trait_key] = 3  # Suggest more variants for diversity
        
        # Configuration changes
        config_changes = []
        if analysis.requires_duplicates and not config.generation.allow_duplicates:
            config_changes.append("Enable 'allow_duplicates' setting to permit duplicate combinations")
        
        if analysis.utilization_ratio > 1.0:
            config_changes.append(f"Reduce collection size to maximum of {analysis.total_possible_combinations:,} for unique generation")
        
        # Optimization suggestions
        optimizations = []
        if analysis.utilization_ratio > self.challenging_threshold:
            optimizations.append("Consider reducing collection size for more efficient generation")
        
        if len([cat for cat in analysis.category_analyses.values() if cat.variant_count < 3]) > 0:
            optimizations.append("Add more trait variants to increase combination diversity")
        
        if analysis.total_possible_combinations < config.collection.size * 2:
            optimizations.append("Consider adding new trait categories to expand combination space")
        
        return FeasibilityRecommendations(
            optimal_collection_size=optimal_size if optimal_size != config.collection.size else None,
            suggested_collection_sizes=suggested_sizes,
            variant_recommendations=variant_recommendations,
            configuration_changes=config_changes,
            optimization_suggestions=optimizations
        )
    
    def _calculate_combination_efficiency_score(self, config: GenConfig, total_combinations: int, collection_size: int) -> float:
        """Calculate efficiency score for combination space usage (0-1)"""
        if total_combinations == 0:
            return 0.0
        
        utilization_ratio = collection_size / total_combinations
        
        # Optimal efficiency around 50-70% utilization
        if utilization_ratio <= 0.5:
            efficiency = utilization_ratio * 2  # Scale up to 1.0 at 50%
        elif utilization_ratio <= 0.7:
            efficiency = 1.0  # Optimal range
        elif utilization_ratio <= 1.0:
            efficiency = 1.0 - (utilization_ratio - 0.7) / 0.3 * 0.5  # Scale down from 1.0 to 0.5
        else:
            efficiency = 0.0  # Over-utilization
        
        return max(0.0, min(1.0, efficiency))
    
    def _determine_overall_feasibility(self, analysis: CombinationSpaceAnalysis, config: GenConfig) -> bool:
        """Determine overall feasibility status"""
        # Not feasible if no combinations possible
        if analysis.total_possible_combinations == 0:
            return False
        
        # Not feasible if collection size exceeds combinations and duplicates not allowed
        if analysis.requires_duplicates and not config.generation.allow_duplicates:
            return False
        
        # Not feasible if utilization ratio is 1.0 or higher (no room for error)
        # Exception: allow 100% utilization for very small collections (≤ 10)
        if analysis.utilization_ratio >= 1.0 and analysis.collection_size > 10:
            return False
        
        # Feasible if duplicates are allowed or collection size is within reasonable bounds
        return True


# Convenience functions for easier usage
def check_collection_feasibility(config: GenConfig, optimal_threshold: float = 0.7, 
                               challenging_threshold: float = 0.9) -> CollectionFeasibilityResult:
    """
    Check collection feasibility against available trait combinations
    
    Args:
        config: GenConfig object to check
        optimal_threshold: Threshold for optimal utilization (default 70%)
        challenging_threshold: Threshold for challenging utilization (default 90%)
        
    Returns:
        CollectionFeasibilityResult: Complete feasibility analysis
    """
    checker = CollectionFeasibilityChecker(optimal_threshold, challenging_threshold)
    return checker.check_feasibility(config)


def calculate_max_unique_combinations(config: GenConfig) -> int:
    """
    Calculate maximum possible unique combinations from trait categories
    
    Args:
        config: GenConfig object with trait categories
        
    Returns:
        int: Maximum possible unique combinations
    """
    checker = CollectionFeasibilityChecker()
    return checker.calculate_max_combinations(config)


def is_collection_size_feasible(config: GenConfig) -> bool:
    """
    Quick check if collection size is feasible
    
    Args:
        config: GenConfig object to check
        
    Returns:
        bool: True if collection size is feasible
    """
    checker = CollectionFeasibilityChecker()
    return checker.check_collection_size_feasibility(config)


def suggest_optimal_collection_size(config: GenConfig) -> int:
    """
    Suggest optimal collection size based on combination space
    
    Args:
        config: GenConfig object with trait categories
        
    Returns:
        int: Suggested optimal collection size
    """
    checker = CollectionFeasibilityChecker()
    return checker.suggest_optimal_collection_size(config)


def get_feasibility_report(result: CollectionFeasibilityResult) -> str:
    """
    Generate human-readable feasibility report
    
    Args:
        result: CollectionFeasibilityResult to format
        
    Returns:
        str: Formatted feasibility report
    """
    lines = []
    lines.append("🔍 Collection Feasibility Analysis Report")
    lines.append("=" * 50)
    
    # Overall status
    feasibility_icon = {
        FeasibilityLevel.OPTIMAL: "🟢",
        FeasibilityLevel.FEASIBLE: "🟡", 
        FeasibilityLevel.CHALLENGING: "🟠",
        FeasibilityLevel.INFEASIBLE: "🔴"
    }[result.feasibility_level]
    
    lines.append(f"Overall Status: {feasibility_icon} {result.feasibility_level.value.upper()}")
    lines.append(f"Feasible: {'✅ Yes' if result.is_feasible else '❌ No'}")
    lines.append("")
    
    # Combination Analysis
    analysis = result.combination_analysis
    lines.append("📊 Combination Space Analysis:")
    lines.append(f"  Collection Size: {analysis.collection_size:,}")
    lines.append(f"  Max Unique Combinations: {analysis.total_possible_combinations:,}")
    lines.append(f"  Utilization: {analysis.utilization_percentage:.1f}%")
    lines.append(f"  Requires Duplicates: {'Yes' if analysis.requires_duplicates else 'No'}")
    lines.append(f"  Efficiency Score: {analysis.combination_efficiency_score:.3f}")
    lines.append("")
    
    # Warnings
    if result.warnings:
        lines.append("⚠️ Warnings:")
        for warning in result.warnings:
            severity_icon = {"low": "ℹ️", "medium": "⚠️", "high": "❗", "critical": "🚨"}[warning.severity]
            lines.append(f"  {severity_icon} {warning.message}")
        lines.append("")
    
    # Recommendations
    if result.recommendations.suggested_collection_sizes:
        lines.append("💡 Recommended Collection Sizes:")
        for size in result.recommendations.suggested_collection_sizes:
            lines.append(f"  • {size:,}")
        lines.append("")
    
    if result.recommendations.optimization_suggestions:
        lines.append("🔧 Optimization Suggestions:")
        for suggestion in result.recommendations.optimization_suggestions:
            lines.append(f"  • {suggestion}")
    
    return "\n".join(lines)


def create_feasibility_checker(optimal_threshold: float = 0.7, 
                             challenging_threshold: float = 0.9) -> CollectionFeasibilityChecker:
    """
    Create a CollectionFeasibilityChecker instance with specified settings
    
    Args:
        optimal_threshold: Threshold for optimal utilization
        challenging_threshold: Threshold for challenging utilization
        
    Returns:
        CollectionFeasibilityChecker: Configured checker instance
    """
    return CollectionFeasibilityChecker(optimal_threshold, challenging_threshold) 