"""
GenConfig File System Utilities

This module provides common file operations and path handling utilities
for the GenConfig system, including safe I/O operations, validation,
and error handling.
"""

import os
import json
import hashlib
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union
from PIL import Image
import tempfile
import logging


class FileOperationError(Exception):
    """Custom exception for file operation errors"""
    pass


class ValidationError(Exception):
    """Custom exception for file validation errors"""
    pass


def safe_read_file(file_path: Union[str, Path], encoding: str = 'utf-8') -> str:
    """
    Safely read a text file with proper error handling.
    
    Args:
        file_path: Path to the file to read
        encoding: File encoding (default: utf-8)
        
    Returns:
        str: File contents
        
    Raises:
        FileOperationError: If file cannot be read
    """
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileOperationError(f"File does not exist: {file_path}")
        
        if not path.is_file():
            raise FileOperationError(f"Path is not a file: {file_path}")
        
        with open(path, 'r', encoding=encoding) as f:
            return f.read()
            
    except (OSError, IOError, UnicodeDecodeError) as e:
        raise FileOperationError(f"Failed to read file {file_path}: {e}")


def safe_write_file(file_path: Union[str, Path], content: str, 
                   encoding: str = 'utf-8', create_dirs: bool = True) -> bool:
    """
    Safely write content to a text file with proper error handling.
    
    Args:
        file_path: Path where to write the file
        content: Content to write
        encoding: File encoding (default: utf-8)
        create_dirs: Whether to create parent directories if they don't exist
        
    Returns:
        bool: True if successful, False otherwise
        
    Raises:
        FileOperationError: If file cannot be written
    """
    try:
        path = Path(file_path)
        
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding=encoding) as f:
            f.write(content)
        
        return True
        
    except (OSError, IOError, UnicodeEncodeError) as e:
        raise FileOperationError(f"Failed to write file {file_path}: {e}")


