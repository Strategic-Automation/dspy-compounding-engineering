from pathlib import Path
from typing import Dict, List, Optional, Union

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


def _format_grep_result(process, max_lines: int = 50) -> str:
    """Format grep process output with a line limit."""
    if process.returncode == 0:
        lines = process.stdout.splitlines()
        if len(lines) > max_lines:
            return "\n".join(lines[:max_lines]) + f"\n... and {len(lines) - max_lines} more matches"
        return process.stdout
    elif process.returncode == 1:
        return "No matches found."
    else:
        return f"Error searching files: {process.stderr}"


def _run_git_grep(query: str, safe_path: str, regex: bool, limit: int = 50) -> Optional[str]:
    """Helper to run git grep."""
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
            return _format_grep_result(process, max_lines=limit)
    except Exception as e:
        msg = f"[dim]Note: git grep failed (likely not a git repo or no matches): {e}[/dim]"
        console.print(msg)
    return None


def _run_standard_grep(query: str, safe_path: str, regex: bool, limit: int = 50) -> str:
    """Helper to run standard grep with exclusions."""
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

    process = run_safe_command(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    return _format_grep_result(process, max_lines=limit)


def search_files(
    query: str, path: str = ".", regex: bool = False, base_dir: str = ".", limit: int = 50
) -> str:
    """
    Search for a string or regex in files at the given path.
    Uses git grep if available, otherwise falls back to grep -r with exclusions.
    """
    try:
        safe_path = validate_path(path, base_dir)

        # 1. Try git grep first
        git_result = _run_git_grep(query, safe_path, regex, limit=limit)
        if git_result:
            return git_result

        # 2. Fallback to standard grep
        return _run_standard_grep(query, safe_path, regex, limit=limit)

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


def _normalize_llm_escapes(content: str) -> str:
    """Normalize escaped newlines/tabs from LLM output to actual characters.

    LLMs sometimes generate literal backslash-n sequences instead of actual
    newlines when constructing multi-line code edits. This function converts
    them to real newlines.

    Uses regex with raw strings to ensure we match the exact two-character
    sequence (backslash followed by 'n').
    """
    import re

    if not content:
        return content

    # Match literal backslash followed by 'n' (two characters, not escape sequence)
    # The raw string r'\\n' matches the two-character sequence: \ followed by n
    content = re.sub(r'\\n', '\n', content)
    content = re.sub(r'\\t', '\t', content)
    # Handle escaped quotes
    content = re.sub(r'\\"', '"', content)
    content = re.sub(r"\\'", "'", content)

    return content


def _validate_file_syntax(file_path: str, content: str) -> tuple:
    """Validate file syntax before writing.

    Returns (is_valid, error_message) tuple.
    """
    ext = Path(file_path).suffix.lower()

    if ext == ".py":
        try:
            import ast
            ast.parse(content)
            return (True, "")
        except SyntaxError as e:
            return (False, f"Python syntax error at line {e.lineno}: {e.msg}")

    if ext == ".json":
        try:
            import json
            json.loads(content)
            return (True, "")
        except json.JSONDecodeError as e:
            return (False, f"JSON syntax error: {e}")

    if ext in (".yaml", ".yml"):
        try:
            import yaml
            yaml.safe_load(content)
            return (True, "")
        except yaml.YAMLError as e:
            return (False, f"YAML syntax error: {e}")

    if ext == ".toml":
        try:
            import tomllib
            tomllib.loads(content)
            return (True, "")
        except Exception as e:
            return (False, f"TOML syntax error: {e}")

    return (True, "")  # No validation for unknown types


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

            # CRITICAL: Normalize escaped newlines from LLM output
            content = _normalize_llm_escapes(content)

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

        # Validate syntax before writing
        final_content = "".join(lines)
        is_valid, error = _validate_file_syntax(file_path, final_content)
        if not is_valid:
            return f"Error: Edit would create syntax errors - {error}"

        # Write back
        safe_write(file_path, final_content, base_dir)
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
