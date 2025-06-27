"""
GenConfig Configuration Manager

This module provides high-level configuration management for the GenConfig system,
orchestrating all configuration components (schema validation, parsing, logic validation)
into a unified configuration lifecycle management system.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.schema_validator import (
    validate_config_schema,
    SchemaValidationError,
    create_sample_config
)
from config.config_parser import (
    ConfigurationParser,
    GenConfig,
    ConfigParseError,
    load_config,
    create_config_summary
)
from config.logic_validator import (
    ConfigurationLogicValidator,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    validate_config_logic,
    get_validation_report
)
from utils.file_utils import validate_file_exists, ValidationError


class ConfigurationManagerError(Exception):
    """Custom exception for configuration manager errors"""
    pass


class ValidationMode(Enum):
    """Configuration validation modes"""
    SCHEMA_ONLY = "schema_only"
    LOGIC_ONLY = "logic_only"
    FULL = "full"
    SKIP_ALL = "skip_all"


class ValidationLevel(Enum):
    """Configuration validation strictness levels"""
    STRICT = "strict"       # Warnings treated as errors
    NORMAL = "normal"       # Standard validation
    PERMISSIVE = "permissive"  # Only critical errors


@dataclass
class ConfigurationState:
    """Complete configuration state"""
    config: Optional[GenConfig] = None
    config_path: Optional[str] = None
    schema_valid: bool = False
    schema_errors: List[str] = None
    logic_valid: bool = False
    logic_result: Optional[ValidationResult] = None
    load_time: Optional[float] = None
    validation_time: Optional[float] = None
    is_loaded: bool = False
    is_validated: bool = False
    
    def __post_init__(self):
        if self.schema_errors is None:
            self.schema_errors = []
    
    @property
    def is_valid(self) -> bool:
        """Check if configuration is fully valid"""
        return self.schema_valid and self.logic_valid and self.is_loaded
    
    @property
    def has_errors(self) -> bool:
        """Check if configuration has any errors"""
        return (len(self.schema_errors) > 0 or 
                (self.logic_result and len(self.logic_result.errors) > 0))
    
    @property
    def has_warnings(self) -> bool:
        """Check if configuration has any warnings"""
        return (self.logic_result and len(self.logic_result.warnings) > 0)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get complete configuration state summary"""
        summary = {
            "is_loaded": self.is_loaded,
            "is_validated": self.is_validated,
            "is_valid": self.is_valid,
            "has_errors": self.has_errors,
            "has_warnings": self.has_warnings,
            "config_path": self.config_path,
            "load_time_ms": round(self.load_time * 1000, 2) if self.load_time else None,
            "validation_time_ms": round(self.validation_time * 1000, 2) if self.validation_time else None,
            "schema_validation": {
                "valid": self.schema_valid,
                "errors": len(self.schema_errors),
                "error_messages": self.schema_errors
            }
        }
        
        if self.logic_result:
            summary["logic_validation"] = {
                "valid": self.logic_valid,
                "total_issues": len(self.logic_result.issues),
                "errors": len(self.logic_result.errors),
                "warnings": len(self.logic_result.warnings),
                "infos": len(self.logic_result.infos),
                "categories": list(set(issue.category for issue in self.logic_result.issues))
            }
        
        if self.config:
            summary["configuration"] = create_config_summary(self.config)
        
        return summary


