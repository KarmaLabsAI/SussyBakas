"""
GenConfig Configuration Logic Validator

This module validates logical consistency of configuration data beyond basic schema validation.
It works with parsed GenConfig objects to check for logical errors, constraints violations,
and business rule consistency.
"""

import os
import math
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.config_parser import GenConfig, TraitCategory, TraitVariant
from utils.file_utils import validate_file_exists, validate_image_file, ValidationError


class ValidationSeverity(Enum):
    """Validation issue severity levels"""
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ValidationIssue:
    """Single validation issue"""
    severity: ValidationSeverity
    category: str
    message: str
    path: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Complete validation result"""
    is_valid: bool
    issues: List[ValidationIssue]
    
    @property
    def errors(self) -> List[ValidationIssue]:
        """Get only error-level issues"""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.ERROR]
    
    @property
    def warnings(self) -> List[ValidationIssue]:
        """Get only warning-level issues"""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.WARNING]
    
    @property
    def infos(self) -> List[ValidationIssue]:
        """Get only info-level issues"""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.INFO]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary"""
        return {
            "is_valid": self.is_valid,
            "total_issues": len(self.issues),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "infos": len(self.infos),
            "categories": list(set(issue.category for issue in self.issues))
        }


class ConfigurationLogicError(Exception):
    """Custom exception for configuration logic validation errors"""
    pass


