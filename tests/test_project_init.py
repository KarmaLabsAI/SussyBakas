"""
Test suite for GenConfig Project Initialization Module

Tests the bootstrapping and validation of complete GenConfig projects with
default configuration, templates, and validation functionality.
"""

import os
import tempfile
import shutil
import json
from pathlib import Path
import sys

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from infrastructure.project_init import (
    bootstrap_genconfig_project,
    validate_project_setup,
    _create_default_config,
    _create_grid_template,
    _create_example_traits,
    _create_project_readme
)


class TestProjectInit:
    """Test cases for the Project Initialization module"""
    
    def setup_method(self):
        """Set up temporary directory for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_project_path = Path(self.temp_dir) / "test-project"
    
    def teardown_method(self):
        """Clean up temporary directory after each test"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_bootstrap_genconfig_project_success(self):
        """Test successful project bootstrapping"""
        result = bootstrap_genconfig_project(
            str(self.test_project_path),
            project_name="Test Collection",
            collection_size=100
        )
        
        assert result is True
        assert self.test_project_path.exists()
        assert self.test_project_path.is_dir()
    
    def test_bootstrap_creates_directory_structure(self):
        """Test that bootstrapping creates the correct directory structure"""
        bootstrap_genconfig_project(str(self.test_project_path), "Test Collection")
        
        # Check main directories
        expected_dirs = [
            "traits",
            "output",
            "output/images",
            "output/metadata",
            "templates",
            "tests",
            "tests/sample-traits",
            "tests/sample-composites"
        ]
        
        for directory in expected_dirs:
            dir_path = self.test_project_path / directory
            assert dir_path.exists(), f"Directory {directory} was not created"
            assert dir_path.is_dir(), f"{directory} is not a directory"
    
    def test_bootstrap_creates_trait_directories(self):
        """Test that all 9 trait position directories are created"""
        bootstrap_genconfig_project(str(self.test_project_path), "Test Collection")
        
        expected_trait_dirs = [
            "traits/position-1-background",
            "traits/position-2-base",
            "traits/position-3-accent",
            "traits/position-4-pattern",
            "traits/position-5-center",
            "traits/position-6-decoration",
            "traits/position-7-border",
            "traits/position-8-highlight",
            "traits/position-9-overlay"
        ]
        
        for directory in expected_trait_dirs:
            dir_path = self.test_project_path / directory
            assert dir_path.exists(), f"Trait directory {directory} was not created"
            assert dir_path.is_dir(), f"{directory} is not a directory"
    
    def test_bootstrap_creates_config_file(self):
        """Test that config.json is created with correct structure"""
        project_name = "Test Collection"
        collection_size = 500
        
        bootstrap_genconfig_project(
            str(self.test_project_path),
            project_name=project_name,
            collection_size=collection_size
        )
        
        config_path = self.test_project_path / "config.json"
        assert config_path.exists(), "config.json was not created"
        assert config_path.is_file(), "config.json is not a file"
        
        # Verify config content
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Check main sections
        required_sections = ["collection", "generation", "traits", "rarity", "validation"]
        for section in required_sections:
            assert section in config, f"Missing '{section}' section in config"
        
        # Check collection details
        assert config["collection"]["name"] == project_name
        assert config["collection"]["size"] == collection_size
        assert "description" in config["collection"]
        assert "symbol" in config["collection"]
        
        # Check traits section has all 9 positions
        assert len(config["traits"]) == 9
        for i in range(1, 10):
            position_key = f"position-{i}-"
            matching_keys = [k for k in config["traits"].keys() if k.startswith(position_key)]
            assert len(matching_keys) == 1, f"Missing or duplicate position {i} trait"
    
    def test_config_trait_structure(self):
        """Test that trait configurations have correct structure"""
        bootstrap_genconfig_project(str(self.test_project_path), "Test Collection")
        
        config_path = self.test_project_path / "config.json"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Check each trait position
        for trait_key, trait_config in config["traits"].items():
            assert "name" in trait_config
            assert "required" in trait_config
            assert "grid_position" in trait_config
            assert "variants" in trait_config
            
            # Check grid position structure
            grid_pos = trait_config["grid_position"]
            assert "row" in grid_pos
            assert "column" in grid_pos
            assert 0 <= grid_pos["row"] <= 2
            assert 0 <= grid_pos["column"] <= 2
            
            # Check variants structure
            variants = trait_config["variants"]
            assert len(variants) >= 1
            for variant in variants:
                assert "name" in variant
                assert "filename" in variant
                assert "rarity_weight" in variant
                assert "color_code" in variant
    
    def test_bootstrap_creates_grid_template(self):
        """Test that grid template image is created"""
        bootstrap_genconfig_project(str(self.test_project_path), "Test Collection")
        
        template_path = self.test_project_path / "templates" / "grid-template.png"
        assert template_path.exists(), "grid-template.png was not created"
        assert template_path.is_file(), "grid-template.png is not a file"
        
        # Check file size is reasonable (should be > 1KB for a 600x600 PNG)
        file_size = template_path.stat().st_size
        assert file_size > 1000, f"Grid template file size too small: {file_size} bytes"
    
    def test_bootstrap_creates_example_traits(self):
        """Test that example trait images are created"""
        bootstrap_genconfig_project(str(self.test_project_path), "Test Collection")
        
        trait_categories = [
            "position-1-background",
            "position-2-base",
            "position-3-accent",
            "position-4-pattern",
            "position-5-center",
            "position-6-decoration",
            "position-7-border",
            "position-8-highlight",
            "position-9-overlay"
        ]
        
        for trait_dir in trait_categories:
            trait_path = self.test_project_path / "traits" / trait_dir
            
            # Should have at least one example trait image
            png_files = list(trait_path.glob("*.png"))
            assert len(png_files) >= 1, f"No example trait images in {trait_dir}"
            
            # Check file naming convention
            for png_file in png_files:
                assert png_file.name.startswith("trait-"), f"Invalid naming: {png_file.name}"
                assert png_file.name.endswith(".png"), f"Invalid extension: {png_file.name}"
    
    def test_bootstrap_creates_readme(self):
        """Test that project README is created"""
        project_name = "Test Collection"
        bootstrap_genconfig_project(str(self.test_project_path), project_name)
        
        readme_path = self.test_project_path / "README.md"
        assert readme_path.exists(), "README.md was not created"
        assert readme_path.is_file(), "README.md is not a file"
        
        # Check README content
        content = readme_path.read_text(encoding='utf-8')
        assert project_name in content, "Project name not in README"
        assert "GenConfig" in content, "GenConfig not mentioned in README"
        assert "Grid Layout" in content, "Grid layout section missing"
        assert "Getting Started" in content, "Getting started section missing"
    
    def test_validate_project_setup_complete(self):
        """Test validation of complete project setup"""
        bootstrap_genconfig_project(str(self.test_project_path), "Test Collection")
        
        is_valid, issues = validate_project_setup(str(self.test_project_path))
        
        assert is_valid is True, f"Validation failed: {issues}"
        assert issues == [], f"Unexpected issues found: {issues}"
    
    def test_validate_project_setup_incomplete(self):
        """Test validation of incomplete project setup"""
        # Create only partial project
        self.test_project_path.mkdir(parents=True)
        (self.test_project_path / "traits").mkdir()
        
        is_valid, issues = validate_project_setup(str(self.test_project_path))
        
        assert is_valid is False
        assert len(issues) > 0
        assert any("Missing config.json" in issue for issue in issues)
    
    def test_bootstrap_custom_parameters(self):
        """Test bootstrapping with custom parameters"""
        result = bootstrap_genconfig_project(
            str(self.test_project_path),
            project_name="Custom Collection",
            collection_size=2000,
            symbol="CUSTOM",
            external_url="https://custom.com",
            image_width=800,
            image_height=800,
            cell_width=266,
            cell_height=266,
            background_color="#F0F0F0"
        )
        
        assert result is True
        
        # Verify custom parameters in config
        config_path = self.test_project_path / "config.json"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        assert config["collection"]["name"] == "Custom Collection"
        assert config["collection"]["size"] == 2000
        assert config["collection"]["symbol"] == "CUSTOM"
        assert config["collection"]["external_url"] == "https://custom.com"
        assert config["generation"]["image_size"]["width"] == 800
        assert config["generation"]["image_size"]["height"] == 800
        assert config["generation"]["grid"]["cell_size"]["width"] == 266
        assert config["generation"]["grid"]["cell_size"]["height"] == 266
        assert config["generation"]["background_color"] == "#F0F0F0"
    
    def test_bootstrap_error_handling(self):
        """Test error handling in bootstrap process"""
        # Try to create project in a path that doesn't allow writing
        restricted_path = "/root/test-project" if os.name == 'posix' else "C:\\Windows\\test-project"
        
        # This should handle the error gracefully
        try:
            result = bootstrap_genconfig_project(restricted_path, "Test Collection")
            # If it somehow succeeds, clean up
            if result and os.path.exists(restricted_path):
                shutil.rmtree(restricted_path)
        except PermissionError:
            # Expected on some systems
            pass
    
    def test_validate_nonexistent_project(self):
        """Test validation of non-existent project"""
        nonexistent_path = str(self.test_project_path / "nonexistent")
        
        is_valid, issues = validate_project_setup(nonexistent_path)
        
        assert is_valid is False
        assert len(issues) > 0
    
    def test_grid_position_mapping(self):
        """Test that grid positions are correctly mapped in config"""
        bootstrap_genconfig_project(str(self.test_project_path), "Test Collection")
        
        config_path = self.test_project_path / "config.json"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Check specific position mappings
        position_mappings = {
            "position-1-background": (0, 0),
            "position-5-center": (1, 1),
            "position-9-overlay": (2, 2)
        }
        
        for trait_key, expected_pos in position_mappings.items():
            trait_config = config["traits"][trait_key]
            grid_pos = trait_config["grid_position"]
            actual_pos = (grid_pos["row"], grid_pos["column"])
            assert actual_pos == expected_pos, f"Wrong position for {trait_key}: {actual_pos} != {expected_pos}"
    
    def test_rarity_tier_configuration(self):
        """Test that rarity tiers are correctly configured"""
        bootstrap_genconfig_project(str(self.test_project_path), "Test Collection")
        
        config_path = self.test_project_path / "config.json"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        rarity = config["rarity"]
        assert rarity["calculation_method"] == "weighted_random"
        assert rarity["distribution_validation"] is True
        
        # Check rarity tiers
        tiers = rarity["rarity_tiers"]
        expected_tiers = ["common", "uncommon", "rare", "epic", "legendary"]
        for tier in expected_tiers:
            assert tier in tiers, f"Missing rarity tier: {tier}"
            assert "min_weight" in tiers[tier]
            assert "max_weight" in tiers[tier]
            assert tiers[tier]["min_weight"] <= tiers[tier]["max_weight"]


