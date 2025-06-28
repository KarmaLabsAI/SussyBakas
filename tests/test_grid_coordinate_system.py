"""
Test Suite for Grid Coordinate System - Component 4.4

Tests unified grid coordinate management system ensuring consistent coordinate 
calculations throughout the application.
"""

import unittest
import tempfile
import shutil
import os
import sys
from typing import Dict, Set, List, Optional, Tuple
from unittest.mock import Mock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from grid.coordinate_system import (
    GridCoordinateSystem,
    GridSystemConfig,
    GridSystemState,
    CoordinateSystemInfo,
    CoordinateValidationMode,
    GridSystemError,
    create_grid_coordinate_system,
    verify_coordinate_system_consistency,
    get_coordinate_system_info,
    get_coordinate_system_report
)

from grid.position_calculator import GridPositionError
from grid.layout_validator import ValidationResult, ValidationSeverity, ValidationIssue
from grid.template_generator import GridTemplateDimensions, GridTemplateStyle


class TestGridSystemConfig(unittest.TestCase):
    """Test GridSystemConfig data structure"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.default_config = GridSystemConfig()
        self.custom_config = GridSystemConfig(
            validation_mode=CoordinateValidationMode.PERMISSIVE,
            enforce_consistency=False,
            cache_calculations=False,
            auto_validate_positions=False
        )
    
    def test_default_config_values(self):
        """Test default configuration values"""
        self.assertEqual(self.default_config.validation_mode, CoordinateValidationMode.STRICT)
        self.assertTrue(self.default_config.enforce_consistency)
        self.assertTrue(self.default_config.cache_calculations)
        self.assertTrue(self.default_config.auto_validate_positions)
        self.assertIsNone(self.default_config.template_style)
        self.assertIsNone(self.default_config.template_dimensions)


class TestGridCoordinateSystem(unittest.TestCase):
    """Test main GridCoordinateSystem class"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.system = GridCoordinateSystem()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Cleanup test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.system.clear_cache()
    
    def test_position_to_coordinates_valid(self):
        """Test valid position to coordinates conversion"""
        expected_results = {
            1: (0, 0), 2: (0, 1), 3: (0, 2),
            4: (1, 0), 5: (1, 1), 6: (1, 2),
            7: (2, 0), 8: (2, 1), 9: (2, 2)
        }
        
        for position, expected_coords in expected_results.items():
            coords = self.system.convert_position_to_coordinates(position)
            self.assertEqual(coords, expected_coords,
                           f"Position {position} should map to {expected_coords}, got {coords}")
    
    def test_coordinates_to_position_valid(self):
        """Test valid coordinates to position conversion"""
        expected_results = {
            (0, 0): 1, (0, 1): 2, (0, 2): 3,
            (1, 0): 4, (1, 1): 5, (1, 2): 6,
            (2, 0): 7, (2, 1): 8, (2, 2): 9
        }
        
        for coords, expected_position in expected_results.items():
            position = self.system.convert_coordinates_to_position(coords[0], coords[1])
            self.assertEqual(position, expected_position,
                           f"Coordinates {coords} should map to {expected_position}, got {position}")
    
    def test_bidirectional_conversion_consistency(self):
        """Test bidirectional conversion consistency"""
        # Test position -> coordinates -> position
        for position in range(1, 10):
            coords = self.system.convert_position_to_coordinates(position)
            back_to_position = self.system.convert_coordinates_to_position(coords[0], coords[1])
            self.assertEqual(position, back_to_position,
                           f"Bidirectional conversion failed for position {position}")
        
        # Test coordinates -> position -> coordinates
        for row in range(3):
            for col in range(3):
                position = self.system.convert_coordinates_to_position(row, col)
                back_to_coords = self.system.convert_position_to_coordinates(position)
                self.assertEqual((row, col), back_to_coords,
                               f"Bidirectional conversion failed for coordinates ({row}, {col})")
    
    def test_verify_consistency_success(self):
        """Test successful consistency verification"""
        result = self.system.verify_consistency()
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid, f"Consistency check failed with issues: {[issue.message for issue in result.issues]}")
        self.assertEqual(len(result.errors), 0)
    
    def test_get_all_valid_positions(self):
        """Test getting all valid positions"""
        positions = self.system.get_all_valid_positions()
        self.assertEqual(positions, [1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(len(positions), 9)
    
    def test_get_system_info(self):
        """Test getting system information"""
        info = self.system.get_system_info()
        self.assertIsInstance(info, CoordinateSystemInfo)
        self.assertEqual(info.grid_dimensions, (3, 3))
        self.assertEqual(info.total_cells, 9)
        self.assertEqual(info.position_range, (1, 9))
        self.assertEqual(info.coordinate_range, ((0, 2), (0, 2)))
        self.assertTrue(info.template_generation_available)
    
    def test_generate_grid_template(self):
        """Test grid template generation"""
        output_path = os.path.join(self.temp_dir, "test_template.png")
        
        result = self.system.generate_grid_template(output_path)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(output_path))
        
        # Check file size is reasonable (should be a valid PNG)
        file_size = os.path.getsize(output_path)
        self.assertGreater(file_size, 1000)  # At least 1KB
        self.assertLess(file_size, 100000)   # Less than 100KB


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions"""
    
    def test_create_grid_coordinate_system(self):
        """Test creating coordinate system via convenience function"""
        system = create_grid_coordinate_system()
        self.assertIsInstance(system, GridCoordinateSystem)
    
    def test_verify_coordinate_system_consistency(self):
        """Test consistency verification convenience function"""
        result = verify_coordinate_system_consistency()
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)
    
    def test_get_coordinate_system_info(self):
        """Test getting system info via convenience function"""
        info = get_coordinate_system_info()
        self.assertIsInstance(info, CoordinateSystemInfo)
        self.assertEqual(info.grid_dimensions, (3, 3))


class TestIntegrationWorkflow(unittest.TestCase):
    """Test complete integration workflow"""
    
    def setUp(self):
        """Setup test fixtures for integration testing"""
        self.system = GridCoordinateSystem()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Cleanup integration test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.system.clear_cache()
    
    def test_complete_coordinate_system_workflow(self):
        """Test complete coordinate system workflow"""
        # 1. System Information
        info = self.system.get_system_info()
        self.assertEqual(info.total_cells, 9)
        self.assertTrue(info.template_generation_available)
        
        # 2. Position Conversions
        for position in range(1, 10):
            coords = self.system.convert_position_to_coordinates(position)
            back_position = self.system.convert_coordinates_to_position(coords[0], coords[1])
            self.assertEqual(position, back_position)
        
        # 3. Consistency Check
        consistency_result = self.system.verify_consistency()
        self.assertTrue(consistency_result.is_valid)
        
        # 4. Template Generation
        template_path = os.path.join(self.temp_dir, "workflow_template.png")
        template_result = self.system.generate_grid_template(template_path)
        self.assertTrue(template_result)
        self.assertTrue(os.path.exists(template_path))
        
        # 5. Cache Management
        initial_stats = self.system.get_cache_stats()
        self.assertGreater(initial_stats['total_cache_entries'], 0)
        
        self.system.clear_cache()
        cleared_stats = self.system.get_cache_stats()
        self.assertEqual(cleared_stats['total_cache_entries'], 0)


if __name__ == '__main__':
    unittest.main()
