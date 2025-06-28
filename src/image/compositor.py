"""
GenConfig Image Compositor

This module provides functionality for combining multiple trait images into single composite
images according to the GenConfig 3×3 grid specification. It handles layering, positioning,
transparency, and creates the final composite NFT images.

Grid Layout (600×600 with 200×200 cells):
┌─────────┬─────────┬─────────┐
│ Pos 1   │ Pos 2   │ Pos 3   │
│ (0,0)   │ (0,1)   │ (0,2)   │
├─────────┼─────────┼─────────┤
│ Pos 4   │ Pos 5   │ Pos 6   │
│ (1,0)   │ (1,1)   │ (1,2)   │
├─────────┼─────────┼─────────┤
│ Pos 7   │ Pos 8   │ Pos 9   │
│ (2,0)   │ (2,1)   │ (2,2)   │
└─────────┴─────────┴─────────┘
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from PIL import Image, ImageDraw
import tempfile

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from grid.position_calculator import position_to_coordinates, validate_position, GridPositionError
from utils.file_utils import validate_file_exists, ensure_directory_exists, get_file_size, FileOperationError
from config.config_parser import GenConfig, GenerationConfig, ImageSize, GridConfig
from traits.asset_loader import TraitAssetLoader, LoadedTraitAsset


class ImageCompositionError(Exception):
    """Custom exception for image composition errors"""
    pass


@dataclass
class CompositeImageResult:
    """Result of composite image creation"""
    success: bool
    output_path: Optional[str] = None
    final_size: Optional[Tuple[int, int]] = None
    cell_size: Optional[Tuple[int, int]] = None
    composition_time: float = 0.0
    traits_used: Dict[int, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Image statistics
    file_size_bytes: int = 0
    memory_usage_bytes: int = 0
    total_layers: int = 0
    
    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes"""
        return self.file_size_bytes / (1024 * 1024)
    
    @property
    def memory_usage_mb(self) -> float:
        """Get memory usage in megabytes"""
        return self.memory_usage_bytes / (1024 * 1024)


