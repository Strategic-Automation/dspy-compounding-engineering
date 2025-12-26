import os
import shutil

from rich.console import Console

console = Console()


def validate_path(path: str, base_dir: str = ".") -> str:
    """Validate path is relative and within base_dir, preventing traversal."""
    # We allow absolute paths as long as they resolve to a location within base_dir.
    # This is necessary for internal services that use absolute paths (like ProjectContext).
    # If it is absolute, we don't need to join it with base_dir.

    # Check for path traversal attempts
    if ".." in path.split(os.sep):
        raise ValueError(f"Path traversal detected: {path}")

    # Resolve both to absolute paths for comparison
    base_abs = os.path.abspath(base_dir)
    full_path = os.path.abspath(os.path.join(base_dir, path))

    # Ensure the resolved path is within the base directory
    if not full_path.startswith(base_abs + os.sep) and full_path != base_abs:
        raise ValueError(f"Path outside base directory (traversal detected): {path} -> {full_path}")

    return full_path


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
