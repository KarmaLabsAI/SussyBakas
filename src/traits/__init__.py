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

from .directory_manager import (
    TraitDirectoryManager,
    TraitDirectoryError,
    TraitFileEntry,
    TraitDirectoryInfo,
    create_trait_directories,
    validate_trait_directories,
    organize_trait_files,
    get_trait_directory_report
)

from .asset_loader import (
    TraitAssetLoader,
    TraitAssetCache,
    TraitAssetError,
    LoadedTraitAsset,
    CacheStats,
    CacheStrategy,
    create_asset_loader,
    load_trait_asset,
    get_asset_loader_report
)

__all__ = [
    # Trait Validator
    'TraitFileValidator',
    'TraitValidationError', 
    'validate_trait_file',
    'validate_multiple_trait_files',
    'get_trait_validation_report',
    
    # Directory Manager
    'TraitDirectoryManager',
    'TraitDirectoryError',
    'TraitFileEntry',
    'TraitDirectoryInfo',
    'create_trait_directories',
    'validate_trait_directories',
    'organize_trait_files',
    'get_trait_directory_report',
    
    # Asset Loader
    'TraitAssetLoader',
    'TraitAssetCache',
    'TraitAssetError',
    'LoadedTraitAsset',
    'CacheStats',
    'CacheStrategy',
    'create_asset_loader',
    'load_trait_asset',
    'get_asset_loader_report'
]
