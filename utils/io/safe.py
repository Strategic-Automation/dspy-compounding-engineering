import os
import re
import shutil
import subprocess
from typing import List, Optional

from rich.console import Console

console = Console()


def validate_path(path: str, base_dir: str = ".") -> str:
    """Validate path is relative and within base_dir, preventing traversal."""
    # Ensure base_dir is absolute and symlinks are resolved
    base_abs = os.path.realpath(os.path.abspath(base_dir))

    # Check for path traversal attempts in the raw string
    if ".." in path.split(os.sep) or path.startswith("/") or "://" in path:
        # We allow absolute paths if they are within base_dir, handled by resolution below.
        # But we block external schemes.
        if "://" in path:
            raise ValueError(f"External schemes/URLs not allowed for file operations: {path}")

    # Resolve to absolute path and resolve symlinks
    try:
        full_path = os.path.realpath(os.path.abspath(os.path.join(base_abs, path)))
    except Exception as e:
        raise ValueError(f"Invalid path format: {path}") from e

    # Ensure the resolved path is within the base directory
    if not full_path.startswith(base_abs + os.sep) and full_path != base_abs:
        raise ValueError(f"Path outside base directory (traversal detected): {path} -> {full_path}")

    return full_path


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

    try:
        from config import settings

        allowlist = settings.command_allowlist
    except (ImportError, AttributeError):
        # Bootstrapping fallback if config is not yet fully loaded
        allowlist = {"git", "gh", "grep", "ruff", "uv", "python"}

    if executable not in allowlist:
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


def validate_agent_filters(agent_filters: list[str]) -> list[str] | None:
    """
    Validate and sanitize agent filter terms.

    Args:
        agent_filters: List of agent filter strings from CLI

    Returns:
        Sanitized list of valid filters, or None if no valid filters remain
    """
    from config import settings
    from utils.io.logger import logger

    valid_filters = []
    for term in agent_filters:
        # Use centralized regex from settings
        if not re.match(settings.agent_filter_regex, term):
            logger.warning(f"Filtering term '{term}' contains invalid characters, skipping.")
            continue
        if len(term) > 50:
            logger.warning(f"Filtering term '{term[:10]}...' too long, skipping.")
            continue
        valid_filters.append(term)

    if not valid_filters:
        logger.warning("No valid agent filters provided.")
        return None

    return valid_filters