class ConfigurationLogicValidator:
    """
    Main configuration logic validator class
    """
    
    def __init__(self, check_file_existence: bool = True, 
                 strict_mode: bool = False):
        """
        Initialize configuration logic validator
        
        Args:
            check_file_existence: Whether to validate trait file existence
            strict_mode: Whether to treat warnings as errors
        """
        self.check_file_existence = check_file_existence
        self.strict_mode = strict_mode
        self.issues: List[ValidationIssue] = []
    
    def validate_config(self, config: GenConfig, 
                       traits_base_path: Optional[str] = None) -> ValidationResult:
        """
        Validate logical consistency of configuration
        
        Args:
            config: Parsed GenConfig object to validate
            traits_base_path: Base path for trait files (optional)
            
        Returns:
            ValidationResult: Complete validation result
        """
        self.issues = []
        
        # Perform all validation checks
        self._validate_grid_consistency(config)
        self._validate_dimension_consistency(config)
        self._validate_collection_constraints(config)
        self._validate_rarity_logic(config)
        self._validate_trait_requirements(config)
        self._validate_generation_feasibility(config)
        
        # File-based validation if enabled
        if self.check_file_existence and traits_base_path:
            self._validate_trait_files(config, traits_base_path)
        
        # Determine if configuration is valid
        error_count = len([issue for issue in self.issues 
                          if issue.severity == ValidationSeverity.ERROR])
        warning_count = len([issue for issue in self.issues 
                           if issue.severity == ValidationSeverity.WARNING])
        
        # In strict mode, warnings are treated as errors
        is_valid = error_count == 0 and (not self.strict_mode or warning_count == 0)
        
        return ValidationResult(is_valid=is_valid, issues=self.issues.copy())
    
    def _validate_grid_consistency(self, config: GenConfig) -> None:
        """Validate grid position consistency and completeness"""
        used_positions = set()
        used_coordinates = set()
        
        # Check each trait's grid position
        for trait_key, trait in config.traits.items():
            # Extract expected position from trait key
            try:
                expected_position = int(trait_key.split('-')[1])
            except (IndexError, ValueError):
                self._add_issue(
                    ValidationSeverity.ERROR,
                    "grid_consistency",
                    f"Invalid trait key format: {trait_key}",
                    f"traits.{trait_key}",
                    "Trait keys should follow 'position-X-category' format"
                )
                continue
            
            # Calculate actual position from coordinates
            actual_position = trait.grid_position.row * 3 + trait.grid_position.column + 1
            
            # Check position consistency
            if expected_position != actual_position:
                self._add_issue(
                    ValidationSeverity.ERROR,
                    "grid_consistency",
                    f"Position mismatch: key indicates position {expected_position}, "
                    f"coordinates indicate position {actual_position}",
                    f"traits.{trait_key}.grid_position",
                    f"Use coordinates ({(expected_position-1)//3}, {(expected_position-1)%3}) for position {expected_position}"
                )
            
            # Check for duplicate positions
            if actual_position in used_positions:
                self._add_issue(
                    ValidationSeverity.ERROR,
                    "grid_consistency",
                    f"Duplicate grid position {actual_position}",
                    f"traits.{trait_key}.grid_position"
                )
            else:
                used_positions.add(actual_position)
            
            # Check for duplicate coordinates
            coord_tuple = (trait.grid_position.row, trait.grid_position.column)
            if coord_tuple in used_coordinates:
                self._add_issue(
                    ValidationSeverity.ERROR,
                    "grid_consistency",
                    f"Duplicate grid coordinates {coord_tuple}",
                    f"traits.{trait_key}.grid_position"
                )
            else:
                used_coordinates.add(coord_tuple)
            
            # Validate coordinate bounds
            if not (0 <= trait.grid_position.row <= 2):
                self._add_issue(
                    ValidationSeverity.ERROR,
                    "grid_consistency",
                    f"Invalid grid row {trait.grid_position.row} (must be 0-2)",
                    f"traits.{trait_key}.grid_position.row"
                )
            
            if not (0 <= trait.grid_position.column <= 2):
                self._add_issue(
                    ValidationSeverity.ERROR,
                    "grid_consistency",
                    f"Invalid grid column {trait.grid_position.column} (must be 0-2)",
                    f"traits.{trait_key}.grid_position.column"
                )
        
        # Check for missing positions if required
        if config.validation.require_all_positions:
            missing_positions = set(range(1, 10)) - used_positions
            if missing_positions:
                self._add_issue(
                    ValidationSeverity.ERROR,
                    "grid_completeness",
                    f"Missing required grid positions: {sorted(missing_positions)}",
                    "traits",
                    "Add trait categories for all missing positions"
                )
        elif used_positions:
            # Warn about incomplete grid even if not required
            missing_positions = set(range(1, 10)) - used_positions
            if missing_positions:
                self._add_issue(
                    ValidationSeverity.WARNING,
                    "grid_completeness",
                    f"Grid incomplete: missing positions {sorted(missing_positions)}",
                    "traits",
                    "Consider adding traits for all 9 positions for complete grid"
                )
    
    def _validate_dimension_consistency(self, config: GenConfig) -> None:
        """Validate image and grid dimension consistency"""
        # Check image size matches grid dimensions
        expected_width = config.generation.grid.cell_size.width * config.generation.grid.columns
        expected_height = config.generation.grid.cell_size.height * config.generation.grid.rows
        
        if config.generation.image_size.width != expected_width:
            self._add_issue(
                ValidationSeverity.ERROR,
                "dimension_consistency",
                f"Image width {config.generation.image_size.width} doesn't match "
                f"grid dimensions (expected {expected_width})",
                "generation.image_size.width",
                f"Set width to {expected_width} or adjust cell/grid size"
            )
        
        if config.generation.image_size.height != expected_height:
            self._add_issue(
                ValidationSeverity.ERROR,
                "dimension_consistency",
                f"Image height {config.generation.image_size.height} doesn't match "
                f"grid dimensions (expected {expected_height})",
                "generation.image_size.height",
                f"Set height to {expected_height} or adjust cell/grid size"
            )
        
        # Validate grid is exactly 3x3
        if config.generation.grid.rows != 3:
            self._add_issue(
                ValidationSeverity.ERROR,
                "dimension_consistency",
                f"Grid rows must be 3, got {config.generation.grid.rows}",
                "generation.grid.rows"
            )
        
        if config.generation.grid.columns != 3:
            self._add_issue(
                ValidationSeverity.ERROR,
                "dimension_consistency",
                f"Grid columns must be 3, got {config.generation.grid.columns}",
                "generation.grid.columns"
            )
        
        # Check for reasonable cell sizes
        if config.generation.grid.cell_size.width < 50:
            self._add_issue(
                ValidationSeverity.WARNING,
                "dimension_reasonableness",
                f"Cell width {config.generation.grid.cell_size.width} is very small (< 50px)",
                "generation.grid.cell_size.width",
                "Consider using larger cell sizes for better image quality"
            )
        
        if config.generation.grid.cell_size.height < 50:
            self._add_issue(
                ValidationSeverity.WARNING,
                "dimension_reasonableness",
                f"Cell height {config.generation.grid.cell_size.height} is very small (< 50px)",
                "generation.grid.cell_size.height",
                "Consider using larger cell sizes for better image quality"
            )
        
        if config.generation.grid.cell_size.width > 2000:
            self._add_issue(
                ValidationSeverity.WARNING,
                "dimension_reasonableness",
                f"Cell width {config.generation.grid.cell_size.width} is very large (> 2000px)",
                "generation.grid.cell_size.width",
                "Large cell sizes may impact performance"
            )
        
        if config.generation.grid.cell_size.height > 2000:
            self._add_issue(
                ValidationSeverity.WARNING,
                "dimension_reasonableness",
                f"Cell height {config.generation.grid.cell_size.height} is very large (> 2000px)",
                "generation.grid.cell_size.height",
                "Large cell sizes may impact performance"
            )
    
    def _validate_collection_constraints(self, config: GenConfig) -> None:
        """Validate collection size and other constraints"""
        # Check collection size reasonableness
        if config.collection.size <= 0:
            self._add_issue(
                ValidationSeverity.ERROR,
                "collection_constraints",
                f"Collection size must be positive, got {config.collection.size}",
                "collection.size"
            )
        elif config.collection.size > 1000000:
            self._add_issue(
                ValidationSeverity.WARNING,
                "collection_constraints",
                f"Collection size {config.collection.size} is very large (> 1M)",
                "collection.size",
                "Large collections may require significant resources"
            )
        
        # Check symbol format
        if not config.collection.symbol.isupper():
            self._add_issue(
                ValidationSeverity.WARNING,
                "collection_constraints",
                f"Collection symbol '{config.collection.symbol}' should be uppercase",
                "collection.symbol",
                f"Use '{config.collection.symbol.upper()}' instead"
            )
        
        # Check for empty fields
        if not config.collection.name.strip():
            self._add_issue(
                ValidationSeverity.ERROR,
                "collection_constraints",
                "Collection name cannot be empty",
                "collection.name"
            )
        
        if not config.collection.description.strip():
            self._add_issue(
                ValidationSeverity.WARNING,
                "collection_constraints",
                "Collection description is empty",
                "collection.description",
                "Add a meaningful description for better discoverability"
            )
    
    def _validate_rarity_logic(self, config: GenConfig) -> None:
        """Validate rarity configuration logic"""
        # Check rarity tier consistency
        tier_ranges = []
        for tier_name, tier in config.rarity.rarity_tiers.items():
            if tier.min_weight > tier.max_weight:
                self._add_issue(
                    ValidationSeverity.ERROR,
                    "rarity_logic",
                    f"Rarity tier '{tier_name}': min_weight ({tier.min_weight}) > max_weight ({tier.max_weight})",
                    f"rarity.rarity_tiers.{tier_name}"
                )
            tier_ranges.append((tier_name, tier.min_weight, tier.max_weight))
        
        # Check for tier overlaps
        tier_ranges.sort(key=lambda x: x[1])  # Sort by min_weight
        for i in range(len(tier_ranges) - 1):
            current_tier, current_min, current_max = tier_ranges[i]
            next_tier, next_min, next_max = tier_ranges[i + 1]
            
            if current_max >= next_min:
                self._add_issue(
                    ValidationSeverity.WARNING,
                    "rarity_logic",
                    f"Rarity tiers '{current_tier}' and '{next_tier}' have overlapping ranges",
                    f"rarity.rarity_tiers",
                    "Ensure tier ranges don't overlap for clear rarity classification"
                )
        
        # Validate trait weights against rarity tiers
        for trait_key, trait in config.traits.items():
            for i, variant in enumerate(trait.variants):
                # Find which tier this weight belongs to
                matching_tiers = []
                for tier_name, tier in config.rarity.rarity_tiers.items():
                    if tier.min_weight <= variant.rarity_weight <= tier.max_weight:
                        matching_tiers.append(tier_name)
                
                if not matching_tiers:
                    self._add_issue(
                        ValidationSeverity.WARNING,
                        "rarity_logic",
                        f"Variant '{variant.name}' weight {variant.rarity_weight} doesn't match any rarity tier",
                        f"traits.{trait_key}.variants[{i}].rarity_weight",
                        "Adjust weight to match a defined rarity tier"
                    )
                elif len(matching_tiers) > 1:
                    self._add_issue(
                        ValidationSeverity.WARNING,
                        "rarity_logic",
                        f"Variant '{variant.name}' weight {variant.rarity_weight} matches multiple tiers: {matching_tiers}",
                        f"traits.{trait_key}.variants[{i}].rarity_weight",
                        "Consider adjusting rarity tier ranges to avoid overlaps"
                    )
    
    def _validate_trait_requirements(self, config: GenConfig) -> None:
        """Validate trait category requirements and consistency"""
        required_traits = []
        optional_traits = []
        
        for trait_key, trait in config.traits.items():
            if trait.required:
                required_traits.append(trait_key)
            else:
                optional_traits.append(trait_key)
            
            # Check for empty trait categories
            if not trait.variants:
                self._add_issue(
                    ValidationSeverity.ERROR,
                    "trait_requirements",
                    f"Trait category '{trait.name}' has no variants",
                    f"traits.{trait_key}.variants",
                    "Add at least one variant to each trait category"
                )
            
            # Check for duplicate variant names within category
            variant_names = set()
            variant_filenames = set()
            for i, variant in enumerate(trait.variants):
                if variant.name in variant_names:
                    self._add_issue(
                        ValidationSeverity.ERROR,
                        "trait_requirements",
                        f"Duplicate variant name '{variant.name}' in trait '{trait.name}'",
                        f"traits.{trait_key}.variants[{i}].name"
                    )
                variant_names.add(variant.name)
                
                if variant.filename in variant_filenames:
                    self._add_issue(
                        ValidationSeverity.ERROR,
                        "trait_requirements",
                        f"Duplicate filename '{variant.filename}' in trait '{trait.name}'",
                        f"traits.{trait_key}.variants[{i}].filename"
                    )
                variant_filenames.add(variant.filename)
                
                # Check rarity weight
                if variant.rarity_weight <= 0:
                    self._add_issue(
                        ValidationSeverity.ERROR,
                        "trait_requirements",
                        f"Variant '{variant.name}' has invalid rarity weight {variant.rarity_weight}",
                        f"traits.{trait_key}.variants[{i}].rarity_weight",
                        "Rarity weights must be positive integers"
                    )
        
        # Warn if no required traits
        if not required_traits and config.validation.require_all_positions:
            self._add_issue(
                ValidationSeverity.WARNING,
                "trait_requirements",
                "No required traits defined but require_all_positions is enabled",
                "traits",
                "Consider marking essential traits as required"
            )
    
    def _validate_generation_feasibility(self, config: GenConfig) -> None:
        """Validate generation feasibility and constraints"""
        # First check if we have any traits at all
        if not config.traits:
            self._add_issue(
                ValidationSeverity.ERROR,
                "generation_feasibility",
                "No trait categories defined",
                "traits",
                "Add at least one trait category to enable generation"
            )
            return
        
        # Calculate maximum possible unique combinations
        total_combinations = 1
        for trait in config.traits.values():
            variant_count = len(trait.variants)
            if variant_count == 0:
                # If any trait has no variants, no combinations are possible
                total_combinations = 0
                break
            total_combinations *= variant_count
        
        # Check if collection size is feasible (only if duplicates not allowed and we have reasonable combinations)
        if not config.generation.allow_duplicates and total_combinations > 0:
            if config.collection.size > total_combinations:
                self._add_issue(
                    ValidationSeverity.ERROR,
                    "generation_feasibility",
                    f"Collection size {config.collection.size} exceeds maximum unique combinations {total_combinations}",
                    "collection.size",
                    f"Reduce collection size to {total_combinations} or enable allow_duplicates"
                )
            elif total_combinations > 1 and config.collection.size > total_combinations * 0.8:
                self._add_issue(
                    ValidationSeverity.WARNING,
                    "generation_feasibility",
                    f"Collection size {config.collection.size} is close to maximum combinations {total_combinations}",
                    "collection.size",
                    "Consider adding more trait variants or enabling duplicates"
                )
        
        # Check for reasonable trait variant distribution
        for trait_key, trait in config.traits.items():
            if len(trait.variants) == 1 and trait.required:
                self._add_issue(
                    ValidationSeverity.WARNING,
                    "generation_feasibility",
                    f"Required trait '{trait.name}' has only one variant",
                    f"traits.{trait_key}.variants",
                    "Single-variant required traits limit collection uniqueness"
                )
            
            # Check weight distribution (only if variants exist)
            if trait.variants:
                total_weight = sum(variant.rarity_weight for variant in trait.variants)
                if total_weight == 0:
                    self._add_issue(
                        ValidationSeverity.ERROR,
                        "generation_feasibility",
                        f"Trait '{trait.name}' has zero total rarity weight",
                        f"traits.{trait_key}.variants",
                        "Ensure at least one variant has positive rarity weight"
                    )
                
                # Check for extremely skewed distributions
                if len(trait.variants) > 1:
                    max_weight = max(variant.rarity_weight for variant in trait.variants)
                    if max_weight > total_weight * 0.9:
                        dominant_variant = next(v for v in trait.variants if v.rarity_weight == max_weight)
                        self._add_issue(
                            ValidationSeverity.WARNING,
                            "generation_feasibility",
                            f"Variant '{dominant_variant.name}' dominates trait '{trait.name}' (>90% probability)",
                            f"traits.{trait_key}.variants",
                            "Consider balancing rarity weights for better distribution"
                        )
    
    def _validate_trait_files(self, config: GenConfig, traits_base_path: str) -> None:
        """Validate trait file existence and properties"""
        if not traits_base_path:
            return
        
        base_path = Path(traits_base_path)
        if not base_path.exists():
            self._add_issue(
                ValidationSeverity.ERROR,
                "file_validation",
                f"Traits base path does not exist: {traits_base_path}",
                "traits_base_path"
            )
            return
        
        expected_cell_size = (
            config.generation.grid.cell_size.width,
            config.generation.grid.cell_size.height
        )
        
        for trait_key, trait in config.traits.items():
            trait_dir = base_path / trait_key
            
            for i, variant in enumerate(trait.variants):
                file_path = trait_dir / variant.filename
                
                # Check file existence
                if not file_path.exists():
                    self._add_issue(
                        ValidationSeverity.ERROR,
                        "file_validation",
                        f"Trait file not found: {file_path}",
                        f"traits.{trait_key}.variants[{i}].filename",
                        f"Create file or update filename in configuration"
                    )
                    continue
                
                # Validate image properties if enabled
                if config.validation.validate_image_dimensions:
                    try:
                        validate_image_file(str(file_path), expected_cell_size)
                    except ValidationError as e:
                        self._add_issue(
                            ValidationSeverity.ERROR,
                            "file_validation",
                            f"Invalid trait file {file_path}: {e}",
                            f"traits.{trait_key}.variants[{i}].filename",
                            "Ensure image matches required format and dimensions"
                        )
    
    def _add_issue(self, severity: ValidationSeverity, category: str, 
                   message: str, path: Optional[str] = None, 
                   suggestion: Optional[str] = None) -> None:
        """Add validation issue to the list"""
        issue = ValidationIssue(
            severity=severity,
            category=category,
            message=message,
            path=path,
            suggestion=suggestion
        )
        self.issues.append(issue)


