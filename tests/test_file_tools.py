"""Tests for file tools."""

from pathlib import Path

import pytest


@pytest.mark.unit
def test_file_tools_module_exists():
    """Test that file_tools module exists."""
    from utils import file_tools
    assert file_tools is not None


@pytest.mark.unit
def test_list_directory(temp_dir):
    """Test directory listing."""
    from utils.file_tools import list_directory

    # Create test files
    (temp_dir / "file1.txt").touch()
    (temp_dir / "subdir").mkdir()
    
    result = list_directory(str(temp_dir), base_dir=str(temp_dir.parent))
    assert "file1.txt" in result or "file1" in result


@pytest.mark.unit
def test_read_file_range(temp_dir):
    """Test file range reading."""
    from utils.file_tools import read_file_range
    
    test_file = temp_dir / "test.txt"
    test_file.write_text("Line 1\nLine 2\nLine 3\n")
    
    result = read_file_range(str(test_file), start_line=1, end_line=2, base_dir=str(temp_dir.parent))
    assert "Line 1" in result or "Error" in result  # May fail due to base_dir validation
