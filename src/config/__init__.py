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

from .logic_validator import (
    ConfigurationLogicValidator,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    ConfigurationLogicError,
    validate_config_logic,
    get_validation_report
)

from .config_manager import (
    ConfigurationManager,
    ConfigurationManagerError,
    ConfigurationState,
    ValidationMode,
    ValidationLevel,
    load_and_validate_config,
    create_configuration_manager,
    validate_config_file
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
    'create_config_summary',
    
    # Logic validation
    'ConfigurationLogicValidator',
    'ValidationResult',
    'ValidationIssue',
    'ValidationSeverity',
    'ConfigurationLogicError',
    'validate_config_logic',
    'get_validation_report',
    
    # Configuration management
    'ConfigurationManager',
    'ConfigurationManagerError',
    'ConfigurationState',
    'ValidationMode',
    'ValidationLevel',
    'load_and_validate_config',
    'create_configuration_manager',
    'validate_config_file'
] 