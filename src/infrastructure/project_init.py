"""
GenConfig Project Initialization Module

This module handles the bootstrapping of new GenConfig projects, creating
complete project setups with default configuration files and templates.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from PIL import Image, ImageDraw

from .directory_manager import create_collection_structure, validate_collection_structure


def bootstrap_genconfig_project(project_path: str, project_name: str = "My NFT Collection", 
                              collection_size: int = 1000, **kwargs) -> bool:
    """
    Bootstrap a complete GenConfig project with default files and configuration.
    
    Args:
        project_path: Directory where the project should be created
        project_name: Name of the NFT collection
        collection_size: Number of NFTs to generate (default: 1000)
        **kwargs: Additional configuration parameters
        
    Returns:
        bool: True if project created successfully, False otherwise
    """
    try:
        project_root = Path(project_path)
        
        # Step 1: Create directory structure
        if not create_collection_structure(str(project_root)):
            print(f"❌ Failed to create directory structure for {project_path}")
            return False
        
        # Step 2: Create default configuration file
        if not _create_default_config(project_root, project_name, collection_size, **kwargs):
            print(f"❌ Failed to create default configuration")
            return False
        
        # Step 3: Create grid template
        if not _create_grid_template(project_root):
            print(f"❌ Failed to create grid template")
            return False
        
        # Step 4: Create example trait files (placeholders)
        if not _create_example_traits(project_root):
            print(f"❌ Failed to create example traits")
            return False
        
        # Step 5: Create project README
        if not _create_project_readme(project_root, project_name):
            print(f"❌ Failed to create project README")
            return False
        
        print(f"✅ GenConfig project '{project_name}' created successfully at: {project_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error bootstrapping project: {e}")
        return False


def _create_default_config(project_root: Path, project_name: str, 
                          collection_size: int, **kwargs) -> bool:
    """
    Create a default config.json file with proper GenConfig structure.
    
    Args:
        project_root: Root directory of the project
        project_name: Name of the collection
        collection_size: Size of the collection
        **kwargs: Additional configuration options
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Default configuration structure following the specification
        config = {
            "collection": {
                "name": project_name,
                "description": f"A generative 3x3 grid NFT collection - {project_name}",
                "size": collection_size,
                "symbol": kwargs.get("symbol", project_name.upper().replace(" ", "")[:8]),
                "external_url": kwargs.get("external_url", "https://example.com")
            },
            "generation": {
                "image_format": "PNG",
                "image_size": {
                    "width": kwargs.get("image_width", 600),
                    "height": kwargs.get("image_height", 600)
                },
                "grid": {
                    "rows": 3,
                    "columns": 3,
                    "cell_size": {
                        "width": kwargs.get("cell_width", 200),
                        "height": kwargs.get("cell_height", 200)
                    }
                },
                "background_color": kwargs.get("background_color", "#FFFFFF"),
                "allow_duplicates": kwargs.get("allow_duplicates", False)
            },
            "traits": {},
            "rarity": {
                "calculation_method": "weighted_random",
                "distribution_validation": True,
                "rarity_tiers": {
                    "common": {"min_weight": 50, "max_weight": 100},
                    "uncommon": {"min_weight": 25, "max_weight": 49},
                    "rare": {"min_weight": 10, "max_weight": 24},
                    "epic": {"min_weight": 5, "max_weight": 9},
                    "legendary": {"min_weight": 1, "max_weight": 4}
                }
            },
            "validation": {
                "enforce_grid_positions": True,
                "require_all_positions": True,
                "check_file_integrity": True,
                "validate_image_dimensions": True
            }
        }
        
        # Add default trait configuration for each position
        trait_categories = [
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
        
        for trait_dir, trait_name, row, col in trait_categories:
            config["traits"][trait_dir] = {
                "name": trait_name,
                "required": True,
                "grid_position": {
                    "row": row,
                    "column": col
                },
                "variants": [
                    {
                        "name": f"Default {trait_name}",
                        "filename": f"trait-default-{trait_name.lower()}-001.png",
                        "rarity_weight": 100,
                        "color_code": "#808080"
                    },
                    {
                        "name": f"Alternative {trait_name}",
                        "filename": f"trait-alt-{trait_name.lower()}-002.png",
                        "rarity_weight": 50,
                        "color_code": "#606060"
                    }
                ]
            }
        
        # Write config.json
        config_path = project_root / "config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return True
        
    except Exception as e:
        print(f"Error creating default config: {e}")
        return False


def _create_grid_template(project_root: Path) -> bool:
    """
    Create a 3x3 grid template PNG image for reference.
    
    Args:
        project_root: Root directory of the project
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create 600x600 image with 3x3 grid
        image_size = (600, 600)
        cell_size = (200, 200)
        
        # Create white background
        image = Image.new('RGBA', image_size, (255, 255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # Draw grid lines
        grid_color = (200, 200, 200, 255)  # Light gray
        line_width = 2
        
        # Vertical lines
        for i in range(1, 3):
            x = i * cell_size[0]
            draw.line([(x, 0), (x, image_size[1])], fill=grid_color, width=line_width)
        
        # Horizontal lines
        for i in range(1, 3):
            y = i * cell_size[1]
            draw.line([(0, y), (image_size[0], y)], fill=grid_color, width=line_width)
        
        # Add position numbers
        from PIL import ImageFont
        try:
            # Try to use a standard font
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        except (OSError, IOError):
            # Fallback to default font
            font = ImageFont.load_default()
        
        text_color = (100, 100, 100, 255)
        position = 1
        
        for row in range(3):
            for col in range(3):
                # Calculate text position (center of cell)
                text_x = col * cell_size[0] + cell_size[0] // 2
                text_y = row * cell_size[1] + cell_size[1] // 2
                
                position_text = f"Pos {position}"
                
                # Get text dimensions for centering
                bbox = draw.textbbox((0, 0), position_text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # Center the text
                final_x = text_x - text_width // 2
                final_y = text_y - text_height // 2
                
                draw.text((final_x, final_y), position_text, fill=text_color, font=font)
                position += 1
        
        # Save the grid template
        template_path = project_root / "templates" / "grid-template.png"
        image.save(template_path, "PNG")
        
        return True
        
    except Exception as e:
        print(f"Error creating grid template: {e}")
        return False


def _create_example_traits(project_root: Path) -> bool:
    """
    Create example trait images (simple colored squares) for demonstration.
    
    Args:
        project_root: Root directory of the project
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        trait_categories = [
            ("position-1-background", "Background", [(255, 200, 200), (200, 255, 200)]),
            ("position-2-base", "Base", [(200, 200, 255), (255, 255, 200)]),
            ("position-3-accent", "Accent", [(255, 200, 255), (200, 255, 255)]),
            ("position-4-pattern", "Pattern", [(255, 180, 180), (180, 255, 180)]),
            ("position-5-center", "Center", [(180, 180, 255), (255, 255, 180)]),
            ("position-6-decoration", "Decoration", [(255, 180, 255), (180, 255, 255)]),
            ("position-7-border", "Border", [(220, 200, 200), (200, 220, 200)]),
            ("position-8-highlight", "Highlight", [(200, 200, 220), (220, 220, 200)]),
            ("position-9-overlay", "Overlay", [(220, 200, 220), (200, 220, 220)])
        ]
        
        for trait_dir, trait_name, colors in trait_categories:
            trait_path = project_root / "traits" / trait_dir
            
            # Create two example traits per category
            for i, color in enumerate(colors, 1):
                # Create a simple 200x200 colored square with some pattern
                img = Image.new('RGBA', (200, 200), (*color, 200))  # Semi-transparent
                draw = ImageDraw.Draw(img)
                
                # Add a simple pattern based on the trait type
                if "background" in trait_name.lower():
                    # Solid background
                    pass
                elif "center" in trait_name.lower():
                    # Circle in center
                    draw.ellipse([50, 50, 150, 150], fill=(*color, 255), outline=(0, 0, 0, 255), width=2)
                elif "border" in trait_name.lower():
                    # Border rectangle
                    draw.rectangle([10, 10, 190, 190], outline=(*color, 255), width=5)
                else:
                    # Simple diagonal lines
                    for j in range(0, 200, 20):
                        draw.line([(j, 0), (j + 40, 40)], fill=(*color, 255), width=2)
                
                # Save the trait image
                trait_type = "default" if i == 1 else "alt"
                filename = f"trait-{trait_type}-{trait_name.lower()}-00{i}.png"
                img.save(trait_path / filename, "PNG")
        
        return True
        
    except Exception as e:
        print(f"Error creating example traits: {e}")
        return False


def _create_project_readme(project_root: Path, project_name: str) -> bool:
    """
    Create a project README.md file with setup instructions.
    
    Args:
        project_root: Root directory of the project
        project_name: Name of the project
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        readme_content = f"""# {project_name}

A GenConfig Phase 1 generative NFT collection project.

## Project Structure

This project follows the GenConfig standard folder structure:

```
{project_name}/
├── config.json                    # Main configuration file
├── traits/                        # Trait assets directory
│   ├── position-1-background/     # Grid position 1 traits
│   ├── position-2-base/          # Grid position 2 traits
│   ├── position-3-accent/        # Grid position 3 traits
│   ├── position-4-pattern/       # Grid position 4 traits
│   ├── position-5-center/        # Grid position 5 traits
│   ├── position-6-decoration/    # Grid position 6 traits
│   ├── position-7-border/        # Grid position 7 traits
│   ├── position-8-highlight/     # Grid position 8 traits
│   └── position-9-overlay/       # Grid position 9 traits
├── output/                        # Generated collection output
│   ├── images/                   # Final composite images
│   └── metadata/                 # Generated metadata files
├── templates/                     # Template files
│   └── grid-template.png         # 3x3 grid template reference
└── tests/                        # Testing assets and results
    ├── sample-traits/            # Individual trait test images
    └── sample-composites/        # Test composite images
```

## Configuration

The project includes a default `config.json` file with:
- Collection metadata (name, description, size)
- Generation settings (image format, dimensions, grid layout)
- Trait definitions for all 9 grid positions
- Rarity configuration with tier system
- Validation settings

## Grid Layout

The collection uses a 3×3 grid system:

```
┌─────────┬─────────┬─────────┐
│ Pos 1   │ Pos 2   │ Pos 3   │
│Background│  Base   │ Accent  │
├─────────┼─────────┼─────────┤
│ Pos 4   │ Pos 5   │ Pos 6   │
│ Pattern │ Center  │Decoration│
├─────────┼─────────┼─────────┤
│ Pos 7   │ Pos 8   │ Pos 9   │
│ Border  │Highlight│ Overlay │
└─────────┴─────────┴─────────┘
```

## Getting Started

1. **Review Configuration**: Edit `config.json` to customize your collection settings
2. **Add Trait Images**: Replace example traits in each `position-X-category/` directory
   - Use PNG format with transparency
   - 200×200 pixel dimensions
   - Follow naming convention: `trait-{{name}}-{{id}}.png`
3. **Test Configuration**: Validate your setup before generation
4. **Generate Collection**: Run the GenConfig generation pipeline

## Trait Requirements

Each trait image must:
- Be in PNG format with transparency support
- Have dimensions of 200×200 pixels
- Be designed for its specific grid position
- Follow the naming convention: `trait-{{descriptive-name}}-{{unique-id}}.png`
- Have a maximum file size of 2MB

## Next Steps

1. Customize the collection configuration in `config.json`
2. Create or import your trait artwork
3. Update trait definitions and rarity weights
4. Test the configuration with a small sample
5. Generate your full NFT collection

---

Generated by GenConfig Phase 1 - Directory Structure Manager & Project Initialization
"""
        
        readme_path = project_root / "README.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        return True
        
    except Exception as e:
        print(f"Error creating project README: {e}")
        return False


def validate_project_setup(project_path: str) -> Tuple[bool, List[str]]:
    """
    Validate that a GenConfig project is properly set up.
    
    Args:
        project_path: Path to the project to validate
        
    Returns:
        Tuple of (is_valid: bool, issues: List[str])
    """
    issues = []
    project_root = Path(project_path)
    
    try:
        # Check directory structure
        is_valid_structure, missing_dirs = validate_collection_structure(project_path)
        if not is_valid_structure:
            issues.extend([f"Missing directory: {d}" for d in missing_dirs])
        
        # Check config.json exists and is valid JSON
        config_path = project_root / "config.json"
        if not config_path.exists():
            issues.append("Missing config.json file")
        else:
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Basic config validation
                required_sections = ["collection", "generation", "traits", "rarity", "validation"]
                for section in required_sections:
                    if section not in config:
                        issues.append(f"Missing '{section}' section in config.json")
                
            except json.JSONDecodeError as e:
                issues.append(f"Invalid JSON in config.json: {e}")
        
        # Check grid template exists
        grid_template_path = project_root / "templates" / "grid-template.png"
        if not grid_template_path.exists():
            issues.append("Missing grid-template.png")
        
        # Check README exists
        readme_path = project_root / "README.md"
        if not readme_path.exists():
            issues.append("Missing README.md")
        
        return len(issues) == 0, issues
        
    except Exception as e:
        issues.append(f"Validation error: {e}")
        return False, issues


if __name__ == "__main__":
    # Example usage
    test_project_path = "./example-nft-project"
    
    print("Creating example GenConfig project...")
    success = bootstrap_genconfig_project(
        test_project_path, 
        project_name="Example NFT Collection",
        collection_size=500
    )
    
    if success:
        print(f"✅ Project created successfully!")
        
        # Validate the setup
        is_valid, issues = validate_project_setup(test_project_path)
        if is_valid:
            print("✅ Project validation passed")
        else:
            print(f"❌ Project validation failed: {issues}")
    else:
        print("❌ Failed to create project") 