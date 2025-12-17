from unittest.mock import MagicMock, patch

import pytest

from utils.git.service import GitService


@pytest.fixture
def mock_git_subprocess():
    with patch("subprocess.run") as mock_run:
        yield mock_run


def test_get_file_status_summary_success(mock_git_subprocess):
    """Test parsing of git status output."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    # Simulate: Modified, Added, Deleted, Renamed
    mock_result.stdout = "M\tfile1.py\nA\tfile2.py\nD\tfile3.py\nR100\told.py\tnew.py\n"
    mock_git_subprocess.return_value = mock_result

    summary = GitService.get_file_status_summary("HEAD")

    assert "file1.py" in summary
    assert "file2.py" in summary
    assert "new.py" in summary
    assert "old.py" in summary  # Should be in original output
    assert mock_git_subprocess.call_count == 1
    # Verify -M flag was used
    args = mock_git_subprocess.call_args[0][0]
    assert "-M" in args


def test_get_file_status_summary_failure(mock_git_subprocess):
    """Test error handling when git fails."""
    import subprocess

    mock_git_subprocess.side_effect = subprocess.CalledProcessError(1, ["git", "diff"])

    summary = GitService.get_file_status_summary("HEAD")
    assert "Could not retrieve file status summary" in summary


def test_get_diff_rename_detection(mock_git_subprocess):
    """Test that get_diff uses -M flag."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "diff content"
    mock_git_subprocess.return_value = mock_result

    GitService.get_diff("HEAD")

    args = mock_git_subprocess.call_args[0][0]
    assert "-M" in args
    assert "git" in args
    assert "diff" in args


def test_is_git_repo_true(mock_git_subprocess):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_git_subprocess.return_value = mock_result
    assert GitService.is_git_repo() is True


def test_is_git_repo_false(mock_git_subprocess):
    mock_result = MagicMock()
    mock_result.returncode = 128
    mock_git_subprocess.return_value = mock_result
    assert GitService.is_git_repo() is False
