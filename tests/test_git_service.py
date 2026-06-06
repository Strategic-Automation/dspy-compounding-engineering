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


@patch("shutil.which")
@patch("utils.git.service.GitService.get_pr_details")
@patch("utils.git.service.GitService._get_repo_from_remote")
@patch("utils.git.service.run_safe_command")
def test_checkout_pr_worktree_fork(
    mock_run_safe, mock_get_repo, mock_get_pr_details, mock_which
):
    """Test that checkout_pr_worktree correctly handles a fork PR using gh CLI."""
    mock_which.return_value = "/usr/bin/gh"

    mock_get_pr_details.return_value = {
        "number": 123,
        "headRefName": "feature-branch",
        "headRepositoryOwner": {"login": "contributor_name"},
    }
    mock_get_repo.return_value = "main_owner/main_repo"

    # Mock the return value of remote list
    mock_remote_list = MagicMock()
    mock_remote_list.stdout = "origin\n"
    mock_run_safe.return_value = mock_remote_list

    GitService.checkout_pr_worktree("123", "/tmp/worktree")

    # Verify we added the fork remote
    mock_run_safe.assert_any_call(["git", "remote", "add", "fork-contributor_name", "https://github.com/contributor_name/main_repo.git"], check=True)
    # Verify we fetched the fork remote
    mock_run_safe.assert_any_call(["git", "fetch", "fork-contributor_name", "feature-branch"], check=True)
    # Verify we created the worktree tracking the fork remote
    mock_run_safe.assert_any_call(["git", "worktree", "add", "-B", "review-pr-123", "/tmp/worktree", "fork-contributor_name/feature-branch"], check=True)


# =============================================================================
# Tests for get_git_log_search (Issue #76)
# =============================================================================


def test_get_git_log_search_success():
    """Test successful git log -S search returning matches."""
    log_output = (
        "abc1234|John Doe|john@example.com|2026-01-15 10:30:00 +0000|Add search endpoint\n"
        "def5678|Jane Smith|jane@example.com|2026-01-10 14:20:00 +0000|Refactor search module\n"
    )
    mock_result = MagicMock(returncode=0, stdout=log_output, stderr="")

    with patch("utils.git.service.run_safe_command", return_value=mock_result):
        result = GitService.get_git_log_search(query="search")

    assert "Found 2 commit(s) containing 'search'" in result
    assert "abc1234" in result
    assert "def5678" in result
    assert "John Doe" in result
    assert "Add search endpoint" in result
    # verify the cmd included -S flag
    call_args = mock_result.__class__.call_args_list if hasattr(mock_result, "call_args_list") else None
    # Instead check via patch verification
    with patch("utils.git.service.run_safe_command", return_value=mock_result) as mock_cmd:
        GitService.get_git_log_search(query="search", path="src/")
        cmd = mock_cmd.call_args[0][0]
        assert "-S" in cmd
        assert "search" in cmd
        assert "src/" in cmd


def test_get_git_log_search_no_results():
    """Test git log -S search with no matches."""
    mock_result = MagicMock(returncode=0, stdout="", stderr="")

    with patch("utils.git.service.run_safe_command", return_value=mock_result):
        result = GitService.get_git_log_search(query="nonexistent_term_xyz")

    assert "No commits found containing 'nonexistent_term_xyz'" in result


def test_get_git_log_search_command_failure():
    """Test git log -S when git command fails."""
    mock_result = MagicMock(returncode=128, stdout="", stderr="fatal: bad revision")

    with patch("utils.git.service.run_safe_command", return_value=mock_result):
        result = GitService.get_git_log_search(query="test")

    assert "git log -S search failed" in result
    assert "fatal: bad revision" in result


def test_get_git_log_search_exception_handling():
    """Test that unexpected exceptions return a clean error message."""
    with patch("utils.git.service.run_safe_command", side_effect=OSError("git not found")):
        result = GitService.get_git_log_search(query="test")

    assert "git log -S search error" in result


# =============================================================================
# Tests for get_git_blame (Issue #76)
# =============================================================================


def test_get_git_blame_success():
    """Test successful git blame output."""
    blame_output = (
        "abc1234 (John Doe 2026-01-15 1) def hello():\n"
        "  def5678 (Jane Smith 2026-01-16 2)     return 'world'\n"
    )
    mock_result = MagicMock(returncode=0, stdout=blame_output, stderr="")

    with (
        patch("os.path.isfile", return_value=True),
        patch("os.path.getsize", return_value=1000),
        patch("utils.git.service.run_safe_command", return_value=mock_result),
    ):
        result = GitService.get_git_blame(file_path="src/main.py")

    assert "abc1234" in result
    assert "John Doe" in result
    assert "def hello():" in result
    assert "Jane Smith" in result


def test_get_git_blame_file_not_found():
    """Test blame when the file doesn't exist."""
    with patch("os.path.isfile", return_value=False):
        result = GitService.get_git_blame(file_path="nonexistent.py")

    assert "File not found: nonexistent.py" in result


def test_get_git_blame_file_too_large():
    """Test blame rejects oversized files."""
    with (
        patch("os.path.isfile", return_value=True),
        patch("os.path.getsize", return_value=5_000_000),
    ):
        result = GitService.get_git_blame(file_path="huge_file.py")

    assert "File too large for blame" in result


def test_get_git_blame_command_failure():
    """Test blame when git command fails."""
    mock_result = MagicMock(returncode=128, stdout="", stderr="fatal: no such path")

    with (
        patch("os.path.isfile", return_value=True),
        patch("os.path.getsize", return_value=500),
        patch("utils.git.service.run_safe_command", return_value=mock_result),
    ):
        result = GitService.get_git_blame(file_path="src/main.py")

    assert "git blame failed" in result
    assert "fatal: no such path" in result


def test_get_git_blame_truncation():
    """Test that very long blame output is truncated at 200 lines."""
    lines = [f"abc1234 (Author {i})     line {i}" for i in range(300)]
    mock_result = MagicMock(returncode=0, stdout="\n".join(lines) + "\n", stderr="")

    with (
        patch("os.path.isfile", return_value=True),
        patch("os.path.getsize", return_value=10000),
        patch("utils.git.service.run_safe_command", return_value=mock_result),
    ):
        result = GitService.get_git_blame(file_path="long_file.py")

    assert "100 more lines truncated" in result
    # Should contain content from first 200 lines
    assert "Author 0" in result
    assert "Author 99" in result
    # Line 250 should NOT be present (beyond first 200)
    blame_output_lines = result.splitlines()
    assert len(blame_output_lines) <= 201  # 200 + truncation message


def test_get_git_blame_os_error():
    """Test blame handles OSError from getsize gracefully."""
    with (
        patch("os.path.isfile", return_value=True),
        patch("os.path.getsize", side_effect=OSError("permission denied")),
    ):
        result = GitService.get_git_blame(file_path="src/main.py")

    assert "Cannot access file" in result