class ImageCompositor:
    """
    Main image compositor class for creating composite NFT images from trait layers
    """
    
    def __init__(self, 
                 final_size: Tuple[int, int] = (600, 600),
                 cell_size: Tuple[int, int] = (200, 200),
                 grid_size: Tuple[int, int] = (3, 3),
                 background_color: str = "#FFFFFF",
                 output_format: str = "PNG"):
        """
        Initialize image compositor
        
        Args:
            final_size: Final composite image size (width, height)
            cell_size: Individual cell/trait size (width, height)
            grid_size: Grid dimensions (rows, columns)
            background_color: Background color for transparent areas
            output_format: Output image format
        """
        self.final_size = final_size
        self.cell_size = cell_size
        self.grid_size = grid_size
        self.background_color = background_color
        self.output_format = output_format
        
        # Validate configuration
        self._validate_configuration()
        
    def _validate_configuration(self):
        """Validate compositor configuration"""
        final_width, final_height = self.final_size
        cell_width, cell_height = self.cell_size
        grid_rows, grid_cols = self.grid_size
        
        # Check that final size matches grid * cell size
        expected_width = grid_cols * cell_width
        expected_height = grid_rows * cell_height
        
        if final_width != expected_width or final_height != expected_height:
            raise ImageCompositionError(
                f"Size mismatch: Final size {self.final_size} doesn't match "
                f"grid {self.grid_size} × cell {self.cell_size} = ({expected_width}, {expected_height})"
            )
        
        # Validate grid size
        if grid_rows != 3 or grid_cols != 3:
            raise ImageCompositionError(
                f"Invalid grid size {self.grid_size}. GenConfig requires 3×3 grid."
            )
    
    def create_composite_from_files(self, trait_images: Dict[int, str], 
                                   output_path: str) -> CompositeImageResult:
        """
        Create composite image from trait image files
        
        Args:
            trait_images: Dictionary mapping grid positions (1-9) to file paths
            output_path: Path for output composite image
            
        Returns:
            CompositeImageResult: Result of composition operation
        """
        start_time = time.time()
        result = CompositeImageResult(success=False)
        
        try:
            # Validate inputs
            self._validate_trait_inputs(trait_images)
            
            # Load trait images
            loaded_images = self._load_trait_images(trait_images, result)
            if not loaded_images:
                result.success = False
                result.errors.append("No valid trait images could be loaded")
                return result
            
            # Create composite
            composite_image = self._create_composite_image(loaded_images, result)
            if composite_image is None:
                result.success = False
                result.errors.append("Failed to create composite image")
                return result
            
            # Save composite
            self._save_composite_image(composite_image, output_path, result)
            
            # Calculate final statistics
            result.composition_time = time.time() - start_time
            result.traits_used = trait_images.copy()
            result.total_layers = len(loaded_images)
            result.success = True
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Composition failed: {str(e)}")
            result.composition_time = time.time() - start_time
        
        return result
    
    def create_composite_from_assets(self, trait_assets: Dict[int, LoadedTraitAsset],
                                    output_path: str) -> CompositeImageResult:
        """
        Create composite image from loaded trait assets
        
        Args:
            trait_assets: Dictionary mapping grid positions to LoadedTraitAsset objects
            output_path: Path for output composite image
            
        Returns:
            CompositeImageResult: Result of composition operation
        """
        start_time = time.time()
        result = CompositeImageResult(success=False)
        
        try:
            # Validate inputs
            if not trait_assets:
                raise ImageCompositionError("No trait assets provided")
            
            # Convert assets to image dictionary
            loaded_images = {}
            for position, asset in trait_assets.items():
                if not validate_position(position):
                    result.warnings.append(f"Invalid position {position}, skipping")
                    continue
                loaded_images[position] = asset.image
                
            if not loaded_images:
                result.success = False
                result.errors.append("No valid trait assets found")
                return result
            
            # Create composite
            composite_image = self._create_composite_image(loaded_images, result)
            if composite_image is None:
                result.success = False
                result.errors.append("Failed to create composite image")
                return result
            
            # Save composite
            self._save_composite_image(composite_image, output_path, result)
            
            # Calculate final statistics
            result.composition_time = time.time() - start_time
            result.traits_used = {pos: asset.file_path for pos, asset in trait_assets.items()}
            result.total_layers = len(loaded_images)
            result.success = True
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Composition failed: {str(e)}")
            result.composition_time = time.time() - start_time
        
        return result
    
    def _validate_trait_inputs(self, trait_images: Dict[int, str]):
        """Validate trait image inputs"""
        if not trait_images:
            raise ImageCompositionError("No trait images provided")
        
        for position, file_path in trait_images.items():
            if not validate_position(position):
                raise ImageCompositionError(f"Invalid grid position: {position}")
            
            if not validate_file_exists(file_path):
                raise ImageCompositionError(f"Trait image file not found: {file_path}")
    
    def _load_trait_images(self, trait_images: Dict[int, str], 
                          result: CompositeImageResult) -> Dict[int, Image.Image]:
        """Load trait images from file paths"""
        loaded_images = {}
        
        for position, file_path in trait_images.items():
            try:
                # Load and validate image
                image = Image.open(file_path)
                
                # Convert to RGBA for consistent handling
                if image.mode != 'RGBA':
                    image = image.convert('RGBA')
                
                # Validate/resize to cell size if needed
                if image.size != self.cell_size:
                    result.warnings.append(
                        f"Position {position}: Resizing from {image.size} to {self.cell_size}"
                    )
                    image = image.resize(self.cell_size, Image.Resampling.LANCZOS)
                
                loaded_images[position] = image
                
            except Exception as e:
                result.errors.append(f"Failed to load image at position {position}: {str(e)}")
        
        return loaded_images
    
    def _create_composite_image(self, loaded_images: Dict[int, Image.Image],
                               result: CompositeImageResult) -> Optional[Image.Image]:
        """Create the composite image from loaded trait images"""
        try:
            # Create base composite image with background
            composite = Image.new('RGBA', self.final_size, self.background_color)
            
            # Calculate memory usage
            width, height = self.final_size
            result.memory_usage_bytes = width * height * 4  # RGBA = 4 bytes per pixel
            
            # Layer images in position order (1-9)
            for position in sorted(loaded_images.keys()):
                image = loaded_images[position]
                
                # Calculate position coordinates
                try:
                    row, col = position_to_coordinates(position)
                except GridPositionError as e:
                    result.warnings.append(f"Invalid position {position}: {str(e)}")
                    continue
                
                # Calculate pixel coordinates for pasting
                x = col * self.cell_size[0]
                y = row * self.cell_size[1]
                
                # Paste image with alpha compositing
                composite.paste(image, (x, y), image)
            
            result.final_size = composite.size
            result.cell_size = self.cell_size
            
            return composite
            
        except Exception as e:
            result.errors.append(f"Failed to create composite: {str(e)}")
            return None
    
    def _save_composite_image(self, composite: Image.Image, output_path: str,
                             result: CompositeImageResult):
        """Save composite image to file"""
        try:
            # Ensure output directory exists
            output_dir = Path(output_path).parent
            ensure_directory_exists(str(output_dir))
            
            # Save image
            composite.save(output_path, format=self.output_format, optimize=True)
            
            # Calculate file size
            result.file_size_bytes = get_file_size(output_path)
            result.output_path = str(Path(output_path).resolve())
            
        except Exception as e:
            raise ImageCompositionError(f"Failed to save composite image: {str(e)}")
    
    @classmethod
    def from_config(cls, config: GenConfig) -> 'ImageCompositor':
        """
        Create compositor from GenConfig configuration
        
        Args:
            config: GenConfig configuration object
            
        Returns:
            ImageCompositor: Configured compositor instance
        """
        generation = config.generation
        
        return cls(
            final_size=(generation.image_size.width, generation.image_size.height),
            cell_size=(generation.grid.cell_size.width, generation.grid.cell_size.height),
            grid_size=(generation.grid.rows, generation.grid.columns),
            background_color=generation.background_color,
            output_format=generation.image_format
        )


