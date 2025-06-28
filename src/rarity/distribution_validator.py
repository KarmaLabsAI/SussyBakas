"""
Rarity Distribution Validator (Component 5.3)

Validates rarity distribution feasibility and accuracy for the GenConfig 
generative NFT system. Ensures collection generation will produce expected
trait distributions within acceptable tolerances.

Validation Requirements (from specification):
- Distribution Accuracy: Generated collection must match expected rarity within 2% tolerance
- Minimum Occurrence: Each trait must appear at least once (unless weight = 0)
- Maximum Occurrence: No trait should exceed expected frequency by more than 5%
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
from rarity.weight_calculator import (
    WeightCalculator, 
    WeightCalculationResult, 
    TraitProbabilityInfo,
    calculate_trait_probabilities,
    WeightCalculationError
)
from rarity.random_selector import (
    WeightedRandomSelector,
    analyze_selection_accuracy,
    SelectionStatistics,
    RandomSelectionError
)


class DistributionValidationError(Exception):
    """Exception raised for distribution validation errors"""
    pass


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Individual validation issue"""
    severity: ValidationSeverity
    category: str
    message: str
    trait_key: Optional[str] = None
    trait_name: Optional[str] = None
    expected_value: Optional[float] = None
    actual_value: Optional[float] = None
    deviation: Optional[float] = None


@dataclass
class TraitDistributionAnalysis:
    """Analysis of trait distribution for a category"""
    category_key: str
    category_name: str
    total_variants: int
    total_weight: int
    min_weight: int
    max_weight: int
    weight_distribution: Dict[str, int]
    expected_frequencies: Dict[str, float]
    expected_occurrences: Dict[str, int]
    min_possible_occurrence: Dict[str, int]
    max_possible_occurrence: Dict[str, int]
    zero_weight_variants: List[str]
    rarity_balance_score: float


@dataclass
class CollectionFeasibilityAnalysis:
    """Analysis of overall collection feasibility"""
    collection_size: int
    total_trait_categories: int
    complete_grid_coverage: bool
    total_possible_combinations: int
    unique_combinations_feasible: bool
    min_trait_occurrences: Dict[str, Dict[str, int]]
    max_trait_occurrences: Dict[str, Dict[str, int]]
    distribution_balance_score: float
    generation_complexity_score: float


@dataclass
class DistributionValidationResult:
    """Complete distribution validation result"""
    is_valid: bool
    overall_score: float
    collection_analysis: CollectionFeasibilityAnalysis
    trait_analyses: Dict[str, TraitDistributionAnalysis]
    validation_issues: List[ValidationIssue]
    recommendations: List[str]
    statistical_simulation_results: Optional[Dict[str, SelectionStatistics]] = None


