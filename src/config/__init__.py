"""
GenConfig Configuration Package

Configuration management and validation for the GenConfig system.
"""

from .schema_validator import (
    validate_config_schema,
    GenConfigSchema,
    SchemaValidationError,
    create_sample_config
)

from .config_parser import (
    ConfigurationParser,
    GenConfig,
    CollectionConfig,
    GenerationConfig,
    TraitCategory,
    TraitVariant,
    RarityConfig,
    ValidationConfig,
    ConfigParseError,
    load_config,
    parse_config_dict,
    create_config_summary
)

__all__ = [
    # Schema validation
    'validate_config_schema',
    'GenConfigSchema',
    'SchemaValidationError',
    'create_sample_config',
    
    # Configuration parsing
    'ConfigurationParser',
    'GenConfig',
    'CollectionConfig',
    'GenerationConfig',
    'TraitCategory',
    'TraitVariant',
    'RarityConfig',
    'ValidationConfig',
    'ConfigParseError',
    'load_config',
    'parse_config_dict',
    'create_config_summary'
] 