"""
GenConfig Trait Directory Manager

This module handles the management and organization of trait directories within
a GenConfig project. It provides functionality for creating, validating, and
maintaining trait directory structures according to the GenConfig specification.
"""

import os
import sys
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Union
from dataclasses import dataclass
from enum import Enum

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config.logic_validator import ValidationResult, ValidationIssue, ValidationSeverity
from utils.file_utils import validate_directory_exists, ensure_directory_exists, list_files_by_pattern


class TraitDirectoryError(Exception):
    """Custom exception for trait directory management errors"""
    pass


@dataclass
class TraitFileEntry:
    """Information about a trait file in a directory"""
    file_path: str
    file_name: str
    trait_name: str
    trait_id: str
    file_size: int
    is_valid_name: bool
    has_metadata: bool = False
    metadata_path: Optional[str] = None


@dataclass
class TraitDirectoryInfo:
    """Information about a trait directory"""
    directory_path: str
    directory_name: str
    position_number: int
    category_name: str
    grid_row: int
    grid_col: int
    has_readme: bool
    readme_path: Optional[str]
    trait_files: List[TraitFileEntry]
    total_files: int
    valid_files: int
    invalid_files: int


class TraitDirectoryManager:
    """
    Manager for trait directory structure and organization
    
    Handles:
    - Creating and maintaining trait directories
    - Organizing trait files within directories
    - Validating directory structure and contents
    - Managing README files for trait categories
    - Scanning and categorizing trait files
    """
    
    # Constants from GenConfig specification
    TRAIT_DIR_PATTERN = re.compile(r'^position-(\d)-([a-zA-Z]+)$')
    TRAIT_FILE_PATTERN = re.compile(r'^trait-([a-zA-Z0-9\-_]+)-(\d{3})\.png$')
    METADATA_FILE_PATTERN = re.compile(r'^trait-([a-zA-Z0-9\-_]+)-(\d{3})\.json$')
    
    TRAIT_CATEGORIES = [
        ("position-1-background", "Background", 0, 0),
        ("position-2-base", "Base", 0, 1),
        ("position-3-accent", "Accent", 0, 2),
        ("position-4-pattern", "Pattern", 1, 0),
        ("position-5-center", "Center", 1, 1),
        ("position-6-decoration", "Decoration", 1, 2),
        ("position-7-border", "Border", 2, 0),
        ("position-8-highlight", "Highlight", 2, 1),
        ("position-9-overlay", "Overlay", 2, 2)
    ]
    
    def __init__(self, collection_root: Union[str, Path]):
        """
        Initialize trait directory manager
        
        Args:
            collection_root: Root path of the GenConfig collection
        """
        self.collection_root = Path(collection_root)
        self.traits_root = self.collection_root / "traits"
        
    def create_trait_directories(self, force_recreate: bool = False) -> ValidationResult:
        """
        Create all required trait directories with README files
        
        Args:
            force_recreate: Whether to recreate existing directories
            
        Returns:
            ValidationResult: Result of directory creation
        """
        issues = []
        
        try:
            # Ensure traits root directory exists
            if not ensure_directory_exists(str(self.traits_root)):
                issues.append(ValidationIssue(
                    ValidationSeverity.ERROR,
                    "directory_creation",
                    f"Failed to create traits root directory: {self.traits_root}",
                    str(self.traits_root),
                    "Check directory permissions and disk space"
                ))
                return ValidationResult(is_valid=False, issues=issues)
            
            # Create each trait directory
            for dir_name, category_name, grid_row, grid_col in self.TRAIT_CATEGORIES:
                trait_dir = self.traits_root / dir_name
                
                # Check if directory exists
                if trait_dir.exists() and not force_recreate:
                    issues.append(ValidationIssue(
                        ValidationSeverity.INFO,
                        "directory_exists",
                        f"Trait directory already exists: {dir_name}",
                        str(trait_dir),
                        None
                    ))
                    continue
                
                # Create directory
                if not ensure_directory_exists(str(trait_dir)):
                    issues.append(ValidationIssue(
                        ValidationSeverity.ERROR,
                        "directory_creation",
                        f"Failed to create trait directory: {dir_name}",
                        str(trait_dir),
                        "Check directory permissions"
                    ))
                    continue
                
                # Create README file
                if not self._create_trait_readme(trait_dir, category_name, 
                                               int(dir_name.split('-')[1]), grid_row, grid_col):
                    issues.append(ValidationIssue(
                        ValidationSeverity.WARNING,
                        "readme_creation",
                        f"Failed to create README for {dir_name}",
                        str(trait_dir / "README.md"),
                        "Create README manually for documentation"
                    ))
                
                issues.append(ValidationIssue(
                    ValidationSeverity.INFO,
                    "directory_created",
                    f"Successfully created trait directory: {dir_name}",
                    str(trait_dir),
                    None
                ))
            
            error_count = len([issue for issue in issues if issue.severity == ValidationSeverity.ERROR])
            return ValidationResult(is_valid=error_count == 0, issues=issues)
            
        except Exception as e:
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                "unexpected_error",
                f"Unexpected error creating trait directories: {str(e)}",
                str(self.traits_root),
                "Check system logs for detailed error information"
            ))
            return ValidationResult(is_valid=False, issues=issues)
    
    def validate_trait_directories(self) -> ValidationResult:
        """
        Validate trait directory structure and organization
        
        Returns:
            ValidationResult: Comprehensive validation result
        """
        issues = []
        
        # Check if traits root exists
        if not validate_directory_exists(str(self.traits_root)):
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                "missing_traits_root",
                f"Traits root directory does not exist: {self.traits_root}",
                str(self.traits_root),
                "Run create_trait_directories() to initialize structure"
            ))
            return ValidationResult(is_valid=False, issues=issues)
        
        # Track found directories
        expected_dirs = {dir_name for dir_name, _, _, _ in self.TRAIT_CATEGORIES}
        found_dirs = set()
        
        # Scan traits directory
        for item in self.traits_root.iterdir():
            if item.is_dir():
                dir_name = item.name
                found_dirs.add(dir_name)
                
                # Validate directory name format
                if not self.TRAIT_DIR_PATTERN.match(dir_name):
                    issues.append(ValidationIssue(
                        ValidationSeverity.WARNING,
                        "invalid_directory_name",
                        f"Directory name doesn't match expected pattern: {dir_name}",
                        str(item),
                        "Use format: position-X-category (e.g., position-1-background)"
                    ))
                    continue
                
                # Check if directory is expected
                if dir_name not in expected_dirs:
                    issues.append(ValidationIssue(
                        ValidationSeverity.WARNING,
                        "unexpected_directory",
                        f"Unexpected trait directory found: {dir_name}",
                        str(item),
                        "Remove if not needed or verify it follows naming convention"
                    ))
                    continue
                
                # Validate directory contents
                dir_validation = self._validate_trait_directory_contents(item)
                issues.extend(dir_validation.issues)
        
        # Check for missing directories
        missing_dirs = expected_dirs - found_dirs
        for missing_dir in missing_dirs:
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                "missing_directory",
                f"Required trait directory missing: {missing_dir}",
                str(self.traits_root / missing_dir),
                "Run create_trait_directories() to create missing directories"
            ))
        
        error_count = len([issue for issue in issues if issue.severity == ValidationSeverity.ERROR])
        return ValidationResult(is_valid=error_count == 0, issues=issues)
    
    def scan_trait_directories(self) -> Dict[str, TraitDirectoryInfo]:
        """
        Scan all trait directories and return detailed information
        
        Returns:
            Dict mapping directory names to TraitDirectoryInfo objects
        """
        directory_info = {}
        
        if not validate_directory_exists(str(self.traits_root)):
            return directory_info
        
        for dir_name, category_name, grid_row, grid_col in self.TRAIT_CATEGORIES:
            trait_dir = self.traits_root / dir_name
            
            if not trait_dir.exists():
                continue
            
            position_number = int(dir_name.split('-')[1])
            
            # Check for README
            readme_path = trait_dir / "README.md"
            has_readme = readme_path.exists()
            
            # Scan trait files
            trait_files = self._scan_trait_files(trait_dir)
            
            # Count valid/invalid files
            valid_files = len([f for f in trait_files if f.is_valid_name])
            invalid_files = len(trait_files) - valid_files
            
            directory_info[dir_name] = TraitDirectoryInfo(
                directory_path=str(trait_dir),
                directory_name=dir_name,
                position_number=position_number,
                category_name=category_name,
                grid_row=grid_row,
                grid_col=grid_col,
                has_readme=has_readme,
                readme_path=str(readme_path) if has_readme else None,
                trait_files=trait_files,
                total_files=len(trait_files),
                valid_files=valid_files,
                invalid_files=invalid_files
            )
        
        return directory_info
    
    def organize_trait_files(self, source_directory: Union[str, Path], 
                           auto_categorize: bool = True, dry_run: bool = False) -> ValidationResult:
        """
        Organize trait files from a source directory into proper trait directories
        
        Args:
            source_directory: Directory containing trait files to organize
            auto_categorize: Whether to automatically categorize files by naming
            dry_run: If True, only report what would be done without actual changes
            
        Returns:
            ValidationResult: Result of organization operation
        """
        issues = []
        source_path = Path(source_directory)
        
        if not validate_directory_exists(str(source_path)):
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR,
                "source_not_found",
                f"Source directory does not exist: {source_directory}",
                str(source_path),
                "Verify the source directory path"
            ))
            return ValidationResult(is_valid=False, issues=issues)
        
        # Find trait files in source directory
        trait_files = list_files_by_pattern(str(source_path), "*.png")
        organized_count = 0
        
        for file_path in trait_files:
            file_name = Path(file_path).name
            
            # Check if file matches trait naming pattern
            match = self.TRAIT_FILE_PATTERN.match(file_name)
            if not match:
                issues.append(ValidationIssue(
                    ValidationSeverity.WARNING,
                    "invalid_filename",
                    f"File doesn't match trait naming pattern: {file_name}",
                    file_path,
                    "Rename to format: trait-{name}-{id}.png"
                ))
                continue
            
            if auto_categorize:
                # Try to determine category from filename
                trait_name = match.group(1)
                target_dir = self._guess_trait_category(trait_name)
                
                if target_dir:
                    target_path = self.traits_root / target_dir / file_name
                    
                    if not dry_run:
                        try:
                            # Ensure target directory exists
                            ensure_directory_exists(str(target_path.parent))
                            
                            # Move or copy file
                            shutil.move(file_path, str(target_path))
                            organized_count += 1
                            
                            issues.append(ValidationIssue(
                                ValidationSeverity.INFO,
                                "file_organized",
                                f"Moved {file_name} to {target_dir}",
                                str(target_path),
                                None
                            ))
                        except Exception as e:
                            issues.append(ValidationIssue(
                                ValidationSeverity.ERROR,
                                "file_move_failed",
                                f"Failed to move {file_name}: {str(e)}",
                                file_path,
                                "Check file permissions and disk space"
                            ))
                    else:
                        issues.append(ValidationIssue(
                            ValidationSeverity.INFO,
                            "file_would_move",
                            f"Would move {file_name} to {target_dir}",
                            file_path,
                            None
                        ))
                        organized_count += 1
                else:
                    issues.append(ValidationIssue(
                        ValidationSeverity.WARNING,
                        "category_unknown",
                        f"Could not determine category for: {file_name}",
                        file_path,
                        "Manually move to appropriate trait directory"
                    ))
        
        if not dry_run:
            issues.append(ValidationIssue(
                ValidationSeverity.INFO,
                "organization_complete",
                f"Successfully organized {organized_count} trait files",
                str(source_path),
                None
            ))
        else:
            issues.append(ValidationIssue(
                ValidationSeverity.INFO,
                "dry_run_complete",
                f"Would organize {organized_count} trait files",
                str(source_path),
                "Run without dry_run=True to execute changes"
            ))
        
        error_count = len([issue for issue in issues if issue.severity == ValidationSeverity.ERROR])
        return ValidationResult(is_valid=error_count == 0, issues=issues)
    
    def update_readme_files(self, force_update: bool = False) -> ValidationResult:
        """
        Update README files in all trait directories
        
        Args:
            force_update: Whether to update existing README files
            
        Returns:
            ValidationResult: Result of README update operation
        """
        issues = []
        updated_count = 0
        
        for dir_name, category_name, grid_row, grid_col in self.TRAIT_CATEGORIES:
            trait_dir = self.traits_root / dir_name
            
            if not trait_dir.exists():
                issues.append(ValidationIssue(
                    ValidationSeverity.WARNING,
                    "directory_missing",
                    f"Trait directory does not exist: {dir_name}",
                    str(trait_dir),
                    "Run create_trait_directories() first"
                ))
                continue
            
            readme_path = trait_dir / "README.md"
            
            # Check if README exists and whether to update
            if readme_path.exists() and not force_update:
                issues.append(ValidationIssue(
                    ValidationSeverity.INFO,
                    "readme_exists",
                    f"README already exists for {dir_name}",
                    str(readme_path),
                    "Use force_update=True to overwrite"
                ))
                continue
            
            position_number = int(dir_name.split('-')[1])
            
            if self._create_trait_readme(trait_dir, category_name, position_number, grid_row, grid_col):
                updated_count += 1
                issues.append(ValidationIssue(
                    ValidationSeverity.INFO,
                    "readme_updated",
                    f"Updated README for {dir_name}",
                    str(readme_path),
                    None
                ))
            else:
                issues.append(ValidationIssue(
                    ValidationSeverity.ERROR,
                    "readme_update_failed",
                    f"Failed to update README for {dir_name}",
                    str(readme_path),
                    "Check file permissions"
                ))
        
        issues.append(ValidationIssue(
            ValidationSeverity.INFO,
            "update_complete",
            f"Successfully updated {updated_count} README files",
            str(self.traits_root),
            None
        ))
        
        error_count = len([issue for issue in issues if issue.severity == ValidationSeverity.ERROR])
        return ValidationResult(is_valid=error_count == 0, issues=issues)
    
    def get_trait_directory_summary(self) -> str:
        """
        Generate a summary report of trait directory structure
        
        Returns:
            String containing formatted summary
        """
        directory_info = self.scan_trait_directories()
        
        if not directory_info:
            return "No trait directories found."
        
        summary_lines = [
            "=== Trait Directory Summary ===",
            f"Collection Root: {self.collection_root}",
            f"Traits Directory: {self.traits_root}",
            ""
        ]
        
        total_files = 0
        total_valid = 0
        total_invalid = 0
        
        for dir_name in sorted(directory_info.keys()):
            info = directory_info[dir_name]
            
            total_files += info.total_files
            total_valid += info.valid_files
            total_invalid += info.invalid_files
            
            summary_lines.extend([
                f"📁 {info.directory_name}",
                f"   Category: {info.category_name}",
                f"   Position: {info.position_number} (Row {info.grid_row}, Col {info.grid_col})",
                f"   Files: {info.total_files} total, {info.valid_files} valid, {info.invalid_files} invalid",
                f"   README: {'✅' if info.has_readme else '❌'}",
                ""
            ])
        
        summary_lines.extend([
            "=== Overall Statistics ===",
            f"Total Directories: {len(directory_info)}",
            f"Total Trait Files: {total_files}",
            f"Valid Files: {total_valid}",
            f"Invalid Files: {total_invalid}",
            f"Completion: {(total_valid / max(total_files, 1)) * 100:.1f}% valid files"
        ])
        
        return "\n".join(summary_lines)
    
    def _validate_trait_directory_contents(self, trait_dir: Path) -> ValidationResult:
        """Validate the contents of a single trait directory"""
        issues = []
        
        # Check for README
        readme_path = trait_dir / "README.md"
        if not readme_path.exists():
            issues.append(ValidationIssue(
                ValidationSeverity.WARNING,
                "missing_readme",
                f"README.md missing in {trait_dir.name}",
                str(readme_path),
                "Create README for documentation"
            ))
        
        # Scan trait files
        trait_files = self._scan_trait_files(trait_dir)
        
        if not trait_files:
            issues.append(ValidationIssue(
                ValidationSeverity.INFO,
                "no_trait_files",
                f"No trait files found in {trait_dir.name}",
                str(trait_dir),
                "Add trait PNG files to this directory"
            ))
        
        # Check for invalid filenames
        invalid_files = [f for f in trait_files if not f.is_valid_name]
        if invalid_files:
            for invalid_file in invalid_files:
                issues.append(ValidationIssue(
                    ValidationSeverity.WARNING,
                    "invalid_filename",
                    f"Invalid trait filename: {invalid_file.file_name}",
                    invalid_file.file_path,
                    "Rename to format: trait-{name}-{id}.png"
                ))
        
        return ValidationResult(is_valid=True, issues=issues)
    
    def _scan_trait_files(self, trait_dir: Path) -> List[TraitFileEntry]:
        """Scan trait files in a directory and return file information"""
        trait_files = []
        
        # Look for PNG files
        png_files = list_files_by_pattern(str(trait_dir), "*.png")
        
        for file_path in png_files:
            file_name = Path(file_path).name
            file_size = 0
            
            try:
                file_size = Path(file_path).stat().st_size
            except Exception:
                pass
            
            # Check if filename matches pattern
            match = self.TRAIT_FILE_PATTERN.match(file_name)
            is_valid_name = match is not None
            
            trait_name = ""
            trait_id = ""
            if match:
                trait_name = match.group(1)
                trait_id = match.group(2)
            
            # Check for metadata file
            metadata_path = str(trait_dir / file_name.replace('.png', '.json'))
            has_metadata = Path(metadata_path).exists()
            
            trait_files.append(TraitFileEntry(
                file_path=file_path,
                file_name=file_name,
                trait_name=trait_name,
                trait_id=trait_id,
                file_size=file_size,
                is_valid_name=is_valid_name,
                has_metadata=has_metadata,
                metadata_path=metadata_path if has_metadata else None
            ))
        
        return trait_files
    
    def _guess_trait_category(self, trait_name: str) -> Optional[str]:
        """Guess the trait category based on trait name"""
        trait_name_lower = trait_name.lower()
        
        # Simple keyword-based categorization
        category_keywords = {
            "position-1-background": ["background", "bg", "backdrop", "base-layer"],
            "position-2-base": ["base", "foundation", "primary", "main"],
            "position-3-accent": ["accent", "secondary", "detail", "feature"],
            "position-4-pattern": ["pattern", "texture", "design", "motif"],
            "position-5-center": ["center", "focal", "core", "middle", "central"],
            "position-6-decoration": ["decoration", "ornament", "embellishment", "adornment"],
            "position-7-border": ["border", "frame", "edge", "outline"],
            "position-8-highlight": ["highlight", "emphasis", "glow", "shine"],
            "position-9-overlay": ["overlay", "effect", "finish", "top-layer"]
        }
        
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in trait_name_lower:
                    return category
        
        return None
    
    def _create_trait_readme(self, trait_dir: Path, category_name: str, 
                           position_number: int, grid_row: int, grid_col: int) -> bool:
        """Create README file for a trait directory"""
        try:
            readme_path = trait_dir / "README.md"
            
            grid_location = f"{'Top' if grid_row == 0 else 'Middle' if grid_row == 1 else 'Bottom'}-{'Left' if grid_col == 0 else 'Center' if grid_col == 1 else 'Right'}"
            
            readme_content = f"""# {category_name} Traits

This directory contains trait images for the **{category_name}** category.

## Grid Position
- **Position Number**: {position_number}
- **Grid Coordinates**: Row {grid_row}, Column {grid_col}
- **Grid Location**: {grid_location}

## File Requirements
- **Format**: PNG with transparency support
- **Dimensions**: 200×200 pixels (configurable)
- **Naming**: `trait-{{descriptive-name}}-{{unique-id}}.png`
- **Color Mode**: RGBA (32-bit)
- **Max File Size**: 2MB per trait

## Example Files
```
trait-{category_name.lower()}-example-001.png
trait-{category_name.lower()}-variant-002.png
trait-{category_name.lower()}-special-003.png
```

## Metadata (Optional)
Each trait can have an optional JSON metadata file:
```
trait-{category_name.lower()}-example-001.json
```

## Visual Guidelines
- Traits should be designed specifically for this grid position
- Background should be transparent for proper layering
- Each variant must be visually distinguishable
- Maintain visual coherence within this category

## Category Description
{self._get_category_description(category_name)}
"""
            
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            return True
            
        except Exception as e:
            print(f"Error creating README for {trait_dir}: {e}")
            return False
    
    def _get_category_description(self, category_name: str) -> str:
        """Get detailed description for a trait category"""
        descriptions = {
            "Background": "Base layer elements that provide the foundational appearance. These traits typically fill the entire cell and provide color, texture, or pattern as the background for other elements.",
            "Base": "Primary structural elements that form the main visual foundation. These traits often contain the core shape or form that other elements build upon.",
            "Accent": "Secondary elements that add visual interest and detail. These traits complement the base elements and provide additional visual complexity.",
            "Pattern": "Textural or repetitive design elements that add visual richness. These traits can include geometric patterns, textures, or stylistic elements.",
            "Center": "Focal point elements that draw attention to the center of the composition. These traits are typically the most prominent visual elements.",
            "Decoration": "Ornamental elements that enhance the overall aesthetic. These traits add polish and refinement to the composition.",
            "Border": "Edge elements that frame or contain the composition. These traits provide visual boundaries and can enhance the overall structure.",
            "Highlight": "Elements that add emphasis, lighting effects, or visual pop. These traits can include glows, sparkles, or other attention-grabbing effects.",
            "Overlay": "Top-layer effects that modify the overall appearance. These traits can include filters, atmospheric effects, or finishing touches."
        }
        
        return descriptions.get(category_name, f"{category_name} traits for this grid position.")