class RarityDistributionValidator:
    """
    Main rarity distribution validator for collection feasibility and accuracy validation
    """
    
    def __init__(self, weight_calculator: Optional[WeightCalculator] = None, 
                 tolerance_accuracy: float = 0.02, tolerance_max_frequency: float = 0.05):
        """
        Initialize rarity distribution validator
        
        Args:
            weight_calculator: WeightCalculator instance for probability calculations
            tolerance_accuracy: Acceptable deviation from expected distribution (default 2%)
            tolerance_max_frequency: Max allowed frequency deviation (default 5%)
        """
        self.weight_calculator = weight_calculator or WeightCalculator()
        self.tolerance_accuracy = tolerance_accuracy
        self.tolerance_max_frequency = tolerance_max_frequency
        self.validation_issues: List[ValidationIssue] = []
    
    def validate_distribution(self, config: GenConfig, run_simulation: bool = True, 
                            simulation_sample_size: int = 10000) -> DistributionValidationResult:
        """
        Validate rarity distribution feasibility and accuracy for entire collection
        
        Args:
            config: GenConfig object with trait categories and collection settings
            run_simulation: Whether to run statistical simulation validation
            simulation_sample_size: Size of simulation for statistical validation
            
        Returns:
            DistributionValidationResult: Complete validation results
            
        Raises:
            DistributionValidationError: If validation process fails
        """
        self.validation_issues.clear()
        
        try:
            # Analyze collection feasibility
            collection_analysis = self._analyze_collection_feasibility(config)
            
            # Analyze individual trait distributions
            trait_analyses = {}
            for trait_key, trait_category in config.traits.items():
                trait_analysis = self._analyze_trait_distribution(trait_key, trait_category, config.collection.size)
                trait_analyses[trait_key] = trait_analysis
            
            # Run statistical simulation if requested
            simulation_results = None
            if run_simulation:
                simulation_results = self._run_statistical_simulation(config, simulation_sample_size)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(collection_analysis, trait_analyses)
            
            # Calculate overall validation score and status
            overall_score, is_valid = self._calculate_overall_validation_score(collection_analysis, trait_analyses)
            
            return DistributionValidationResult(
                is_valid=is_valid,
                overall_score=overall_score,
                collection_analysis=collection_analysis,
                trait_analyses=trait_analyses,
                validation_issues=self.validation_issues.copy(),
                recommendations=recommendations,
                statistical_simulation_results=simulation_results
            )
            
        except Exception as e:
            raise DistributionValidationError(f"Distribution validation failed: {str(e)}") from e
    
    def validate_trait_distribution(self, trait_category: TraitCategory, collection_size: int) -> TraitDistributionAnalysis:
        """
        Validate distribution for a single trait category
        
        Args:
            trait_category: TraitCategory to validate
            collection_size: Size of the collection
            
        Returns:
            TraitDistributionAnalysis: Analysis results for the trait
        """
        return self._analyze_trait_distribution(trait_category.name, trait_category, collection_size)
    
    def check_distribution_feasibility(self, config: GenConfig) -> bool:
        """
        Quick feasibility check for distribution requirements
        
        Args:
            config: GenConfig object to check
            
        Returns:
            bool: True if distribution is feasible
        """
        try:
            result = self.validate_distribution(config, run_simulation=False)
            return result.is_valid
        except DistributionValidationError:
            return False
    
    def simulate_generation_accuracy(self, config: GenConfig, sample_size: int = 10000, 
                                   tolerance: Optional[float] = None) -> Dict[str, SelectionStatistics]:
        """
        Simulate trait generation to validate statistical accuracy
        
        Args:
            config: GenConfig object with trait categories
            sample_size: Number of simulated selections per category
            tolerance: Custom tolerance for simulation (uses instance default if None)
            
        Returns:
            Dict[str, SelectionStatistics]: Simulation results by trait category
        """
        tolerance = tolerance or self.tolerance_accuracy
        return self._run_statistical_simulation(config, sample_size, tolerance)
    
    def _analyze_collection_feasibility(self, config: GenConfig) -> CollectionFeasibilityAnalysis:
        """Analyze overall collection feasibility"""
        collection_size = config.collection.size
        trait_categories = len(config.traits)
        complete_grid = config.is_complete_grid()
        
        # Calculate total possible combinations
        total_combinations = 1
        for trait_category in config.traits.values():
            total_combinations *= len(trait_category.variants)
        
        # Check if unique combinations are feasible
        unique_feasible = total_combinations >= collection_size if not config.generation.allow_duplicates else True
        
        # Calculate min/max trait occurrences
        min_occurrences = {}
        max_occurrences = {}
        
        for trait_key, trait_category in config.traits.items():
            trait_probs = self.weight_calculator.calculate_trait_probabilities(trait_category)
            
            category_min = {}
            category_max = {}
            
            for prob_info in trait_probs:
                expected_count = prob_info.probability * collection_size
                
                # Minimum: at least 1 if weight > 0, otherwise 0
                min_count = 1 if prob_info.weight > 0 else 0
                
                # Maximum: expected + tolerance
                max_count = math.ceil(expected_count * (1 + self.tolerance_max_frequency))
                
                category_min[prob_info.trait_name] = min_count
                category_max[prob_info.trait_name] = max_count
            
            min_occurrences[trait_key] = category_min
            max_occurrences[trait_key] = category_max
        
        # Calculate balance and complexity scores
        distribution_balance = self._calculate_distribution_balance_score(config)
        complexity_score = self._calculate_generation_complexity_score(config)
        
        # Add validation issues
        if not complete_grid:
            self.validation_issues.append(ValidationIssue(
                ValidationSeverity.WARNING,
                "grid_coverage",
                f"Incomplete grid coverage: only {len(config.get_all_positions())} of 9 positions filled"
            ))
        
        if not unique_feasible:
            self.validation_issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                "combination_feasibility",
                f"Insufficient trait combinations ({total_combinations}) for unique collection size ({collection_size})"
            ))
        
        return CollectionFeasibilityAnalysis(
            collection_size=collection_size,
            total_trait_categories=trait_categories,
            complete_grid_coverage=complete_grid,
            total_possible_combinations=total_combinations,
            unique_combinations_feasible=unique_feasible,
            min_trait_occurrences=min_occurrences,
            max_trait_occurrences=max_occurrences,
            distribution_balance_score=distribution_balance,
            generation_complexity_score=complexity_score
        )
    
    def _analyze_trait_distribution(self, trait_key: str, trait_category: TraitCategory, 
                                  collection_size: int) -> TraitDistributionAnalysis:
        """Analyze distribution for individual trait category"""
        if not trait_category.variants:
            self.validation_issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                "empty_category",
                f"Trait category '{trait_category.name}' has no variants",
                trait_key=trait_key
            ))
            # Return minimal analysis for empty category
            return TraitDistributionAnalysis(
                category_key=trait_key,
                category_name=trait_category.name,
                total_variants=0,
                total_weight=0,
                min_weight=0,
                max_weight=0,
                weight_distribution={},
                expected_frequencies={},
                expected_occurrences={},
                min_possible_occurrence={},
                max_possible_occurrence={},
                zero_weight_variants=[],
                rarity_balance_score=0.0
            )
        
        # Calculate trait probabilities
        trait_probs = self.weight_calculator.calculate_trait_probabilities(trait_category)
        
        # Extract weight information
        weights = [variant.rarity_weight for variant in trait_category.variants]
        total_weight = sum(weights)
        min_weight = min(weights)
        max_weight = max(weights)
        
        # Build analysis data
        weight_distribution = {variant.name: variant.rarity_weight for variant in trait_category.variants}
        expected_frequencies = {prob.trait_name: prob.probability for prob in trait_probs}
        expected_occurrences = {prob.trait_name: prob.probability * collection_size for prob in trait_probs}
        
        # Calculate min/max possible occurrences
        min_possible = {}
        max_possible = {}
        zero_weight_variants = []
        
        for prob in trait_probs:
            if prob.weight == 0:
                zero_weight_variants.append(prob.trait_name)
                min_possible[prob.trait_name] = 0
                max_possible[prob.trait_name] = 0
            else:
                min_possible[prob.trait_name] = 1  # Must appear at least once
                expected_count = prob.probability * collection_size
                max_possible[prob.trait_name] = math.ceil(expected_count * (1 + self.tolerance_max_frequency))
        
        # Calculate rarity balance score
        balance_score = self._calculate_trait_balance_score(weights)
        
        # Validate distribution requirements
        self._validate_trait_requirements(trait_key, trait_category, trait_probs, collection_size)
        
        return TraitDistributionAnalysis(
            category_key=trait_key,
            category_name=trait_category.name,
            total_variants=len(trait_category.variants),
            total_weight=total_weight,
            min_weight=min_weight,
            max_weight=max_weight,
            weight_distribution=weight_distribution,
            expected_frequencies=expected_frequencies,
            expected_occurrences=expected_occurrences,
            min_possible_occurrence=min_possible,
            max_possible_occurrence=max_possible,
            zero_weight_variants=zero_weight_variants,
            rarity_balance_score=balance_score
        )
    
    def _run_statistical_simulation(self, config: GenConfig, sample_size: int, 
                                  tolerance: Optional[float] = None) -> Dict[str, SelectionStatistics]:
        """Run statistical simulation to validate generation accuracy"""
        tolerance = tolerance or self.tolerance_accuracy
        simulation_results = {}
        
        for trait_key, trait_category in config.traits.items():
            if not trait_category.variants:
                continue
            
            try:
                weights = [variant.rarity_weight for variant in trait_category.variants]
                stats = analyze_selection_accuracy(weights, sample_size, tolerance, seed=42)
                simulation_results[trait_key] = stats
                
                # Add validation issues for simulation failures
                if not stats.within_tolerance:
                    self.validation_issues.append(ValidationIssue(
                        ValidationSeverity.WARNING,
                        "simulation_accuracy",
                        f"Statistical simulation for '{trait_category.name}' exceeds tolerance",
                        trait_key=trait_key,
                        expected_value=tolerance,
                        actual_value=stats.max_deviation,
                        deviation=stats.max_deviation - tolerance
                    ))
                
            except (RandomSelectionError, WeightCalculationError) as e:
                self.validation_issues.append(ValidationIssue(
                    ValidationSeverity.ERROR,
                    "simulation_failure",
                    f"Simulation failed for '{trait_category.name}': {str(e)}",
                    trait_key=trait_key
                ))
        
        return simulation_results
    
    def _validate_trait_requirements(self, trait_key: str, trait_category: TraitCategory, 
                                   trait_probs: List[TraitProbabilityInfo], collection_size: int) -> None:
        """Validate specific trait requirements"""
        for prob in trait_probs:
            expected_count = prob.probability * collection_size
            
            # Check minimum occurrence requirement
            if prob.weight > 0 and expected_count < 1:
                self.validation_issues.append(ValidationIssue(
                    ValidationSeverity.WARNING,
                    "minimum_occurrence",
                    f"Trait '{prob.trait_name}' may not appear in collection",
                    trait_key=trait_key,
                    trait_name=prob.trait_name,
                    expected_value=1.0,
                    actual_value=expected_count
                ))
            
            # Check maximum frequency requirement
            max_allowed = collection_size * (prob.probability + self.tolerance_max_frequency)
            if expected_count > max_allowed:
                self.validation_issues.append(ValidationIssue(
                    ValidationSeverity.WARNING,
                    "maximum_frequency",
                    f"Trait '{prob.trait_name}' may exceed maximum frequency tolerance",
                    trait_key=trait_key,
                    trait_name=prob.trait_name,
                    expected_value=max_allowed,
                    actual_value=expected_count
                ))
    
    def _calculate_distribution_balance_score(self, config: GenConfig) -> float:
        """Calculate overall distribution balance score (0-1)"""
        balance_scores = []
        
        for trait_category in config.traits.values():
            if trait_category.variants:
                weights = [variant.rarity_weight for variant in trait_category.variants]
                trait_balance = self._calculate_trait_balance_score(weights)
                balance_scores.append(trait_balance)
        
        return sum(balance_scores) / len(balance_scores) if balance_scores else 0.0
    
    def _calculate_trait_balance_score(self, weights: List[int]) -> float:
        """Calculate balance score for trait weights (0-1, higher is more balanced)"""
        if not weights or len(weights) <= 1:
            return 1.0
        
        # Calculate coefficient of variation (lower is more balanced)
        mean_weight = sum(weights) / len(weights)
        if mean_weight == 0:
            return 0.0
        
        variance = sum((w - mean_weight) ** 2 for w in weights) / len(weights)
        std_dev = math.sqrt(variance)
        cv = std_dev / mean_weight
        
        # Convert to 0-1 score (1 is perfectly balanced, 0 is highly imbalanced)
        # CV of 0 = perfect balance (score 1), higher CV = lower score
        balance_score = 1.0 / (1.0 + cv)
        
        return balance_score
    
    def _calculate_generation_complexity_score(self, config: GenConfig) -> float:
        """Calculate generation complexity score (0-1, higher is more complex)"""
        total_combinations = 1
        total_variants = 0
        
        for trait_category in config.traits.values():
            variant_count = len(trait_category.variants)
            total_combinations *= variant_count
            total_variants += variant_count
        
        # Complexity based on combination space vs collection size
        if config.collection.size == 0:
            return 0.0
        
        complexity_ratio = total_combinations / config.collection.size
        
        # Normalize to 0-1 scale
        if complexity_ratio >= 100:
            complexity_score = 1.0  # Very high complexity
        elif complexity_ratio >= 10:
            complexity_score = 0.7 + 0.3 * min(1.0, (complexity_ratio - 10) / 90)
        elif complexity_ratio >= 2:
            complexity_score = 0.3 + 0.4 * (complexity_ratio - 2) / 8
        else:
            complexity_score = 0.3 * complexity_ratio / 2
        
        return min(1.0, complexity_score)
    
    def _calculate_overall_validation_score(self, collection_analysis: CollectionFeasibilityAnalysis, 
                                          trait_analyses: Dict[str, TraitDistributionAnalysis]) -> Tuple[float, bool]:
        """Calculate overall validation score and validity status"""
        # Count validation issues by severity
        error_count = sum(1 for issue in self.validation_issues if issue.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for issue in self.validation_issues if issue.severity == ValidationSeverity.WARNING)
        critical_count = sum(1 for issue in self.validation_issues if issue.severity == ValidationSeverity.CRITICAL)
        
        # Base score from distribution balance
        base_score = collection_analysis.distribution_balance_score
        
        # Penalty for issues
        score_penalty = critical_count * 0.5 + error_count * 0.2 + warning_count * 0.05
        
        # Calculate final score
        final_score = max(0.0, base_score - score_penalty)
        
        # Determine validity (no critical errors, limited other issues)
        is_valid = (critical_count == 0 and error_count <= 1 and 
                   collection_analysis.unique_combinations_feasible)
        
        return final_score, is_valid
    
    def _generate_recommendations(self, collection_analysis: CollectionFeasibilityAnalysis, 
                                trait_analyses: Dict[str, TraitDistributionAnalysis]) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        # Collection-level recommendations
        if not collection_analysis.complete_grid_coverage:
            recommendations.append("Consider adding traits for all 9 grid positions for complete coverage")
        
        if not collection_analysis.unique_combinations_feasible:
            recommendations.append("Increase trait variants or reduce collection size to ensure unique combinations")
        
        if collection_analysis.distribution_balance_score < 0.5:
            recommendations.append("Consider balancing trait weights for more even distribution")
        
        # Trait-level recommendations
        for trait_key, analysis in trait_analyses.items():
            if analysis.rarity_balance_score < 0.3:
                recommendations.append(f"Rebalance weights in '{analysis.category_name}' category for better distribution")
            
            if analysis.zero_weight_variants:
                recommendations.append(f"Consider removing or adjusting zero-weight variants in '{analysis.category_name}'")
        
        # Issue-based recommendations
        error_categories = set(issue.category for issue in self.validation_issues 
                             if issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL])
        
        if "combination_feasibility" in error_categories:
            recommendations.append("Add more trait variants or enable duplicate combinations")
        
        if "minimum_occurrence" in error_categories:
            recommendations.append("Increase weights for rare traits or reduce collection size")
        
        return recommendations


