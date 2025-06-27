"""
GenConfig JSON Schema Validator

This module validates configuration files against the GenConfig Phase 1 schema,
ensuring proper structure, data types, and required fields are present.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Union, Optional
import re
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.file_utils import safe_read_json, ValidationError, FileOperationError


class SchemaValidationError(Exception):
    """Custom exception for schema validation errors"""
    pass


class GenConfigSchema:
    """
    GenConfig Phase 1 schema definition and validation logic
    """
    
    @staticmethod
    def get_schema() -> Dict[str, Any]:
        """
        Returns the complete GenConfig Phase 1 JSON schema definition
        """
        return {
            "type": "object",
            "required": ["collection", "generation", "traits", "rarity", "validation"],
            "properties": {
                "collection": {
                    "type": "object",
                    "required": ["name", "description", "size", "symbol", "external_url"],
                    "properties": {
                        "name": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 100,
                            "description": "Collection name"
                        },
                        "description": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 1000,
                            "description": "Collection description"
                        },
                        "size": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 1000000,
                            "description": "Number of NFTs in collection"
                        },
                        "symbol": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 20,
                            "pattern": "^[A-Z0-9_]+$",
                            "description": "Collection symbol/ticker"
                        },
                        "external_url": {
                            "type": "string",
                            "pattern": "^https?://.*",
                            "description": "External URL for collection"
                        }
                    },
                    "additionalProperties": False
                },
                "generation": {
                    "type": "object",
                    "required": ["image_format", "image_size", "grid", "background_color", "allow_duplicates"],
                    "properties": {
                        "image_format": {
                            "type": "string",
                            "enum": ["PNG"],
                            "description": "Output image format"
                        },
                        "image_size": {
                            "type": "object",
                            "required": ["width", "height"],
                            "properties": {
                                "width": {
                                    "type": "integer",
                                    "minimum": 100,
                                    "maximum": 10000,
                                    "description": "Image width in pixels"
                                },
                                "height": {
                                    "type": "integer",
                                    "minimum": 100,
                                    "maximum": 10000,
                                    "description": "Image height in pixels"
                                }
                            },
                            "additionalProperties": False
                        },
                        "grid": {
                            "type": "object",
                            "required": ["rows", "columns", "cell_size"],
                            "properties": {
                                "rows": {
                                    "type": "integer",
                                    "enum": [3],
                                    "description": "Number of grid rows (must be 3)"
                                },
                                "columns": {
                                    "type": "integer",
                                    "enum": [3],
                                    "description": "Number of grid columns (must be 3)"
                                },
                                "cell_size": {
                                    "type": "object",
                                    "required": ["width", "height"],
                                    "properties": {
                                        "width": {
                                            "type": "integer",
                                            "minimum": 50,
                                            "maximum": 5000,
                                            "description": "Cell width in pixels"
                                        },
                                        "height": {
                                            "type": "integer",
                                            "minimum": 50,
                                            "maximum": 5000,
                                            "description": "Cell height in pixels"
                                        }
                                    },
                                    "additionalProperties": False
                                }
                            },
                            "additionalProperties": False
                        },
                        "background_color": {
                            "type": "string",
                            "pattern": "^#[0-9A-Fa-f]{6}$",
                            "description": "Background color as hex code"
                        },
                        "allow_duplicates": {
                            "type": "boolean",
                            "description": "Whether to allow duplicate NFTs"
                        }
                    },
                    "additionalProperties": False
                },
                "traits": {
                    "type": "object",
                    "minProperties": 1,
                    "maxProperties": 9,
                    "patternProperties": {
                        "^position-[1-9]-.+$": {
                            "type": "object",
                            "required": ["name", "required", "grid_position", "variants"],
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "minLength": 1,
                                    "maxLength": 50,
                                    "description": "Trait category name"
                                },
                                "required": {
                                    "type": "boolean",
                                    "description": "Whether this trait is required"
                                },
                                "grid_position": {
                                    "type": "object",
                                    "required": ["row", "column"],
                                    "properties": {
                                        "row": {
                                            "type": "integer",
                                            "minimum": 0,
                                            "maximum": 2,
                                            "description": "Grid row (0-2)"
                                        },
                                        "column": {
                                            "type": "integer",
                                            "minimum": 0,
                                            "maximum": 2,
                                            "description": "Grid column (0-2)"
                                        }
                                    },
                                    "additionalProperties": False
                                },
                                "variants": {
                                    "type": "array",
                                    "minItems": 1,
                                    "maxItems": 1000,
                                    "items": {
                                        "type": "object",
                                        "required": ["name", "filename", "rarity_weight"],
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                                "minLength": 1,
                                                "maxLength": 100,
                                                "description": "Trait variant name"
                                            },
                                            "filename": {
                                                "type": "string",
                                                "pattern": "^trait-.+\\.png$",
                                                "description": "Trait image filename"
                                            },
                                            "rarity_weight": {
                                                "type": "integer",
                                                "minimum": 1,
                                                "maximum": 10000,
                                                "description": "Rarity weight for selection"
                                            },
                                            "color_code": {
                                                "type": "string",
                                                "pattern": "^#[0-9A-Fa-f]{6}$",
                                                "description": "Primary color code"
                                            }
                                        },
                                        "additionalProperties": False
                                    }
                                }
                            },
                            "additionalProperties": False
                        }
                    },
                    "additionalProperties": False
                },
                "rarity": {
                    "type": "object",
                    "required": ["calculation_method", "distribution_validation", "rarity_tiers"],
                    "properties": {
                        "calculation_method": {
                            "type": "string",
                            "enum": ["weighted_random"],
                            "description": "Rarity calculation method"
                        },
                        "distribution_validation": {
                            "type": "boolean",
                            "description": "Whether to validate distribution"
                        },
                        "rarity_tiers": {
                            "type": "object",
                            "required": ["common", "uncommon", "rare", "epic", "legendary"],
                            "properties": {
                                "common": {
                                    "type": "object",
                                    "required": ["min_weight", "max_weight"],
                                    "properties": {
                                        "min_weight": {"type": "integer", "minimum": 1},
                                        "max_weight": {"type": "integer", "minimum": 1}
                                    },
                                    "additionalProperties": False
                                },
                                "uncommon": {
                                    "type": "object",
                                    "required": ["min_weight", "max_weight"],
                                    "properties": {
                                        "min_weight": {"type": "integer", "minimum": 1},
                                        "max_weight": {"type": "integer", "minimum": 1}
                                    },
                                    "additionalProperties": False
                                },
                                "rare": {
                                    "type": "object",
                                    "required": ["min_weight", "max_weight"],
                                    "properties": {
                                        "min_weight": {"type": "integer", "minimum": 1},
                                        "max_weight": {"type": "integer", "minimum": 1}
                                    },
                                    "additionalProperties": False
                                },
                                "epic": {
                                    "type": "object",
                                    "required": ["min_weight", "max_weight"],
                                    "properties": {
                                        "min_weight": {"type": "integer", "minimum": 1},
                                        "max_weight": {"type": "integer", "minimum": 1}
                                    },
                                    "additionalProperties": False
                                },
                                "legendary": {
                                    "type": "object",
                                    "required": ["min_weight", "max_weight"],
                                    "properties": {
                                        "min_weight": {"type": "integer", "minimum": 1},
                                        "max_weight": {"type": "integer", "minimum": 1}
                                    },
                                    "additionalProperties": False
                                }
                            },
                            "additionalProperties": False
                        }
                    },
                    "additionalProperties": False
                },
                "validation": {
                    "type": "object",
                    "required": ["enforce_grid_positions", "require_all_positions", "check_file_integrity", "validate_image_dimensions"],
                    "properties": {
                        "enforce_grid_positions": {
                            "type": "boolean",
                            "description": "Whether to enforce grid position uniqueness"
                        },
                        "require_all_positions": {
                            "type": "boolean",
                            "description": "Whether all 9 positions are required"
                        },
                        "check_file_integrity": {
                            "type": "boolean",
                            "description": "Whether to check file integrity"
                        },
                        "validate_image_dimensions": {
                            "type": "boolean",
                            "description": "Whether to validate image dimensions"
                        }
                    },
                    "additionalProperties": False
                }
            },
            "additionalProperties": False
        }


def validate_config_schema(config_path: str) -> Tuple[bool, List[str]]:
    """
    Validates configuration against GenConfig Phase 1 schema.
    
    Args:
        config_path: Path to the config.json file
        
    Returns:
        Tuple of (is_valid: bool, error_messages: List[str])
    """
    errors = []
    
    try:
        # Load and parse JSON
        config_data = safe_read_json(config_path)
        
        # Validate against schema
        schema = GenConfigSchema.get_schema()
        is_valid = _validate_object(config_data, schema, "config", errors)
        
        # Additional GenConfig-specific validations
        if is_valid:
            _validate_genconfig_rules(config_data, errors)
        
        return len(errors) == 0, errors
        
    except (FileOperationError, ValidationError) as e:
        errors.append(f"File error: {e}")
        return False, errors
    except Exception as e:
        errors.append(f"Unexpected error during validation: {e}")
        return False, errors


def _validate_object(data: Any, schema: Dict[str, Any], path: str, errors: List[str]) -> bool:
    """
    Validate a data object against a schema definition.
    
    Args:
        data: Data to validate
        schema: Schema definition
        path: Current path in the data structure
        errors: List to collect error messages
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(data, dict):
        errors.append(f"{path}: Expected object, got {type(data).__name__}")
        return False
    
    # Check required properties
    required = schema.get("required", [])
    for prop in required:
        if prop not in data:
            errors.append(f"{path}: Missing required property '{prop}'")
    
    # Check pattern properties first (for traits section)
    pattern_properties = schema.get("patternProperties", {})
    matched_pattern_props = set()
    
    if pattern_properties:
        for prop, value in data.items():
            prop_path = f"{path}.{prop}" if path != "config" else prop
            matched = False
            
            for pattern, pattern_schema in pattern_properties.items():
                if re.match(pattern, prop):
                    matched = True
                    matched_pattern_props.add(prop)
                    _validate_property(value, pattern_schema, prop_path, errors)
                    break
            
            if not matched and pattern_properties:
                errors.append(f"{prop_path}: Property name does not match required pattern")
    
    # Check regular properties
    properties = schema.get("properties", {})
    for prop, value in data.items():
        prop_path = f"{path}.{prop}" if path != "config" else prop
        
        if prop in properties:
            prop_schema = properties[prop]
            _validate_property(value, prop_schema, prop_path, errors)
        elif prop not in matched_pattern_props and not schema.get("additionalProperties", True):
            errors.append(f"{prop_path}: Additional property not allowed")
    
    # Check min/max properties
    if "minProperties" in schema and len(data) < schema["minProperties"]:
        errors.append(f"{path}: Too few properties (minimum {schema['minProperties']})")
    
    if "maxProperties" in schema and len(data) > schema["maxProperties"]:
        errors.append(f"{path}: Too many properties (maximum {schema['maxProperties']})")
    
    return len([e for e in errors if e.startswith(path)]) == 0


