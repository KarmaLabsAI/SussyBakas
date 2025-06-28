"""
Test suite for GenConfig Trait Directory Manager

Tests the management and organization of trait directories within a GenConfig project.
Follows the testing strategy: Setup -> Execution -> Validation -> Cleanup
"""

import os
import tempfile
import shutil
import json
from pathlib import Path
import pytest
import sys
from PIL import Image

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from traits.directory_manager import (
    TraitDirectoryManager,
    TraitDirectoryError,
    TraitFileEntry,
    TraitDirectoryInfo,
    create_trait_directories,
    validate_trait_directories,
    organize_trait_files,
    get_trait_directory_report
)
from config.logic_validator import ValidationResult, ValidationSeverity
from infrastructure.directory_manager import create_collection_structure


class TestTraitDirectoryManager:
    """Test cases for the Trait Directory Manager"""
    
    def setup_method(self):
        """Setup: Create test fixtures and sample data"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_collection = Path(self.temp_dir) / "test-collection"
        self.source_dir = Path(self.temp_dir) / "source-traits"
        
        # Create basic collection structure
        create_collection_structure(str(self.test_collection))
        
        # Create source directory for organization tests
        self.source_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize manager
        self.manager = TraitDirectoryManager(self.test_collection)
        
        # Create sample trait files for testing
        self._create_sample_trait_files()
    
    def teardown_method(self):
        """Cleanup: Remove test files and reset state"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _create_sample_trait_files(self):
        """Create sample trait files for testing"""
        # Create sample PNG files in source directory
        sample_files = [
            "trait-red-background-001.png",
            "trait-blue-background-002.png",
            "trait-circle-base-001.png",
            "trait-star-accent-001.png",
            "trait-invalid-name.png",  # Invalid naming
            "not-a-trait.png"         # Invalid naming
        ]
        
        for filename in sample_files:
            file_path = self.source_dir / filename
            
            # Create a simple 200x200 PNG image
            image = Image.new('RGBA', (200, 200), (255, 0, 0, 128))
            image.save(file_path, 'PNG')
        
        # Create some metadata files
        metadata_file = self.source_dir / "trait-red-background-001.json"
        with open(metadata_file, 'w') as f:
            json.dump({"color": "#FF0000", "rarity": "common"}, f)
    
    def test_manager_initialization(self):
        """Test: TraitDirectoryManager initialization"""
        # Execution
        manager = TraitDirectoryManager(self.test_collection)
        
        # Validation
        assert manager.collection_root == self.test_collection
        assert manager.traits_root == self.test_collection / "traits"
        assert len(manager.TRAIT_CATEGORIES) == 9
    
    def test_create_trait_directories_success(self):
        """Test: Successful creation of trait directories"""
        # Execution
        result = self.manager.create_trait_directories()
        
        # Validation
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        
        # Check all directories were created
        for dir_name, _, _, _ in self.manager.TRAIT_CATEGORIES:
            trait_dir = self.test_collection / "traits" / dir_name
            assert trait_dir.exists()
            assert trait_dir.is_dir()
            
            # Check README was created
            readme_path = trait_dir / "README.md"
            assert readme_path.exists()
            assert readme_path.is_file()
    
    def test_create_trait_directories_already_exists(self):
        """Test: Creating directories when they already exist"""
        # Setup: Create directories first
        self.manager.create_trait_directories()
        
        # Execution: Create again
        result = self.manager.create_trait_directories()
        
        # Validation
        assert result.is_valid is True
        # Should have INFO messages about existing directories
        info_issues = [issue for issue in result.issues if issue.severity == ValidationSeverity.INFO]
        assert len(info_issues) > 0
        assert any("already exists" in issue.message for issue in info_issues)
    
    def test_create_trait_directories_force_recreate(self):
        """Test: Force recreating existing directories"""
        # Setup: Create directories first
        self.manager.create_trait_directories()
        
        # Execution: Force recreate
        result = self.manager.create_trait_directories(force_recreate=True)
        
        # Validation
        assert result.is_valid is True
        # Should have creation messages
        creation_issues = [issue for issue in result.issues 
                         if "Successfully created" in issue.message]
        assert len(creation_issues) == 9  # All 9 directories
    
    def test_validate_trait_directories_complete(self):
        """Test: Validation of complete trait directory structure"""
        # Setup: Create complete structure
        self.manager.create_trait_directories()
        
        # Execution
        result = self.manager.validate_trait_directories()
        
        # Validation
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        
        # Should have no error issues
        error_issues = [issue for issue in result.issues if issue.severity == ValidationSeverity.ERROR]
        assert len(error_issues) == 0
    
    def test_validate_trait_directories_missing(self):
        """Test: Validation when trait directories are missing"""
        # Setup: Don't create directories (traits root exists but is empty)
        
        # Execution
        result = self.manager.validate_trait_directories()
        
        # Validation
        assert result.is_valid is False
        
        # Should report missing directories
        error_issues = [issue for issue in result.issues if issue.severity == ValidationSeverity.ERROR]
        assert len(error_issues) == 9  # All 9 missing directories
        
        missing_issues = [issue for issue in error_issues if "missing" in issue.message.lower()]
        assert len(missing_issues) == 9
    
    def test_validate_trait_directories_no_traits_root(self):
        """Test: Validation when traits root doesn't exist"""
        # Setup: Remove traits directory
        traits_dir = self.test_collection / "traits"
        if traits_dir.exists():
            shutil.rmtree(traits_dir)
        
        # Execution
        result = self.manager.validate_trait_directories()
        
        # Validation
        assert result.is_valid is False
        
        # Should report missing traits root
        error_issues = [issue for issue in result.issues if issue.severity == ValidationSeverity.ERROR]
        assert len(error_issues) == 1
        assert "does not exist" in error_issues[0].message
    
    def test_scan_trait_directories_empty(self):
        """Test: Scanning empty trait directories"""
        # Setup: Create empty directories
        self.manager.create_trait_directories()
        
        # Execution
        directory_info = self.manager.scan_trait_directories()
        
        # Validation
        assert isinstance(directory_info, dict)
        assert len(directory_info) == 9
        
        for dir_name, info in directory_info.items():
            assert isinstance(info, TraitDirectoryInfo)
            assert info.directory_name == dir_name
            assert info.has_readme is True
            assert info.total_files == 0
            assert info.valid_files == 0
            assert info.invalid_files == 0
    
    def test_scan_trait_directories_with_files(self):
        """Test: Scanning trait directories with files"""
        # Setup: Create directories and add some files
        self.manager.create_trait_directories()
        
        # Add some valid trait files
        bg_dir = self.test_collection / "traits" / "position-1-background"
        valid_file = bg_dir / "trait-red-bg-001.png"
        invalid_file = bg_dir / "invalid-name.png"
        
        # Create sample images
        image = Image.new('RGBA', (200, 200), (255, 0, 0, 128))
        image.save(valid_file, 'PNG')
        image.save(invalid_file, 'PNG')
        
        # Execution
        directory_info = self.manager.scan_trait_directories()
        
        # Validation
        bg_info = directory_info["position-1-background"]
        assert bg_info.total_files == 2
        assert bg_info.valid_files == 1  # Only the properly named file
        assert bg_info.invalid_files == 1
        
        # Check file entries
        assert len(bg_info.trait_files) == 2
        valid_entries = [f for f in bg_info.trait_files if f.is_valid_name]
        assert len(valid_entries) == 1
        assert valid_entries[0].trait_name == "red-bg"
        assert valid_entries[0].trait_id == "001"
    
    def test_organize_trait_files_auto_categorize(self):
        """Test: Auto-categorizing and organizing trait files"""
        # Setup: Create trait directories
        self.manager.create_trait_directories()
        
        # Execution
        result = self.manager.organize_trait_files(
            source_directory=self.source_dir,
            auto_categorize=True,
            dry_run=False
        )
        
        # Validation
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        
        # Check that files were moved to appropriate directories
        bg_dir = self.test_collection / "traits" / "position-1-background"
        assert (bg_dir / "trait-red-background-001.png").exists()
        assert (bg_dir / "trait-blue-background-002.png").exists()
        
        base_dir = self.test_collection / "traits" / "position-2-base"
        assert (base_dir / "trait-circle-base-001.png").exists()
        
        # Check that metadata was moved too if it exists
        if (self.source_dir / "trait-red-background-001.json").exists():
            # Note: Current implementation doesn't move metadata files
            # This would be an enhancement
            pass
    
    def test_organize_trait_files_dry_run(self):
        """Test: Dry run of trait file organization"""
        # Setup: Create trait directories
        self.manager.create_trait_directories()
        
        # Execution
        result = self.manager.organize_trait_files(
            source_directory=self.source_dir,
            auto_categorize=True,
            dry_run=True
        )
        
        # Validation
        assert result.is_valid is True
        
        # Files should NOT have been moved
        assert (self.source_dir / "trait-red-background-001.png").exists()
        assert (self.source_dir / "trait-blue-background-002.png").exists()
        
        # Should have "would move" messages
        would_move_issues = [issue for issue in result.issues 
                           if "would move" in issue.message.lower()]
        assert len(would_move_issues) > 0
    
    def test_organize_trait_files_invalid_source(self):
        """Test: Organizing files from non-existent source directory"""
        # Execution
        result = self.manager.organize_trait_files(
            source_directory="/non/existent/path",
            auto_categorize=True,
            dry_run=False
        )
        
        # Validation
        assert result.is_valid is False
        
        error_issues = [issue for issue in result.issues if issue.severity == ValidationSeverity.ERROR]
        assert len(error_issues) == 1
        assert "does not exist" in error_issues[0].message
    
    def test_update_readme_files(self):
        """Test: Updating README files in trait directories"""
        # Setup: Create directories
        self.manager.create_trait_directories()
        
        # Execution
        result = self.manager.update_readme_files(force_update=True)
        
        # Validation
        assert result.is_valid is True
        
        # Check that all README files exist and have proper content
        for dir_name, category_name, _, _ in self.manager.TRAIT_CATEGORIES:
            readme_path = self.test_collection / "traits" / dir_name / "README.md"
            assert readme_path.exists()
            
            content = readme_path.read_text(encoding='utf-8')
            assert f"# {category_name} Traits" in content
            assert "Grid Position" in content
            assert "File Requirements" in content
    
    def test_update_readme_files_no_force(self):
        """Test: Updating README files without force (should skip existing)"""
        # Setup: Create directories (READMEs already exist)
        self.manager.create_trait_directories()
        
        # Execution
        result = self.manager.update_readme_files(force_update=False)
        
        # Validation
        assert result.is_valid is True
        
        # Should have messages about existing READMEs
        existing_issues = [issue for issue in result.issues 
                          if "already exists" in issue.message]
        assert len(existing_issues) == 9
    
    def test_get_trait_directory_summary(self):
        """Test: Generating trait directory summary report"""
        # Setup: Create directories with some files
        self.manager.create_trait_directories()
        
        # Add a file to one directory
        bg_dir = self.test_collection / "traits" / "position-1-background"
        test_file = bg_dir / "trait-test-bg-001.png"
        image = Image.new('RGBA', (200, 200), (255, 0, 0, 128))
        image.save(test_file, 'PNG')
        
        # Execution
        summary = self.manager.get_trait_directory_summary()
        
        # Validation
        assert isinstance(summary, str)
        assert "Trait Directory Summary" in summary
        assert "Collection Root:" in summary
        assert "position-1-background" in summary
        assert "Background" in summary
        assert "Total Directories: 9" in summary
        assert "✅" in summary  # README checkmarks


