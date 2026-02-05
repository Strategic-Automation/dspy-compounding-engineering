"""Tests for the sync command and workflow."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cli import app
from workflows.sync import (
    _extract_github_issue_number,
    _extract_title_from_body,
    _map_priority_to_label,
    _map_tags_to_labels,
)

runner = CliRunner()


class TestHelperFunctions:
    """Tests for helper functions in sync workflow."""

    def test_extract_title_from_body_with_h1(self):
        """Should extract the first H1 heading."""
        body = "Some intro\n# My Title\n\nContent here"
        assert _extract_title_from_body(body) == "My Title"

    def test_extract_title_from_body_no_h1(self):
        """Should return default if no H1 found."""
        body = "## Only H2 heading\nSome content"
        assert _extract_title_from_body(body) == "Untitled Todo"

    def test_map_priority_to_label(self):
        """Should map lowercase priority to uppercase label."""
        assert _map_priority_to_label("p1") == "P1"
        assert _map_priority_to_label("p2") == "P2"
        assert _map_priority_to_label("p3") == "P3"
        assert _map_priority_to_label("unknown") == "P2"  # Default

    def test_map_tags_to_labels_case_insensitive(self):
        """Should map tags to labels case-insensitively."""
        available = ["bug", "Enhancement", "P1"]
        tags = ["Bug", "enhancement", "performance"]
        result = _map_tags_to_labels(tags, available)
        assert "bug" in result
        assert "Enhancement" in result
        assert "performance" not in result  # Not in available

    def test_extract_github_issue_number_from_int(self):
        """Should handle integer input."""
        assert _extract_github_issue_number(42) == 42

    def test_extract_github_issue_number_from_string(self):
        """Should handle string digit input."""
        assert _extract_github_issue_number("123") == 123

    def test_extract_github_issue_number_from_url(self):
        """Should extract number from GitHub URL."""
        url = "https://github.com/owner/repo/issues/456"
        assert _extract_github_issue_number(url) == 456

    def test_extract_github_issue_number_none(self):
        """Should return None for empty input."""
        assert _extract_github_issue_number("") is None
        assert _extract_github_issue_number(None) is None


class TestSyncCommand:
    """Tests for the sync CLI command."""

    @pytest.fixture
    def mock_sync(self):
        """Mock the run_sync function."""
        with patch("cli.run_sync") as m_sync:
            m_sync.return_value = {"created": [], "updated": [], "errors": []}
            yield m_sync

    def test_sync_command_default(self, mock_sync):
        """Sync command should call run_sync with defaults."""
        result = runner.invoke(app, ["sync"])
        assert result.exit_code == 0
        mock_sync.assert_called_once_with(dry_run=False, pattern="*")

    def test_sync_command_dry_run(self, mock_sync):
        """Sync command with --dry-run flag."""
        result = runner.invoke(app, ["sync", "--dry-run"])
        assert result.exit_code == 0
        mock_sync.assert_called_once_with(dry_run=True, pattern="*")

    def test_sync_command_pattern(self, mock_sync):
        """Sync command with --pattern option."""
        result = runner.invoke(app, ["sync", "--pattern", "*-p1-*"])
        assert result.exit_code == 0
        mock_sync.assert_called_once_with(dry_run=False, pattern="*-p1-*")

    def test_sync_help(self):
        """Sync command help should show options."""
        result = runner.invoke(app, ["sync", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in result.stdout
        assert "--pattern" in result.stdout
        assert "GitHub issues" in result.stdout


class TestSyncWorkflow:
    """Integration-style tests for the sync workflow."""

    @pytest.fixture
    def temp_todos_dir(self):
        """Create a temporary todos directory with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            todos_dir = os.path.join(tmpdir, "todos")
            os.makedirs(todos_dir)

            # Create a pending todo
            pending_content = """---
status: pending
priority: p1
tags: [bug, security]
---

# Fix Critical Bug

This is a critical bug that needs fixing.
"""
            with open(os.path.join(todos_dir, "001-pending-p1-fix-bug.md"), "w") as f:
                f.write(pending_content)

            # Create a completed todo (should be skipped)
            completed_content = """---
status: completed
priority: p2
---

# Already Done

This is already completed.
"""
            with open(os.path.join(todos_dir, "002-complete-p2-done.md"), "w") as f:
                f.write(completed_content)

            yield todos_dir

    @patch("workflows.sync.GitHubService")
    def test_sync_creates_issue_for_pending(self, mock_gh, temp_todos_dir):
        """Should create issue for pending todos."""
        from workflows.sync import run_sync

        mock_gh.list_labels.return_value = ["P1", "P2", "P3", "bug", "security"]
        mock_gh.create_issue.return_value = {
            "number": 99,
            "url": "https://github.com/owner/repo/issues/99",
        }

        results = run_sync(dry_run=False, todos_dir=temp_todos_dir)

        # Should have created 1 issue
        assert len(results["created"]) == 1
        assert results["created"][0]["issue"] == 99

        # The todo file should now have github_issue in frontmatter
        with open(os.path.join(temp_todos_dir, "001-pending-p1-fix-bug.md")) as f:
            content = f.read()
        assert "github_issue" in content

    @patch("workflows.sync.GitHubService")
    def test_sync_dry_run_does_not_create(self, mock_gh, temp_todos_dir):
        """Dry run should not create issues."""
        from workflows.sync import run_sync

        results = run_sync(dry_run=True, todos_dir=temp_todos_dir)

        # Should report what would be created
        assert len(results["created"]) == 1
        assert "title" in results["created"][0]

        # But GitHubService.create_issue should NOT be called
        mock_gh.create_issue.assert_not_called()

    @patch("workflows.sync.GitHubService")
    def test_sync_skips_completed_todos(self, mock_gh, temp_todos_dir):
        """Should skip todos with completed status."""
        from workflows.sync import run_sync

        results = run_sync(dry_run=True, todos_dir=temp_todos_dir)

        # Only the pending todo should be processed, not the completed one
        assert len(results["created"]) == 1
        assert "002-complete" not in str(results)
