import os
import shutil
import subprocess
from typing import List, Optional, Union

from rich.console import Console

console = Console()


def validate_path(path: str, base_dir: str = ".") -> str:
    """Validate path is relative and within base_dir, preventing traversal."""
    # Ensure base_dir is absolute
    base_abs = os.path.abspath(base_dir)
    
    # Check for path traversal attempts in the raw string
    if ".." in path.split(os.sep) or path.startswith("/") or "://" in path:
        # We allow absolute paths if they are within base_dir, handled by resolution below.
        # But we block external schemes.
        if "://" in path:
            raise ValueError(f"External schemes/URLs not allowed for file operations: {path}")

    # Resolve to absolute path
    try:
        full_path = os.path.abspath(os.path.join(base_abs, path))
    except Exception as e:
        raise ValueError(f"Invalid path format: {path}") from e

    # Ensure the resolved path is within the base directory
    if not full_path.startswith(base_abs + os.sep) and full_path != base_abs:
        raise ValueError(f"Path outside base directory (traversal detected): {path} -> {full_path}")

    return full_path


COMMAND_ALLOWLIST = {"git", "gh", "grep", "ruff", "uv", "python"}


def run_safe_command(
    cmd: List[str],
    cwd: Optional[str] = None,
    capture_output: bool = True,
    text: bool = True,
    check: bool = True,
    **kwargs,
) -> subprocess.CompletedProcess:
    """
    Safely execute a command from an allowlist.
    Disallows shell=True and validates the executable.
    """
    if kwargs.get("shell"):
        raise ValueError("Running commands with shell=True is disallowed for security.")

    if not cmd:
        raise ValueError("Empty command list.")

    # Get the base executable name (handle paths if necessary)
    executable = os.path.basename(cmd[0])
    if executable not in COMMAND_ALLOWLIST:
        raise ValueError(f"Command '{executable}' is not in the security allowlist.")

    return subprocess.run(
        cmd, cwd=cwd, capture_output=capture_output, text=text, check=check, **kwargs
    )


def safe_write(file_path: str, content: str, base_dir: str = ".", overwrite: bool = True) -> None:
    """
    Safely write content to file within base_dir.
    If overwrite is False and file exists, raises FileExistsError.
    """
    safe_path = validate_path(file_path, base_dir)
    if not overwrite and os.path.exists(safe_path):
        raise FileExistsError(f"File already exists: {file_path}")

    os.makedirs(os.path.dirname(safe_path), exist_ok=True)
    with open(safe_path, "w", encoding="utf-8") as f:
        f.write(content)
    console.print(f"[green]Wrote:[/green] {safe_path}")


def safe_delete(file_path: str, base_dir: str = ".") -> None:
    """Safely delete file or directory within base_dir."""
    safe_path = validate_path(file_path, base_dir)
    if os.path.exists(safe_path):
        if os.path.isfile(safe_path):
            os.remove(safe_path)
            console.print(f"[green]Deleted file:[/green] {safe_path}")
        elif os.path.isdir(safe_path):
            shutil.rmtree(safe_path)
            console.print(f"[green]Deleted dir:[/green] {safe_path}")
        else:
            console.print(f"[yellow]Path exists but not file/dir:[/yellow] {safe_path}")
    else:
        console.print(f"[yellow]Path not found:[/yellow] {safe_path}")


def safe_apply_operations(operations: list[dict], base_dir: str = ".") -> None:
    """Safely apply a list of file operations (create/modify/delete)."""
    for op in operations:
        action = op.get("action")
        if action in ("create", "modify"):
            safe_write(op["file_path"], op["content"], base_dir)
        elif action == "delete":
            safe_delete(op["file_path"], base_dir)
        else:
            console.print(f"[yellow]Unknown action skipped:[/yellow] {action}")


def skip_ai_commands(
    commands: list, reason: str = "AI-generated commands disabled for security"
) -> None:
    """Log and skip AI-generated commands."""
    if commands:
        console.print(f"[bold yellow]{reason}: {len(commands)} command(s) skipped[/bold yellow]")
        for cmd in commands[:3]:  # Show first few
            console.print(f"  - {cmd}")
        if len(commands) > 3:
            console.print(f"  ... and {len(commands) - 3} more")
