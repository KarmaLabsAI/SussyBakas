"""
Test suite for GenConfig File System Utilities

Tests comprehensive file operations, validation, error handling,
and edge cases for the file_utils module.
"""

import os
import tempfile
import shutil
import json
from pathlib import Path
import sys
from PIL import Image, ImageDraw

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.file_utils import (
    FileOperationError,
    ValidationError,
    safe_read_file,
    safe_write_file,
    safe_read_json,
    safe_write_json,
    validate_file_exists,
    validate_directory_exists,
    get_file_size,
    calculate_file_hash,
    validate_image_file,
    copy_file_safe,
    move_file_safe,
    delete_file_safe,
    create_temp_file,
    cleanup_temp_file,
    normalize_path,
    get_relative_path,
    list_files_by_pattern,
    ensure_directory_exists
)


class TestFileUtils:
    """Test cases for File System Utilities"""
    
    def setup_method(self):
        """Set up temporary directory for each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_root = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up temporary directory after each test"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_file(self, name: str, content: str = "test content") -> Path:
        """Helper to create a test file"""
        file_path = self.test_root / name
        file_path.write_text(content, encoding='utf-8')
        return file_path
    
    def create_test_json(self, name: str, data: dict) -> Path:
        """Helper to create a test JSON file"""
        file_path = self.test_root / name
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        return file_path
    
    def create_test_image(self, name: str, size: tuple = (200, 200), 
                         mode: str = 'RGBA') -> Path:
        """Helper to create a test PNG image"""
        file_path = self.test_root / name
        img = Image.new(mode, size, (255, 0, 0, 128))
        img.save(file_path, 'PNG')
        return file_path
    
    # File Reading/Writing Tests
    
    def test_safe_read_file_success(self):
        """Test successful file reading"""
        content = "Hello, GenConfig!"
        file_path = self.create_test_file("test.txt", content)
        
        result = safe_read_file(file_path)
        assert result == content
    
    def test_safe_read_file_nonexistent(self):
        """Test reading non-existent file"""
        nonexistent = self.test_root / "nonexistent.txt"
        
        try:
            safe_read_file(nonexistent)
            assert False, "Should have raised FileOperationError"
        except FileOperationError as e:
            assert "does not exist" in str(e)
    
    def test_safe_read_file_directory(self):
        """Test reading a directory (should fail)"""
        test_dir = self.test_root / "testdir"
        test_dir.mkdir()
        
        try:
            safe_read_file(test_dir)
            assert False, "Should have raised FileOperationError"
        except FileOperationError as e:
            assert "not a file" in str(e)
    
    def test_safe_write_file_success(self):
        """Test successful file writing"""
        content = "Test content for writing"
        file_path = self.test_root / "write_test.txt"
        
        result = safe_write_file(file_path, content)
        assert result is True
        assert file_path.exists()
        assert file_path.read_text() == content
    
    def test_safe_write_file_create_dirs(self):
        """Test writing file with directory creation"""
        content = "Test content"
        file_path = self.test_root / "subdir" / "subsubdir" / "test.txt"
        
        result = safe_write_file(file_path, content, create_dirs=True)
        assert result is True
        assert file_path.exists()
        assert file_path.read_text() == content
    
    # JSON Operations Tests
    
    def test_safe_read_json_success(self):
        """Test successful JSON reading"""
        test_data = {"name": "GenConfig", "version": "1.0", "count": 42}
        file_path = self.create_test_json("test.json", test_data)
        
        result = safe_read_json(file_path)
        assert result == test_data
    
    def test_safe_read_json_invalid(self):
        """Test reading invalid JSON"""
        file_path = self.create_test_file("invalid.json", "{ invalid json }")
        
        try:
            safe_read_json(file_path)
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "Invalid JSON" in str(e)
    
    def test_safe_write_json_success(self):
        """Test successful JSON writing"""
        test_data = {"test": "data", "numbers": [1, 2, 3]}
        file_path = self.test_root / "output.json"
        
        result = safe_write_json(file_path, test_data)
        assert result is True
        assert file_path.exists()
        
        # Verify content
        loaded = safe_read_json(file_path)
        assert loaded == test_data
    
    # File Validation Tests
    
    def test_validate_file_exists_true(self):
        """Test file existence validation - positive case"""
        file_path = self.create_test_file("exists.txt")
        assert validate_file_exists(file_path) is True
    
    def test_validate_file_exists_false(self):
        """Test file existence validation - negative case"""
        nonexistent = self.test_root / "nonexistent.txt"
        assert validate_file_exists(nonexistent) is False
    
    def test_validate_directory_exists_true(self):
        """Test directory existence validation - positive case"""
        test_dir = self.test_root / "testdir"
        test_dir.mkdir()
        assert validate_directory_exists(test_dir) is True
    
    def test_validate_directory_exists_false(self):
        """Test directory existence validation - negative case"""
        nonexistent = self.test_root / "nonexistent_dir"
        assert validate_directory_exists(nonexistent) is False
    
    # File Operations Tests
    
    def test_get_file_size(self):
        """Test file size calculation"""
        content = "A" * 100  # 100 bytes
        file_path = self.create_test_file("size_test.txt", content)
        
        size = get_file_size(file_path)
        assert size == 100
    
    def test_get_file_size_nonexistent(self):
        """Test file size for non-existent file"""
        nonexistent = self.test_root / "nonexistent.txt"
        
        try:
            get_file_size(nonexistent)
            assert False, "Should have raised FileOperationError"
        except FileOperationError as e:
            assert "does not exist" in str(e)
    
    def test_calculate_file_hash(self):
        """Test file hash calculation"""
        content = "test content for hashing"
        file_path = self.create_test_file("hash_test.txt", content)
        
        hash_value = calculate_file_hash(file_path)
        assert len(hash_value) == 64  # SHA256 hex length
        assert hash_value.isalnum()
        
        # Test consistency
        hash_value2 = calculate_file_hash(file_path)
        assert hash_value == hash_value2
    
    def test_calculate_file_hash_different_algorithms(self):
        """Test different hash algorithms"""
        file_path = self.create_test_file("hash_test.txt", "test")
        
        sha256_hash = calculate_file_hash(file_path, 'sha256')
        md5_hash = calculate_file_hash(file_path, 'md5')
        
        assert len(sha256_hash) == 64
        assert len(md5_hash) == 32
        assert sha256_hash != md5_hash
    
    # Image Validation Tests
    
    def test_validate_image_file_valid(self):
        """Test valid image file validation"""
        img_path = self.create_test_image("valid.png", (200, 200), 'RGBA')
        
        is_valid, issues = validate_image_file(img_path, expected_size=(200, 200))
        assert is_valid is True
        assert issues == []
    
    def test_validate_image_file_wrong_size(self):
        """Test image validation with wrong size"""
        img_path = self.create_test_image("wrong_size.png", (100, 100), 'RGBA')
        
        is_valid, issues = validate_image_file(img_path, expected_size=(200, 200))
        assert is_valid is False
        assert any("does not match expected" in issue for issue in issues)
    
    def test_validate_image_file_wrong_format(self):
        """Test image validation with wrong format"""
        file_path = self.create_test_file("not_image.txt", "not an image")
        
        is_valid, issues = validate_image_file(file_path)
        assert is_valid is False
        assert any("not a PNG" in issue for issue in issues)
        assert any("Cannot open image" in issue for issue in issues)
    
    def test_validate_image_file_no_transparency(self):
        """Test image validation without transparency support"""
        img_path = self.create_test_image("no_transparency.png", (200, 200), 'RGB')
        
        is_valid, issues = validate_image_file(img_path)
        assert is_valid is False
        assert any("does not support transparency" in issue for issue in issues)
    
    def test_validate_image_file_too_large(self):
        """Test image validation with file too large"""
        # Create a large image (this test is conceptual since we won't create a real 3MB image)
        img_path = self.create_test_image("large.png", (200, 200), 'RGBA')
        
        # Test with very small max size
        is_valid, issues = validate_image_file(img_path, max_file_size=100)
        assert is_valid is False
        assert any("too large" in issue for issue in issues)
    
    # File Copy/Move/Delete Tests
    
    def test_copy_file_safe_success(self):
        """Test successful file copying"""
        content = "Content to copy"
        src_path = self.create_test_file("source.txt", content)
        dest_path = self.test_root / "destination.txt"
        
        result = copy_file_safe(src_path, dest_path)
        assert result is True
        assert dest_path.exists()
        assert dest_path.read_text() == content
        assert src_path.exists()  # Original should still exist
    
    def test_copy_file_safe_create_dirs(self):
        """Test file copying with directory creation"""
        content = "Content to copy"
        src_path = self.create_test_file("source.txt", content)
        dest_path = self.test_root / "subdir" / "newdir" / "destination.txt"
        
        result = copy_file_safe(src_path, dest_path, create_dirs=True)
        assert result is True
        assert dest_path.exists()
        assert dest_path.read_text() == content
    
    def test_copy_file_safe_nonexistent_source(self):
        """Test copying non-existent file"""
        src_path = self.test_root / "nonexistent.txt"
        dest_path = self.test_root / "destination.txt"
        
        try:
            copy_file_safe(src_path, dest_path)
            assert False, "Should have raised FileOperationError"
        except FileOperationError as e:
            assert "does not exist" in str(e)
    
    def test_move_file_safe_success(self):
        """Test successful file moving"""
        content = "Content to move"
        src_path = self.create_test_file("source.txt", content)
        dest_path = self.test_root / "destination.txt"
        
        result = move_file_safe(src_path, dest_path)
        assert result is True
        assert dest_path.exists()
        assert dest_path.read_text() == content
        assert not src_path.exists()  # Original should be gone
    
    def test_delete_file_safe_success(self):
        """Test successful file deletion"""
        file_path = self.create_test_file("to_delete.txt")
        assert file_path.exists()
        
        result = delete_file_safe(file_path)
        assert result is True
        assert not file_path.exists()
    
    def test_delete_file_safe_nonexistent(self):
        """Test deleting non-existent file (should succeed)"""
        nonexistent = self.test_root / "nonexistent.txt"
        
        result = delete_file_safe(nonexistent)
        assert result is True
    
    def test_delete_file_safe_directory(self):
        """Test deleting directory as file (should fail)"""
        test_dir = self.test_root / "testdir"
        test_dir.mkdir()
        
        try:
            delete_file_safe(test_dir)
            assert False, "Should have raised FileOperationError"
        except FileOperationError as e:
            assert "not a file" in str(e)
    
    # Temporary File Tests
    
    def test_create_temp_file(self):
        """Test temporary file creation"""
        temp_path, fd = create_temp_file(suffix='.json', prefix='genconfig_test_')
        
        assert os.path.exists(temp_path)
        assert temp_path.endswith('.json')
        assert 'genconfig_test_' in temp_path
        
        # Cleanup
        cleanup_temp_file(temp_path, fd)
        assert not os.path.exists(temp_path)
    
    def test_cleanup_temp_file(self):
        """Test temporary file cleanup"""
        temp_path, fd = create_temp_file()
        assert os.path.exists(temp_path)
        
        result = cleanup_temp_file(temp_path, fd)
        assert result is True
        assert not os.path.exists(temp_path)
    
    # Path Operations Tests
    
    def test_normalize_path(self):
        """Test path normalization"""
        test_path = self.test_root / "subdir" / ".." / "file.txt"
        normalized = normalize_path(test_path)
        
        assert ".." not in str(normalized)
        assert normalized.is_absolute()
    
    def test_get_relative_path(self):
        """Test relative path calculation"""
        base_path = self.test_root
        target_path = self.test_root / "subdir" / "file.txt"
        
        relative = get_relative_path(target_path, base_path)
        assert str(relative) == "subdir/file.txt"
    
    def test_get_relative_path_invalid(self):
        """Test relative path calculation with invalid paths"""
        base_path = self.test_root
        target_path = Path("/completely/different/path")
        
        try:
            get_relative_path(target_path, base_path)
            assert False, "Should have raised FileOperationError"
        except FileOperationError as e:
            assert "Cannot calculate relative path" in str(e)
    
    # Directory and Pattern Tests
    
    def test_list_files_by_pattern(self):
        """Test file listing by pattern"""
        # Create test files
        self.create_test_file("test1.txt")
        self.create_test_file("test2.txt")
        self.create_test_file("other.json")
        (self.test_root / "subdir").mkdir()
        
        # Test *.txt pattern
        txt_files = list_files_by_pattern(self.test_root, "*.txt")
        assert len(txt_files) == 2
        assert all(f.suffix == '.txt' for f in txt_files)
        
        # Test all files
        all_files = list_files_by_pattern(self.test_root, "*")
        assert len(all_files) == 3  # Only files, not directories
    
    def test_list_files_by_pattern_nonexistent_dir(self):
        """Test file listing in non-existent directory"""
        nonexistent = self.test_root / "nonexistent"
        
        try:
            list_files_by_pattern(nonexistent)
            assert False, "Should have raised FileOperationError"
        except FileOperationError as e:
            assert "does not exist" in str(e)
    
    def test_ensure_directory_exists(self):
        """Test directory creation"""
        new_dir = self.test_root / "new" / "nested" / "directory"
        
        result = ensure_directory_exists(new_dir)
        assert result is True
        assert new_dir.exists()
        assert new_dir.is_dir()
    
    def test_ensure_directory_exists_already_exists(self):
        """Test directory creation when already exists"""
        existing_dir = self.test_root / "existing"
        existing_dir.mkdir()
        
        result = ensure_directory_exists(existing_dir)
        assert result is True
        assert existing_dir.exists()


# Integration tests
def test_integration_file_operations():
    """Integration test for complete file operations workflow"""
    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir)
        
        print("🧪 Testing GenConfig File System Utilities...")
        
        # Test 1: Create and validate directory structure
        print("📁 Testing directory operations...")
        project_dir = base_path / "test-project"
        ensure_directory_exists(project_dir / "traits" / "position-1-background")
        
        assert validate_directory_exists(project_dir)
        assert validate_directory_exists(project_dir / "traits")
        print("✅ Directory operations successful")
        
        # Test 2: JSON configuration operations
        print("⚙️ Testing JSON operations...")
        config_data = {
            "collection": {"name": "Test Collection", "size": 1000},
            "generation": {"image_format": "PNG"}
        }
        config_path = project_dir / "config.json"
        
        safe_write_json(config_path, config_data)
        loaded_config = safe_read_json(config_path)
        assert loaded_config == config_data
        print("✅ JSON operations successful")
        
        # Test 3: Image file validation
        print("🖼️ Testing image validation...")
        img = Image.new('RGBA', (200, 200), (255, 0, 0, 128))
        img_path = project_dir / "traits" / "position-1-background" / "trait-test-001.png"
        img.save(img_path, 'PNG')
        
        is_valid, issues = validate_image_file(img_path, expected_size=(200, 200))
        assert is_valid, f"Image validation failed: {issues}"
        print("✅ Image validation successful")
        
        # Test 4: File operations (copy, move, hash)
        print("🔄 Testing file operations...")
        original_path = project_dir / "original.txt"
        safe_write_file(original_path, "Original content")
        
        copied_path = project_dir / "copied.txt"
        copy_file_safe(original_path, copied_path)
        assert validate_file_exists(copied_path)
        
        original_hash = calculate_file_hash(original_path)
        copied_hash = calculate_file_hash(copied_path)
        assert original_hash == copied_hash
        print("✅ File operations successful")
        
        # Test 5: File pattern matching
        print("🔍 Testing pattern matching...")
        png_files = list_files_by_pattern(project_dir / "traits" / "position-1-background", "*.png")
        assert len(png_files) == 1
        assert png_files[0].name == "trait-test-001.png"
        print("✅ Pattern matching successful")
        
        # Test 6: Temporary file operations
        print("🗂️ Testing temporary file operations...")
        temp_path, fd = create_temp_file(suffix='.json', prefix='test_')
        test_data = {"temporary": True, "test": "data"}
        safe_write_json(temp_path, test_data)
        
        loaded_temp = safe_read_json(temp_path)
        assert loaded_temp == test_data
        
        cleanup_success = cleanup_temp_file(temp_path, fd)
        assert cleanup_success
        assert not os.path.exists(temp_path)
        print("✅ Temporary file operations successful")
        
        print("\n🎉 All integration tests passed! File System Utilities working correctly.")
        return True


if __name__ == "__main__":
    try:
        test_integration_file_operations()
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1) 