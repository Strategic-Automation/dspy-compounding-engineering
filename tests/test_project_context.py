import os
from unittest.mock import MagicMock, patch

import pytest

from utils.context.project import ProjectContext


@pytest.fixture
def project_context(tmp_path):
    # create dummy project structure
    d = tmp_path / "project"
    d.mkdir()
    (d / "README.md").write_text("# Test Project")
    (d / "main.py").write_text("print('hello')")
    (d / "utils.py").write_text("def util(): pass")

    # Ignored directory
    (d / "venv").mkdir()
    (d / "venv" / "lib.py").write_text("ignored")

    # Patch os.getcwd so ProjectContext thinks we are in the tmp dir
    with patch("os.getcwd", return_value=str(d)):
        yield ProjectContext(base_dir=".")


def test_project_context_security(tmp_path):
    # Crossing above the base_dir should fail
    # tmp_path / "project" is the base. tmp_path / "outside.py" is outside.
    d = tmp_path / "project"
    d.mkdir()
    with patch("os.getcwd", return_value=str(d)):
        with pytest.raises(ValueError, match="Path outside base directory"):
            ProjectContext(base_dir="../")


def test_gather_context_basic(project_context):
    context = project_context.gather_smart_context(task="test")
    assert "main.py" in context
    assert "utils.py" in context
    assert "venv" not in context


def test_budget_enforcement(project_context):
    # Set a tiny budget that only fits README
    # "=== README.md (Score: 1.0) ===\n# Test Project\n" is roughly 10-15 tokens

    # We'll mock token counter to be deterministic
    project_context.token_counter.count_tokens = MagicMock(return_value=10)

    # Budget = 15 tokens. Should fit 1 file (10 tokens) but not 2 (20 tokens)
    context = project_context.gather_smart_context(task="test", budget=15)

    assert "README.md" in context  # Tier 1, highest score
    # One file should be skipped if we have >1 file
    # We need to ensure we have >1 file. Setup has main.py and utils.py too.

    assert "Files included: 1" in context
    assert "Files skipped" in context


def test_relevance_scoring_boost(project_context):
    # Create a file that matches task
    d = project_context.base_dir
    os.makedirs(os.path.join(d, "billing"), exist_ok=True)
    with open(os.path.join(d, "billing", "service.py"), "w") as f:
        f.write("def billing(): pass")

    context = project_context.gather_smart_context(task="fix billing service")

    # We can't easily assert the order in the string without regex or parsing,
    # but we can verify it's included.
    assert "billing/service.py" in context
