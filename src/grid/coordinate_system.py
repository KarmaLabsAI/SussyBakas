"""
Grid Coordinate System - Component 4.4

Unified grid coordinate management system that provides a consistent interface
for all grid-related operations in the GenConfig system. This module integrates
Components 4.1-4.3 (Position Calculator, Layout Validator, Template Generator)
to ensure consistent coordinate calculations throughout the application.
"""

import os
import sys
from typing import Dict, Set, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import existing grid components
from .position_calculator import (
    position_to_coordinates,
    coordinates_to_position,
    validate_position,
    validate_coordinates,
    get_all_positions,
    get_all_coordinates,
    get_position_mapping,
    get_coordinate_mapping,
    get_position_description,
    get_neighbor_positions,
    GridPositionError
)

from .layout_validator import (
    GridLayoutValidator,
    GridPositionAssignment,
    ValidationResult,
    ValidationSeverity,
    ValidationIssue,
    GridLayoutError
)

from .template_generator import (
    GridTemplateGenerator,
    GridTemplateDimensions,
    GridTemplateStyle,
    GridTemplateError
)


class GridSystemError(Exception):
    """Base exception for grid coordinate system errors"""
    pass


class CoordinateValidationMode(Enum):
    """Coordinate validation modes"""
    STRICT = "strict"
    PERMISSIVE = "permissive"
    DISABLED = "disabled"


@dataclass
class GridSystemConfig:
    """Configuration for the grid coordinate system"""
    validation_mode: CoordinateValidationMode = CoordinateValidationMode.STRICT
    enforce_consistency: bool = True
    cache_calculations: bool = True
    auto_validate_positions: bool = True
    template_style: Optional[GridTemplateStyle] = None
    template_dimensions: Optional[GridTemplateDimensions] = None


@dataclass
class GridSystemState:
    """Current state of the grid coordinate system"""
    total_positions: int
    assigned_positions: Set[int]
    unassigned_positions: Set[int]
    position_assignments: Dict[int, GridPositionAssignment]
    is_complete: bool
    is_valid: bool
    validation_issues: List[ValidationIssue]
    last_validation_time: Optional[str] = None


@dataclass
class CoordinateSystemInfo:
    """Information about the coordinate system"""
    grid_dimensions: Tuple[int, int]
    total_cells: int
    position_range: Tuple[int, int]
    coordinate_range: Tuple[Tuple[int, int], Tuple[int, int]]
    mapping_functions_available: List[str]
    validation_capabilities: List[str]
    template_generation_available: bool