# Convenience functions for easier usage
def validate_distribution(config: GenConfig, tolerance_accuracy: float = 0.02, 
                        tolerance_max_frequency: float = 0.05, 
                        run_simulation: bool = True) -> DistributionValidationResult:
    """
    Validate rarity distribution for a GenConfig collection
    
    Args:
        config: GenConfig object to validate
        tolerance_accuracy: Acceptable deviation from expected distribution (default 2%)
        tolerance_max_frequency: Max allowed frequency deviation (default 5%)
        run_simulation: Whether to run statistical simulation
        
    Returns:
        DistributionValidationResult: Validation results
    """
    validator = RarityDistributionValidator(
        tolerance_accuracy=tolerance_accuracy,
        tolerance_max_frequency=tolerance_max_frequency
    )
    return validator.validate_distribution(config, run_simulation=run_simulation)


def check_distribution_feasibility(config: GenConfig) -> bool:
    """
    Quick feasibility check for distribution requirements
    
    Args:
        config: GenConfig object to check
        
    Returns:
        bool: True if distribution is feasible
    """
    validator = RarityDistributionValidator()
    return validator.check_distribution_feasibility(config)


def simulate_generation_accuracy(config: GenConfig, sample_size: int = 10000, 
                               tolerance: float = 0.02) -> Dict[str, SelectionStatistics]:
    """
    Simulate trait generation to validate statistical accuracy
    
    Args:
        config: GenConfig object with trait categories
        sample_size: Number of simulated selections per category
        tolerance: Acceptable deviation from expected frequency
        
    Returns:
        Dict[str, SelectionStatistics]: Simulation results by trait category
    """
    validator = RarityDistributionValidator(tolerance_accuracy=tolerance)
    return validator.simulate_generation_accuracy(config, sample_size, tolerance)


