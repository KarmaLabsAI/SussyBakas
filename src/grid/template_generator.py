"""
Grid Template Generator - Component 4.3

This module provides functionality for generating reference grid template images
that visualize the 3×3 grid layout used in GenConfig NFT generation. The templates
serve as visual references for understanding grid positioning and cell layout.
"""

import os
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List, Union
from PIL import Image, ImageDraw, ImageFont
from dataclasses import dataclass

from .position_calculator import position_to_coordinates, GridPositionError


@dataclass
class GridTemplateStyle:
    """
    Configuration for grid template visual styling
    """
    background_color: Tuple[int, int, int, int] = (255, 255, 255, 255)  # White background
    grid_line_color: Tuple[int, int, int, int] = (200, 200, 200, 255)   # Light gray lines
    text_color: Tuple[int, int, int, int] = (100, 100, 100, 255)        # Dark gray text
    border_color: Tuple[int, int, int, int] = (150, 150, 150, 255)      # Medium gray border
    grid_line_width: int = 2
    border_width: int = 3
    font_size: int = 24
    show_position_numbers: bool = True
    show_category_labels: bool = True
    show_coordinates: bool = False


@dataclass
class GridTemplateDimensions:
    """
    Configuration for grid template dimensions
    """
    image_width: int = 600
    image_height: int = 600
    cell_width: int = 200
    cell_height: int = 200
    
    def __post_init__(self):
        """Validate dimensions consistency"""
        if self.image_width != self.cell_width * 3:
            raise ValueError(f"Image width {self.image_width} must equal cell_width * 3 ({self.cell_width * 3})")
        if self.image_height != self.cell_height * 3:
            raise ValueError(f"Image height {self.image_height} must equal cell_height * 3 ({self.cell_height * 3})")


class GridTemplateError(Exception):
    """Custom exception for grid template generation errors"""
    pass


class GridTemplateGenerator:
    """
    Generator for 3×3 grid template images
    
    Creates reference template images that visualize the GenConfig grid layout
    with position numbers, category labels, and coordinate information.
    """
    
    # Default category mapping for the 9 grid positions
    DEFAULT_CATEGORIES = {
        1: "Background",
        2: "Base", 
        3: "Accent",
        4: "Pattern",
        5: "Center",
        6: "Decoration",
        7: "Border",
        8: "Highlight",
        9: "Overlay"
    }
    
    def __init__(self, dimensions: Optional[GridTemplateDimensions] = None,
                 style: Optional[GridTemplateStyle] = None):
        """
        Initialize grid template generator
        
        Args:
            dimensions: Template dimensions configuration
            style: Template visual styling configuration
        """
        self.dimensions = dimensions or GridTemplateDimensions()
        self.style = style or GridTemplateStyle()
        self.font = self._load_font()
    
    def generate_template(self, output_path: Union[str, Path], 
                         categories: Optional[Dict[int, str]] = None,
                         include_guides: bool = True) -> bool:
        """
        Generate a grid template image and save to file
        
        Args:
            output_path: Path where template image should be saved
            categories: Custom category names for positions (default: DEFAULT_CATEGORIES)
            include_guides: Whether to include visual guides (grid lines, borders)
            
        Returns:
            bool: True if template generated successfully, False otherwise
            
        Raises:
            GridTemplateError: If template generation fails
        """
        try:
            categories = categories or self.DEFAULT_CATEGORIES
            
            # Create the template image
            template_image = self._create_template_image(categories, include_guides)
            
            # Ensure output directory exists
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save the template
            template_image.save(output_path, "PNG")
            
            return True
            
        except Exception as e:
            raise GridTemplateError(f"Failed to generate grid template: {e}")
    
    def create_template_data(self, categories: Optional[Dict[int, str]] = None,
                           include_guides: bool = True) -> Image.Image:
        """
        Create a grid template image in memory (without saving to file)
        
        Args:
            categories: Custom category names for positions
            include_guides: Whether to include visual guides
            
        Returns:
            PIL.Image.Image: Generated template image
        """
        categories = categories or self.DEFAULT_CATEGORIES
        return self._create_template_image(categories, include_guides)
    
    def _create_template_image(self, categories: Dict[int, str], 
                              include_guides: bool) -> Image.Image:
        """
        Internal method to create the template image
        
        Args:
            categories: Category names for positions
            include_guides: Whether to include guides
            
        Returns:
            PIL.Image.Image: Generated template image
        """
        # Create image with background
        image = Image.new('RGBA', 
                         (self.dimensions.image_width, self.dimensions.image_height),
                         self.style.background_color)
        draw = ImageDraw.Draw(image)
        
        # Draw border if guides enabled
        if include_guides:
            self._draw_border(draw)
            self._draw_grid_lines(draw)
        
        # Add position information to each cell
        for position in range(1, 10):
            row, col = position_to_coordinates(position)
            self._draw_cell_content(draw, position, row, col, categories.get(position, f"Position {position}"))
        
        return image
    
    def _draw_border(self, draw: ImageDraw.Draw) -> None:
        """Draw border around the entire grid"""
        border_rect = [0, 0, self.dimensions.image_width - 1, self.dimensions.image_height - 1]
        draw.rectangle(border_rect, outline=self.style.border_color, width=self.style.border_width)
    
    def _draw_grid_lines(self, draw: ImageDraw.Draw) -> None:
        """Draw the grid lines separating cells"""
        # Vertical lines
        for i in range(1, 3):
            x = i * self.dimensions.cell_width
            draw.line([(x, 0), (x, self.dimensions.image_height)], 
                     fill=self.style.grid_line_color, width=self.style.grid_line_width)
        
        # Horizontal lines  
        for i in range(1, 3):
            y = i * self.dimensions.cell_height
            draw.line([(0, y), (self.dimensions.image_width, y)], 
                     fill=self.style.grid_line_color, width=self.style.grid_line_width)
    
    def _draw_cell_content(self, draw: ImageDraw.Draw, position: int, row: int, col: int, 
                          category: str) -> None:
        """Draw content for a specific grid cell"""
        # Calculate cell boundaries
        cell_x = col * self.dimensions.cell_width
        cell_y = row * self.dimensions.cell_height
        cell_center_x = cell_x + self.dimensions.cell_width // 2
        cell_center_y = cell_y + self.dimensions.cell_height // 2
        
        # Prepare text elements
        texts = []
        
        if self.style.show_position_numbers:
            texts.append(f"Pos {position}")
        
        if self.style.show_category_labels:
            texts.append(category)
        
        if self.style.show_coordinates:
            texts.append(f"({row},{col})")
        
        # Draw text elements vertically centered
        total_text_height = len(texts) * (self.style.font_size + 5)
        start_y = cell_center_y - total_text_height // 2
        
        for i, text in enumerate(texts):
            text_y = start_y + i * (self.style.font_size + 5)
            self._draw_centered_text(draw, text, cell_center_x, text_y)
    
    def _draw_centered_text(self, draw: ImageDraw.Draw, text: str, x: int, y: int) -> None:
        """Draw text centered at the given coordinates"""
        bbox = draw.textbbox((0, 0), text, font=self.font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        final_x = x - text_width // 2
        final_y = y - text_height // 2
        
        draw.text((final_x, final_y), text, fill=self.style.text_color, font=self.font)
    
    def _load_font(self) -> ImageFont.ImageFont:
        """Load font for text rendering"""
        try:
            # Try common system fonts
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 
                "/System/Library/Fonts/Helvetica.ttc",  # macOS
                "C:/Windows/Fonts/arial.ttf"  # Windows
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, self.style.font_size)
            
            # Fallback to default font
            return ImageFont.load_default()
            
        except (OSError, IOError):
            return ImageFont.load_default()