def safe_read_json(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Safely read and parse a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dict[str, Any]: Parsed JSON data
        
    Raises:
        FileOperationError: If file cannot be read
        ValidationError: If JSON is invalid
    """
    try:
        content = safe_read_file(file_path)
        return json.loads(content)
        
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON in file {file_path}: {e}")


def safe_write_json(file_path: Union[str, Path], data: Dict[str, Any], 
                   indent: int = 2, create_dirs: bool = True) -> bool:
    """
    Safely write data to a JSON file.
    
    Args:
        file_path: Path where to write the JSON file
        data: Data to write
        indent: JSON indentation (default: 2)
        create_dirs: Whether to create parent directories
        
    Returns:
        bool: True if successful
        
    Raises:
        FileOperationError: If file cannot be written
    """
    try:
        json_content = json.dumps(data, indent=indent, ensure_ascii=False)
        return safe_write_file(file_path, json_content, create_dirs=create_dirs)
        
    except (TypeError, ValueError) as e:
        raise FileOperationError(f"Failed to serialize JSON data for {file_path}: {e}")


def validate_file_exists(file_path: Union[str, Path]) -> bool:
    """
    Check if a file exists and is accessible.
    
    Args:
        file_path: Path to check
        
    Returns:
        bool: True if file exists and is accessible
    """
    try:
        path = Path(file_path)
        return path.exists() and path.is_file()
    except (OSError, IOError):
        return False


def validate_directory_exists(dir_path: Union[str, Path]) -> bool:
    """
    Check if a directory exists and is accessible.
    
    Args:
        dir_path: Path to check
        
    Returns:
        bool: True if directory exists and is accessible
    """
    try:
        path = Path(dir_path)
        return path.exists() and path.is_dir()
    except (OSError, IOError):
        return False


def get_file_size(file_path: Union[str, Path]) -> int:
    """
    Get the size of a file in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        int: File size in bytes
        
    Raises:
        FileOperationError: If file size cannot be determined
    """
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileOperationError(f"File does not exist: {file_path}")
        
        return path.stat().st_size
        
    except (OSError, IOError) as e:
        raise FileOperationError(f"Failed to get file size for {file_path}: {e}")


def calculate_file_hash(file_path: Union[str, Path], algorithm: str = 'sha256') -> str:
    """
    Calculate hash of a file for integrity checking.
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use (default: sha256)
        
    Returns:
        str: Hexadecimal hash string
        
    Raises:
        FileOperationError: If hash cannot be calculated
    """
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileOperationError(f"File does not exist: {file_path}")
        
        hash_func = hashlib.new(algorithm)
        
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
        
    except (OSError, IOError, ValueError) as e:
        raise FileOperationError(f"Failed to calculate hash for {file_path}: {e}")


def validate_image_file(file_path: Union[str, Path], 
                       expected_size: Optional[Tuple[int, int]] = None,
                       max_file_size: int = 2 * 1024 * 1024) -> Tuple[bool, List[str]]:
    """
    Validate an image file according to GenConfig requirements.
    
    Args:
        file_path: Path to the image file
        expected_size: Expected (width, height) dimensions
        max_file_size: Maximum file size in bytes (default: 2MB)
        
    Returns:
        Tuple of (is_valid: bool, issues: List[str])
    """
    issues = []
    path = Path(file_path)
    
    try:
        # Check file exists
        if not path.exists():
            issues.append(f"File does not exist: {file_path}")
            return False, issues
        
        # Check file extension
        if path.suffix.lower() != '.png':
            issues.append(f"File is not a PNG: {path.suffix}")
        
        # Check file size
        file_size = get_file_size(path)
        if file_size > max_file_size:
            issues.append(f"File too large: {file_size} bytes (max: {max_file_size})")
        
        # Check image can be opened and properties
        try:
            with Image.open(path) as img:
                # Check format
                if img.format != 'PNG':
                    issues.append(f"Image format is not PNG: {img.format}")
                
                # Check mode supports transparency
                if img.mode not in ['RGBA', 'LA', 'P']:
                    issues.append(f"Image mode does not support transparency: {img.mode}")
                
                # Check dimensions if specified
                if expected_size:
                    if img.size != expected_size:
                        issues.append(f"Image size {img.size} does not match expected {expected_size}")
                        
        except Exception as e:
            issues.append(f"Cannot open image file: {e}")
        
        return len(issues) == 0, issues
        
    except Exception as e:
        issues.append(f"Validation error: {e}")
        return False, issues


def copy_file_safe(src_path: Union[str, Path], dest_path: Union[str, Path], 
                  create_dirs: bool = True) -> bool:
    """
    Safely copy a file with error handling.
    
    Args:
        src_path: Source file path
        dest_path: Destination file path
        create_dirs: Whether to create destination directories
        
    Returns:
        bool: True if successful
        
    Raises:
        FileOperationError: If copy operation fails
    """
    try:
        src = Path(src_path)
        dest = Path(dest_path)
        
        if not src.exists():
            raise FileOperationError(f"Source file does not exist: {src_path}")
        
        if create_dirs:
            dest.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(src, dest)
        return True
        
    except (OSError, IOError, shutil.Error) as e:
        raise FileOperationError(f"Failed to copy file from {src_path} to {dest_path}: {e}")


def move_file_safe(src_path: Union[str, Path], dest_path: Union[str, Path],
                  create_dirs: bool = True) -> bool:
    """
    Safely move a file with error handling.
    
    Args:
        src_path: Source file path
        dest_path: Destination file path
        create_dirs: Whether to create destination directories
        
    Returns:
        bool: True if successful
        
    Raises:
        FileOperationError: If move operation fails
    """
    try:
        src = Path(src_path)
        dest = Path(dest_path)
        
        if not src.exists():
            raise FileOperationError(f"Source file does not exist: {src_path}")
        
        if create_dirs:
            dest.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.move(str(src), str(dest))
        return True
        
    except (OSError, IOError, shutil.Error) as e:
        raise FileOperationError(f"Failed to move file from {src_path} to {dest_path}: {e}")


def delete_file_safe(file_path: Union[str, Path]) -> bool:
    """
    Safely delete a file with error handling.
    
    Args:
        file_path: Path to the file to delete
        
    Returns:
        bool: True if successful or file doesn't exist
        
    Raises:
        FileOperationError: If deletion fails
    """
    try:
        path = Path(file_path)
        
        if not path.exists():
            return True  # Already deleted
        
        if path.is_file():
            path.unlink()
            return True
        else:
            raise FileOperationError(f"Path is not a file: {file_path}")
        
    except (OSError, IOError) as e:
        raise FileOperationError(f"Failed to delete file {file_path}: {e}")


def create_temp_file(suffix: str = '', prefix: str = 'genconfig_', 
                    dir: Optional[str] = None) -> Tuple[str, int]:
    """
    Create a temporary file for safe operations.
    
    Args:
        suffix: File suffix/extension
        prefix: File prefix
        dir: Directory to create temp file in
        
    Returns:
        Tuple of (file_path: str, file_descriptor: int)
        
    Raises:
        FileOperationError: If temp file cannot be created
    """
    try:
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dir)
        return path, fd
        
    except (OSError, IOError) as e:
        raise FileOperationError(f"Failed to create temporary file: {e}")


def cleanup_temp_file(file_path: str, file_descriptor: Optional[int] = None) -> bool:
    """
    Clean up a temporary file safely.
    
    Args:
        file_path: Path to the temporary file
        file_descriptor: File descriptor to close (optional)
        
    Returns:
        bool: True if successful
    """
    try:
        if file_descriptor is not None:
            os.close(file_descriptor)
        
        return delete_file_safe(file_path)
        
    except Exception:
        return False


def normalize_path(path: Union[str, Path]) -> Path:
    """
    Normalize a file path for consistent handling.
    
    Args:
        path: Path to normalize
        
    Returns:
        Path: Normalized path object
    """
    return Path(path).resolve()


def get_relative_path(path: Union[str, Path], base_path: Union[str, Path]) -> Path:
    """
    Get relative path from base path.
    
    Args:
        path: Target path
        base_path: Base path to calculate relative from
        
    Returns:
        Path: Relative path
        
    Raises:
        FileOperationError: If relative path cannot be calculated
    """
    try:
        target = normalize_path(path)
        base = normalize_path(base_path)
        return target.relative_to(base)
        
    except ValueError as e:
        raise FileOperationError(f"Cannot calculate relative path from {base_path} to {path}: {e}")


def list_files_by_pattern(directory: Union[str, Path], pattern: str = "*") -> List[Path]:
    """
    List files in a directory matching a pattern.
    
    Args:
        directory: Directory to search
        pattern: Glob pattern to match
        
    Returns:
        List[Path]: List of matching file paths
        
    Raises:
        FileOperationError: If directory cannot be accessed
    """
    try:
        dir_path = Path(directory)
        
        if not dir_path.exists():
            raise FileOperationError(f"Directory does not exist: {directory}")
        
        if not dir_path.is_dir():
            raise FileOperationError(f"Path is not a directory: {directory}")
        
        return [f for f in dir_path.glob(pattern) if f.is_file()]
        
    except (OSError, IOError) as e:
        raise FileOperationError(f"Failed to list files in {directory}: {e}")


def ensure_directory_exists(dir_path: Union[str, Path]) -> bool:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        dir_path: Directory path to ensure exists
        
    Returns:
        bool: True if directory exists or was created
        
    Raises:
        FileOperationError: If directory cannot be created
    """
    try:
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        return True
        
    except (OSError, IOError) as e:
        raise FileOperationError(f"Failed to create directory {dir_path}: {e}")


if __name__ == "__main__":
    # Example usage and testing
    print("GenConfig File System Utilities")
    print("Testing basic operations...")
    
    try:
        # Test temporary file creation
        temp_path, fd = create_temp_file(suffix='.json', prefix='test_')
        print(f"✅ Created temp file: {temp_path}")
        
        # Test JSON operations
        test_data = {"test": "data", "number": 42}
        safe_write_json(temp_path, test_data)
        print("✅ JSON write successful")
        
        loaded_data = safe_read_json(temp_path)
        assert loaded_data == test_data
        print("✅ JSON read/write validation passed")
        
        # Test file operations
        file_size = get_file_size(temp_path)
        print(f"✅ File size: {file_size} bytes")
        
        file_hash = calculate_file_hash(temp_path)
        print(f"✅ File hash: {file_hash[:16]}...")
        
        # Cleanup
        cleanup_temp_file(temp_path, fd)
        print("✅ Cleanup successful")
        
        print("\n🎉 All basic tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 