def _validate_property(data: Any, schema: Dict[str, Any], path: str, errors: List[str]) -> bool:
    """
    Validate a single property against its schema.
    
    Args:
        data: Property value to validate
        schema: Property schema definition
        path: Current path in the data structure
        errors: List to collect error messages
        
    Returns:
        bool: True if valid, False otherwise
    """
    prop_type = schema.get("type")
    
    # Type validation
    if prop_type == "string":
        if not isinstance(data, str):
            errors.append(f"{path}: Expected string, got {type(data).__name__}")
            return False
        return _validate_string(data, schema, path, errors)
    
    elif prop_type == "integer":
        if not isinstance(data, int):
            errors.append(f"{path}: Expected integer, got {type(data).__name__}")
            return False
        return _validate_integer(data, schema, path, errors)
    
    elif prop_type == "boolean":
        if not isinstance(data, bool):
            errors.append(f"{path}: Expected boolean, got {type(data).__name__}")
            return False
        return True
    
    elif prop_type == "object":
        return _validate_object(data, schema, path, errors)
    
    elif prop_type == "array":
        if not isinstance(data, list):
            errors.append(f"{path}: Expected array, got {type(data).__name__}")
            return False
        return _validate_array(data, schema, path, errors)
    
    else:
        errors.append(f"{path}: Unknown type '{prop_type}' in schema")
        return False