def test_integration_project_bootstrap():
    """Integration test demonstrating full project bootstrap workflow"""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "integration-test-project"
        
        # Step 1: Bootstrap project with basic parameters
        print("🚀 Bootstrapping GenConfig project...")
        success = bootstrap_genconfig_project(
            str(project_path),
            project_name="Integration Test Collection",
            collection_size=1000,
            symbol="INTTEST"
        )
        assert success, "Failed to bootstrap project"
        print("✅ Project bootstrapped successfully")
        
        # Step 2: Validate project structure
        print("🔍 Validating project structure...")
        is_valid, issues = validate_project_setup(str(project_path))
        assert is_valid, f"Project validation failed: {issues}"
        print("✅ Project validation passed")
        
        # Step 3: Verify all key files exist
        print("📁 Checking key files...")
        key_files = [
            "config.json",
            "README.md",
            "templates/grid-template.png"
        ]
        
        for file_path in key_files:
            full_path = project_path / file_path
            assert full_path.exists(), f"Missing key file: {file_path}"
        print(f"✅ All {len(key_files)} key files present")
        
        # Step 4: Verify config structure
        print("⚙️ Verifying configuration structure...")
        config_path = project_path / "config.json"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        assert config["collection"]["name"] == "Integration Test Collection"
        assert config["collection"]["size"] == 1000
        assert config["collection"]["symbol"] == "INTTEST"
        assert len(config["traits"]) == 9
        print("✅ Configuration structure verified")
        
        # Step 5: Verify trait images exist
        print("🎨 Checking trait images...")
        trait_count = 0
        for i in range(1, 10):
            trait_categories = [
                "background", "base", "accent", "pattern", "center",
                "decoration", "border", "highlight", "overlay"
            ]
            category = trait_categories[i-1]
            trait_dir = project_path / "traits" / f"position-{i}-{category}"
            
            png_files = list(trait_dir.glob("*.png"))
            assert len(png_files) > 0, f"No trait images in position-{i}-{category}"
            trait_count += len(png_files)
        
        print(f"✅ Found {trait_count} example trait images across 9 categories")
        
        # Step 6: Verify directory structure completeness
        print("🏗️ Verifying directory structure...")
        expected_dirs = [
            "traits", "output", "output/images", "output/metadata",
            "templates", "tests", "tests/sample-traits", "tests/sample-composites"
        ]
        
        for directory in expected_dirs:
            dir_path = project_path / directory
            assert dir_path.exists(), f"Missing directory: {directory}"
            assert dir_path.is_dir(), f"{directory} is not a directory"
            
        # Count trait directories
        trait_dirs = [d for d in (project_path / "traits").iterdir() if d.is_dir()]
        assert len(trait_dirs) == 9, f"Expected 9 trait directories, found {len(trait_dirs)}"
        print(f"✅ Directory structure complete with {len(trait_dirs)} trait directories")
        
        # Step 7: Test custom parameters
        print("🔧 Testing custom parameters...")
        custom_project_path = Path(temp_dir) / "custom-test-project"
        custom_success = bootstrap_genconfig_project(
            str(custom_project_path),
            project_name="Custom Collection",
            collection_size=2500,
            symbol="CUSTOM",
            external_url="https://custom.example.com",
            image_width=900,
            image_height=900,
            background_color="#F5F5F5"
        )
        assert custom_success, "Failed to bootstrap custom project"
        
        # Verify custom parameters were applied
        custom_config_path = custom_project_path / "config.json"
        with open(custom_config_path, 'r', encoding='utf-8') as f:
            custom_config = json.load(f)
        
        assert custom_config["collection"]["name"] == "Custom Collection"
        assert custom_config["collection"]["size"] == 2500
        assert custom_config["collection"]["symbol"] == "CUSTOM"
        assert custom_config["collection"]["external_url"] == "https://custom.example.com"
        assert custom_config["generation"]["image_size"]["width"] == 900
        assert custom_config["generation"]["image_size"]["height"] == 900
        assert custom_config["generation"]["background_color"] == "#F5F5F5"
        print("✅ Custom parameters applied correctly")
        
        print("\n🎉 All integration tests passed! Project Initialization working correctly.")
        return True


if __name__ == "__main__":
    try:
        test_integration_project_bootstrap()
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1) 