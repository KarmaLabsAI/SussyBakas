"""
Grid Position Calculator

Converts between position numbers (1-9) and grid coordinates (row, col) 
for the GenConfig 3×3 grid system.

Grid Layout:
┌─────────┬─────────┬─────────┐
│ Pos 1   │ Pos 2   │ Pos 3   │
│ (0,0)   │ (0,1)   │ (0,2)   │
├─────────┼─────────┼─────────┤
│ Pos 4   │ Pos 5   │ Pos 6   │
│ (1,0)   │ (1,1)   │ (1,2)   │
├─────────┼─────────┼─────────┤
│ Pos 7   │ Pos 8   │ Pos 9   │
│ (2,0)   │ (2,1)   │ (2,2)   │
└─────────┴─────────┴─────────┘
"""

from typing import Tuple, List


class GridPositionError(Exception):
    """Exception raised for invalid grid position operations"""
    pass


def position_to_coordinates(position: int) -> Tuple[int, int]:
    """
    Converts position number (1-9) to grid coordinates (row, col)
    
    Args:
        position: Position number from 1 to 9
        
    Returns:
        Tuple[int, int]: Grid coordinates as (row, column) where:
            - row: 0-2 (top to bottom)
            - column: 0-2 (left to right)
            
    Raises:
        GridPositionError: If position is not in valid range (1-9)
        
    Examples:
        >>> position_to_coordinates(1)
        (0, 0)
        >>> position_to_coordinates(5)
        (1, 1)
        >>> position_to_coordinates(9)
        (2, 2)
    """
    if not validate_position(position):
        raise GridPositionError(f"Invalid position: {position}. Position must be between 1 and 9.")
    
    # Convert position (1-9) to 0-based index (0-8)
    zero_based_position = position - 1
    
    # Calculate row and column from 0-based position
    # Formula: position = row * 3 + column (for 3x3 grid)
    row = zero_based_position // 3
    column = zero_based_position % 3
    
    return (row, column)


def coordinates_to_position(row: int, col: int) -> int:
    """
    Converts grid coordinates to position number
    
    Args:
        row: Row coordinate (0-2)
        col: Column coordinate (0-2)
        
    Returns:
        int: Position number from 1 to 9
        
    Raises:
        GridPositionError: If coordinates are not in valid range (0-2)
        
    Examples:
        >>> coordinates_to_position(0, 0)
        1
        >>> coordinates_to_position(1, 1)
        5
        >>> coordinates_to_position(2, 2)
        9
    """
    if not validate_coordinates(row, col):
        raise GridPositionError(f"Invalid coordinates: ({row}, {col}). Row and column must be between 0 and 2.")
    
    # Convert coordinates to position using standard grid formula
    # Formula: position = row * 3 + column + 1 (for 3x3 grid, 1-based)
    position = row * 3 + col + 1
    
    return position


def validate_position(position: int) -> bool:
    """
    Validate that a position number is in the valid range (1-9)
    
    Args:
        position: Position number to validate
        
    Returns:
        bool: True if position is valid, False otherwise
        
    Examples:
        >>> validate_position(1)
        True
        >>> validate_position(5)
        True
        >>> validate_position(9)
        True
        >>> validate_position(0)
        False
        >>> validate_position(10)
        False
    """
    return isinstance(position, int) and 1 <= position <= 9


def validate_coordinates(row: int, col: int) -> bool:
    """
    Validate that grid coordinates are in the valid range (0-2)
    
    Args:
        row: Row coordinate to validate
        col: Column coordinate to validate
        
    Returns:
        bool: True if coordinates are valid, False otherwise
        
    Examples:
        >>> validate_coordinates(0, 0)
        True
        >>> validate_coordinates(1, 1)
        True
        >>> validate_coordinates(2, 2)
        True
        >>> validate_coordinates(-1, 0)
        False
        >>> validate_coordinates(3, 0)
        False
    """
    return (isinstance(row, int) and isinstance(col, int) and 
            0 <= row <= 2 and 0 <= col <= 2)


def get_all_positions() -> List[int]:
    """
    Get list of all valid position numbers
    
    Returns:
        List[int]: List of position numbers [1, 2, 3, 4, 5, 6, 7, 8, 9]
    """
    return list(range(1, 10))


def get_all_coordinates() -> List[Tuple[int, int]]:
    """
    Get list of all valid grid coordinates
    
    Returns:
        List[Tuple[int, int]]: List of all coordinate pairs for 3x3 grid
    """
    coordinates = []
    for row in range(3):
        for col in range(3):
            coordinates.append((row, col))
    return coordinates


def get_position_mapping() -> dict:
    """
    Get complete mapping of positions to coordinates
    
    Returns:
        dict: Dictionary mapping position numbers to coordinate tuples
        
    Example:
        >>> mapping = get_position_mapping()
        >>> mapping[1]
        (0, 0)
        >>> mapping[5]
        (1, 1)
    """
    mapping = {}
    for position in range(1, 10):
        mapping[position] = position_to_coordinates(position)
    return mapping


def get_coordinate_mapping() -> dict:
    """
    Get complete mapping of coordinates to positions
    
    Returns:
        dict: Dictionary mapping coordinate tuples to position numbers
        
    Example:
        >>> mapping = get_coordinate_mapping()
        >>> mapping[(0, 0)]
        1
        >>> mapping[(1, 1)]
        5
    """
    mapping = {}
    for row in range(3):
        for col in range(3):
            mapping[(row, col)] = coordinates_to_position(row, col)
    return mapping


def get_position_description(position: int) -> str:
    """
    Get descriptive text for a position
    
    Args:
        position: Position number (1-9)
        
    Returns:
        str: Description of the position's location in the grid
        
    Raises:
        GridPositionError: If position is invalid
    """
    if not validate_position(position):
        raise GridPositionError(f"Invalid position: {position}")
    
    row, col = position_to_coordinates(position)
    
    # Map coordinates to descriptive terms
    row_names = ["Top", "Middle", "Bottom"]
    col_names = ["Left", "Center", "Right"]
    
    return f"{row_names[row]}-{col_names[col]}"


def get_neighbor_positions(position: int, include_diagonal: bool = True) -> List[int]:
    """
    Get neighboring positions for a given position
    
    Args:
        position: Position number (1-9)
        include_diagonal: Whether to include diagonal neighbors
        
    Returns:
        List[int]: List of neighboring position numbers
        
    Raises:
        GridPositionError: If position is invalid
    """
    if not validate_position(position):
        raise GridPositionError(f"Invalid position: {position}")
    
    row, col = position_to_coordinates(position)
    neighbors = []
    
    # Define offsets for neighbors
    if include_diagonal:
        offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    else:
        offsets = [(-1, 0), (0, -1), (0, 1), (1, 0)]  # Only orthogonal neighbors
    
    for row_offset, col_offset in offsets:
        neighbor_row = row + row_offset
        neighbor_col = col + col_offset
        
        if validate_coordinates(neighbor_row, neighbor_col):
            neighbor_position = coordinates_to_position(neighbor_row, neighbor_col)
            neighbors.append(neighbor_position)
    
    return sorted(neighbors) 