"""
Grid System - 3x3 grid positioning and layout management

This module provides utilities for converting between grid positions (1-9) 
and grid coordinates (row, col) for the GenConfig 3x3 grid system, as well
as validating grid layout configurations and generating reference templates.
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

from .template_generator import (
    GridTemplateGenerator,
    GridTemplateDimensions,
    GridTemplateStyle,
    GridTemplateError,
    generate_grid_template,
    create_standard_template,
    get_template_info,
    validate_template_config
)

from .coordinate_system import (
    GridCoordinateSystem,
    GridSystemConfig,
    GridSystemState,
    CoordinateSystemInfo,
    CoordinateValidationMode,
    GridSystemError,
    create_grid_coordinate_system,
    verify_coordinate_system_consistency,
    get_coordinate_system_info,
    get_coordinate_system_report
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
    'check_position_uniqueness',
    
    # Template Generator (Component 4.3)
    'GridTemplateGenerator',
    'GridTemplateDimensions',
    'GridTemplateStyle',
    'GridTemplateError',
    'generate_grid_template',
    'create_standard_template',
    'get_template_info',
    'validate_template_config',
    
    # Coordinate System (Component 4.4)
    'GridCoordinateSystem',
    'GridSystemConfig',
    'GridSystemState',
    'CoordinateSystemInfo',
    'CoordinateValidationMode',
    'GridSystemError',
    'create_grid_coordinate_system',
    'verify_coordinate_system_consistency',
    'get_coordinate_system_info',
    'get_coordinate_system_report'
] 