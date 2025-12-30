from pathlib import Path
from typing import Dict, List, Union

from rich.console import Console

from .safe import run_safe_command, safe_write, validate_path

console = Console()


def list_directory(path: str, base_dir: str = ".") -> str:
    """
    List files and directories at the given path.
    Returns a formatted string listing contents.
    """
    try:
        safe_path_str = validate_path(path, base_dir)
        safe_path = Path(safe_path_str)

        if not safe_path.exists():
            return f"Error: Path not found: {path}"

        if not safe_path.is_dir():
            return f"Error: Not a directory: {path}"

        items = sorted(safe_path.iterdir())
        result = []
        for item in items:
            if item.is_dir():
                result.append(f"{item.name}/")
            else:
                result.append(item.name)

        return "\n".join(result) if result else "(empty directory)"
    except Exception as e:
        return f"Error listing directory: {str(e)}"


def search_files(query: str, path: str = ".", regex: bool = False, base_dir: str = ".") -> str:
    """
    Search for a string or regex in files at the given path.
    Uses git grep if available, otherwise falls back to grep -r with exclusions.
    """
    try:
        safe_path = validate_path(path, base_dir)

        # 1. Try git grep first (faster, respects .gitignore)
        git_cmd = ["git", "grep", "-n"]
        if not regex:
            git_cmd.append("-F")
        git_cmd.append(query)
        git_cmd.append(".")

        try:
            process = run_safe_command(
                git_cmd,
                cwd=safe_path,
                capture_output=True,
                text=True,
                check=False,
            )
            if process.returncode == 0:
                lines = process.stdout.splitlines()
                if len(lines) > 50:
                    return "\n".join(lines[:50]) + f"\n... and {len(lines) - 50} more matches"
                return process.stdout
            elif process.returncode == 1:
                # No matches in git, but there might be untracked files
                pass
        except Exception:
            # git command failed or not a git repo
            pass

        # 2. Fallback to standard grep with exclusions
        cmd = ["grep", "-r", "-n"]
        if not regex:
            cmd.append("-F")

        # Exclude large/irrelevant directories
        exclude_dirs = [
            ".venv",
            "qdrant_storage",
            ".git",
            "site",
            "__pycache__",
            ".knowledge",
            ".pytest_cache",
            "plans",
            "todos",
        ]
        for d in exclude_dirs:
            cmd.append(f"--exclude-dir={d}")

        cmd.append(query)
        cmd.append(safe_path)

        # Run grep
        process = run_safe_command(
            cmd,
            capture_output=True,
            text=True,
            check=False,  # Don't raise on exit code 1 (no matches)
        )

        if process.returncode == 0:
            # Limit output to avoid context overflow
            lines = process.stdout.splitlines()
            if len(lines) > 50:
                return "\n".join(lines[:50]) + f"\n... and {len(lines) - 50} more matches"
            return process.stdout
        elif process.returncode == 1:
            return "No matches found."
        else:
            return f"Error searching files: {process.stderr}"

    except Exception as e:
        return f"Error executing search: {str(e)}"


def read_file_range(
    file_path: str, start_line: int = 1, end_line: int = -1, base_dir: str = "."
) -> str:
    """
    Read a file within a specific line range (1-based).
    If end_line is -1, read to the end.
    """
    try:
        safe_path_str = validate_path(file_path, base_dir)
        safe_path = Path(safe_path_str)

        if not safe_path.exists():
            return f"Error: File not found: {file_path}"

        if not safe_path.is_file():
            return f"Error: Not a file: {file_path}"

        lines = safe_path.read_text(encoding="utf-8").splitlines()

        total_lines = len(lines)
        if start_line < 1:
            start_line = 1
        if end_line == -1 or end_line > total_lines:
            end_line = total_lines

        if start_line > total_lines:
            return f"Error: Start line {start_line} exceeds file length {total_lines}"

        selected_lines = lines[start_line - 1 : end_line]

        # Add line numbers for context
        result = []
        for i, line in enumerate(selected_lines):
            result.append(f"{start_line + i}: {line}")

        return "\n".join(result)

    except Exception as e:
        return f"Error reading file: {str(e)}"


def edit_file_lines(  # noqa: C901
    file_path: str,
    edits: List[Dict[str, Union[int, str]]],
    base_dir: str = ".",
) -> str:
    """
    Edit specific lines in a file.

    Args:
        file_path: Path to the file (relative to base_dir)
        edits: List of dicts with keys:
        - start_line: int (1-indexed)
        - end_line: int (1-indexed, inclusive)
        - content: str (new content)
        base_dir: Base directory for path resolution

    Edits must be non-overlapping and sorted by start_line (descending) to avoid index shifts,
    but we will handle sorting here.
    """
    try:
        # Input Validation (Todo 1009)
        if not isinstance(edits, list):
            return "Error: arguments 'edits' must be a list"

        for i, edit in enumerate(edits):
            if not isinstance(edit, dict):
                return f"Error: edit item {i} must be a dictionary"
            if "start_line" not in edit or "end_line" not in edit or "content" not in edit:
                return f"Error: edit item {i} missing required keys (start_line, end_line, content)"

        safe_path_str = validate_path(file_path, base_dir)
        safe_path = Path(safe_path_str)

        if not safe_path.exists():
            return f"Error: File not found: {file_path}"

        # Read file using pathlib
        lines = safe_path.read_text(encoding="utf-8").splitlines(keepends=True)

        # Sort edits by start_line descending to apply from bottom up
        sorted_edits = sorted(edits, key=lambda x: x["start_line"], reverse=True)

        for edit in sorted_edits:
            start = edit["start_line"]
            end = edit["end_line"]
            content = edit["content"]

            # Validate range
            if start < 1 or end < start:
                return f"Error: Invalid line range {start}-{end}"

            # Adjust for 0-based indexing
            new_lines = [line + "\n" for line in content.splitlines()]
            if not content.endswith("\n") and content:
                pass

            # If content is empty string, it's a deletion
            if content == "":
                new_lines = []

            # Handle extending file if start > len(lines)?
            if start > len(lines) + 1:
                return f"Error: Edit start line {start} beyond EOF {len(lines)}"

            lines[start - 1 : end] = new_lines

        # Write back
        safe_write(file_path, "".join(lines), base_dir)
        return f"Successfully applied {len(edits)} edits to {file_path}"

    except Exception as e:
        return f"Error editing file: {str(e)}"


def create_file(file_path: str, content: str, base_dir: str = ".") -> str:
    """
    Create a new file with the given content.
    Fails if file already exists.
    """
    try:
        safe_write(file_path, content, base_dir=base_dir, overwrite=False)
        return f"Successfully created file: {file_path}"
    except FileExistsError:
        return f"Error: File already exists: {file_path}"
    except Exception as e:
        return f"Error creating file: {str(e)}"


def get_project_context(task: str = "", base_dir: str = ".") -> str:
    """
    Gather relevant project context (file contents) based on a task description.
    Uses smart relevance scoring and lazy loading.
    """
    try:
        from ..context.project import ProjectContext

        ctx = ProjectContext(base_dir=base_dir)
        return ctx.gather_smart_context(task=task)
    except Exception as e:
        return f"Error gathering project context: {str(e)}"