class GridCoordinateSystem:
    """
    Unified Grid Coordinate Management System
    
    This class provides a consistent interface for all grid-related operations
    in the GenConfig system, ensuring coordinate consistency and integrating
    all grid components.
    """
    
    def __init__(self, config: Optional[GridSystemConfig] = None):
        """Initialize the grid coordinate system"""
        self.config = config or GridSystemConfig()
        self._layout_validator = GridLayoutValidator(
            strict_mode=(self.config.validation_mode == CoordinateValidationMode.STRICT)
        )
        self._template_generator = GridTemplateGenerator(
            dimensions=self.config.template_dimensions,
            style=self.config.template_style
        )
        
        # Cache for performance optimization
        self._position_cache: Dict[str, Any] = {}
        self._validation_cache: Dict[str, ValidationResult] = {}
        
        # Current grid state
        self._current_state: Optional[GridSystemState] = None
    
    def convert_position_to_coordinates(self, position: int) -> Tuple[int, int]:
        """Convert position number to grid coordinates with system validation"""
        try:
            if self.config.auto_validate_positions and not validate_position(position):
                raise GridSystemError(f"Invalid position {position}: must be between 1 and 9")
            
            # Use cached result if available
            cache_key = f"pos_to_coord_{position}"
            if self.config.cache_calculations and cache_key in self._position_cache:
                return self._position_cache[cache_key]
            
            coordinates = position_to_coordinates(position)
            
            # Cache the result
            if self.config.cache_calculations:
                self._position_cache[cache_key] = coordinates
            
            return coordinates
            
        except GridPositionError as e:
            raise GridSystemError(f"Position conversion failed: {e}")
    
    def convert_coordinates_to_position(self, row: int, col: int) -> int:
        """Convert grid coordinates to position number with system validation"""
        try:
            if self.config.auto_validate_positions and not validate_coordinates(row, col):
                raise GridSystemError(f"Invalid coordinates ({row}, {col}): must be between 0 and 2")
            
            # Use cached result if available
            cache_key = f"coord_to_pos_{row}_{col}"
            if self.config.cache_calculations and cache_key in self._position_cache:
                return self._position_cache[cache_key]
            
            position = coordinates_to_position(row, col)
            
            # Cache the result
            if self.config.cache_calculations:
                self._position_cache[cache_key] = position
            
            return position
            
        except GridPositionError as e:
            raise GridSystemError(f"Coordinate conversion failed: {e}")
    
    def validate_position_number(self, position: int) -> bool:
        """Validate position number with system configuration"""
        return validate_position(position)
    
    def validate_grid_coordinates(self, row: int, col: int) -> bool:
        """Validate grid coordinates with system configuration"""
        return validate_coordinates(row, col)
    
    def validate_grid_layout(self, config) -> ValidationResult:
        """Validate grid layout using integrated layout validator"""
        try:
            result = self._layout_validator.validate_grid_layout(config)
            
            # Cache validation result
            if self.config.cache_calculations:
                cache_key = f"layout_validation_{id(config)}"
                self._validation_cache[cache_key] = result
            
            # Update current state
            self._update_state_from_validation(config, result)
            
            return result
            
        except Exception as e:
            raise GridSystemError(f"Grid layout validation failed: {e}")
    
    def get_position_assignments(self, config) -> List[GridPositionAssignment]:
        """Get position assignments from configuration"""
        return self._layout_validator.get_position_assignments(config)
    
    def check_grid_completeness(self, config) -> Tuple[bool, Set[int]]:
        """Check if grid is complete (all positions assigned)"""
        return self._layout_validator.check_grid_completeness(config)
    
    def check_position_uniqueness(self, config) -> Tuple[bool, Dict[int, List[str]]]:
        """Check if all position assignments are unique"""
        return self._layout_validator.check_position_uniqueness(config)
    
    def generate_grid_template(self, output_path: Union[str, Path], 
                             categories: Optional[Dict[int, str]] = None,
                             include_guides: bool = True) -> bool:
        """Generate grid template using integrated template generator"""
        try:
            return self._template_generator.generate_template(
                output_path=output_path,
                categories=categories,
                include_guides=include_guides
            )
        except GridTemplateError as e:
            raise GridSystemError(f"Template generation failed: {e}")
    
    def create_template_in_memory(self, categories: Optional[Dict[int, str]] = None,
                                include_guides: bool = True):
        """Create template image in memory without saving to file"""
        try:
            return self._template_generator.create_template_data(
                categories=categories,
                include_guides=include_guides
            )
        except GridTemplateError as e:
            raise GridSystemError(f"In-memory template creation failed: {e}")
    
    def get_current_state(self) -> Optional[GridSystemState]:
        """Get current grid system state"""
        return self._current_state
    
    def get_system_info(self) -> CoordinateSystemInfo:
        """Get information about the coordinate system"""
        return CoordinateSystemInfo(
            grid_dimensions=(3, 3),
            total_cells=9,
            position_range=(1, 9),
            coordinate_range=((0, 2), (0, 2)),
            mapping_functions_available=[
                "position_to_coordinates",
                "coordinates_to_position",
                "get_position_mapping",
                "get_coordinate_mapping",
                "get_neighbor_positions"
            ],
            validation_capabilities=[
                "position_validation",
                "coordinate_validation", 
                "layout_validation",
                "completeness_checking",
                "uniqueness_checking"
            ],
            template_generation_available=True
        )
    
    def get_position_mappings(self) -> Dict[str, Dict]:
        """Get complete position and coordinate mappings"""
        return {
            "position_to_coordinates": get_position_mapping(),
            "coordinates_to_position": get_coordinate_mapping()
        }
    
    def get_all_valid_positions(self) -> List[int]:
        """Get list of all valid position numbers"""
        return get_all_positions()
    
    def get_all_valid_coordinates(self) -> List[Tuple[int, int]]:
        """Get list of all valid coordinate pairs"""
        return get_all_coordinates()
    
    def get_position_description(self, position: int) -> str:
        """Get human-readable description of position"""
        if not self.validate_position_number(position):
            raise GridSystemError(f"Invalid position {position}: cannot get description")
        return get_position_description(position)
    
    def get_neighbor_positions(self, position: int, include_diagonal: bool = True) -> List[int]:
        """Get neighboring positions for a given position"""
        if not self.validate_position_number(position):
            raise GridSystemError(f"Invalid position {position}: cannot get neighbors")
        return get_neighbor_positions(position, include_diagonal)
    
    def verify_consistency(self) -> ValidationResult:
        """Verify coordinate system consistency across all components"""
        issues = []
        
        # Test bidirectional conversion consistency
        for position in range(1, 10):
            try:
                # Position -> Coordinates -> Position
                coords = self.convert_position_to_coordinates(position)
                back_to_position = self.convert_coordinates_to_position(coords[0], coords[1])
                
                if position != back_to_position:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="consistency_error",
                        message=f"Bidirectional conversion failed: position {position} -> {coords} -> {back_to_position}",
                        suggestion="Check position calculation algorithms"
                    ))
            except Exception as e:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="conversion_error",
                    message=f"Conversion failed for position {position}: {e}",
                    suggestion="Check position calculation functions"
                ))
        
        # Test coordinate range consistency
        for row in range(3):
            for col in range(3):
                try:
                    # Coordinates -> Position -> Coordinates
                    position = self.convert_coordinates_to_position(row, col)
                    back_to_coords = self.convert_position_to_coordinates(position)
                    
                    if (row, col) != back_to_coords:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            category="consistency_error", 
                            message=f"Bidirectional conversion failed: ({row}, {col}) -> {position} -> {back_to_coords}",
                            suggestion="Check coordinate calculation algorithms"
                        ))
                except Exception as e:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="conversion_error",
                        message=f"Conversion failed for coordinates ({row}, {col}): {e}",
                        suggestion="Check coordinate calculation functions"
                    ))
        
        # Test mapping consistency
        try:
            pos_mapping = get_position_mapping()
            coord_mapping = get_coordinate_mapping()
            
            for pos, coords in pos_mapping.items():
                if coord_mapping.get(coords) != pos:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        category="mapping_inconsistency",
                        message=f"Mapping inconsistency: position {pos} maps to {coords}, but {coords} maps to {coord_mapping.get(coords)}",
                        suggestion="Check mapping generation functions"
                    ))
        except Exception as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="mapping_error",
                message=f"Mapping consistency check failed: {e}",
                suggestion="Check mapping functions"
            ))
        
        is_valid = len([issue for issue in issues if issue.severity == ValidationSeverity.ERROR]) == 0
        
        return ValidationResult(is_valid=is_valid, issues=issues)
    
    def clear_cache(self) -> None:
        """Clear all cached calculations"""
        self._position_cache.clear()
        self._validation_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            "position_cache_size": len(self._position_cache),
            "validation_cache_size": len(self._validation_cache),
            "total_cache_entries": len(self._position_cache) + len(self._validation_cache)
        }
    
    def _update_state_from_validation(self, config, validation_result: ValidationResult) -> None:
        """Update current state based on validation result"""
        try:
            assignments = self._layout_validator.get_position_assignments(config)
            assigned_positions = {assignment.position for assignment in assignments}
            all_positions = set(range(1, 10))
            unassigned_positions = all_positions - assigned_positions
            
            position_assignments = {assignment.position: assignment for assignment in assignments}
            
            self._current_state = GridSystemState(
                total_positions=9,
                assigned_positions=assigned_positions,
                unassigned_positions=unassigned_positions,
                position_assignments=position_assignments,
                is_complete=len(unassigned_positions) == 0,
                is_valid=validation_result.is_valid,
                validation_issues=validation_result.issues,
                last_validation_time=None
            )
        except Exception:
            # If state update fails, create minimal state
            self._current_state = GridSystemState(
                total_positions=9,
                assigned_positions=set(),
                unassigned_positions=set(range(1, 10)),
                position_assignments={},
                is_complete=False,
                is_valid=validation_result.is_valid,
                validation_issues=validation_result.issues
            )


