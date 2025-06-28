"""
GenConfig Trait Metadata Manager

Manages trait-specific metadata and properties including:
- JSON sidecar files for individual trait images
- Metadata synchronization with configuration files
- Trait property validation and consistency
- Color codes, names, descriptions, and custom properties
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import re

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config.logic_validator import ValidationResult, ValidationIssue, ValidationSeverity
from config.config_parser import GenConfig, TraitVariant, TraitCategory, GridPosition
from utils.file_utils import (
    safe_read_json, safe_write_json, validate_file_exists, 
    ValidationError, FileOperationError
)


class MetadataError(Exception):
    """Exception raised for metadata management errors"""
    pass


@dataclass
class TraitMetadata:
    """
    Comprehensive metadata for a single trait
    
    Extends the basic TraitVariant with additional properties
    and file-specific information
    """
    # Core properties (matches TraitVariant)
    name: str
    filename: str
    rarity_weight: int
    color_code: Optional[str] = None
    description: Optional[str] = None
    
    # Extended metadata properties
    category: Optional[str] = None
    grid_position: Optional[Tuple[int, int]] = None
    tags: List[str] = field(default_factory=list)
    artist: Optional[str] = None
    creation_date: Optional[str] = None
    file_hash: Optional[str] = None
    
    # Custom properties (extensible)
    custom_properties: Dict[str, Any] = field(default_factory=dict)
    
    # File association
    image_path: Optional[str] = None
    metadata_path: Optional[str] = None
    
    def to_trait_variant(self) -> TraitVariant:
        """Convert to TraitVariant for config integration"""
        return TraitVariant(
            name=self.name,
            filename=self.filename,
            rarity_weight=self.rarity_weight,
            color_code=self.color_code,
            description=self.description
        )
    
    @classmethod
    def from_trait_variant(cls, variant: TraitVariant, 
                          category: Optional[str] = None,
                          grid_position: Optional[Tuple[int, int]] = None) -> 'TraitMetadata':
        """Create from TraitVariant"""
        return cls(
            name=variant.name,
            filename=variant.filename,
            rarity_weight=variant.rarity_weight,
            color_code=variant.color_code,
            description=variant.description,
            category=category,
            grid_position=grid_position
        )


@dataclass
class MetadataValidationStats:
    """Statistics from metadata validation"""
    total_files: int = 0
    valid_metadata: int = 0
    invalid_metadata: int = 0
    missing_metadata: int = 0
    config_sync_issues: int = 0
    property_conflicts: int = 0


class MetadataSyncMode(Enum):
    """Synchronization mode for metadata operations"""
    CONFIG_TO_FILES = "config_to_files"  # Config.json is source of truth
    FILES_TO_CONFIG = "files_to_config"  # JSON files are source of truth  
    MERGE_FAVOR_CONFIG = "merge_favor_config"  # Merge with config priority
    MERGE_FAVOR_FILES = "merge_favor_files"  # Merge with files priority


class TraitMetadataManager:
    """
    Manager for trait-specific metadata and properties
    
    Handles:
    - Loading and saving JSON metadata files for individual traits
    - Synchronizing metadata between config.json and JSON sidecar files
    - Validating metadata consistency and completeness
    - Managing trait properties like color codes, names, descriptions
    - Supporting custom metadata properties and extensibility
    """
    
    # Pattern matching for trait files and metadata
    TRAIT_FILE_PATTERN = re.compile(r'^trait-([a-zA-Z0-9\-_]+)-(\d{3})\.png$')
    METADATA_FILE_PATTERN = re.compile(r'^trait-([a-zA-Z0-9\-_]+)-(\d{3})\.json$')
    
    def __init__(self, collection_root: Union[str, Path]):
        """
        Initialize trait metadata manager
        
        Args:
            collection_root: Root path of the GenConfig collection
        """
        self.collection_root = Path(collection_root)
        self.traits_root = self.collection_root / "traits"
        self.config_path = self.collection_root / "config.json"
        
    def load_trait_metadata(self, metadata_path: Union[str, Path]) -> TraitMetadata:
        """
        Load metadata from a JSON file
        
        Args:
            metadata_path: Path to the metadata JSON file
            
        Returns:
            TraitMetadata: Loaded metadata object
            
        Raises:
            MetadataError: If metadata cannot be loaded or is invalid
        """
        try:
            metadata_dict = safe_read_json(str(metadata_path))
            
            # Convert to TraitMetadata
            metadata = TraitMetadata(
                name=metadata_dict.get("name", ""),
                filename=metadata_dict.get("filename", ""),
                rarity_weight=metadata_dict.get("rarity_weight", 100),
                color_code=metadata_dict.get("color_code"),
                description=metadata_dict.get("description"),
                category=metadata_dict.get("category"),
                grid_position=tuple(metadata_dict["grid_position"]) if metadata_dict.get("grid_position") else None,
                tags=metadata_dict.get("tags", []),
                artist=metadata_dict.get("artist"),
                creation_date=metadata_dict.get("creation_date"),
                file_hash=metadata_dict.get("file_hash"),
                custom_properties=metadata_dict.get("custom_properties", {}),
                image_path=metadata_dict.get("image_path"),
                metadata_path=str(metadata_path)
            )
            
            return metadata
            
        except (ValidationError, FileOperationError, json.JSONDecodeError, KeyError) as e:
            raise MetadataError(f"Failed to load metadata from {metadata_path}: {str(e)}")
    
    def save_trait_metadata(self, metadata: TraitMetadata, 
                           metadata_path: Optional[Union[str, Path]] = None) -> bool:
        """
        Save metadata to a JSON file
        
        Args:
            metadata: TraitMetadata object to save
            metadata_path: Optional path to save to (uses metadata.metadata_path if not provided)
            
        Returns:
            bool: Success status
            
        Raises:
            MetadataError: If metadata cannot be saved
        """
        try:
            save_path = metadata_path or metadata.metadata_path
            if not save_path:
                raise MetadataError("No metadata path specified")
            
            # Convert to dictionary for serialization
            metadata_dict = asdict(metadata)
            
            # Remove None values and internal fields
            metadata_dict = {k: v for k, v in metadata_dict.items() 
                           if v is not None and k not in ["metadata_path"]}
            
            # Convert grid_position tuple to list for JSON serialization
            if metadata_dict.get("grid_position"):
                metadata_dict["grid_position"] = list(metadata_dict["grid_position"])
            
            # Add GenConfig metadata
            metadata_dict["_genconfig_version"] = "1.0"
            metadata_dict["_metadata_type"] = "trait"
            
            safe_write_json(str(save_path), metadata_dict)
            return True
            
        except (ValidationError, FileOperationError) as e:
            raise MetadataError(f"Failed to save metadata to {save_path}: {str(e)}")
    
    def create_metadata_from_config(self, config: GenConfig) -> Dict[str, List[TraitMetadata]]:
        """
        Create metadata objects from configuration
        
        Args:
            config: GenConfig configuration object
            
        Returns:
            Dict mapping trait category names to lists of TraitMetadata
        """
        metadata_by_category = {}
        
        for trait_key, trait_category in config.traits.items():
            category_metadata = []
            
            for variant in trait_category.variants:
                grid_pos = (trait_category.grid_position.row, trait_category.grid_position.column)
                
                metadata = TraitMetadata.from_trait_variant(
                    variant,
                    category=trait_category.name,
                    grid_position=grid_pos
                )
                
                # Set paths based on trait directory structure
                trait_dir = self.traits_root / trait_key
                metadata.image_path = str(trait_dir / variant.filename)
                metadata.metadata_path = str(trait_dir / f"{variant.filename.replace('.png', '.json')}")
                
                category_metadata.append(metadata)
            
            metadata_by_category[trait_key] = category_metadata
        
        return metadata_by_category
    
    def scan_metadata_files(self) -> Dict[str, List[TraitMetadata]]:
        """
        Scan traits directory for existing metadata files
        
        Returns:
            Dict mapping trait category directories to lists of found metadata
        """
        metadata_by_category = {}
        
        if not self.traits_root.exists():
            return metadata_by_category
        
        # Scan each trait directory
        for trait_dir in self.traits_root.iterdir():
            if not trait_dir.is_dir():
                continue
            
            category_metadata = []
            
            # Look for JSON metadata files
            for file_path in trait_dir.glob("*.json"):
                if self.METADATA_FILE_PATTERN.match(file_path.name):
                    try:
                        metadata = self.load_trait_metadata(file_path)
                        category_metadata.append(metadata)
                    except MetadataError:
                        # Skip invalid metadata files
                        continue
            
            if category_metadata:
                metadata_by_category[trait_dir.name] = category_metadata
        
        return metadata_by_category
    
    def validate_metadata_consistency(self, config: Optional[GenConfig] = None) -> ValidationResult:
        """
        Validate metadata consistency across config and files
        
        Args:
            config: Optional GenConfig to validate against (loads from file if not provided)
            
        Returns:
            ValidationResult: Comprehensive validation results
        """
        issues = []
        
        try:
            # Load config if not provided
            if config is None:
                if not validate_file_exists(str(self.config_path)):
                    issues.append(ValidationIssue(
                        ValidationSeverity.ERROR,
                        "config_missing",
                        f"Configuration file not found: {self.config_path}",
                        str(self.config_path),
                        "Create or restore the configuration file"
                    ))
                    return ValidationResult(is_valid=False, issues=issues)
                
                from config.config_parser import ConfigurationParser
                parser = ConfigurationParser(validate_schema=False)  # Skip schema validation for tests
                config = parser.parse_config_file(str(self.config_path))
            
            # Get metadata from config and files
            config_metadata = self.create_metadata_from_config(config)
            file_metadata = self.scan_metadata_files()
            
            # Track validation stats
            stats = MetadataValidationStats()
            
            # Validate each trait category
            for trait_key, trait_category in config.traits.items():
                config_variants = {v.filename: v for v in trait_category.variants}
                file_variants = {m.filename: m for m in file_metadata.get(trait_key, [])}
                
                stats.total_files += len(config_variants)
                
                # Check for missing metadata files
                for filename, variant in config_variants.items():
                    if filename not in file_variants:
                        stats.missing_metadata += 1
                        issues.append(ValidationIssue(
                            ValidationSeverity.INFO,
                            "missing_metadata",
                            f"No metadata file found for trait '{variant.name}' ({filename})",
                            f"traits/{trait_key}/{filename.replace('.png', '.json')}",
                            "Create metadata file or use sync function"
                        ))
                
                # Check for orphaned metadata files
                for filename, metadata in file_variants.items():
                    if filename not in config_variants:
                        issues.append(ValidationIssue(
                            ValidationSeverity.WARNING,
                            "orphaned_metadata",
                            f"Metadata file exists for unknown trait: {filename}",
                            metadata.metadata_path or f"traits/{trait_key}/{filename.replace('.png', '.json')}",
                            "Remove orphaned metadata or update configuration"
                        ))
                
                # Check for property conflicts
                for filename in set(config_variants.keys()) & set(file_variants.keys()):
                    config_variant = config_variants[filename]
                    file_metadata_obj = file_variants[filename]
                    
                    stats.valid_metadata += 1
                    
                    # Compare core properties
                    conflicts = []
                    if config_variant.name != file_metadata_obj.name:
                        conflicts.append(f"name: config='{config_variant.name}' vs file='{file_metadata_obj.name}'")
                    if config_variant.rarity_weight != file_metadata_obj.rarity_weight:
                        conflicts.append(f"rarity_weight: config={config_variant.rarity_weight} vs file={file_metadata_obj.rarity_weight}")
                    if config_variant.color_code != file_metadata_obj.color_code:
                        conflicts.append(f"color_code: config='{config_variant.color_code}' vs file='{file_metadata_obj.color_code}'")
                    if config_variant.description != file_metadata_obj.description:
                        conflicts.append(f"description: config='{config_variant.description}' vs file='{file_metadata_obj.description}'")
                    
                    if conflicts:
                        stats.property_conflicts += 1
                        stats.config_sync_issues += 1
                        issues.append(ValidationIssue(
                            ValidationSeverity.WARNING,
                            "metadata_conflict",
                            f"Property conflicts for trait '{filename}': {'; '.join(conflicts)}",
                            file_metadata_obj.metadata_path or f"traits/{trait_key}/{filename.replace('.png', '.json')}",
                            "Use sync_metadata() to resolve conflicts"
                        ))
            
            # Add validation summary
            if stats.total_files > 0:
                coverage = (stats.valid_metadata / stats.total_files) * 100
                issues.append(ValidationIssue(
                    ValidationSeverity.INFO,
                    "validation_summary",
                    f"Metadata coverage: {coverage:.1f}% ({stats.valid_metadata}/{stats.total_files} traits)",
                    str(self.traits_root),
                    None
                ))
                
                if stats.config_sync_issues > 0:
                    issues.append(ValidationIssue(
                        ValidationSeverity.WARNING,
                        "sync_needed",
                        f"Found {stats.config_sync_issues} sync issues that need resolution",
                        str(self.traits_root),
                        "Use sync_metadata() to resolve conflicts"
                    ))
            
            error_count = len([issue for issue in issues if issue.severity == ValidationSeverity.ERROR])
            return ValidationResult(is_valid=error_count == 0, issues=issues)
            
        except Exception as e:
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                "validation_error",
                f"Unexpected error during metadata validation: {str(e)}",
                str(self.traits_root),
                "Check system logs for detailed error information"
            ))
            return ValidationResult(is_valid=False, issues=issues)
    
    def sync_metadata(self, mode: MetadataSyncMode = MetadataSyncMode.MERGE_FAVOR_CONFIG,
                     config: Optional[GenConfig] = None) -> ValidationResult:
        """
        Synchronize metadata between config and JSON files
        
        Args:
            mode: Synchronization mode (CONFIG_TO_FILES, FILES_TO_CONFIG, etc.)
            config: Optional GenConfig to sync (loads from file if not provided)
            
        Returns:
            ValidationResult: Results of synchronization operation
        """
        issues = []
        
        try:
            # Load config if not provided
            if config is None:
                from config.config_parser import ConfigurationParser
                parser = ConfigurationParser(validate_schema=False)  # Skip schema validation for tests
                config = parser.parse_config_file(str(self.config_path))
            
            # Get current state
            config_metadata = self.create_metadata_from_config(config)
            file_metadata = self.scan_metadata_files()
            
            sync_count = 0
            
            if mode == MetadataSyncMode.CONFIG_TO_FILES:
                # Create/update JSON files from config
                for trait_key, metadata_list in config_metadata.items():
                    trait_dir = self.traits_root / trait_key
                    if not trait_dir.exists():
                        continue
                    
                    for metadata in metadata_list:
                        if metadata.metadata_path and self.save_trait_metadata(metadata):
                            sync_count += 1
                            issues.append(ValidationIssue(
                                ValidationSeverity.INFO,
                                "metadata_created",
                                f"Created/updated metadata for '{metadata.name}'",
                                metadata.metadata_path,
                                None
                            ))
            
            elif mode == MetadataSyncMode.FILES_TO_CONFIG:
                # Update config from JSON files (this would require config modification)
                issues.append(ValidationIssue(
                    ValidationSeverity.WARNING,
                    "sync_limitation",
                    "FILES_TO_CONFIG mode requires manual config.json editing",
                    str(self.config_path),
                    "Use configuration management tools to update config.json"
                ))
            
            elif mode in [MetadataSyncMode.MERGE_FAVOR_CONFIG, MetadataSyncMode.MERGE_FAVOR_FILES]:
                # Merge metadata with priority rules
                for trait_key in set(config_metadata.keys()) | set(file_metadata.keys()):
                    config_variants = {m.filename: m for m in config_metadata.get(trait_key, [])}
                    file_variants = {m.filename: m for m in file_metadata.get(trait_key, [])}
                    
                    # Process each file
                    for filename in set(config_variants.keys()) | set(file_variants.keys()):
                        config_meta = config_variants.get(filename)
                        file_meta = file_variants.get(filename)
                        
                        if config_meta and file_meta:
                            # Merge existing metadata
                            if mode == MetadataSyncMode.MERGE_FAVOR_CONFIG:
                                merged = config_meta
                                # Keep extended properties from file
                                merged.tags = file_meta.tags
                                merged.artist = file_meta.artist
                                merged.creation_date = file_meta.creation_date
                                merged.file_hash = file_meta.file_hash
                                merged.custom_properties = file_meta.custom_properties
                            else:  # MERGE_FAVOR_FILES
                                merged = file_meta
                                # Update core properties from config if different
                                if config_meta.name != file_meta.name:
                                    merged.name = config_meta.name
                                if config_meta.rarity_weight != file_meta.rarity_weight:
                                    merged.rarity_weight = config_meta.rarity_weight
                            
                            if self.save_trait_metadata(merged):
                                sync_count += 1
                        
                        elif config_meta and not file_meta:
                            # Create from config
                            if self.save_trait_metadata(config_meta):
                                sync_count += 1
                        
                        # Note: Orphaned file metadata is left as-is
            
            issues.append(ValidationIssue(
                ValidationSeverity.INFO,
                "sync_complete",
                f"Synchronized {sync_count} metadata files using {mode.value} mode",
                str(self.traits_root),
                None
            ))
            
            return ValidationResult(is_valid=True, issues=issues)
            
        except Exception as e:
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                "sync_error",
                f"Error during metadata sync: {str(e)}",
                str(self.traits_root),
                "Check system logs for detailed error information"
            ))
            return ValidationResult(is_valid=False, issues=issues)
    
    def create_metadata_template(self, trait_name: str, filename: str,
                                category: str, grid_position: Tuple[int, int],
                                **kwargs) -> TraitMetadata:
        """
        Create a template metadata object with common properties
        
        Args:
            trait_name: Name of the trait
            filename: Image filename
            category: Trait category
            grid_position: Grid position as (row, col)
            **kwargs: Additional properties
            
        Returns:
            TraitMetadata: Template metadata object
        """
        return TraitMetadata(
            name=trait_name,
            filename=filename,
            rarity_weight=kwargs.get('rarity_weight', 100),
            color_code=kwargs.get('color_code'),
            description=kwargs.get('description'),
            category=category,
            grid_position=grid_position,
            tags=kwargs.get('tags', []),
            artist=kwargs.get('artist'),
            creation_date=kwargs.get('creation_date'),
            custom_properties=kwargs.get('custom_properties', {})
        )
    
    def get_metadata_summary(self) -> str:
        """
        Get a human-readable summary of metadata status
        
        Returns:
            str: Formatted summary
        """
        try:
            validation_result = self.validate_metadata_consistency()
            file_metadata = self.scan_metadata_files()
            
            # Try to get collection name from config
            collection_name = "Unknown Collection"
            try:
                if validate_file_exists(str(self.config_path)):
                    from config.config_parser import ConfigurationParser
                    parser = ConfigurationParser(validate_schema=False)
                    config = parser.parse_config_file(str(self.config_path))
                    collection_name = config.collection.name
            except:
                pass  # Keep default name if config cannot be loaded
            
            total_categories = len([d for d in self.traits_root.iterdir() if d.is_dir()]) if self.traits_root.exists() else 0
            total_metadata_files = sum(len(metadata_list) for metadata_list in file_metadata.values())
            
            summary_lines = [
                "# Trait Metadata Summary",
                f"**Collection**: {collection_name}",
                f"**Collection Root**: {self.collection_root}",
                f"**Trait Categories**: {total_categories}",
                f"**Metadata Files**: {total_metadata_files}",
                "",
                "## Validation Status",
            ]
            
            if validation_result.is_valid:
                summary_lines.append("✅ **Status**: All validations passed")
            else:
                error_count = len([issue for issue in validation_result.issues if issue.severity == ValidationSeverity.ERROR])
                warning_count = len([issue for issue in validation_result.issues if issue.severity == ValidationSeverity.WARNING])
                summary_lines.append(f"⚠️ **Status**: {error_count} errors, {warning_count} warnings")
            
            summary_lines.extend([
                "",
                "## Metadata by Category",
            ])
            
            for category, metadata_list in file_metadata.items():
                summary_lines.append(f"- **{category}**: {len(metadata_list)} metadata files")
            
            if validation_result.issues:
                summary_lines.extend([
                    "",
                    "## Recent Issues",
                ])
                for issue in validation_result.issues[:5]:  # Show first 5 issues
                    icon = "🔴" if issue.severity == ValidationSeverity.ERROR else "🟡" if issue.severity == ValidationSeverity.WARNING else "ℹ️"
                    summary_lines.append(f"{icon} {issue.message}")
            
            return "\n".join(summary_lines)
            
        except Exception as e:
            return f"Error generating metadata summary: {str(e)}"


# Convenience functions matching the module pattern

def load_trait_metadata(metadata_path: Union[str, Path]) -> TraitMetadata:
    """
    Load trait metadata from a JSON file
    
    Args:
        metadata_path: Path to the metadata JSON file
        
    Returns:
        TraitMetadata: Loaded metadata object
    """
    manager = TraitMetadataManager(Path(metadata_path).parent.parent.parent)
    return manager.load_trait_metadata(metadata_path)


def validate_metadata_consistency(collection_root: Union[str, Path]) -> ValidationResult:
    """
    Validate metadata consistency for a collection
    
    Args:
        collection_root: Root path of the GenConfig collection
        
    Returns:
        ValidationResult: Validation results
    """
    manager = TraitMetadataManager(collection_root)
    return manager.validate_metadata_consistency()


def sync_metadata(collection_root: Union[str, Path], 
                 mode: MetadataSyncMode = MetadataSyncMode.MERGE_FAVOR_CONFIG) -> ValidationResult:
    """
    Synchronize metadata between config and JSON files
    
    Args:
        collection_root: Root path of the GenConfig collection
        mode: Synchronization mode
        
    Returns:
        ValidationResult: Sync operation results
    """
    manager = TraitMetadataManager(collection_root)
    return manager.sync_metadata(mode)


def get_metadata_report(collection_root: Union[str, Path]) -> str:
    """
    Get a comprehensive metadata report for a collection
    
    Args:
        collection_root: Root path of the GenConfig collection
        
    Returns:
        str: Human-readable metadata report
    """
    manager = TraitMetadataManager(collection_root)
    return manager.get_metadata_summary() 