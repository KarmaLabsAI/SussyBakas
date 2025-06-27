"""
Test suite for GenConfig JSON Schema Validator

Tests comprehensive schema validation, error reporting, and GenConfig-specific
business rules for the schema_validator module.
"""

import os
import tempfile
import shutil
from pathlib import Path
import sys
import json

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config.schema_validator import (
    validate_config_schema,
    GenConfigSchema,
    SchemaValidationError,
    create_sample_config
)
from utils.file_utils import safe_write_json, create_temp_file, cleanup_temp_file


class TestSchemaValidator:
    """Test cases for JSON Schema Validator"""
    
    def setup_method(self):
        """Set up temporary directory for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_root = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up temporary directory after each test"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_config(self, config_data: dict, filename: str = "test_config.json") -> Path:
        """Helper to create a test config file"""
        config_path = self.test_root / filename
        safe_write_json(config_path, config_data)
        return config_path
    
    def get_base_valid_config(self) -> dict:
        """Helper to get a valid base configuration"""
        return {
            "collection": {
                "name": "Test Collection",
                "description": "A test collection",
                "size": 1000,
                "symbol": "TEST",
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
    
    # Basic Schema Validation Tests
    
    def test_valid_config_passes(self):
        """Test that a valid configuration passes validation"""
        config = self.get_base_valid_config()
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is True
        assert errors == []
    
    def test_missing_required_root_property(self):
        """Test validation fails when required root properties are missing"""
        config = self.get_base_valid_config()
        del config["collection"]  # Remove required property
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("Missing required property 'collection'" in error for error in errors)
    
    def test_invalid_json_file(self):
        """Test validation handles invalid JSON gracefully"""
        invalid_json_path = self.test_root / "invalid.json"
        with open(invalid_json_path, 'w') as f:
            f.write("{ invalid json }")
        
        is_valid, errors = validate_config_schema(str(invalid_json_path))
        assert is_valid is False
        assert any("Invalid JSON" in error for error in errors)
    
    def test_nonexistent_file(self):
        """Test validation handles non-existent files gracefully"""
        nonexistent_path = self.test_root / "nonexistent.json"
        
        is_valid, errors = validate_config_schema(str(nonexistent_path))
        assert is_valid is False
        assert any("File does not exist" in error for error in errors)
    
    # Collection Section Tests
    
    def test_collection_missing_required_fields(self):
        """Test validation fails when collection fields are missing"""
        config = self.get_base_valid_config()
        del config["collection"]["name"]
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("collection: Missing required property 'name'" in error for error in errors)
    
    def test_collection_invalid_symbol_pattern(self):
        """Test validation fails for invalid symbol patterns"""
        config = self.get_base_valid_config()
        config["collection"]["symbol"] = "invalid-symbol"  # Contains hyphen
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("symbol: String does not match required pattern" in error for error in errors)
    
    def test_collection_invalid_url_pattern(self):
        """Test validation fails for invalid URL patterns"""
        config = self.get_base_valid_config()
        config["collection"]["external_url"] = "invalid-url"
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("external_url: String does not match required pattern" in error for error in errors)
    
    def test_collection_size_limits(self):
        """Test validation enforces collection size limits"""
        config = self.get_base_valid_config()
        config["collection"]["size"] = 0  # Below minimum
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("size: Value too small" in error for error in errors)
        
        # Test upper limit
        config["collection"]["size"] = 2000000  # Above maximum
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("size: Value too large" in error for error in errors)
    
    # Generation Section Tests
    
    def test_generation_invalid_image_format(self):
        """Test validation fails for invalid image formats"""
        config = self.get_base_valid_config()
        config["generation"]["image_format"] = "JPEG"
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("image_format: Value must be one of ['PNG']" in error for error in errors)
    
    def test_generation_grid_must_be_3x3(self):
        """Test validation enforces 3x3 grid requirement"""
        config = self.get_base_valid_config()
        config["generation"]["grid"]["rows"] = 4
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("rows: Value must be one of [3]" in error for error in errors)
    
    def test_generation_invalid_background_color(self):
        """Test validation fails for invalid background color format"""
        config = self.get_base_valid_config()
        config["generation"]["background_color"] = "red"  # Not hex format
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("background_color: String does not match required pattern" in error for error in errors)
    
    # Traits Section Tests
    
    def test_traits_invalid_position_pattern(self):
        """Test validation fails for invalid trait position patterns"""
        config = self.get_base_valid_config()
        config["traits"]["invalid-position"] = config["traits"]["position-1-background"]
        del config["traits"]["position-1-background"]
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("Property name does not match required pattern" in error for error in errors)
    
    def test_traits_invalid_filename_pattern(self):
        """Test validation fails for invalid trait filename patterns"""
        config = self.get_base_valid_config()
        config["traits"]["position-1-background"]["variants"][0]["filename"] = "invalid.jpg"
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("filename: String does not match required pattern" in error for error in errors)
    
    def test_traits_invalid_rarity_weight_range(self):
        """Test validation fails for invalid rarity weight ranges"""
        config = self.get_base_valid_config()
        config["traits"]["position-1-background"]["variants"][0]["rarity_weight"] = 0
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("rarity_weight: Value too small" in error for error in errors)
    
    def test_traits_empty_variants_array(self):
        """Test validation fails for empty variants array"""
        config = self.get_base_valid_config()
        config["traits"]["position-1-background"]["variants"] = []
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("variants: Array too short" in error for error in errors)
    
    # Rarity Section Tests
    
    def test_rarity_invalid_calculation_method(self):
        """Test validation fails for invalid calculation methods"""
        config = self.get_base_valid_config()
        config["rarity"]["calculation_method"] = "invalid_method"
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("calculation_method: Value must be one of ['weighted_random']" in error for error in errors)
    
    def test_rarity_missing_tier(self):
        """Test validation fails when rarity tiers are missing"""
        config = self.get_base_valid_config()
        del config["rarity"]["rarity_tiers"]["common"]
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("Missing required property 'common'" in error for error in errors)
    
    # GenConfig-Specific Business Rules Tests
    
    def test_image_dimensions_must_match_grid(self):
        """Test validation enforces image dimensions matching grid cell sizes"""
        config = self.get_base_valid_config()
        config["generation"]["image_size"]["width"] = 500  # Should be 600 (200*3)
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("Expected 600 (3 * cell_width), got 500" in error for error in errors)
    
    def test_grid_position_uniqueness(self):
        """Test validation enforces unique grid positions"""
        config = self.get_base_valid_config()
        # Add another trait with the same grid position
        config["traits"]["position-2-base"] = {
            "name": "Base",
            "required": True,
            "grid_position": {
                "row": 0,
                "column": 0  # Same as position-1-background
            },
            "variants": [
                {
                    "name": "Test Base",
                    "filename": "trait-test-base-001.png",
                    "rarity_weight": 100
                }
            ]
        }
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("Duplicate grid position (0, 0)" in error for error in errors)
    
    def test_position_number_coordinate_mismatch(self):
        """Test validation catches position number and coordinate mismatches"""
        config = self.get_base_valid_config()
        # Position 1 should be (0,0) but we'll put it at (1,1)
        config["traits"]["position-1-background"]["grid_position"]["row"] = 1
        config["traits"]["position-1-background"]["grid_position"]["column"] = 1
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("Position number 1 does not match coordinates (1, 1)" in error for error in errors)
    
    def test_rarity_tier_range_validation(self):
        """Test validation catches invalid rarity tier ranges"""
        config = self.get_base_valid_config()
        # Make min_weight greater than max_weight
        config["rarity"]["rarity_tiers"]["common"]["min_weight"] = 100
        config["rarity"]["rarity_tiers"]["common"]["max_weight"] = 50
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("min_weight (100) cannot be greater than max_weight (50)" in error for error in errors)
    
    def test_require_all_positions_validation(self):
        """Test validation enforces all 9 positions when required"""
        config = self.get_base_valid_config()
        config["validation"]["require_all_positions"] = True
        # Only has position-1, missing positions 2-9
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("Missing required positions: [2, 3, 4, 5, 6, 7, 8, 9]" in error for error in errors)
    
    # Type Validation Tests
    
    def test_string_type_validation(self):
        """Test validation enforces string types"""
        config = self.get_base_valid_config()
        config["collection"]["name"] = 123  # Should be string
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("Expected string, got int" in error for error in errors)
    
    def test_integer_type_validation(self):
        """Test validation enforces integer types"""
        config = self.get_base_valid_config()
        config["collection"]["size"] = "1000"  # Should be integer
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("Expected integer, got str" in error for error in errors)
    
    def test_boolean_type_validation(self):
        """Test validation enforces boolean types"""
        config = self.get_base_valid_config()
        config["generation"]["allow_duplicates"] = "false"  # Should be boolean
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("Expected boolean, got str" in error for error in errors)
    
    def test_array_type_validation(self):
        """Test validation enforces array types"""
        config = self.get_base_valid_config()
        config["traits"]["position-1-background"]["variants"] = "not an array"
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("Expected array, got str" in error for error in errors)
    
    # Edge Cases Tests
    
    def test_additional_properties_not_allowed(self):
        """Test validation rejects additional properties where not allowed"""
        config = self.get_base_valid_config()
        config["collection"]["extra_field"] = "not allowed"
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("Additional property not allowed" in error for error in errors)
    
    def test_string_length_constraints(self):
        """Test validation enforces string length constraints"""
        config = self.get_base_valid_config()
        config["collection"]["name"] = ""  # Too short
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("String too short" in error for error in errors)
        
        # Test too long
        config["collection"]["name"] = "x" * 101  # Too long
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is False
        assert any("String too long" in error for error in errors)
    
    def test_complex_valid_configuration(self):
        """Test validation with a complex but valid configuration"""
        config = self.get_base_valid_config()
        
        # Add all 9 positions
        for i in range(2, 10):
            row = (i - 1) // 3
            col = (i - 1) % 3
            config["traits"][f"position-{i}-trait{i}"] = {
                "name": f"Trait {i}",
                "required": True,
                "grid_position": {
                    "row": row,
                    "column": col
                },
                "variants": [
                    {
                        "name": f"Variant {i}A",
                        "filename": f"trait-variant-{i}a-001.png",
                        "rarity_weight": 100,
                        "color_code": "#FF0000"
                    },
                    {
                        "name": f"Variant {i}B",
                        "filename": f"trait-variant-{i}b-002.png",
                        "rarity_weight": 50,
                        "color_code": "#00FF00"
                    }
                ]
            }
        
        config["validation"]["require_all_positions"] = True
        config_path = self.create_test_config(config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is True
        assert errors == []


# Helper functions for schema testing
def test_schema_definition():
    """Test that the schema definition is properly structured"""
    schema = GenConfigSchema.get_schema()
    
    assert schema["type"] == "object"
    assert "required" in schema
    assert "properties" in schema
    assert len(schema["required"]) == 5  # collection, generation, traits, rarity, validation
    
    # Check main sections exist
    required_sections = ["collection", "generation", "traits", "rarity", "validation"]
    for section in required_sections:
        assert section in schema["properties"]


def test_create_sample_config():
    """Test that create_sample_config produces a valid configuration"""
    sample_config = create_sample_config()
    
    # Create temporary file for testing
    temp_path, fd = create_temp_file(suffix='.json', prefix='sample_test_')
    try:
        safe_write_json(temp_path, sample_config)
        is_valid, errors = validate_config_schema(temp_path)
        
        assert is_valid is True
        assert errors == []
    finally:
        cleanup_temp_file(temp_path, fd)


# Integration tests
def test_integration_schema_validation():
    """Integration test for complete schema validation workflow"""
    with tempfile.TemporaryDirectory() as temp_dir:
        print("🧪 Testing GenConfig JSON Schema Validator...")
        
        # Test 1: Valid configuration
        print("📋 Testing valid configuration...")
        sample_config = create_sample_config()
        config_path = Path(temp_dir) / "valid_config.json"
        safe_write_json(config_path, sample_config)
        
        is_valid, errors = validate_config_schema(str(config_path))
        assert is_valid is True
        assert errors == []
        print("✅ Valid configuration passed validation")
        
        # Test 2: Invalid configuration - missing required field
        print("❌ Testing invalid configuration...")
        invalid_config = create_sample_config()  # Get fresh copy
        del invalid_config["collection"]["name"]
        
        invalid_path = Path(temp_dir) / "invalid_config.json"
        safe_write_json(invalid_path, invalid_config)
        
        is_valid, errors = validate_config_schema(str(invalid_path))
        assert is_valid is False
        assert len(errors) > 0
        assert any("Missing required property 'name'" in error for error in errors)
        print("✅ Invalid configuration correctly rejected")
        
        # Test 3: Business rule validation
        print("🔧 Testing business rules...")
        business_rule_config = create_sample_config()  # Get fresh copy
        business_rule_config["generation"]["image_size"]["width"] = 500  # Should be 600
        
        business_path = Path(temp_dir) / "business_rule_config.json"
        safe_write_json(business_path, business_rule_config)
        
        is_valid, errors = validate_config_schema(str(business_path))
        assert is_valid is False
        assert any("Expected 600 (3 * cell_width), got 500" in error for error in errors)
        print("✅ Business rule validation working correctly")
        
        # Test 4: Complex valid configuration
        print("🏗️ Testing complex configuration...")
        complex_config = create_sample_config()  # Get fresh copy
        
        # Add multiple traits for position-1
        complex_config["traits"]["position-1-background"]["variants"].append({
            "name": "Blue Background",
            "filename": "trait-blue-bg-002.png",
            "rarity_weight": 50,
            "color_code": "#0000FF"
        })
        
        complex_path = Path(temp_dir) / "complex_config.json"
        safe_write_json(complex_path, complex_config)
        
        is_valid, errors = validate_config_schema(str(complex_path))
        if not is_valid:
            print(f"Complex config validation failed with errors: {errors}")
        assert is_valid is True
        assert errors == []
        print("✅ Complex configuration validation successful")
        
        print("\n🎉 All schema validation integration tests passed!")
        return True


if __name__ == "__main__":
    try:
        test_integration_schema_validation()
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1) 