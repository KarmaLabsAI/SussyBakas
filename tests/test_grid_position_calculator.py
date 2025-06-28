"""
Tests for Grid Position Calculator (Component 4.1)

This test suite validates the grid position calculator functionality according to
the GenConfig Phase 1 specification and task breakdown requirements.

Test Requirements:
- Position 1 = (0,0), Position 5 = (1,1), Position 9 = (2,2)
- Accurate position mapping for all 9 grid positions
- Error handling for invalid inputs
- Integration with existing grid coordinate system

Testing Strategy:
- Setup: Create test fixtures and sample data
- Execution: Run component functions with various inputs
- Validation: Assert expected outputs and behaviors
- Cleanup: Remove test files and reset state
"""

import unittest
from typing import Dict, List, Tuple

from grid.position_calculator import (
    position_to_coordinates,
    coordinates_to_position,
    validate_position,
    validate_coordinates,
    get_all_positions,
    get_all_coordinates,
    get_position_mapping,
    get_coordinate_mapping,
    get_position_description,
    get_neighbor_positions,
    GridPositionError
)


class TestGridPositionCalculator(unittest.TestCase):
    """Test cases for grid position calculator functions"""
    
    def setUp(self):
        """Setup test fixtures and sample data"""
        # Core test data from task specification
        self.test_position_mappings = {
            1: (0, 0),  # Position 1 = (0,0) - Top-left
            2: (0, 1),  # Position 2 = (0,1) - Top-center
            3: (0, 2),  # Position 3 = (0,2) - Top-right
            4: (1, 0),  # Position 4 = (1,0) - Middle-left
            5: (1, 1),  # Position 5 = (1,1) - Center
            6: (1, 2),  # Position 6 = (1,2) - Middle-right
            7: (2, 0),  # Position 7 = (2,0) - Bottom-left
            8: (2, 1),  # Position 8 = (2,1) - Bottom-center
            9: (2, 2),  # Position 9 = (2,2) - Bottom-right
        }
        
        # Reverse mapping for coordinate tests
        self.test_coordinate_mappings = {
            (0, 0): 1, (0, 1): 2, (0, 2): 3,
            (1, 0): 4, (1, 1): 5, (1, 2): 6,
            (2, 0): 7, (2, 1): 8, (2, 2): 9,
        }
        
        # Invalid test data for error handling
        self.invalid_positions = [0, -1, 10, 11, 100, -100, 3.5, "5", None]
        self.invalid_coordinates = [
            (-1, 0), (0, -1), (3, 0), (0, 3), (3, 3), (-1, -1),
            (0, 3.5), ("0", 1), (None, 0), (0, None)
        ]
        
    def tearDown(self):
        """Cleanup test state"""
        # No persistent state to clean up for this component
        pass


class TestPositionToCoordinates(TestGridPositionCalculator):
    """Test position_to_coordinates function"""
    
    def test_core_position_mappings(self):
        """Test core position mappings per task specification"""
        # Test the specific requirements from task breakdown
        self.assertEqual(position_to_coordinates(1), (0, 0))  # Position 1 = (0,0)
        self.assertEqual(position_to_coordinates(5), (1, 1))  # Position 5 = (1,1)
        self.assertEqual(position_to_coordinates(9), (2, 2))  # Position 9 = (2,2)
    
    def test_all_valid_positions(self):
        """Test conversion for all valid positions (1-9)"""
        for position, expected_coords in self.test_position_mappings.items():
            with self.subTest(position=position):
                result = position_to_coordinates(position)
                self.assertEqual(result, expected_coords)
                self.assertIsInstance(result, tuple)
                self.assertEqual(len(result), 2)
                self.assertIsInstance(result[0], int)
                self.assertIsInstance(result[1], int)
    
    def test_coordinate_ranges(self):
        """Test that all returned coordinates are within valid ranges"""
        for position in range(1, 10):
            row, col = position_to_coordinates(position)
            self.assertGreaterEqual(row, 0)
            self.assertLessEqual(row, 2)
            self.assertGreaterEqual(col, 0)
            self.assertLessEqual(col, 2)
    
    def test_invalid_positions(self):
        """Test error handling for invalid position inputs"""
        for invalid_position in self.invalid_positions:
            with self.subTest(position=invalid_position):
                with self.assertRaises(GridPositionError) as context:
                    position_to_coordinates(invalid_position)
                self.assertIn("Invalid position", str(context.exception))


