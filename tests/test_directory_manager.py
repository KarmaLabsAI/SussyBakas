"""
Test suite for GenConfig Directory Structure Manager

Tests the creation and validation of the standardized GenConfig folder structure.
"""

import os
import tempfile
import shutil
from pathlib import Path
import pytest
import sys

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from infrastructure.directory_manager import (
    create_collection_structure,
    validate_collection_structure,
    get_trait_directories
)


class TestDirectoryManager:
    """Test cases for the Directory Structure Manager"""
    
    def setup_method(self):
        """Set up temporary directory for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_root = Path(self.temp_dir) / "test-collection"
    
    def teardown_method(self):
        """Clean up temporary directory after each test"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_create_collection_structure_success(self):
        """Test successful creation of collection structure"""
        result = create_collection_structure(str(self.test_root))
        
        assert result is True
        assert self.test_root.exists()
        assert self.test_root.is_dir()
    
    def test_main_directories_created(self):
        """Test that all main directories are created"""
        create_collection_structure(str(self.test_root))
        
        expected_main_dirs = [
            "traits",
            "output",
            "output/images",
            "output/metadata",
            "templates",
            "tests",
            "tests/sample-traits",
            "tests/sample-composites"
        ]
        
        for directory in expected_main_dirs:
            dir_path = self.test_root / directory
            assert dir_path.exists(), f"Directory {directory} was not created"
            assert dir_path.is_dir(), f"{directory} is not a directory"
    
    def test_trait_directories_created(self):
        """Test that all 9 trait position directories are created"""
        create_collection_structure(str(self.test_root))
        
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
            dir_path = self.test_root / directory
            assert dir_path.exists(), f"Trait directory {directory} was not created"
            assert dir_path.is_dir(), f"{directory} is not a directory"
    
    def test_trait_readmes_created(self):
        """Test that README.md files are created in trait directories"""
        create_collection_structure(str(self.test_root))
        
        trait_categories = [
            "background", "base", "accent", "pattern", "center",
            "decoration", "border", "highlight", "overlay"
        ]
        
        for i, category in enumerate(trait_categories, 1):
            readme_path = self.test_root / f"traits/position-{i}-{category}/README.md"
            assert readme_path.exists(), f"README.md not created for position-{i}-{category}"
            assert readme_path.is_file(), f"README.md is not a file for position-{i}-{category}"
            
            # Check README content has basic required information
            content = readme_path.read_text(encoding='utf-8')
            assert f"# {category.title()} Traits" in content
            assert f"Position Number**: {i}" in content
            assert "Grid Coordinates" in content
            assert "File Requirements" in content
    
    def test_grid_position_mapping(self):
        """Test that grid positions are correctly mapped in README files"""
        create_collection_structure(str(self.test_root))
        
        # Test specific position mappings
        position_mappings = {
            1: ("Row 0", "Column 0", "Top-Left"),
            5: ("Row 1", "Column 1", "Middle-Center"),
            9: ("Row 2", "Column 2", "Bottom-Right")
        }
        
        trait_categories = ["background", "base", "accent", "pattern", "center",
                          "decoration", "border", "highlight", "overlay"]
        
        for pos, (row, col, location) in position_mappings.items():
            category = trait_categories[pos-1]
            readme_path = self.test_root / f"traits/position-{pos}-{category}/README.md"
            content = readme_path.read_text(encoding='utf-8')
            
            assert row in content, f"Row info missing for position {pos}"
            assert col in content, f"Column info missing for position {pos}"
            assert location in content, f"Location info missing for position {pos}"
    
    def test_validate_collection_structure_complete(self):
        """Test validation of complete structure"""
        create_collection_structure(str(self.test_root))
        
        is_valid, missing = validate_collection_structure(str(self.test_root))
        
        assert is_valid is True
        assert missing == []
    
    def test_validate_collection_structure_incomplete(self):
        """Test validation of incomplete structure"""
        # Create only partial structure
        (self.test_root / "traits").mkdir(parents=True)
        (self.test_root / "output").mkdir(parents=True)
        
        is_valid, missing = validate_collection_structure(str(self.test_root))
        
        assert is_valid is False
        assert len(missing) > 0
        assert "output/images" in missing
        assert "templates" in missing
    
    def test_validate_nonexistent_structure(self):
        """Test validation of non-existent structure"""
        nonexistent_path = str(self.test_root / "nonexistent")
        
        is_valid, missing = validate_collection_structure(nonexistent_path)
        
        assert is_valid is False
        assert len(missing) > 0
    
    def test_get_trait_directories(self):
        """Test getting list of trait directories"""
        create_collection_structure(str(self.test_root))
        
        trait_dirs = get_trait_directories(str(self.test_root))
        
        expected_dirs = [
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
        
        assert len(trait_dirs) == 9
        assert trait_dirs == expected_dirs  # Should be sorted
    
    def test_get_trait_directories_empty(self):
        """Test getting trait directories from non-existent collection"""
        nonexistent_path = str(self.test_root / "nonexistent")
        
        trait_dirs = get_trait_directories(nonexistent_path)
        
        assert trait_dirs == []
    
    def test_create_structure_already_exists(self):
        """Test creating structure when directories already exist"""
        # Create structure twice
        result1 = create_collection_structure(str(self.test_root))
        result2 = create_collection_structure(str(self.test_root))
        
        assert result1 is True
        assert result2 is True  # Should not fail if directories exist
        
        # Verify structure is still valid
        is_valid, missing = validate_collection_structure(str(self.test_root))
        assert is_valid is True
    
    def test_directory_permissions(self):
        """Test handling of permission errors (if applicable)"""
        # This test may not be meaningful on all systems
        # but demonstrates error handling capability
        
        # Try to create in a location that might not be writable
        restricted_path = "/root/genconfig-test" if os.name == 'posix' else "C:\\Windows\\genconfig-test"
        
        # This should handle the error gracefully rather than crash
        try:
            result = create_collection_structure(restricted_path)
            # If it succeeds, clean up
            if result and os.path.exists(restricted_path):
                shutil.rmtree(restricted_path)
        except PermissionError:
            # Expected on some systems
            pass


# Integration test that can be run standalone
def test_integration_example():
    """Integration test demonstrating full workflow"""
    with tempfile.TemporaryDirectory() as temp_dir:
        collection_path = Path(temp_dir) / "example-collection"
        
        # Step 1: Create structure
        success = create_collection_structure(str(collection_path))
        assert success, "Failed to create collection structure"
        
        # Step 2: Validate structure
        is_valid, missing = validate_collection_structure(str(collection_path))
        assert is_valid, f"Structure validation failed: {missing}"
        
        # Step 3: Get trait directories
        trait_dirs = get_trait_directories(str(collection_path))
        assert len(trait_dirs) == 9, f"Expected 9 trait directories, got {len(trait_dirs)}"
        
        # Step 4: Verify README files exist and contain expected content
        for trait_dir in trait_dirs:
            readme_path = collection_path / "traits" / trait_dir / "README.md"
            assert readme_path.exists(), f"README missing for {trait_dir}"
            
            content = readme_path.read_text()
            assert "# " in content, f"README missing title for {trait_dir}"
            assert "Grid Position" in content, f"README missing grid info for {trait_dir}"


if __name__ == "__main__":
    # Run the integration test
    test_integration_example()
    print("✅ All integration tests passed!") 