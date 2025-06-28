"""
GenConfig Schema Validation Suite

This module provides a comprehensive validation system that coordinates all validation
components to ensure complete configuration validation per GenConfig specification.
It serves as the central validation orchestrator for all configuration aspects.
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.schema_validator import validate_config_schema, SchemaValidationError
from config.config_parser import ConfigurationParser, GenConfig, ConfigParseError
from config.logic_validator import ConfigurationLogicValidator, ValidationResult, ValidationIssue, ValidationSeverity
from config.config_manager import ConfigurationManager, ValidationMode as ConfigValidationMode
from traits.trait_validator import validate_trait_file, TraitFileValidator
from utils.file_utils import validate_file_exists, safe_read_json


class ValidationPhase(Enum):
    """Validation phase indicators"""
    SCHEMA = "schema"
    PARSING = "parsing"
    LOGIC = "logic"
    TRAITS = "traits"
    INTEGRATION = "integration"


class ValidationMode(Enum):
    """Validation execution modes"""
    MINIMAL = "minimal"          # Schema validation only
    STANDARD = "standard"        # Schema + logic validation
    COMPREHENSIVE = "comprehensive"  # All validation phases
    STRICT = "strict"            # Comprehensive with strict mode


@dataclass
class PhaseResult:
    """Result for a single validation phase"""
    phase: ValidationPhase
    success: bool
    duration_ms: float
    issues: List[ValidationIssue] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComprehensiveValidationResult:
    """Complete comprehensive validation result"""
    overall_success: bool
    validation_mode: ValidationMode
    total_duration_ms: float
    config_path: str
    phase_results: Dict[ValidationPhase, PhaseResult] = field(default_factory=dict)
    config: Optional[GenConfig] = None
    
    @property
    def all_issues(self) -> List[ValidationIssue]:
        """Get all issues from all phases"""
        issues = []
        for phase_result in self.phase_results.values():
            issues.extend(phase_result.issues)
        return issues
    
    @property
    def errors(self) -> List[ValidationIssue]:
        """Get only error-level issues"""
        return [issue for issue in self.all_issues if issue.severity == ValidationSeverity.ERROR]
    
    @property
    def warnings(self) -> List[ValidationIssue]:
        """Get only warning-level issues"""
        return [issue for issue in self.all_issues if issue.severity == ValidationSeverity.WARNING]
    
    @property
    def infos(self) -> List[ValidationIssue]:
        """Get only info-level issues"""
        return [issue for issue in self.all_issues if issue.severity == ValidationSeverity.INFO]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive validation summary"""
        return {
            "overall_success": self.overall_success,
            "validation_mode": self.validation_mode.value,
            "total_duration_ms": self.total_duration_ms,
            "config_path": self.config_path,
            "phases_executed": [phase.value for phase in self.phase_results.keys()],
            "phase_success": {phase.value: result.success for phase, result in self.phase_results.items()},
            "total_issues": len(self.all_issues),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "infos": len(self.infos),
            "issue_categories": list(set(issue.category for issue in self.all_issues))
        }
    
    def get_phase_summary(self, phase: ValidationPhase) -> Optional[Dict[str, Any]]:
        """Get summary for specific phase"""
        if phase not in self.phase_results:
            return None
        
        result = self.phase_results[phase]
        return {
            "phase": result.phase.value,
            "success": result.success,
            "duration_ms": result.duration_ms,
            "issues_count": len(result.issues),
            "details": result.details
        }


