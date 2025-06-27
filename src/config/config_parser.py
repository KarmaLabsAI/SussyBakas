"""
GenConfig Configuration Parser

This module loads and parses configuration files into structured Python objects
that can be used throughout the GenConfig system for NFT generation.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, NamedTuple
from dataclasses import dataclass
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.file_utils import safe_read_json, ValidationError, FileOperationError
from config.schema_validator import validate_config_schema, SchemaValidationError


class ConfigParseError(Exception):
    """Custom exception for configuration parsing errors"""
    pass


@dataclass
class CollectionConfig:
    """Collection configuration data"""
    name: str
    description: str
    size: int
    symbol: str
    external_url: str


@dataclass
class ImageSize:
    """Image size configuration"""
    width: int
    height: int


@dataclass
class CellSize:
    """Grid cell size configuration"""
    width: int
    height: int


@dataclass
class GridConfig:
    """Grid configuration data"""
    rows: int
    columns: int
    cell_size: CellSize


@dataclass
class GenerationConfig:
    """Generation configuration data"""
    image_format: str
    image_size: ImageSize
    grid: GridConfig
    background_color: str
    allow_duplicates: bool


@dataclass
class GridPosition:
    """Grid position coordinates"""
    row: int
    column: int


@dataclass
class TraitVariant:
    """Individual trait variant data"""
    name: str
    filename: str
    rarity_weight: int
    color_code: Optional[str] = None
    description: Optional[str] = None


@dataclass
class TraitCategory:
    """Trait category configuration"""
    name: str
    required: bool
    grid_position: GridPosition
    variants: List[TraitVariant]


@dataclass
class RarityTier:
    """Rarity tier configuration"""
    min_weight: int
    max_weight: int


@dataclass
class RarityConfig:
    """Rarity configuration data"""
    calculation_method: str
    distribution_validation: bool
    rarity_tiers: Dict[str, RarityTier]


@dataclass
class ValidationConfig:
    """Validation configuration data"""
    enforce_grid_positions: bool
    require_all_positions: bool
    check_file_integrity: bool
    validate_image_dimensions: bool


@dataclass
class GenConfig:
    """Complete GenConfig configuration object"""
    collection: CollectionConfig
    generation: GenerationConfig
    traits: Dict[str, TraitCategory]
    rarity: RarityConfig
    validation: ValidationConfig
    
    # Additional computed properties
    config_path: Optional[str] = None
    total_positions: int = 9
    
    def get_trait_by_position(self, position: int) -> Optional[TraitCategory]:
        """Get trait category by grid position number (1-9)"""
        for trait_key, trait in self.traits.items():
            # Calculate position from grid coordinates
            calculated_position = trait.grid_position.row * 3 + trait.grid_position.column + 1
            if calculated_position == position:
                return trait
        return None
    
    def get_all_positions(self) -> List[int]:
        """Get all grid positions used by traits"""
        positions = []
        for trait in self.traits.values():
            position = trait.grid_position.row * 3 + trait.grid_position.column + 1
            positions.append(position)
        return sorted(positions)
    
    def is_complete_grid(self) -> bool:
        """Check if all 9 grid positions are filled"""
        return len(set(self.get_all_positions())) == 9
    
    def get_trait_counts(self) -> Dict[str, int]:
        """Get count of variants for each trait category"""
        return {key: len(trait.variants) for key, trait in self.traits.items()}


class ConfigurationParser:
    """
    Main configuration parser class for loading and parsing GenConfig files
    """
    
    def __init__(self, validate_schema: bool = True):
        """
        Initialize configuration parser
        
        Args:
            validate_schema: Whether to validate against schema before parsing
        """
        self.validate_schema = validate_schema
    
    def parse_config_file(self, config_path: str) -> GenConfig:
        """
        Parse configuration file into structured GenConfig object
        
        Args:
            config_path: Path to configuration JSON file
            
        Returns:
            GenConfig: Parsed configuration object
            
        Raises:
            ConfigParseError: If parsing fails
            ValidationError: If file operations fail
            SchemaValidationError: If schema validation fails
        """
        try:
            # Validate schema first if enabled
            if self.validate_schema:
                is_valid, errors = validate_config_schema(config_path)
                if not is_valid:
                    error_msg = f"Configuration schema validation failed:\n" + "\n".join(errors)
                    raise SchemaValidationError(error_msg)
            
            # Load configuration data
            config_data = safe_read_json(config_path)
            
            # Parse into structured objects
            parsed_config = self._parse_config_data(config_data)
            parsed_config.config_path = str(Path(config_path).resolve())
            
            return parsed_config
            
        except (FileOperationError, ValidationError) as e:
            raise ConfigParseError(f"Failed to load configuration file: {e}")
        except SchemaValidationError as e:
            # Convert schema validation errors to config parse errors for file I/O issues
            if "File error:" in str(e):
                raise ConfigParseError(f"Configuration file error: {e}")
            else:
                raise  # Re-raise actual schema validation errors
        except Exception as e:
            raise ConfigParseError(f"Failed to parse configuration: {e}")
    
    def parse_config_data(self, config_data: Dict[str, Any]) -> GenConfig:
        """
        Parse configuration data dictionary into structured GenConfig object
        
        Args:
            config_data: Configuration data dictionary
            
        Returns:
            GenConfig: Parsed configuration object
            
        Raises:
            ConfigParseError: If parsing fails
        """
        try:
            return self._parse_config_data(config_data)
        except Exception as e:
            raise ConfigParseError(f"Failed to parse configuration data: {e}")
    
    def _parse_config_data(self, config_data: Dict[str, Any]) -> GenConfig:
        """
        Internal method to parse configuration data
        
        Args:
            config_data: Raw configuration dictionary
            
        Returns:
            GenConfig: Parsed configuration object
        """
        # Parse collection section
        collection_data = config_data["collection"]
        collection = CollectionConfig(
            name=collection_data["name"],
            description=collection_data["description"],
            size=collection_data["size"],
            symbol=collection_data["symbol"],
            external_url=collection_data["external_url"]
        )
        
        # Parse generation section
        generation_data = config_data["generation"]
        image_size = ImageSize(
            width=generation_data["image_size"]["width"],
            height=generation_data["image_size"]["height"]
        )
        cell_size = CellSize(
            width=generation_data["grid"]["cell_size"]["width"],
            height=generation_data["grid"]["cell_size"]["height"]
        )
        grid = GridConfig(
            rows=generation_data["grid"]["rows"],
            columns=generation_data["grid"]["columns"],
            cell_size=cell_size
        )
        generation = GenerationConfig(
            image_format=generation_data["image_format"],
            image_size=image_size,
            grid=grid,
            background_color=generation_data["background_color"],
            allow_duplicates=generation_data["allow_duplicates"]
        )
        
        # Parse traits section
        traits_data = config_data["traits"]
        traits = {}
        for trait_key, trait_data in traits_data.items():
            grid_position = GridPosition(
                row=trait_data["grid_position"]["row"],
                column=trait_data["grid_position"]["column"]
            )
            
            variants = []
            for variant_data in trait_data["variants"]:
                variant = TraitVariant(
                    name=variant_data["name"],
                    filename=variant_data["filename"],
                    rarity_weight=variant_data["rarity_weight"],
                    color_code=variant_data.get("color_code"),
                    description=variant_data.get("description")
                )
                variants.append(variant)
            
            trait_category = TraitCategory(
                name=trait_data["name"],
                required=trait_data["required"],
                grid_position=grid_position,
                variants=variants
            )
            traits[trait_key] = trait_category
        
        # Parse rarity section
        rarity_data = config_data["rarity"]
        rarity_tiers = {}
        for tier_name, tier_data in rarity_data["rarity_tiers"].items():
            rarity_tier = RarityTier(
                min_weight=tier_data["min_weight"],
                max_weight=tier_data["max_weight"]
            )
            rarity_tiers[tier_name] = rarity_tier
        
        rarity = RarityConfig(
            calculation_method=rarity_data["calculation_method"],
            distribution_validation=rarity_data["distribution_validation"],
            rarity_tiers=rarity_tiers
        )
        
        # Parse validation section
        validation_data = config_data["validation"]
        validation = ValidationConfig(
            enforce_grid_positions=validation_data["enforce_grid_positions"],
            require_all_positions=validation_data["require_all_positions"],
            check_file_integrity=validation_data["check_file_integrity"],
            validate_image_dimensions=validation_data["validate_image_dimensions"]
        )
        
        # Create complete configuration
        return GenConfig(
            collection=collection,
            generation=generation,
            traits=traits,
            rarity=rarity,
            validation=validation
        )


def load_config(config_path: str, validate_schema: bool = True) -> GenConfig:
    """
    Convenience function to load and parse configuration file
    
    Args:
        config_path: Path to configuration JSON file
        validate_schema: Whether to validate against schema before parsing
        
    Returns:
        GenConfig: Parsed configuration object
        
    Raises:
        ConfigParseError: If parsing fails
        ValidationError: If file operations fail
        SchemaValidationError: If schema validation fails
    """
    parser = ConfigurationParser(validate_schema=validate_schema)
    return parser.parse_config_file(config_path)


def parse_config_dict(config_data: Dict[str, Any]) -> GenConfig:
    """
    Convenience function to parse configuration dictionary
    
    Args:
        config_data: Configuration data dictionary
        
    Returns:
        GenConfig: Parsed configuration object
        
    Raises:
        ConfigParseError: If parsing fails
    """
    parser = ConfigurationParser(validate_schema=False)
    return parser.parse_config_data(config_data)


def create_config_summary(config: GenConfig) -> Dict[str, Any]:
    """
    Create a summary of the configuration for logging/debugging
    
    Args:
        config: Parsed GenConfig object
        
    Returns:
        Dict containing configuration summary
    """
    return {
        "collection_name": config.collection.name,
        "collection_size": config.collection.size,
        "image_dimensions": f"{config.generation.image_size.width}x{config.generation.image_size.height}",
        "grid_dimensions": f"{config.generation.grid.rows}x{config.generation.grid.columns}",
        "cell_size": f"{config.generation.grid.cell_size.width}x{config.generation.grid.cell_size.height}",
        "trait_categories": len(config.traits),
        "total_variants": sum(len(trait.variants) for trait in config.traits.values()),
        "positions_used": config.get_all_positions(),
        "complete_grid": config.is_complete_grid(),
        "rarity_calculation": config.rarity.calculation_method,
        "rarity_tiers": list(config.rarity.rarity_tiers.keys()),
        "validation_enabled": {
            "grid_positions": config.validation.enforce_grid_positions,
            "all_positions": config.validation.require_all_positions,
            "file_integrity": config.validation.check_file_integrity,
            "image_dimensions": config.validation.validate_image_dimensions
        }
    } 