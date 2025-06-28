"""
Grid Layout Validator

Validates grid position assignments in GenConfig configurations to ensure:
- All required positions are assigned
- No duplicate position assignments
- Grid positions are valid (1-9)
- Position assignments match trait category keys
- Grid completeness and consistency

This module works with GenConfig objects to validate the grid layout
according to the 3×3 grid specification.
"""

import os
import sys
from typing import Dict, Set, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from grid.position_calculator import (
    position_to_coordinates, 
    coordinates_to_position,
    validate_position,
    validate_coordinates,
    GridPositionError
)


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
    
    def get_summary(self) -> Dict[str, any]:
        """Get validation summary"""
        return {
            "is_valid": self.is_valid,
            "total_issues": len(self.issues),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "infos": len(self.infos),
            "categories": list(set(issue.category for issue in self.issues))
        }


class GridLayoutError(Exception):
    """Exception raised for grid layout validation errors"""
    pass


@dataclass
class GridPositionAssignment:
    """Information about a single grid position assignment"""
    position: int
    coordinates: Tuple[int, int]
    trait_category_key: str
    trait_name: str
    is_required: bool


class GridLayoutValidator:
    """
    Grid Layout Validator for GenConfig configurations
    
    Validates grid position assignments to ensure:
    - Grid completeness (all 9 positions assigned if required)
    - Position uniqueness (no duplicate assignments)
    - Valid position numbers (1-9)
    - Coordinate consistency
    - Trait category key format compliance
    """
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize grid layout validator
        
        Args:
            strict_mode: Whether to treat warnings as errors
        """
        self.strict_mode = strict_mode
        self.issues: List[ValidationIssue] = []
    
    def validate_grid_layout(self, config) -> ValidationResult:
        """
        Validate grid layout from GenConfig object
        
        Args:
            config: GenConfig object containing trait configuration
            
        Returns:
            ValidationResult: Complete validation result
        """
        self.issues = []
        
        # Extract position assignments from config
        assignments = self._extract_position_assignments(config)
        
        # Perform validation checks
        self._validate_position_uniqueness(assignments)
        self._validate_position_validity(assignments)
        self._validate_coordinate_consistency(assignments)
        self._validate_trait_key_format(assignments)
        self._validate_grid_completeness(assignments, config)
        
        # Generate summary information
        self._add_grid_summary(assignments, config)
        
        # Determine if layout is valid
        error_count = len([issue for issue in self.issues 
                          if issue.severity == ValidationSeverity.ERROR])
        warning_count = len([issue for issue in self.issues 
                           if issue.severity == ValidationSeverity.WARNING])
        
        # In strict mode, warnings are treated as errors
        is_valid = error_count == 0 and (not self.strict_mode or warning_count == 0)
        
        return ValidationResult(is_valid=is_valid, issues=self.issues.copy())
    
    def get_position_assignments(self, config) -> List[GridPositionAssignment]:
        """
        Get list of all grid position assignments from configuration
        
        Args:
            config: GenConfig object
            
        Returns:
            List[GridPositionAssignment]: List of position assignments
        """
        return self._extract_position_assignments(config)
    
    def check_grid_completeness(self, config) -> Tuple[bool, Set[int]]:
        """
        Check if grid is complete (all 9 positions assigned)
        
        Args:
            config: GenConfig object
            
        Returns:
            Tuple[bool, Set[int]]: (is_complete, missing_positions)
        """
        assignments = self._extract_position_assignments(config)
        assigned_positions = {assignment.position for assignment in assignments}
        all_positions = set(range(1, 10))
        missing_positions = all_positions - assigned_positions
        
        return len(missing_positions) == 0, missing_positions
    
    def check_position_uniqueness(self, config) -> Tuple[bool, Dict[int, List[str]]]:
        """
        Check if all position assignments are unique
        
        Args:
            config: GenConfig object
            
        Returns:
            Tuple[bool, Dict[int, List[str]]]: (is_unique, duplicate_assignments)
        """
        assignments = self._extract_position_assignments(config)
        position_map = {}
        duplicates = {}
        
        for assignment in assignments:
            if assignment.position in position_map:
                if assignment.position not in duplicates:
                    duplicates[assignment.position] = [position_map[assignment.position]]
                duplicates[assignment.position].append(assignment.trait_category_key)
            else:
                position_map[assignment.position] = assignment.trait_category_key
        
        return len(duplicates) == 0, duplicates
    
    def _extract_position_assignments(self, config) -> List[GridPositionAssignment]:
        """Extract grid position assignments from GenConfig object"""
        assignments = []
        
        for trait_key, trait in config.traits.items():
            try:
                # Calculate position from grid coordinates
                position = coordinates_to_position(
                    trait.grid_position.row, 
                    trait.grid_position.column
                )
                
                assignment = GridPositionAssignment(
                    position=position,
                    coordinates=(trait.grid_position.row, trait.grid_position.column),
                    trait_category_key=trait_key,
                    trait_name=trait.name,
                    is_required=trait.required
                )
                
                assignments.append(assignment)
                
            except GridPositionError as e:
                self._add_issue(
                    ValidationSeverity.ERROR,
                    "invalid_coordinates",
                    f"Invalid grid coordinates for trait '{trait_key}': {e}",
                    f"traits.{trait_key}.grid_position",
                    "Use valid coordinates (row: 0-2, column: 0-2)"
                )
        
        return assignments
    
    def _validate_position_uniqueness(self, assignments: List[GridPositionAssignment]) -> None:
        """Validate that each grid position is assigned exactly once"""
        position_assignments = {}
        
        for assignment in assignments:
            position = assignment.position
            
            if position in position_assignments:
                # Found duplicate position assignment
                existing_trait = position_assignments[position]
                self._add_issue(
                    ValidationSeverity.ERROR,
                    "duplicate_position",
                    f"Grid position {position} assigned to multiple traits: '{existing_trait.trait_category_key}' and '{assignment.trait_category_key}'",
                    f"traits.{assignment.trait_category_key}.grid_position",
                    f"Each grid position (1-9) must be assigned to exactly one trait"
                )
            else:
                position_assignments[position] = assignment
    
    def _validate_position_validity(self, assignments: List[GridPositionAssignment]) -> None:
        """Validate that all position numbers are valid (1-9)"""
        for assignment in assignments:
            if not validate_position(assignment.position):
                self._add_issue(
                    ValidationSeverity.ERROR,
                    "invalid_position",
                    f"Invalid grid position {assignment.position} for trait '{assignment.trait_category_key}'",
                    f"traits.{assignment.trait_category_key}.grid_position",
                    "Grid positions must be between 1 and 9"
                )
    
    def _validate_coordinate_consistency(self, assignments: List[GridPositionAssignment]) -> None:
        """Validate that coordinates match expected positions"""
        for assignment in assignments:
            try:
                # Verify coordinates are valid
                if not validate_coordinates(assignment.coordinates[0], assignment.coordinates[1]):
                    self._add_issue(
                        ValidationSeverity.ERROR,
                        "invalid_coordinates",
                        f"Invalid coordinates {assignment.coordinates} for trait '{assignment.trait_category_key}'",
                        f"traits.{assignment.trait_category_key}.grid_position",
                        "Use valid coordinates (row: 0-2, column: 0-2)"
                    )
                    continue
                
                # Verify position calculation consistency
                expected_position = coordinates_to_position(
                    assignment.coordinates[0], 
                    assignment.coordinates[1]
                )
                
                if expected_position != assignment.position:
                    self._add_issue(
                        ValidationSeverity.ERROR,
                        "coordinate_position_mismatch",
                        f"Coordinate mismatch for trait '{assignment.trait_category_key}': "
                        f"coordinates {assignment.coordinates} should map to position {expected_position}, "
                        f"but position {assignment.position} was calculated",
                        f"traits.{assignment.trait_category_key}.grid_position",
                        f"Use coordinates {position_to_coordinates(assignment.position)} for position {assignment.position}"
                    )
                    
            except GridPositionError as e:
                self._add_issue(
                    ValidationSeverity.ERROR,
                    "coordinate_calculation_error",
                    f"Error calculating position for trait '{assignment.trait_category_key}': {e}",
                    f"traits.{assignment.trait_category_key}.grid_position",
                    "Check coordinate values and format"
                )
    
    def _validate_trait_key_format(self, assignments: List[GridPositionAssignment]) -> None:
        """Validate that trait category keys follow the position-X-category format"""
        for assignment in assignments:
            trait_key = assignment.trait_category_key
            
            # Check if key follows expected format: position-X-category
            parts = trait_key.split('-')
            if len(parts) < 3 or parts[0] != 'position':
                self._add_issue(
                    ValidationSeverity.WARNING,
                    "trait_key_format",
                    f"Trait key '{trait_key}' doesn't follow recommended format 'position-X-category'",
                    f"traits.{trait_key}",
                    f"Consider renaming to 'position-{assignment.position}-{{category}}'"
                )
                continue
            
            try:
                key_position = int(parts[1])
                if key_position != assignment.position:
                    self._add_issue(
                        ValidationSeverity.WARNING,
                        "trait_key_position_mismatch",
                        f"Trait key '{trait_key}' indicates position {key_position} but grid coordinates indicate position {assignment.position}",
                        f"traits.{trait_key}",
                        f"Rename to 'position-{assignment.position}-{'-'.join(parts[2:])}' or update coordinates"
                    )
            except ValueError:
                self._add_issue(
                    ValidationSeverity.WARNING,
                    "trait_key_format",
                    f"Trait key '{trait_key}' has invalid position number format",
                    f"traits.{trait_key}",
                    f"Use format 'position-{assignment.position}-{{category}}'"
                )
    
    def _validate_grid_completeness(self, assignments: List[GridPositionAssignment], config) -> None:
        """Validate grid completeness based on configuration requirements"""
        assigned_positions = {assignment.position for assignment in assignments}
        all_positions = set(range(1, 10))
        missing_positions = all_positions - assigned_positions
        
        # Check validation configuration
        require_all_positions = getattr(config.validation, 'require_all_positions', True)
        
        if require_all_positions and missing_positions:
            self._add_issue(
                ValidationSeverity.ERROR,
                "incomplete_grid",
                f"Grid incomplete: missing required positions {sorted(missing_positions)}",
                "traits",
                f"Add trait categories for positions: {', '.join(str(p) for p in sorted(missing_positions))}"
            )
        elif missing_positions:
            self._add_issue(
                ValidationSeverity.WARNING,
                "incomplete_grid",
                f"Grid incomplete: missing positions {sorted(missing_positions)}",
                "traits",
                f"Consider adding traits for complete 3×3 grid coverage"
            )
        
        # Check for required traits
        required_assignments = [a for a in assignments if a.is_required]
        if require_all_positions and len(required_assignments) == 0:
            self._add_issue(
                ValidationSeverity.WARNING,
                "no_required_traits",
                "No traits marked as required but require_all_positions is enabled",
                "traits",
                "Consider marking essential traits as required"
            )
    
    def _add_grid_summary(self, assignments: List[GridPositionAssignment], config) -> None:
        """Add informational summary of grid layout"""
        if not assignments:
            self._add_issue(
                ValidationSeverity.ERROR,
                "no_grid_assignments",
                "No grid position assignments found",
                "traits",
                "Add trait categories with grid position assignments"
            )
            return
        
        assigned_positions = {assignment.position for assignment in assignments}
        required_count = len([a for a in assignments if a.is_required])
        
        self._add_issue(
            ValidationSeverity.INFO,
            "grid_summary",
            f"Grid layout: {len(assigned_positions)}/9 positions assigned, {required_count} required traits",
            "traits",
            None
        )
        
        # Check for good coverage
        coverage_percentage = (len(assigned_positions) / 9) * 100
        if coverage_percentage == 100:
            self._add_issue(
                ValidationSeverity.INFO,
                "grid_coverage",
                "Complete 3×3 grid coverage achieved",
                "traits",
                None
            )
        elif coverage_percentage >= 75:
            self._add_issue(
                ValidationSeverity.INFO,
                "grid_coverage",
                f"Good grid coverage: {coverage_percentage:.1f}%",
                "traits",
                None
            )
        elif coverage_percentage < 50:
            self._add_issue(
                ValidationSeverity.WARNING,
                "grid_coverage",
                f"Low grid coverage: {coverage_percentage:.1f}%",
                "traits",
                "Consider adding more trait categories for better coverage"
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


def validate_grid_layout(config, strict_mode: bool = False) -> ValidationResult:
    """
    Convenience function to validate grid layout from GenConfig object
    
    Args:
        config: GenConfig object to validate
        strict_mode: Whether to treat warnings as errors
        
    Returns:
        ValidationResult: Grid layout validation result
    """
    validator = GridLayoutValidator(strict_mode=strict_mode)
    return validator.validate_grid_layout(config)


def get_grid_layout_report(result: ValidationResult) -> str:
    """
    Generate human-readable grid layout validation report
    
    Args:
        result: ValidationResult to format
        
    Returns:
        str: Formatted validation report
    """
    report_lines = []
    summary = result.get_summary()
    
    # Header
    status = "✅ VALID" if result.is_valid else "❌ INVALID"
    report_lines.append(f"Grid Layout Validation: {status}")
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


def check_grid_completeness(config) -> Tuple[bool, Set[int]]:
    """
    Quick check for grid completeness
    
    Args:
        config: GenConfig object
        
    Returns:
        Tuple[bool, Set[int]]: (is_complete, missing_positions)
    """
    validator = GridLayoutValidator()
    return validator.check_grid_completeness(config)


def check_position_uniqueness(config) -> Tuple[bool, Dict[int, List[str]]]:
    """
    Quick check for position uniqueness
    
    Args:
        config: GenConfig object
        
    Returns:
        Tuple[bool, Dict[int, List[str]]]: (is_unique, duplicate_assignments)
    """
    validator = GridLayoutValidator()
    return validator.check_position_uniqueness(config) 