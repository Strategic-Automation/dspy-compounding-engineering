"""Tests for the auto-generated API docs script."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.generate_api_docs import (
    extract_classes_and_functions,
    extract_docstring,
    generate_module_docs,
)

# =============================================================================
# Tests for extract_docstring
# =============================================================================


def test_extract_docstring_with_docstring():
    """Test extracting module-level docstring."""
    source = '''"""This is a module docstring."""

def foo():
    pass
'''
    result = extract_docstring(source)
    assert result == "This is a module docstring."


def test_extract_docstring_no_docstring():
    """Test default when no docstring present."""
    source = "def foo():\n    pass\n"
    result = extract_docstring(source)
    assert result == "No module documentation available."


def test_extract_docstring_multiline():
    """Test multi-line docstring extraction."""
    source = '''"""
First line.
Second line.
"""

x = 1
'''
    result = extract_docstring(source)
    assert "First line." in result
    assert "Second line." in result


# =============================================================================
# Tests for extract_classes_and_functions
# =============================================================================


def test_extract_class_and_function():
    """Test extraction of class and function definitions."""
    source = '''class MyService:
    """A test service."""

    def __init__(self):
        """Initialize."""
        pass

    def do_thing(self, name: str):
        """Does a thing."""
        pass


def helper_func():
    """A helper function."""
    pass
'''
    items = extract_classes_and_functions(source)
    assert len(items) == 2
    assert items[0]["kind"] == "class"
    assert items[0]["name"] == "MyService"
    assert items[1]["kind"] == "function"
    assert items[1]["name"] == "helper_func"


def test_extract_skips_private():
    """Test that private class/functions are skipped."""
    source = '''class _PrivateClass:
    """Should be skipped."""
    pass


def _private_func():
    """Should be skipped."""
    pass


class PublicClass:
    """Should be kept."""
    pass


def public_func():
    """Should be kept."""
    pass
'''
    items = extract_classes_and_functions(source)
    names = [item["name"] for item in items]
    assert "_PrivateClass" not in names
    assert "_private_func" not in names
    assert "PublicClass" in names
    assert "public_func" in names


def test_extract_empty_source():
    """Test extraction from source with no definitions."""
    source = "x = 1 + 2\n"
    items = extract_classes_and_functions(source)
    assert items == []


# =============================================================================
# Tests for generate_module_docs
# =============================================================================


def test_generate_module_docs(tmp_path):
    """Test generating markdown for a module file."""
    mod_file = tmp_path / "mymodule.py"
    mod_file.write_text('''"""Module for testing."""

class Foo:
    """Foo class docstring."""

    def bar(self, arg):
        """Bar method."""
        pass
''')
    md = generate_module_docs(str(mod_file), str(tmp_path))
    assert "mymodule" in md
    assert "Module for testing." in md
    assert "Foo" in md
    assert "bar" in md


def test_generate_module_docs_invalid_syntax(tmp_path):
    """Test handling of files with invalid Python syntax."""
    mod_file = tmp_path / "broken.py"
    mod_file.write_text("def foo(\n  # syntax error\n")
    md = generate_module_docs(str(mod_file), str(tmp_path))
    assert "broken" in md  # Still generates module header


# =============================================================================
# Integration: run the script end-to-end
# =============================================================================


def test_script_runs_end_to_end():
    """Test that the script produces output files without crashing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [sys.executable, "scripts/generate_api_docs.py", "--output-dir", tmpdir],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        # Verify all 4 files were created
        for fname in ["agents.md", "workflows.md", "utilities.md", "config.md"]:
            fpath = os.path.join(tmpdir, fname)
            assert os.path.isfile(fpath), f"Missing {fname}"
            with open(fpath) as f:
                content = f.read()
            assert len(content) > 100, f"{fname} is suspiciously small"
