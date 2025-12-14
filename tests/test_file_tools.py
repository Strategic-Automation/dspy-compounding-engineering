"""Tests for file tools."""

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

    # Pass relative path "." and set base_dir to temp_dir
    result = list_directory(".", base_dir=str(temp_dir))
    assert "file1.txt" in result
    assert "subdir/" in result


@pytest.mark.unit
def test_read_file_range(temp_dir):
    """Test file range reading."""
    from utils.file_tools import read_file_range

    test_file = temp_dir / "test.txt"
    test_file.write_text("Line 1\nLine 2\nLine 3\n")

    # Use relative path "test.txt"
    result = read_file_range(
        "test.txt", start_line=1, end_line=2, base_dir=str(temp_dir)
    )
    assert "Line 1" in result
    assert "Line 2" in result


@pytest.mark.unit
def test_safe_write_overwrite(temp_dir):
    """Test safe_write overwrite behavior."""
    from utils.safe_io import safe_write
    import pytest

    test_file = temp_dir / "test.txt"
    test_file.write_text("Original", encoding="utf-8")

    # Overwrite=True (default)
    safe_write("test.txt", "New", base_dir=str(temp_dir))
    assert test_file.read_text(encoding="utf-8") == "New"

    # Overwrite=False
    with pytest.raises(FileExistsError):
        safe_write("test.txt", "Another", base_dir=str(temp_dir), overwrite=False)

    assert test_file.read_text(encoding="utf-8") == "New"


@pytest.mark.unit
def test_create_file(temp_dir):
    """Test create_file function."""
    from utils.file_tools import create_file

    test_file = temp_dir / "new_file.txt"

    # Success
    result = create_file("new_file.txt", "Content", base_dir=str(temp_dir))
    assert "Successfully created" in result
    assert test_file.read_text(encoding="utf-8") == "Content"

    # Failure (exists)
    result = create_file("new_file.txt", "New Content", base_dir=str(temp_dir))
    assert "Error: File already exists" in result
    assert test_file.read_text(encoding="utf-8") == "Content"


@pytest.mark.unit
def test_edit_file_lines_validation(temp_dir):
    """Test validation in edit_file_lines."""
    from utils.file_tools import edit_file_lines

    # Create dummy file
    (temp_dir / "test.txt").write_text("Line 1\nLine 2")

    # Invalid edits type
    result = edit_file_lines("test.txt", edits="invalid", base_dir=str(temp_dir))
    assert "Error: arguments 'edits' must be a list" in result

    # Invalid edit item type
    result = edit_file_lines("test.txt", edits=["invalid"], base_dir=str(temp_dir))
    assert "Error: edit item 0 must be a dictionary" in result

    # Missing keys
    result = edit_file_lines(
        "test.txt", edits=[{"start_line": 1}], base_dir=str(temp_dir)
    )
    assert "missing required keys" in result