class TestCoordinatesToPosition(TestGridPositionCalculator):
    """Test coordinates_to_position function"""
    
    def test_core_coordinate_mappings(self):
        """Test core coordinate mappings per task specification"""
        # Test the reverse of the core requirements
        self.assertEqual(coordinates_to_position(0, 0), 1)  # (0,0) = Position 1
        self.assertEqual(coordinates_to_position(1, 1), 5)  # (1,1) = Position 5
        self.assertEqual(coordinates_to_position(2, 2), 9)  # (2,2) = Position 9
    
    def test_all_valid_coordinates(self):
        """Test conversion for all valid coordinates"""
        for coords, expected_position in self.test_coordinate_mappings.items():
            row, col = coords
            with self.subTest(coordinates=coords):
                result = coordinates_to_position(row, col)
                self.assertEqual(result, expected_position)
                self.assertIsInstance(result, int)
                self.assertGreaterEqual(result, 1)
                self.assertLessEqual(result, 9)
    
    def test_position_ranges(self):
        """Test that all returned positions are within valid ranges"""
        for row in range(3):
            for col in range(3):
                position = coordinates_to_position(row, col)
                self.assertGreaterEqual(position, 1)
                self.assertLessEqual(position, 9)
    
    def test_invalid_coordinates(self):
        """Test error handling for invalid coordinate inputs"""
        for invalid_coords in self.invalid_coordinates:
            with self.subTest(coordinates=invalid_coords):
                with self.assertRaises((GridPositionError, TypeError)):
                    if len(invalid_coords) == 2:
                        coordinates_to_position(invalid_coords[0], invalid_coords[1])


class TestBidirectionalConversion(TestGridPositionCalculator):
    """Test bidirectional conversion consistency"""
    
    def test_position_to_coordinates_to_position(self):
        """Test that position → coordinates → position is consistent"""
        for position in range(1, 10):
            coords = position_to_coordinates(position)
            back_to_position = coordinates_to_position(coords[0], coords[1])
            self.assertEqual(position, back_to_position)
    
    def test_coordinates_to_position_to_coordinates(self):
        """Test that coordinates → position → coordinates is consistent"""
        for row in range(3):
            for col in range(3):
                position = coordinates_to_position(row, col)
                back_to_coords = position_to_coordinates(position)
                self.assertEqual((row, col), back_to_coords)
    
    def test_mapping_completeness(self):
        """Test that all positions and coordinates map uniquely"""
        # Test that each position maps to unique coordinates
        position_coords = set()
        for position in range(1, 10):
            coords = position_to_coordinates(position)
            self.assertNotIn(coords, position_coords)
            position_coords.add(coords)
        
        # Test that each coordinate maps to unique position
        coord_positions = set()
        for row in range(3):
            for col in range(3):
                position = coordinates_to_position(row, col)
                self.assertNotIn(position, coord_positions)
                coord_positions.add(position)


class TestValidationFunctions(TestGridPositionCalculator):
    """Test validation helper functions"""
    
    def test_validate_position(self):
        """Test position validation function"""
        # Test valid positions
        for position in range(1, 10):
            self.assertTrue(validate_position(position))
        
        # Test invalid positions
        for invalid_position in self.invalid_positions:
            self.assertFalse(validate_position(invalid_position))
    
    def test_validate_coordinates(self):
        """Test coordinates validation function"""
        # Test valid coordinates
        for row in range(3):
            for col in range(3):
                self.assertTrue(validate_coordinates(row, col))
        
        # Test invalid coordinates
        invalid_coords = [
            (-1, 0), (0, -1), (3, 0), (0, 3), (3, 3), (-1, -1),
            (0, 3.5), ("0", 1), (None, 0), (0, None)
        ]
        for coords in invalid_coords:
            if len(coords) == 2:
                self.assertFalse(validate_coordinates(coords[0], coords[1]))


