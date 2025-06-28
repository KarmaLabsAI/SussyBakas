"""
GenConfig Validation Framework

This package provides comprehensive validation capabilities for the GenConfig system,
including schema validation, logic validation, asset validation, and integration testing.
"""

from .schema_suite import (
    SchemaValidationSuite,
    ComprehensiveValidationResult,
    ValidationPhase,
    ValidationMode,
    validate_config_comprehensive,
    get_comprehensive_validation_report
)

__all__ = [
    'SchemaValidationSuite',
    'ComprehensiveValidationResult', 
    'ValidationPhase',
    'ValidationMode',
    'validate_config_comprehensive',
    'get_comprehensive_validation_report'
] 