def _validate_string(data: str, schema: Dict[str, Any], path: str, errors: List[str]) -> bool:
    """Validate string-specific constraints"""
    # Length constraints
    if "minLength" in schema and len(data) < schema["minLength"]:
        errors.append(f"{path}: String too short (minimum {schema['minLength']} characters)")
    
    if "maxLength" in schema and len(data) > schema["maxLength"]:
        errors.append(f"{path}: String too long (maximum {schema['maxLength']} characters)")
    
    # Pattern validation
    if "pattern" in schema:
        if not re.match(schema["pattern"], data):
            errors.append(f"{path}: String does not match required pattern")
    
    # Enum validation
    if "enum" in schema:
        if data not in schema["enum"]:
            errors.append(f"{path}: Value must be one of {schema['enum']}")
    
    return True


def _validate_integer(data: int, schema: Dict[str, Any], path: str, errors: List[str]) -> bool:
    """Validate integer-specific constraints"""
    # Range constraints
    if "minimum" in schema and data < schema["minimum"]:
        errors.append(f"{path}: Value too small (minimum {schema['minimum']})")
    
    if "maximum" in schema and data > schema["maximum"]:
        errors.append(f"{path}: Value too large (maximum {schema['maximum']})")
    
    # Enum validation
    if "enum" in schema:
        if data not in schema["enum"]:
            errors.append(f"{path}: Value must be one of {schema['enum']}")
    
    return True