class ConfigurationManager:
    """
    High-level configuration manager for the GenConfig system
    
    Orchestrates all configuration components:
    - Component 2.1: Schema validation
    - Component 2.2: Configuration parsing
    - Component 2.3: Logic validation
    """
    
    def __init__(self, 
                 validation_mode: ValidationMode = ValidationMode.FULL,
                 validation_level: ValidationLevel = ValidationLevel.NORMAL,
                 check_file_existence: bool = True):
        """
        Initialize configuration manager
        
        Args:
            validation_mode: What types of validation to perform
            validation_level: How strict validation should be
            check_file_existence: Whether to validate trait file existence
        """
        self.validation_mode = validation_mode
        self.validation_level = validation_level
        self.check_file_existence = check_file_existence
        self.state = ConfigurationState()
        
        # Initialize component processors
        self._parser = ConfigurationParser(validate_schema=False)
        self._logic_validator = ConfigurationLogicValidator(
            check_file_existence=check_file_existence,
            strict_mode=(validation_level == ValidationLevel.STRICT)
        )
    
    def load_configuration(self, config_path: str, 
                          traits_base_path: Optional[str] = None) -> ConfigurationState:
        """
        Load and validate configuration file
        
        Args:
            config_path: Path to configuration JSON file
            traits_base_path: Base path for trait files (optional)
            
        Returns:
            ConfigurationState: Complete configuration state
            
        Raises:
            ConfigurationManagerError: If loading fails critically
        """
        start_time = time.time()
        
        try:
            # Reset state
            self.state = ConfigurationState()
            self.state.config_path = str(Path(config_path).resolve())
            
            # Validate file exists
            if not validate_file_exists(config_path):
                raise ConfigurationManagerError(f"Configuration file not found: {config_path}")
            
            # Step 1: Schema validation (if enabled)
            if self.validation_mode in [ValidationMode.SCHEMA_ONLY, ValidationMode.FULL]:
                self.state.schema_valid, self.state.schema_errors = self._validate_schema(config_path)
                
                # In strict mode or schema-only mode, fail on schema errors
                if not self.state.schema_valid and (
                    self.validation_level == ValidationLevel.STRICT or 
                    self.validation_mode == ValidationMode.SCHEMA_ONLY
                ):
                    error_msg = f"Schema validation failed:\n" + "\n".join(self.state.schema_errors)
                    raise ConfigurationManagerError(error_msg)
            else:
                self.state.schema_valid = True  # Skip schema validation
            
            # Step 2: Configuration parsing
            self.state.config = self._parse_configuration(config_path)
            self.state.is_loaded = True
            self.state.load_time = time.time() - start_time
            
            # Step 3: Logic validation (if enabled)
            if self.validation_mode in [ValidationMode.LOGIC_ONLY, ValidationMode.FULL]:
                validation_start = time.time()
                self.state.logic_result = self._validate_logic(self.state.config, traits_base_path)
                self.state.logic_valid = self.state.logic_result.is_valid
                self.state.validation_time = time.time() - validation_start
                
                # In strict mode, fail on any logic issues
                if not self.state.logic_valid and self.validation_level == ValidationLevel.STRICT:
                    error_msg = f"Logic validation failed:\n{get_validation_report(self.state.logic_result)}"
                    raise ConfigurationManagerError(error_msg)
                
                # In permissive mode, only fail on critical errors (not warnings)
                # Note: currently all errors are considered critical, so permissive mode
                # allows configurations with warnings but not errors
                if (self.validation_level == ValidationLevel.PERMISSIVE and 
                    len(self.state.logic_result.errors) > 0):
                    error_msg = f"Critical logic validation errors:\n{get_validation_report(self.state.logic_result)}"
                    raise ConfigurationManagerError(error_msg)
            else:
                self.state.logic_valid = True  # Skip logic validation
            
            self.state.is_validated = True
            
            return self.state
            
        except ConfigurationManagerError:
            raise
        except Exception as e:
            raise ConfigurationManagerError(f"Failed to load configuration: {e}")
    
    def reload_configuration(self, traits_base_path: Optional[str] = None) -> ConfigurationState:
        """
        Reload the current configuration file
        
        Args:
            traits_base_path: Base path for trait files (optional)
            
        Returns:
            ConfigurationState: Reloaded configuration state
            
        Raises:
            ConfigurationManagerError: If no configuration is loaded or reload fails
        """
        if not self.state.config_path:
            raise ConfigurationManagerError("No configuration file to reload")
        
        return self.load_configuration(self.state.config_path, traits_base_path)
    
    def validate_configuration(self, config: GenConfig, 
                             traits_base_path: Optional[str] = None) -> ValidationResult:
        """
        Validate an already-loaded configuration object
        
        Args:
            config: GenConfig object to validate
            traits_base_path: Base path for trait files (optional)
            
        Returns:
            ValidationResult: Logic validation result
        """
        if self.validation_mode == ValidationMode.SKIP_ALL:
            return ValidationResult(is_valid=True, issues=[])
        
        return self._validate_logic(config, traits_base_path)
    
    def get_configuration(self) -> Optional[GenConfig]:
        """
        Get the currently loaded configuration
        
        Returns:
            GenConfig: Current configuration or None if not loaded
        """
        return self.state.config
    
    def get_state(self) -> ConfigurationState:
        """
        Get the current configuration state
        
        Returns:
            ConfigurationState: Complete current state
        """
        return self.state
    
    def is_valid(self) -> bool:
        """
        Check if current configuration is valid
        
        Returns:
            bool: True if configuration is fully valid
        """
        return self.state.is_valid
    
    def get_validation_report(self) -> str:
        """
        Get comprehensive validation report
        
        Returns:
            str: Formatted validation report
        """
        report_lines = []
        
        # Header
        status = "✅ VALID" if self.state.is_valid else "❌ INVALID"
        report_lines.append(f"GenConfig Configuration Manager Report: {status}")
        report_lines.append("=" * 70)
        
        # Configuration info
        if self.state.config_path:
            report_lines.append(f"Configuration File: {self.state.config_path}")
        
        if self.state.config:
            report_lines.append(f"Collection: {self.state.config.collection.name}")
            report_lines.append(f"Size: {self.state.config.collection.size}")
        
        # Performance metrics
        if self.state.load_time:
            report_lines.append(f"Load Time: {self.state.load_time * 1000:.2f}ms")
        if self.state.validation_time:
            report_lines.append(f"Validation Time: {self.state.validation_time * 1000:.2f}ms")
        
        # Validation results
        report_lines.append(f"\nValidation Mode: {self.validation_mode.value}")
        report_lines.append(f"Validation Level: {self.validation_level.value}")
        
        # Schema validation
        if self.validation_mode in [ValidationMode.SCHEMA_ONLY, ValidationMode.FULL]:
            schema_status = "✅ PASSED" if self.state.schema_valid else "❌ FAILED"
            report_lines.append(f"\nSchema Validation: {schema_status}")
            if self.state.schema_errors:
                report_lines.append(f"Schema Errors ({len(self.state.schema_errors)}):")
                for error in self.state.schema_errors:
                    report_lines.append(f"  ❌ {error}")
        
        # Logic validation
        if (self.validation_mode in [ValidationMode.LOGIC_ONLY, ValidationMode.FULL] and 
            self.state.logic_result):
            logic_status = "✅ PASSED" if self.state.logic_valid else "❌ FAILED"
            report_lines.append(f"\nLogic Validation: {logic_status}")
            
            if self.state.logic_result.issues:
                report_lines.append(get_validation_report(self.state.logic_result))
            else:
                report_lines.append("  ✅ No logic validation issues found")
        
        # Summary
        report_lines.append(f"\n📊 Summary:")
        report_lines.append(f"  Loaded: {'✅' if self.state.is_loaded else '❌'}")
        report_lines.append(f"  Validated: {'✅' if self.state.is_validated else '❌'}")
        report_lines.append(f"  Valid: {'✅' if self.state.is_valid else '❌'}")
        report_lines.append(f"  Errors: {'❌' if self.state.has_errors else '✅'}")
        report_lines.append(f"  Warnings: {'⚠️' if self.state.has_warnings else '✅'}")
        
        return "\n".join(report_lines)
    
    def save_configuration(self, config: GenConfig, output_path: str) -> bool:
        """
        Save configuration to file (placeholder for future implementation)
        
        Args:
            config: GenConfig object to save
            output_path: Path to save configuration
            
        Returns:
            bool: True if saved successfully
            
        Note:
            This is a placeholder method for future implementation
        """
        # TODO: Implement configuration saving in future components
        raise NotImplementedError("Configuration saving will be implemented in future components")
    
    def _validate_schema(self, config_path: str) -> Tuple[bool, List[str]]:
        """
        Perform schema validation using Component 2.1
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, error_messages)
        """
        try:
            return validate_config_schema(config_path)
        except Exception as e:
            return False, [f"Schema validation error: {e}"]
    
    def _parse_configuration(self, config_path: str) -> GenConfig:
        """
        Parse configuration using Component 2.2
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            GenConfig: Parsed configuration object
            
        Raises:
            ConfigurationManagerError: If parsing fails
        """
        try:
            # Use parser without schema validation since we handle that separately
            return self._parser.parse_config_file(config_path)
        except (ConfigParseError, SchemaValidationError) as e:
            raise ConfigurationManagerError(f"Configuration parsing failed: {e}")
        except Exception as e:
            raise ConfigurationManagerError(f"Unexpected parsing error: {e}")
    
    def _validate_logic(self, config: GenConfig, 
                       traits_base_path: Optional[str] = None) -> ValidationResult:
        """
        Perform logic validation using Component 2.3
        
        Args:
            config: GenConfig object to validate
            traits_base_path: Base path for trait files
            
        Returns:
            ValidationResult: Logic validation result
        """
        try:
            return self._logic_validator.validate_config(config, traits_base_path)
        except Exception as e:
            # Create error result if logic validation fails unexpectedly
            error_issue = ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="logic_validation_error",
                message=f"Logic validation failed: {e}",
                suggestion="Check configuration format and try again"
            )
            return ValidationResult(is_valid=False, issues=[error_issue])