class TestTraitDirectoryManagerDataStructures:
    """Test data structures used by TraitDirectoryManager"""
    
    def test_trait_file_entry_creation(self):
        """Test: TraitFileEntry data structure"""
        # Execution
        entry = TraitFileEntry(
            file_path="/path/to/trait-test-001.png",
            file_name="trait-test-001.png",
            trait_name="test",
            trait_id="001",
            file_size=1024,
            is_valid_name=True,
            has_metadata=True,
            metadata_path="/path/to/trait-test-001.json"
        )
        
        # Validation
        assert entry.file_path == "/path/to/trait-test-001.png"
        assert entry.trait_name == "test"
        assert entry.trait_id == "001"
        assert entry.is_valid_name is True
        assert entry.has_metadata is True
    
    def test_trait_directory_info_creation(self):
        """Test: TraitDirectoryInfo data structure"""
        # Execution
        info = TraitDirectoryInfo(
            directory_path="/path/to/position-1-background",
            directory_name="position-1-background",
            position_number=1,
            category_name="Background",
            grid_row=0,
            grid_col=0,
            has_readme=True,
            readme_path="/path/to/README.md",
            trait_files=[],
            total_files=0,
            valid_files=0,
            invalid_files=0
        )
        
        # Validation
        assert info.position_number == 1
        assert info.category_name == "Background"
        assert info.grid_row == 0
        assert info.grid_col == 0
        assert info.has_readme is True