# Convenience functions
def create_trait_directories(collection_root: Union[str, Path], 
                           force_recreate: bool = False) -> ValidationResult:
    """
    Create all trait directories for a collection
    
    Args:
        collection_root: Root path of the GenConfig collection
        force_recreate: Whether to recreate existing directories
        
    Returns:
        ValidationResult: Result of directory creation
    """
    manager = TraitDirectoryManager(collection_root)
    return manager.create_trait_directories(force_recreate)


def validate_trait_directories(collection_root: Union[str, Path]) -> ValidationResult:
    """
    Validate trait directory structure for a collection
    
    Args:
        collection_root: Root path of the GenConfig collection
        
    Returns:
        ValidationResult: Comprehensive validation result
    """
    manager = TraitDirectoryManager(collection_root)
    return manager.validate_trait_directories()


def organize_trait_files(collection_root: Union[str, Path], 
                        source_directory: Union[str, Path],
                        auto_categorize: bool = True, 
                        dry_run: bool = False) -> ValidationResult:
    """
    Organize trait files into proper directories
    
    Args:
        collection_root: Root path of the GenConfig collection
        source_directory: Directory containing trait files to organize
        auto_categorize: Whether to automatically categorize files
        dry_run: If True, only report what would be done
        
    Returns:
        ValidationResult: Result of organization operation
    """
    manager = TraitDirectoryManager(collection_root)
    return manager.organize_trait_files(source_directory, auto_categorize, dry_run)


def get_trait_directory_report(collection_root: Union[str, Path]) -> str:
    """
    Get a comprehensive report of trait directory structure
    
    Args:
        collection_root: Root path of the GenConfig collection
        
    Returns:
        String containing formatted report
    """
    manager = TraitDirectoryManager(collection_root)
    return manager.get_trait_directory_summary() 