class SchemaValidationSuite:
    """
    Comprehensive schema validation suite that coordinates all validation components
    """
    
    def __init__(self, validation_mode: ValidationMode = ValidationMode.STANDARD):
        """
        Initialize schema validation suite
        
        Args:
            validation_mode: Validation execution mode
        """
        self.validation_mode = validation_mode
        self.schema_validator = None
        self.config_parser = ConfigurationParser()
        self.logic_validator = ConfigurationLogicValidator(
            strict_mode=(validation_mode == ValidationMode.STRICT)
        )
        self.trait_validator = TraitFileValidator()
        
        # Track validation state
        self.current_config_path: Optional[str] = None
        self.current_config: Optional[GenConfig] = None
    
    def validate_configuration(self, config_path: Union[str, Path], 
                             traits_base_path: Optional[Union[str, Path]] = None) -> ComprehensiveValidationResult:
        """
        Perform comprehensive configuration validation
        
        Args:
            config_path: Path to configuration file
            traits_base_path: Base path for trait files (optional)
            
        Returns:
            ComprehensiveValidationResult: Complete validation result
        """
        config_path_str = str(config_path)
        self.current_config_path = config_path_str
        start_time = time.time()
        
        result = ComprehensiveValidationResult(
            overall_success=True,
            validation_mode=self.validation_mode,
            total_duration_ms=0.0,
            config_path=config_path_str
        )
        
        try:
            # Phase 1: Schema Validation
            if self.validation_mode != ValidationMode.MINIMAL or True:  # Always do schema validation
                schema_result = self._validate_schema_phase(config_path_str)
                result.phase_results[ValidationPhase.SCHEMA] = schema_result
                if not schema_result.success:
                    result.overall_success = False
                    if self.validation_mode == ValidationMode.MINIMAL:
                        return self._finalize_result(result, start_time)
            
            # Phase 2: Parsing Validation
            if self.validation_mode in [ValidationMode.STANDARD, ValidationMode.COMPREHENSIVE, ValidationMode.STRICT]:
                parsing_result = self._validate_parsing_phase(config_path_str)
                result.phase_results[ValidationPhase.PARSING] = parsing_result
                if not parsing_result.success:
                    result.overall_success = False
                    return self._finalize_result(result, start_time)
                
                # Store parsed config for subsequent phases
                result.config = parsing_result.details.get('config')
                self.current_config = result.config
            
            # Phase 3: Logic Validation
            if self.validation_mode in [ValidationMode.STANDARD, ValidationMode.COMPREHENSIVE, ValidationMode.STRICT]:
                if result.config:
                    logic_result = self._validate_logic_phase(result.config, traits_base_path)
                    result.phase_results[ValidationPhase.LOGIC] = logic_result
                    if not logic_result.success:
                        result.overall_success = False
                        if self.validation_mode == ValidationMode.STANDARD:
                            return self._finalize_result(result, start_time)
            
            # Phase 4: Trait File Validation
            if self.validation_mode in [ValidationMode.COMPREHENSIVE, ValidationMode.STRICT]:
                if result.config and traits_base_path:
                    traits_result = self._validate_traits_phase(result.config, traits_base_path)
                    result.phase_results[ValidationPhase.TRAITS] = traits_result
                    if not traits_result.success:
                        result.overall_success = False
            
            # Phase 5: Integration Validation
            if self.validation_mode in [ValidationMode.COMPREHENSIVE, ValidationMode.STRICT]:
                if result.config:
                    integration_result = self._validate_integration_phase(result.config, traits_base_path)
                    result.phase_results[ValidationPhase.INTEGRATION] = integration_result
                    if not integration_result.success:
                        result.overall_success = False
        
        except Exception as e:
            # Handle unexpected errors
            error_issue = ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="validation_error",
                message=f"Unexpected validation error: {str(e)}",
                path=config_path_str
            )
            
            error_result = PhaseResult(
                phase=ValidationPhase.SCHEMA,
                success=False,
                duration_ms=0.0,
                issues=[error_issue]
            )
            result.phase_results[ValidationPhase.SCHEMA] = error_result
            result.overall_success = False
        
        return self._finalize_result(result, start_time)
    
    def _validate_schema_phase(self, config_path: str) -> PhaseResult:
        """Validate JSON schema compliance"""
        start_time = time.time()
        
        try:
            is_valid, errors = validate_config_schema(config_path)
            
            issues = []
            for error in errors:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="schema_error",
                    message=error,
                    path=config_path
                ))
            
            duration = (time.time() - start_time) * 1000
            
            return PhaseResult(
                phase=ValidationPhase.SCHEMA,
                success=is_valid,
                duration_ms=duration,
                issues=issues,
                details={"schema_errors": errors}
            )
        
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            
            error_issue = ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="schema_validation_error",
                message=f"Schema validation failed: {str(e)}",
                path=config_path
            )
            
            return PhaseResult(
                phase=ValidationPhase.SCHEMA,
                success=False,
                duration_ms=duration,
                issues=[error_issue]
            )
    
    def _validate_parsing_phase(self, config_path: str) -> PhaseResult:
        """Validate configuration parsing"""
        start_time = time.time()
        
        try:
            config = self.config_parser.parse_config_file(config_path)
            
            duration = (time.time() - start_time) * 1000
            
            return PhaseResult(
                phase=ValidationPhase.PARSING,
                success=True,
                duration_ms=duration,
                issues=[],
                details={
                    "config": config,
                    "trait_count": len(config.traits),
                    "total_variants": sum(len(trait.variants) for trait in config.traits.values())
                }
            )
        
        except ConfigParseError as e:
            duration = (time.time() - start_time) * 1000
            
            error_issue = ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="parsing_error",
                message=f"Configuration parsing failed: {str(e)}",
                path=config_path
            )
            
            return PhaseResult(
                phase=ValidationPhase.PARSING,
                success=False,
                duration_ms=duration,
                issues=[error_issue]
            )
        
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            
            error_issue = ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="parsing_unexpected_error",
                message=f"Unexpected parsing error: {str(e)}",
                path=config_path
            )
            
            return PhaseResult(
                phase=ValidationPhase.PARSING,
                success=False,
                duration_ms=duration,
                issues=[error_issue]
            )
    
    def _validate_logic_phase(self, config: GenConfig, 
                             traits_base_path: Optional[Union[str, Path]]) -> PhaseResult:
        """Validate configuration logic"""
        start_time = time.time()
        
        try:
            traits_path_str = str(traits_base_path) if traits_base_path else None
            validation_result = self.logic_validator.validate_config(config, traits_path_str)
            
            duration = (time.time() - start_time) * 1000
            
            return PhaseResult(
                phase=ValidationPhase.LOGIC,
                success=validation_result.is_valid,
                duration_ms=duration,
                issues=validation_result.issues,
                details={
                    "total_issues": len(validation_result.issues),
                    "error_count": len(validation_result.errors),
                    "warning_count": len(validation_result.warnings),
                    "info_count": len(validation_result.infos)
                }
            )
        
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            
            error_issue = ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="logic_validation_error",
                message=f"Logic validation failed: {str(e)}",
                path=self.current_config_path
            )
            
            return PhaseResult(
                phase=ValidationPhase.LOGIC,
                success=False,
                duration_ms=duration,
                issues=[error_issue]
            )
    
    def _validate_traits_phase(self, config: GenConfig, 
                              traits_base_path: Union[str, Path]) -> PhaseResult:
        """Validate trait files"""
        start_time = time.time()
        issues = []
        
        try:
            traits_path = Path(traits_base_path)
            validated_files = 0
            failed_files = 0
            
            # Expected image size from config
            expected_size = (
                config.generation.grid.cell_size.width,
                config.generation.grid.cell_size.height
            )
            
            # Validate each trait file
            for trait_key, trait in config.traits.items():
                trait_dir = traits_path / trait_key
                
                for variant in trait.variants:
                    trait_file_path = trait_dir / variant.filename
                    
                    try:
                        validation_result = validate_trait_file(str(trait_file_path), expected_size)
                        validated_files += 1
                        
                        if not validation_result.success:
                            failed_files += 1
                            for error in validation_result.errors:
                                issues.append(ValidationIssue(
                                    severity=ValidationSeverity.ERROR,
                                    category="trait_file_error",
                                    message=error,
                                    path=str(trait_file_path)
                                ))
                    
                    except Exception as e:
                        failed_files += 1
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            category="trait_file_validation_error",
                            message=f"Failed to validate trait file: {str(e)}",
                            path=str(trait_file_path)
                        ))
            
            duration = (time.time() - start_time) * 1000
            success = failed_files == 0
            
            return PhaseResult(
                phase=ValidationPhase.TRAITS,
                success=success,
                duration_ms=duration,
                issues=issues,
                details={
                    "validated_files": validated_files,
                    "failed_files": failed_files,
                    "expected_size": expected_size
                }
            )
        
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            
            error_issue = ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="traits_validation_error",
                message=f"Trait validation failed: {str(e)}",
                path=str(traits_base_path)
            )
            
            return PhaseResult(
                phase=ValidationPhase.TRAITS,
                success=False,
                duration_ms=duration,
                issues=[error_issue]
            )
    
    def _validate_integration_phase(self, config: GenConfig, 
                                   traits_base_path: Optional[Union[str, Path]]) -> PhaseResult:
        """Validate end-to-end integration"""
        start_time = time.time()
        issues = []
        
        try:
            # Integration checks
            integration_checks = {
                "grid_completeness": self._check_grid_completeness(config),
                "rarity_distribution": self._check_rarity_distribution(config),
                "collection_feasibility": self._check_collection_feasibility(config),
                "dimension_consistency": self._check_dimension_consistency(config)
            }
            
            # Add issues for failed checks
            for check_name, (success, message) in integration_checks.items():
                if not success:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="integration_check",
                        message=f"{check_name}: {message}",
                        path=self.current_config_path
                    ))
            
            duration = (time.time() - start_time) * 1000
            success = len([check for check, (result, _) in integration_checks.items() if not result]) == 0
            
            return PhaseResult(
                phase=ValidationPhase.INTEGRATION,
                success=success,
                duration_ms=duration,
                issues=issues,
                details={
                    "integration_checks": {name: result for name, (result, _) in integration_checks.items()}
                }
            )
        
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            
            error_issue = ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="integration_validation_error",
                message=f"Integration validation failed: {str(e)}",
                path=self.current_config_path
            )
            
            return PhaseResult(
                phase=ValidationPhase.INTEGRATION,
                success=False,
                duration_ms=duration,
                issues=[error_issue]
            )
    
    def _check_grid_completeness(self, config: GenConfig) -> Tuple[bool, str]:
        """Check if all grid positions are covered"""
        expected_positions = set(range(1, 10))
        actual_positions = set()
        
        for trait_key in config.traits.keys():
            try:
                position = int(trait_key.split('-')[1])
                actual_positions.add(position)
            except (IndexError, ValueError):
                continue
        
        missing = expected_positions - actual_positions
        if missing:
            return False, f"Missing grid positions: {sorted(missing)}"
        
        return True, "All grid positions covered"
    
    def _check_rarity_distribution(self, config: GenConfig) -> Tuple[bool, str]:
        """Check rarity distribution sanity"""
        total_combinations = 1
        for trait in config.traits.values():
            total_combinations *= len(trait.variants)
        
        if total_combinations < config.collection.size:
            return False, f"Not enough combinations ({total_combinations}) for collection size ({config.collection.size})"
        
        return True, f"Sufficient combinations ({total_combinations}) for collection"
    
    def _check_collection_feasibility(self, config: GenConfig) -> Tuple[bool, str]:
        """Check collection generation feasibility"""
        if not config.generation.allow_duplicates:
            total_combinations = 1
            for trait in config.traits.values():
                total_combinations *= len(trait.variants)
            
            if total_combinations < config.collection.size:
                return False, "Collection size exceeds unique combinations (duplicates disabled)"
        
        return True, "Collection generation is feasible"
    
    def _check_dimension_consistency(self, config: GenConfig) -> Tuple[bool, str]:
        """Check dimension consistency across config"""
        grid_width = config.generation.grid.columns * config.generation.grid.cell_size.width
        grid_height = config.generation.grid.rows * config.generation.grid.cell_size.height
        
        if (grid_width != config.generation.image_size.width or 
            grid_height != config.generation.image_size.height):
            return False, f"Grid dimensions ({grid_width}x{grid_height}) don't match image size ({config.generation.image_size.width}x{config.generation.image_size.height})"
        
        return True, "Dimensions are consistent"
    
    def _finalize_result(self, result: ComprehensiveValidationResult, start_time: float) -> ComprehensiveValidationResult:
        """Finalize validation result with timing"""
        result.total_duration_ms = (time.time() - start_time) * 1000
        return result


