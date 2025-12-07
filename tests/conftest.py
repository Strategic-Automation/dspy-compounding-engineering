"""Pytest configuration and shared fixtures."""

import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_knowledge_base(temp_dir):
    """Create a mock knowledge base for testing."""
    kb_dir = temp_dir / ".knowledge"
    kb_dir.mkdir(exist_ok=True)
    return kb_dir


@pytest.fixture
def sample_learning():
    """Return a sample learning dictionary."""
    return {
        "category": "test",
        "summary": "Test learning summary",
        "content": "Detailed test learning content",
        "tags": ["test", "example"],
        "source": "test_source",
    }