def _validate_array(data: List[Any], schema: Dict[str, Any], path: str, errors: List[str]) -> bool:
    """Validate array-specific constraints"""
    # Length constraints
    if "minItems" in schema and len(data) < schema["minItems"]:
        errors.append(f"{path}: Array too short (minimum {schema['minItems']} items)")
    
    if "maxItems" in schema and len(data) > schema["maxItems"]:
        errors.append(f"{path}: Array too long (maximum {schema['maxItems']} items)")
    
    # Item validation
    if "items" in schema:
        item_schema = schema["items"]
        for i, item in enumerate(data):
            item_path = f"{path}[{i}]"
            _validate_property(item, item_schema, item_path, errors)
    
    return True


def _validate_genconfig_rules(config: Dict[str, Any], errors: List[str]) -> None:
    """
    Validate GenConfig-specific business rules.
    
    Args:
        config: Configuration data
        errors: List to collect error messages
    """
    # Validate grid dimensions match image dimensions
    try:
        image_width = config["generation"]["image_size"]["width"]
        image_height = config["generation"]["image_size"]["height"]
        cell_width = config["generation"]["grid"]["cell_size"]["width"]
        cell_height = config["generation"]["grid"]["cell_size"]["height"]
        
        expected_width = cell_width * 3
        expected_height = cell_height * 3
        
        if image_width != expected_width:
            errors.append(f"generation.image_size.width: Expected {expected_width} (3 * cell_width), got {image_width}")
        
        if image_height != expected_height:
            errors.append(f"generation.image_size.height: Expected {expected_height} (3 * cell_height), got {image_height}")
    
    except KeyError as e:
        errors.append(f"Missing required field for dimension validation: {e}")
    
    # Validate grid positions are unique and complete
    try:
        traits = config.get("traits", {})
        used_positions = set()
        position_keys = set()
        
        for trait_key, trait_data in traits.items():
            # Extract position number from trait key
            position_match = re.match(r"position-(\d+)-", trait_key)
            if position_match:
                position_num = int(position_match.group(1))
                if position_num < 1 or position_num > 9:
                    errors.append(f"traits.{trait_key}: Invalid position number {position_num} (must be 1-9)")
                else:
                    position_keys.add(position_num)
            
            # Check grid position coordinates
            if "grid_position" in trait_data:
                row = trait_data["grid_position"]["row"]
                col = trait_data["grid_position"]["column"]
                position_tuple = (row, col)
                
                if position_tuple in used_positions:
                    errors.append(f"traits.{trait_key}.grid_position: Duplicate grid position ({row}, {col})")
                else:
                    used_positions.add(position_tuple)
                
                # Validate position number matches coordinates
                if position_match:
                    expected_position = row * 3 + col + 1
                    actual_position = int(position_match.group(1))
                    if expected_position != actual_position:
                        errors.append(f"traits.{trait_key}: Position number {actual_position} does not match coordinates ({row}, {col})")
        
        # Check if all positions are covered (if required)
        if config.get("validation", {}).get("require_all_positions", False):
            missing_positions = set(range(1, 10)) - position_keys
            if missing_positions:
                errors.append(f"traits: Missing required positions: {sorted(missing_positions)}")
    
    except KeyError as e:
        errors.append(f"Error validating grid positions: {e}")
    
    # Validate rarity tier ranges don't overlap
    try:
        rarity_tiers = config.get("rarity", {}).get("rarity_tiers", {})
        tier_ranges = []
        
        for tier_name, tier_data in rarity_tiers.items():
            min_weight = tier_data["min_weight"]
            max_weight = tier_data["max_weight"]
            
            if min_weight > max_weight:
                errors.append(f"rarity.rarity_tiers.{tier_name}: min_weight ({min_weight}) cannot be greater than max_weight ({max_weight})")
            
            tier_ranges.append((tier_name, min_weight, max_weight))
        
        # Check for overlapping ranges
        tier_ranges.sort(key=lambda x: x[1])  # Sort by min_weight
        for i in range(len(tier_ranges) - 1):
            current_tier, current_min, current_max = tier_ranges[i]
            next_tier, next_min, next_max = tier_ranges[i + 1]
            
            if current_max >= next_min:
                errors.append(f"rarity.rarity_tiers: Overlapping weight ranges between {current_tier} and {next_tier}")
    
    except KeyError as e:
        errors.append(f"Error validating rarity tiers: {e}")