def load_and_validate_config(config_path: str,
                           traits_base_path: Optional[str] = None,
                           validation_mode: ValidationMode = ValidationMode.FULL,
                           validation_level: ValidationLevel = ValidationLevel.NORMAL,
                           check_file_existence: bool = True) -> Tuple[GenConfig, ConfigurationState]:
    """
    Convenience function to load and validate configuration
    
    Args:
        config_path: Path to configuration JSON file
        traits_base_path: Base path for trait files (optional)
        validation_mode: What types of validation to perform
        validation_level: How strict validation should be
        check_file_existence: Whether to validate trait file existence
        
    Returns:
        Tuple[GenConfig, ConfigurationState]: Loaded config and state
        
    Raises:
        ConfigurationManagerError: If loading or validation fails
    """
    manager = ConfigurationManager(
        validation_mode=validation_mode,
        validation_level=validation_level,
        check_file_existence=check_file_existence
    )
    
    state = manager.load_configuration(config_path, traits_base_path)
    
    if not state.config:
        raise ConfigurationManagerError("Failed to load configuration")
    
    return state.config, state


def create_configuration_manager(validation_mode: ValidationMode = ValidationMode.FULL,
                               validation_level: ValidationLevel = ValidationLevel.NORMAL,
                               check_file_existence: bool = True) -> ConfigurationManager:
    """
    Factory function to create configuration manager
    
    Args:
        validation_mode: What types of validation to perform
        validation_level: How strict validation should be
        check_file_existence: Whether to validate trait file existence
        
    Returns:
        ConfigurationManager: Configured manager instance
    """
    return ConfigurationManager(
        validation_mode=validation_mode,
        validation_level=validation_level,
        check_file_existence=check_file_existence
    )