def validate_config_logic(config: GenConfig, 
                         traits_base_path: Optional[str] = None,
                         check_file_existence: bool = True,
                         strict_mode: bool = False) -> ValidationResult:
    """
    Convenience function to validate configuration logic
    
    Args:
        config: Parsed GenConfig object to validate
        traits_base_path: Base path for trait files (optional)
        check_file_existence: Whether to validate trait file existence
        strict_mode: Whether to treat warnings as errors
        
    Returns:
        ValidationResult: Complete validation result
    """
    validator = ConfigurationLogicValidator(
        check_file_existence=check_file_existence,
        strict_mode=strict_mode
    )
    return validator.validate_config(config, traits_base_path)


def get_validation_report(result: ValidationResult) -> str:
    """
    Generate a human-readable validation report
    
    Args:
        result: ValidationResult to format
        
    Returns:
        str: Formatted validation report
    """
    report_lines = []
    summary = result.get_summary()
    
    # Header
    status = "✅ VALID" if result.is_valid else "❌ INVALID"
    report_lines.append(f"Configuration Logic Validation: {status}")
    report_lines.append("=" * 60)
    
    # Summary
    report_lines.append(f"Total Issues: {summary['total_issues']}")
    report_lines.append(f"Errors: {summary['errors']}")
    report_lines.append(f"Warnings: {summary['warnings']}")
    report_lines.append(f"Info: {summary['infos']}")
    
    if summary['categories']:
        report_lines.append(f"Categories: {', '.join(summary['categories'])}")
    
    # Issues by severity
    for severity in [ValidationSeverity.ERROR, ValidationSeverity.WARNING, ValidationSeverity.INFO]:
        issues = [issue for issue in result.issues if issue.severity == severity]
        if issues:
            report_lines.append(f"\n{severity.value}S:")
            for issue in issues:
                prefix = "❌" if severity == ValidationSeverity.ERROR else "⚠️" if severity == ValidationSeverity.WARNING else "ℹ️"
                path_info = f" ({issue.path})" if issue.path else ""
                report_lines.append(f"  {prefix} {issue.message}{path_info}")
                if issue.suggestion:
                    report_lines.append(f"     💡 {issue.suggestion}")
    
    return "\n".join(report_lines) 