# Convenience functions

def validate_config_comprehensive(config_path: Union[str, Path], 
                                 traits_base_path: Optional[Union[str, Path]] = None,
                                 validation_mode: ValidationMode = ValidationMode.STANDARD) -> ComprehensiveValidationResult:
    """
    Convenience function for comprehensive configuration validation
    
    Args:
        config_path: Path to configuration file
        traits_base_path: Base path for trait files (optional)
        validation_mode: Validation execution mode
        
    Returns:
        ComprehensiveValidationResult: Complete validation result
    """
    suite = SchemaValidationSuite(validation_mode)
    return suite.validate_configuration(config_path, traits_base_path)


def get_comprehensive_validation_report(result: ComprehensiveValidationResult) -> str:
    """
    Generate human-readable comprehensive validation report
    
    Args:
        result: Comprehensive validation result
        
    Returns:
        str: Formatted validation report
    """
    lines = []
    lines.append("=" * 80)
    lines.append("GENCONFIG COMPREHENSIVE VALIDATION REPORT")
    lines.append("=" * 80)
    lines.append("")
    
    # Overall summary
    status = "✅ PASSED" if result.overall_success else "❌ FAILED"
    lines.append(f"Overall Status: {status}")
    lines.append(f"Validation Mode: {result.validation_mode.value.upper()}")
    lines.append(f"Configuration: {result.config_path}")
    lines.append(f"Total Duration: {result.total_duration_ms:.2f} ms")
    lines.append("")
    
    # Phase results
    lines.append("VALIDATION PHASES:")
    lines.append("-" * 40)
    for phase, phase_result in result.phase_results.items():
        status_icon = "✅" if phase_result.success else "❌"
        lines.append(f"{status_icon} {phase.value.upper()}: {phase_result.duration_ms:.2f} ms")
        
        if phase_result.issues:
            for issue in phase_result.issues[:3]:  # Show first 3 issues
                lines.append(f"    {issue.severity.value}: {issue.message}")
            if len(phase_result.issues) > 3:
                lines.append(f"    ... and {len(phase_result.issues) - 3} more issues")
    lines.append("")
    
    # Issue summary
    if result.all_issues:
        lines.append("ISSUE SUMMARY:")
        lines.append("-" * 40)
        lines.append(f"Total Issues: {len(result.all_issues)}")
        lines.append(f"Errors: {len(result.errors)}")
        lines.append(f"Warnings: {len(result.warnings)}")
        lines.append(f"Info: {len(result.infos)}")
        lines.append("")
        
        # Group issues by category
        issues_by_category = {}
        for issue in result.all_issues:
            if issue.category not in issues_by_category:
                issues_by_category[issue.category] = []
            issues_by_category[issue.category].append(issue)
        
        for category, issues in issues_by_category.items():
            lines.append(f"{category.upper()} ({len(issues)} issues):")
            for issue in issues[:5]:  # Show first 5 issues per category
                lines.append(f"  {issue.severity.value}: {issue.message}")
                if issue.path:
                    lines.append(f"    Path: {issue.path}")
            if len(issues) > 5:
                lines.append(f"  ... and {len(issues) - 5} more issues")
            lines.append("")
    
    # Recommendations
    if not result.overall_success:
        lines.append("RECOMMENDATIONS:")
        lines.append("-" * 40)
        
        if result.errors:
            lines.append("• Fix all ERROR-level issues before proceeding")
        
        if result.warnings and result.validation_mode == ValidationMode.STRICT:
            lines.append("• Address WARNING-level issues (strict mode enabled)")
        
        failed_phases = [phase.value for phase, result in result.phase_results.items() if not result.success]
        if failed_phases:
            lines.append(f"• Review failed validation phases: {', '.join(failed_phases)}")
        
        lines.append("• Check GenConfig specification for requirements")
        lines.append("")
    
    lines.append("=" * 80)
    
    return "\n".join(lines) 