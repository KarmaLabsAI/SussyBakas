"""
GenConfig Image Processing Engine

This package provides image processing functionality for the GenConfig system,
including composite image generation, validation, and utilities.
"""

from .compositor import (
    create_composite,
    ImageCompositor,
    CompositeImageResult,
    ImageCompositionError
)

from .image_validator import (
    validate_image,
    validate_multiple_images,
    get_image_validation_report,
    create_image_validator,
    get_image_info,
    ImageValidator,
    ImageValidationInfo,
    ImageValidationMode,
    ImageValidationError
)

__all__ = [
    # Compositor exports
    'create_composite',
    'ImageCompositor', 
    'CompositeImageResult',
    'ImageCompositionError',
    
    # Validator exports
    'validate_image',
    'validate_multiple_images',
    'get_image_validation_report',
    'create_image_validator',
    'get_image_info',
    'ImageValidator',
    'ImageValidationInfo',
    'ImageValidationMode',
    'ImageValidationError'
] 