# Convenience Functions


def create_composite(trait_images: Dict[int, str], output_path: str) -> bool:
    """
    Creates composite image from trait files positioned by grid number
    
    Args:
        trait_images: Dictionary mapping grid positions (1-9) to file paths
        output_path: Path for output composite image
        
    Returns:
        bool: True if composite created successfully, False otherwise
    """
    try:
        # Create 600x600 composite with RGBA support
        composite = Image.new('RGBA', (600, 600), (255, 255, 255, 0))
        
        # Process each trait image
        for position, file_path in trait_images.items():
            if not validate_position(position):
                continue
                
            if not validate_file_exists(file_path):
                continue
                
            # Load trait image
            trait_img = Image.open(file_path)
            if trait_img.mode != 'RGBA':
                trait_img = trait_img.convert('RGBA')
                
            # Resize to 200x200 if needed
            if trait_img.size != (200, 200):
                trait_img = trait_img.resize((200, 200), Image.Resampling.LANCZOS)
            
            # Calculate position
            row, col = position_to_coordinates(position)
            x = col * 200
            y = row * 200
            
            # Paste with transparency
            composite.paste(trait_img, (x, y), trait_img)
        
        # Ensure output directory exists
        ensure_directory_exists(str(Path(output_path).parent))
        
        # Save composite
        composite.save(output_path, 'PNG')
        return True
        
    except Exception:
        return False


def create_composite_from_config(trait_images: Dict[int, str], output_path: str,
                                config: GenConfig) -> CompositeImageResult:
    """
    Create composite image using configuration settings
    
    Args:
        trait_images: Dictionary mapping grid positions to file paths
        output_path: Path for output composite image
        config: GenConfig configuration object
        
    Returns:
        CompositeImageResult: Detailed result of composition operation
    """
    compositor = ImageCompositor.from_config(config)
    return compositor.create_composite_from_files(trait_images, output_path)


def validate_composite_inputs(trait_images: Dict[int, str],
                             final_size: Tuple[int, int] = (600, 600),
                             cell_size: Tuple[int, int] = (200, 200)) -> Tuple[bool, List[str]]:
    """
    Validate inputs for composite creation
    
    Args:
        trait_images: Dictionary mapping grid positions to file paths
        final_size: Final composite image size
        cell_size: Individual cell size
        
    Returns:
        Tuple[bool, List[str]]: (is_valid, error_messages)
    """
    errors = []
    
    try:
        # Validate positions
        for position in trait_images.keys():
            if not validate_position(position):
                errors.append(f"Invalid grid position: {position}")
        
        # Validate file existence
        for position, file_path in trait_images.items():
            if not validate_file_exists(file_path):
                errors.append(f"File not found for position {position}: {file_path}")
        
        # Validate size configuration
        if final_size[0] != cell_size[0] * 3 or final_size[1] != cell_size[1] * 3:
            errors.append(
                f"Size mismatch: Final {final_size} != Grid 3×3 × Cell {cell_size}"
            )
        
        return len(errors) == 0, errors
        
    except Exception as e:
        errors.append(f"Validation error: {str(e)}")
        return False, errors


def get_composition_info(final_size: Tuple[int, int] = (600, 600),
                        cell_size: Tuple[int, int] = (200, 200)) -> Dict[str, Any]:
    """
    Get information about composition configuration
    
    Args:
        final_size: Final composite image size
        cell_size: Individual cell size
        
    Returns:
        Dict[str, Any]: Configuration information
    """
    return {
        'final_size': final_size,
        'cell_size': cell_size,
        'grid_size': (3, 3),
        'total_cells': 9,
        'expected_final_size': (cell_size[0] * 3, cell_size[1] * 3),
        'memory_estimate_mb': (final_size[0] * final_size[1] * 4) / (1024 * 1024),
        'supported_formats': ['PNG', 'JPEG', 'WEBP'],
        'cell_positions': {
            1: (0, 0), 2: (0, 1), 3: (0, 2),
            4: (1, 0), 5: (1, 1), 6: (1, 2),
            7: (2, 0), 8: (2, 1), 9: (2, 2)
        }
    } 