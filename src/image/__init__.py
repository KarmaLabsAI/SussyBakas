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

from .image_utils import (
    resize_image,
    convert_image_format,
    handle_image_transparency,
    get_image_info as get_image_info_utils,
    standardize_trait_image,
    batch_process_images,
    ImageProcessingError
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
    'ImageValidationError',
    
    # Utilities exports
    'resize_image',
    'convert_image_format',
    'handle_image_transparency',
    'get_image_info_utils',
    'standardize_trait_image',
    'batch_process_images',
    'ImageProcessingError'
] 