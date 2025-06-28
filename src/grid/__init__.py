"""
Grid System - 3x3 grid positioning and layout management

This module provides utilities for converting between grid positions (1-9) 
and grid coordinates (row, col) for the GenConfig 3x3 grid system, as well
as validating grid layout configurations.
"""

from .position_calculator import (
    position_to_coordinates,
    coordinates_to_position,
    validate_position,
    validate_coordinates,
    GridPositionError
)

from .layout_validator import (
    GridLayoutValidator,
    GridPositionAssignment,
    GridLayoutError,
    validate_grid_layout,
    get_grid_layout_report,
    check_grid_completeness,
    check_position_uniqueness
)

__all__ = [
    # Position Calculator (Component 4.1)
    'position_to_coordinates',
    'coordinates_to_position', 
    'validate_position',
    'validate_coordinates',
    'GridPositionError',
    
    # Layout Validator (Component 4.2)
    'GridLayoutValidator',
    'GridPositionAssignment',
    'GridLayoutError',
    'validate_grid_layout',
    'get_grid_layout_report',
    'check_grid_completeness',
    'check_position_uniqueness'
] 