class TestTraitDirectoryManagerConvenienceFunctions:
    """Test convenience functions for trait directory management"""
    
    def setup_method(self):
        """Setup: Create test collection"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_collection = Path(self.temp_dir) / "test-collection"
        create_collection_structure(str(self.test_collection))
    
    def teardown_method(self):
        """Cleanup: Remove test files"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_create_trait_directories_function(self):
        """Test: create_trait_directories convenience function"""
        # Execution
        result = create_trait_directories(self.test_collection)
        
        # Validation
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        
        # Check directories exist
        for i in range(1, 10):
            trait_dirs = list((self.test_collection / "traits").glob("position-*"))
            assert len(trait_dirs) == 9
    
    def test_validate_trait_directories_function(self):
        """Test: validate_trait_directories convenience function"""
        # Setup: Create directories first
        create_trait_directories(self.test_collection)
        
        # Execution
        result = validate_trait_directories(self.test_collection)
        
        # Validation
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
    
    def test_organize_trait_files_function(self):
        """Test: organize_trait_files convenience function"""
        # Setup: Create directories and source files
        create_trait_directories(self.test_collection)
        source_dir = Path(self.temp_dir) / "source"
        source_dir.mkdir()
        
        # Create a test file
        test_file = source_dir / "trait-test-bg-001.png"
        image = Image.new('RGBA', (200, 200), (255, 0, 0, 128))
        image.save(test_file, 'PNG')
        
        # Execution
        result = organize_trait_files(
            collection_root=self.test_collection,
            source_directory=source_dir,
            dry_run=True
        )
        
        # Validation
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
    
    def test_get_trait_directory_report_function(self):
        """Test: get_trait_directory_report convenience function"""
        # Setup: Create directories
        create_trait_directories(self.test_collection)
        
        # Execution
        report = get_trait_directory_report(self.test_collection)
        
        # Validation
        assert isinstance(report, str)
        assert "Trait Directory Summary" in report
        assert len(report) > 100  # Should be a substantial report


