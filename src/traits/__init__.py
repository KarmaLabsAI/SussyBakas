"""
GenConfig Traits Package

Trait file handling and validation for the GenConfig system.
"""

from .trait_validator import (
    TraitFileValidator,
    TraitValidationError,
    validate_trait_file,
    validate_multiple_trait_files,
    get_trait_validation_report
)

__all__ = [
    'TraitFileValidator',
    'TraitValidationError', 
    'validate_trait_file',
    'validate_multiple_trait_files',
    'get_trait_validation_report'
]