class TestUtilityFunctions(TestGridPositionCalculator):
    """Test utility and helper functions"""
    
    def test_get_all_positions(self):
        """Test get_all_positions function"""
        positions = get_all_positions()
        expected = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        self.assertEqual(positions, expected)
        self.assertIsInstance(positions, list)
        self.assertEqual(len(positions), 9)
    
    def test_get_all_coordinates(self):
        """Test get_all_coordinates function"""
        coordinates = get_all_coordinates()
        expected = [
            (0, 0), (0, 1), (0, 2),
            (1, 0), (1, 1), (1, 2),
            (2, 0), (2, 1), (2, 2)
        ]
        self.assertEqual(coordinates, expected)
        self.assertIsInstance(coordinates, list)
        self.assertEqual(len(coordinates), 9)
    
    def test_get_position_mapping(self):
        """Test get_position_mapping function"""
        mapping = get_position_mapping()
        self.assertEqual(mapping, self.test_position_mappings)
        self.assertIsInstance(mapping, dict)
        self.assertEqual(len(mapping), 9)
    
    def test_get_coordinate_mapping(self):
        """Test get_coordinate_mapping function"""
        mapping = get_coordinate_mapping()
        self.assertEqual(mapping, self.test_coordinate_mappings)
        self.assertIsInstance(mapping, dict)
        self.assertEqual(len(mapping), 9)
    
    def test_get_position_description(self):
        """Test get_position_description function"""
        # Test specific position descriptions
        self.assertEqual(get_position_description(1), "Top-Left")
        self.assertEqual(get_position_description(5), "Middle-Center")
        self.assertEqual(get_position_description(9), "Bottom-Right")
        
        # Test all positions have descriptions
        for position in range(1, 10):
            description = get_position_description(position)
            self.assertIsInstance(description, str)
            self.assertGreater(len(description), 0)
        
        # Test invalid position
        with self.assertRaises(GridPositionError):
            get_position_description(0)
    
    def test_get_neighbor_positions(self):
        """Test get_neighbor_positions function"""
        # Test center position (5) - should have 8 neighbors
        neighbors = get_neighbor_positions(5)
        expected_neighbors = [1, 2, 3, 4, 6, 7, 8, 9]
        self.assertEqual(sorted(neighbors), expected_neighbors)
        
        # Test corner position (1) - should have 3 neighbors
        neighbors = get_neighbor_positions(1)
        expected_neighbors = [2, 4, 5]
        self.assertEqual(sorted(neighbors), expected_neighbors)
        
        # Test orthogonal neighbors only
        neighbors = get_neighbor_positions(5, include_diagonal=False)
        expected_neighbors = [2, 4, 6, 8]
        self.assertEqual(sorted(neighbors), expected_neighbors)
        
        # Test invalid position
        with self.assertRaises(GridPositionError):
            get_neighbor_positions(0)


class TestErrorHandling(TestGridPositionCalculator):
    """Test error handling and edge cases"""
    
    def test_grid_position_error_creation(self):
        """Test GridPositionError exception creation"""
        error = GridPositionError("Test error message")
        self.assertIsInstance(error, Exception)
        self.assertEqual(str(error), "Test error message")
    
    def test_type_safety(self):
        """Test type safety for function inputs"""
        # Test string inputs
        with self.assertRaises(GridPositionError):
            position_to_coordinates("5")
        
        # Test None inputs
        with self.assertRaises(GridPositionError):
            position_to_coordinates(None)
        
        # Test float inputs
        with self.assertRaises(GridPositionError):
            position_to_coordinates(5.5)


class TestIntegrationWorkflow(TestGridPositionCalculator):
    """Integration testing workflow as per testing strategy"""
    
    def test_complete_workflow(self):
        """
        Complete integration test workflow:
        Setup → Execution → Validation → Cleanup
        """
        # SETUP: Prepare test scenario
        test_positions = [1, 5, 9]
        expected_coordinates = [(0, 0), (1, 1), (2, 2)]
        
        # EXECUTION: Run position calculator functions
        results = []
        for position in test_positions:
            coords = position_to_coordinates(position)
            back_position = coordinates_to_position(coords[0], coords[1])
            results.append((position, coords, back_position))
        
        # VALIDATION: Assert expected results
        for i, (orig_position, coords, back_position) in enumerate(results):
            self.assertEqual(coords, expected_coordinates[i])
            self.assertEqual(orig_position, back_position)
            self.assertTrue(validate_position(orig_position))
            self.assertTrue(validate_coordinates(coords[0], coords[1]))
        
        # CLEANUP: No cleanup needed for stateless functions
        # Verify functions still work after test execution
        self.assertEqual(position_to_coordinates(1), (0, 0))
    
    def test_performance_characteristics(self):
        """Test that functions perform within acceptable limits"""
        import time
        
        # Test position conversion performance
        start_time = time.time()
        for _ in range(1000):
            for position in range(1, 10):
                position_to_coordinates(position)
        position_time = time.time() - start_time
        
        # Test coordinate conversion performance
        start_time = time.time()
        for _ in range(1000):
            for row in range(3):
                for col in range(3):
                    coordinates_to_position(row, col)
        coordinate_time = time.time() - start_time
        
        # Assert reasonable performance (should be very fast)
        self.assertLess(position_time, 1.0)  # Less than 1 second for 9000 conversions
        self.assertLess(coordinate_time, 1.0)  # Less than 1 second for 9000 conversions


if __name__ == '__main__':
    unittest.main() 