# Convenience Functions

def create_grid_coordinate_system(config: Optional[GridSystemConfig] = None) -> GridCoordinateSystem:
    """Create a grid coordinate system with optional configuration"""
    return GridCoordinateSystem(config)


def verify_coordinate_system_consistency() -> ValidationResult:
    """Verify coordinate system consistency using default configuration"""
    system = GridCoordinateSystem()
    return system.verify_consistency()


def get_coordinate_system_info() -> CoordinateSystemInfo:
    """Get information about the coordinate system"""
    system = GridCoordinateSystem()
    return system.get_system_info()


def get_coordinate_system_report(system: GridCoordinateSystem) -> str:
    """Generate a human-readable report about the coordinate system"""
    info = system.get_system_info()
    state = system.get_current_state()
    cache_stats = system.get_cache_stats()
    
    report_lines = [
        "=== Grid Coordinate System Report ===",
        f"Grid Dimensions: {info.grid_dimensions}",
        f"Total Cells: {info.total_cells}",
        f"Position Range: {info.position_range}",
        f"Coordinate Range: {info.coordinate_range}",
        f"Template Generation: {'Available' if info.template_generation_available else 'Not Available'}",
        "",
        "Available Functions:",
    ]
    
    for func in info.mapping_functions_available:
        report_lines.append(f"  - {func}")
    
    report_lines.extend([
        "",
        "Validation Capabilities:",
    ])
    
    for capability in info.validation_capabilities:
        report_lines.append(f"  - {capability}")
    
    if state:
        report_lines.extend([
            "",
            "Current State:",
            f"  - Total Positions: {state.total_positions}",
            f"  - Assigned Positions: {len(state.assigned_positions)}",
            f"  - Unassigned Positions: {len(state.unassigned_positions)}",
            f"  - Grid Complete: {state.is_complete}",
            f"  - Grid Valid: {state.is_valid}",
            f"  - Validation Issues: {len(state.validation_issues)}",
        ])
    
    report_lines.extend([
        "",
        "Cache Statistics:",
        f"  - Position Cache Entries: {cache_stats['position_cache_size']}",
        f"  - Validation Cache Entries: {cache_stats['validation_cache_size']}",
        f"  - Total Cache Entries: {cache_stats['total_cache_entries']}",
    ])
    
    return "\n".join(report_lines)
