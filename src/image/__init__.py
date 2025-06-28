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

__all__ = [
    'create_composite',
    'ImageCompositor', 
    'CompositeImageResult',
    'ImageCompositionError'
] 