# Convenience functions

def generate_grid_template(output_path: Union[str, Path], 
                          image_size: Tuple[int, int] = (600, 600),
                          cell_size: Tuple[int, int] = (200, 200),
                          categories: Optional[Dict[int, str]] = None,
                          include_guides: bool = True) -> bool:
    """
    Convenience function to generate a grid template with basic configuration
    
    Args:
        output_path: Path where template should be saved
        image_size: (width, height) of the template image
        cell_size: (width, height) of each grid cell
        categories: Custom category names for positions
        include_guides: Whether to include grid lines and borders
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        dimensions = GridTemplateDimensions(
            image_width=image_size[0],
            image_height=image_size[1], 
            cell_width=cell_size[0],
            cell_height=cell_size[1]
        )
        
        generator = GridTemplateGenerator(dimensions=dimensions)
        return generator.generate_template(output_path, categories, include_guides)
        
    except Exception:
        return False


def create_standard_template(output_path: Union[str, Path]) -> bool:
    """
    Create a standard 600×600 grid template with default settings
    
    Args:
        output_path: Path where template should be saved
        
    Returns:
        bool: True if successful, False otherwise
    """
    return generate_grid_template(output_path)


def get_template_info(dimensions: Optional[GridTemplateDimensions] = None) -> Dict[str, Any]:
    """
    Get information about template configuration
    
    Args:
        dimensions: Template dimensions (default: standard dimensions)
        
    Returns:
        Dict containing template information
    """
    dimensions = dimensions or GridTemplateDimensions()
    
    return {
        "image_size": (dimensions.image_width, dimensions.image_height),
        "cell_size": (dimensions.cell_width, dimensions.cell_height),
        "grid_dimensions": (3, 3),
        "total_cells": 9,
        "categories": GridTemplateGenerator.DEFAULT_CATEGORIES.copy()
    }


def validate_template_config(image_size: Tuple[int, int], 
                           cell_size: Tuple[int, int]) -> Tuple[bool, List[str]]:
    """
    Validate template configuration parameters
    
    Args:
        image_size: (width, height) of template image
        cell_size: (width, height) of each cell
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Validate positive dimensions
    if image_size[0] <= 0 or image_size[1] <= 0:
        errors.append("Image dimensions must be positive")
    
    if cell_size[0] <= 0 or cell_size[1] <= 0:
        errors.append("Cell dimensions must be positive")
    
    # Validate 3×3 grid consistency
    if image_size[0] != cell_size[0] * 3:
        errors.append(f"Image width {image_size[0]} must equal cell_width * 3 ({cell_size[0] * 3})")
    
    if image_size[1] != cell_size[1] * 3:
        errors.append(f"Image height {image_size[1]} must equal cell_height * 3 ({cell_size[1] * 3})")
    
    # Validate reasonable sizes
    if image_size[0] > 5000 or image_size[1] > 5000:
        errors.append("Image dimensions should not exceed 5000×5000 pixels")
    
    if cell_size[0] < 50 or cell_size[1] < 50:
        errors.append("Cell dimensions should be at least 50×50 pixels")
    
    return len(errors) == 0, errors 