import pytest
import os
from pathlib import Path
from utils.io.safe import run_safe_command, validate_path

def test_run_safe_command_allowed():
    # 'git status' is in the allowlist
    result = run_safe_command(["git", "status"], capture_output=True)
    assert result.returncode == 0

def test_run_safe_command_denied():
    # 'ls' is NOT in the allowlist
    with pytest.raises(ValueError, match="not in the security allowlist"):
        run_safe_command(["ls"])

def test_run_safe_command_no_shell():
    # shell=True is disallowed
    with pytest.raises(ValueError, match="shell=True is disallowed"):
        run_safe_command(["git", "status"], shell=True)

def test_validate_path_valid(tmp_path):
    base = tmp_path / "app"
    base.mkdir()
    path = "src/main.py"
    # Should not raise
    validated = validate_path(path, str(base))
    assert validated.endswith(path)

def test_validate_path_traversal(tmp_path):
    base = tmp_path / "app"
    base.mkdir()
    path = "../secret.txt"
    with pytest.raises(ValueError, match="Path outside base directory"):
        validate_path(path, str(base))

def test_validate_path_absolute(tmp_path):
    base = tmp_path / "app"
    base.mkdir()
    path = "/etc/passwd"
    with pytest.raises(ValueError, match="Path outside base directory"):
        validate_path(path, str(base))

def test_validate_path_symlink_traversal(tmp_path):
    # Setup: app/
    #        app/data -> /etc/
    base = tmp_path / "app"
    base.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    (external / "confidential.txt").write_text("secrets")
    
    link = base / "trap"
    os.symlink(external, link)
    
    # Even if it looks like it's inside, realpath should catch it
    with pytest.raises(ValueError, match="Path outside base directory"):
        validate_path("trap/confidential.txt", str(base))
