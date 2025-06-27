"""
GenConfig Directory Structure Manager

This module handles the creation and management of the standardized
GenConfig folder structure as defined in the Phase 1 specification.
"""

import os
from pathlib import Path
from typing import List, Tuple


def create_collection_structure(root_path: str) -> bool:
    """
    Creates the standardized GenConfig folder structure.
    
    Args:
        root_path: The root directory where the collection structure should be created
        
    Returns:
        bool: True if structure created successfully, False otherwise
        
    Raises:
        OSError: If directory creation fails due to permissions or other system issues
    """
    try:
        root = Path(root_path)
        
        # Create main directories
        directories = [
            "traits",
            "output",
            "output/images", 
            "output/metadata",
            "templates",
            "tests",
            "tests/sample-traits",
            "tests/sample-composites"
        ]
        
        # Create trait position directories (1-9)
        trait_categories = [
            ("position-1-background", "Background"),
            ("position-2-base", "Base"),
            ("position-3-accent", "Accent"),
            ("position-4-pattern", "Pattern"),
            ("position-5-center", "Center"),
            ("position-6-decoration", "Decoration"),
            ("position-7-border", "Border"),
            ("position-8-highlight", "Highlight"),
            ("position-9-overlay", "Overlay")
        ]
        
        # Add trait directories to the list
        for trait_dir, _ in trait_categories:
            directories.append(f"traits/{trait_dir}")
        
        # Create all directories
        for directory in directories:
            dir_path = root / directory
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Create README files for trait directories
        _create_trait_readmes(root, trait_categories)
        
        return True
        
    except OSError as e:
        print(f"Error creating directory structure: {e}")
        return False


def _create_trait_readmes(root_path: Path, trait_categories: List[Tuple[str, str]]) -> None:
    """
    Creates README.md files for each trait category directory.
    
    Args:
        root_path: Root path of the collection
        trait_categories: List of (directory_name, category_name) tuples
    """
    for trait_dir, category_name in trait_categories:
        readme_path = root_path / "traits" / trait_dir / "README.md"
        
        position_num = trait_dir.split('-')[1]  # Extract position number
        grid_row = (int(position_num) - 1) // 3
        grid_col = (int(position_num) - 1) % 3
        
        readme_content = f"""# {category_name} Traits

This directory contains trait images for the **{category_name}** category.

## Grid Position
- **Position Number**: {position_num}
- **Grid Coordinates**: Row {grid_row}, Column {grid_col}
- **Grid Location**: {"Top" if grid_row == 0 else "Middle" if grid_row == 1 else "Bottom"}-{"Left" if grid_col == 0 else "Center" if grid_col == 1 else "Right"}

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
"""
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)


def validate_collection_structure(root_path: str) -> Tuple[bool, List[str]]:
    """
    Validates that the collection structure exists and is complete.
    
    Args:
        root_path: Path to validate
        
    Returns:
        Tuple of (is_valid: bool, missing_directories: List[str])
    """
    root = Path(root_path)
    missing = []
    
    # Required directories
    required_dirs = [
        "traits",
        "output",
        "output/images",
        "output/metadata", 
        "templates",
        "tests",
        "tests/sample-traits",
        "tests/sample-composites"
    ]
    
    # Add trait position directories
    for i in range(1, 10):
        trait_categories = [
            "background", "base", "accent", "pattern", "center",
            "decoration", "border", "highlight", "overlay"
        ]
        category = trait_categories[i-1]
        required_dirs.append(f"traits/position-{i}-{category}")
    
    # Check each required directory
    for directory in required_dirs:
        dir_path = root / directory
        if not dir_path.exists() or not dir_path.is_dir():
            missing.append(directory)
    
    return len(missing) == 0, missing


def get_trait_directories(root_path: str) -> List[str]:
    """
    Returns a list of trait directories in the collection.
    
    Args:
        root_path: Root path of the collection
        
    Returns:
        List of trait directory names
    """
    root = Path(root_path)
    traits_dir = root / "traits"
    
    if not traits_dir.exists():
        return []
    
    trait_dirs = []
    for item in traits_dir.iterdir():
        if item.is_dir() and item.name.startswith('position-'):
            trait_dirs.append(item.name)
    
    return sorted(trait_dirs)


if __name__ == "__main__":
    # Example usage
    test_path = "./test-collection"
    
    print("Creating GenConfig collection structure...")
    success = create_collection_structure(test_path)
    
    if success:
        print(f"✅ Collection structure created successfully at: {test_path}")
        
        # Validate the structure
        is_valid, missing = validate_collection_structure(test_path)
        if is_valid:
            print("✅ Structure validation passed")
        else:
            print(f"❌ Structure validation failed. Missing: {missing}")
    else:
        print("❌ Failed to create collection structure") 