def create_sample_config() -> Dict[str, Any]:
    """
    Create a sample configuration for testing purposes.
    
    Returns:
        Dict[str, Any]: Valid sample configuration
    """
    return {
        "collection": {
            "name": "Sample NFT Collection",
            "description": "A sample generative 3x3 grid NFT collection",
            "size": 1000,
            "symbol": "SAMPLE",
            "external_url": "https://example.com"
        },
        "generation": {
            "image_format": "PNG",
            "image_size": {
                "width": 600,
                "height": 600
            },
            "grid": {
                "rows": 3,
                "columns": 3,
                "cell_size": {
                    "width": 200,
                    "height": 200
                }
            },
            "background_color": "#FFFFFF",
            "allow_duplicates": False
        },
        "traits": {
            "position-1-background": {
                "name": "Background",
                "required": True,
                "grid_position": {
                    "row": 0,
                    "column": 0
                },
                "variants": [
                    {
                        "name": "Red Background",
                        "filename": "trait-red-bg-001.png",
                        "rarity_weight": 100,
                        "color_code": "#FF0000"
                    }
                ]
            }
        },
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
            "require_all_positions": False,
            "check_file_integrity": True,
            "validate_image_dimensions": True
        }
    }


if __name__ == "__main__":
    # Example usage and testing
    print("GenConfig JSON Schema Validator")
    print("Testing schema validation...")
    
    try:
        # Create a sample config for testing
        sample_config = create_sample_config()
        
        # Test with valid config
        from utils.file_utils import safe_write_json, create_temp_file, cleanup_temp_file
        
        temp_path, fd = create_temp_file(suffix='.json', prefix='test_config_')
        safe_write_json(temp_path, sample_config)
        
        is_valid, errors = validate_config_schema(temp_path)
        if is_valid:
            print("✅ Sample config validation passed")
        else:
            print("❌ Sample config validation failed:")
            for error in errors:
                print(f"  - {error}")
        
        # Test with invalid config
        invalid_config = sample_config.copy()
        del invalid_config["collection"]["name"]  # Remove required field
        
        temp_path2, fd2 = create_temp_file(suffix='.json', prefix='test_invalid_')
        safe_write_json(temp_path2, invalid_config)
        
        is_valid2, errors2 = validate_config_schema(temp_path2)
        if not is_valid2:
            print("✅ Invalid config correctly rejected")
            print(f"  Errors detected: {len(errors2)}")
        else:
            print("❌ Invalid config incorrectly accepted")
        
        # Cleanup
        cleanup_temp_file(temp_path, fd)
        cleanup_temp_file(temp_path2, fd2)
        
        print("\n🎉 Schema validator tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 