class TestTraitDirectoryManagerErrorHandling:
    """Test error handling and edge cases"""
    
    def setup_method(self):
        """Setup: Create test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_collection = Path(self.temp_dir) / "test-collection"
    
    def teardown_method(self):
        """Cleanup: Remove test files"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_manager_with_nonexistent_collection(self):
        """Test: Manager with non-existent collection root"""
        # Execution
        manager = TraitDirectoryManager("/non/existent/path")
        result = manager.validate_trait_directories()
        
        # Validation
        assert result.is_valid is False
        error_issues = [issue for issue in result.issues if issue.severity == ValidationSeverity.ERROR]
        assert len(error_issues) >= 1
    
    def test_trait_directory_error_exception(self):
        """Test: TraitDirectoryError exception"""
        # Execution & Validation
        with pytest.raises(TraitDirectoryError):
            raise TraitDirectoryError("Test error message")


def test_integration_workflow():
    """
    Integration test: Complete workflow from creation to validation
    Tests: Setup -> Execution -> Validation -> Cleanup
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Setup
        collection_root = Path(temp_dir) / "integration-test"
        create_collection_structure(str(collection_root))
        
        # Execution: Create trait directories
        manager = TraitDirectoryManager(collection_root)
        create_result = manager.create_trait_directories()
        
        # Validation: Check creation
        assert create_result.is_valid is True
        
        # Execution: Validate structure
        validate_result = manager.validate_trait_directories()
        
        # Validation: Check validation
        assert validate_result.is_valid is True
        
        # Execution: Generate summary
        summary = manager.get_trait_directory_summary()
        
        # Validation: Check summary
        assert "Total Directories: 9" in summary
        assert "✅" in summary  # All READMEs should exist
        
        # Integration test successful
        assert True
        
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir) 