def validate_config_file(config_path: str,
                        traits_base_path: Optional[str] = None,
                        validation_level: ValidationLevel = ValidationLevel.NORMAL) -> ValidationResult:
    """
    Quick validation of a configuration file
    
    Args:
        config_path: Path to configuration JSON file
        traits_base_path: Base path for trait files (optional)
        validation_level: How strict validation should be
        
    Returns:
        ValidationResult: Combined validation result
        
    Raises:
        ConfigurationManagerError: If validation setup fails
    """
    manager = ConfigurationManager(
        validation_mode=ValidationMode.FULL,
        validation_level=validation_level,
        check_file_existence=(traits_base_path is not None)
    )
    
    try:
        state = manager.load_configuration(config_path, traits_base_path)
        
        # Combine schema and logic validation results
        all_issues = []
        
        # Add schema errors as validation issues
        for error in state.schema_errors:
            issue = ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="schema_validation",
                message=error
            )
            all_issues.append(issue)
        
        # Add logic validation issues
        if state.logic_result:
            all_issues.extend(state.logic_result.issues)
        
        # Determine overall validity
        is_valid = state.is_valid
        
        return ValidationResult(is_valid=is_valid, issues=all_issues)
        
    except ConfigurationManagerError:
        # Convert manager errors to validation results
        error_issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            category="configuration_manager",
            message="Configuration loading failed"
        )
        return ValidationResult(is_valid=False, issues=[error_issue]) 