def get_distribution_report(validation_result: DistributionValidationResult) -> str:
    """
    Generate human-readable distribution validation report
    
    Args:
        validation_result: DistributionValidationResult to format
        
    Returns:
        str: Formatted validation report
    """
    lines = []
    lines.append("🎲 Rarity Distribution Validation Report")
    lines.append("=" * 50)
    lines.append(f"Overall Status: {'✅ VALID' if validation_result.is_valid else '❌ INVALID'}")
    lines.append(f"Overall Score: {validation_result.overall_score:.3f}")
    lines.append("")
    
    # Collection Analysis
    collection = validation_result.collection_analysis
    lines.append("📊 Collection Analysis:")
    lines.append(f"  Collection Size: {collection.collection_size:,}")
    lines.append(f"  Trait Categories: {collection.total_trait_categories}")
    lines.append(f"  Grid Coverage: {'Complete (9/9)' if collection.complete_grid_coverage else 'Incomplete'}")
    lines.append(f"  Possible Combinations: {collection.total_possible_combinations:,}")
    lines.append(f"  Unique Feasible: {'✅ Yes' if collection.unique_combinations_feasible else '❌ No'}")
    lines.append(f"  Balance Score: {collection.distribution_balance_score:.3f}")
    lines.append("")
    
    # Validation Issues
    if validation_result.validation_issues:
        lines.append("⚠️ Validation Issues:")
        for issue in validation_result.validation_issues:
            severity_icon = {
                ValidationSeverity.INFO: "ℹ️",
                ValidationSeverity.WARNING: "⚠️",
                ValidationSeverity.ERROR: "❌",
                ValidationSeverity.CRITICAL: "🚨"
            }[issue.severity]
            lines.append(f"  {severity_icon} {issue.message}")
        lines.append("")
    
    # Recommendations
    if validation_result.recommendations:
        lines.append("💡 Recommendations:")
        for rec in validation_result.recommendations:
            lines.append(f"  • {rec}")
        lines.append("")
    
    return "\n".join(lines)


def create_distribution_validator(tolerance_accuracy: float = 0.02, 
                                tolerance_max_frequency: float = 0.05) -> RarityDistributionValidator:
    """
    Create a RarityDistributionValidator instance with specified settings
    
    Args:
        tolerance_accuracy: Acceptable deviation from expected distribution
        tolerance_max_frequency: Max allowed frequency deviation
        
    Returns:
        RarityDistributionValidator: Configured validator instance
    """
    return RarityDistributionValidator(
        tolerance_accuracy=tolerance_accuracy,
        tolerance_max_frequency=tolerance_max_frequency
    ) 