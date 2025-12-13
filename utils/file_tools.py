import os
import subprocess
from typing import Dict, List, Union

from rich.console import Console

from utils.safe_io import safe_write, validate_path

console = Console()


def list_directory(path: str, base_dir: str = ".") -> str:
    """
    List files and directories at the given path.
    Returns a formatted string listing contents.
    """
    try:
        safe_path = validate_path(path, base_dir)
        if not os.path.exists(safe_path):
            return f"Error: Path not found: {path}"

        if not os.path.isdir(safe_path):
            return f"Error: Not a directory: {path}"

        items = sorted(os.listdir(safe_path))
        result = []
        for item in items:
            item_path = os.path.join(safe_path, item)
            if os.path.isdir(item_path):
                result.append(f"{item}/")
            else:
                result.append(item)

        return "\n".join(result) if result else "(empty directory)"
    except Exception as e:
        return f"Error listing directory: {str(e)}"


def search_files(
    query: str, path: str = ".", regex: bool = False, base_dir: str = "."
) -> str:
    """
    Search for a string or regex in files at the given path using grep.
    """
    try:
        safe_path = validate_path(path, base_dir)

        # Construct grep command
        cmd = ["grep", "-r", "-n"]  # recursive, line number
        if not regex:
            cmd.append("-F")  # fixed string
        cmd.append(query)
        cmd.append(safe_path)

        # Run grep
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,  # Don't raise on exit code 1 (no matches)
        )

        if process.returncode == 0:
            # Limit output to avoid context overflow
            lines = process.stdout.splitlines()
            if len(lines) > 50:
                return (
                    "\n".join(lines[:50]) + f"\n... and {len(lines) - 50} more matches"
                )
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
        safe_path = validate_path(file_path, base_dir)
        if not os.path.exists(safe_path):
            return f"Error: File not found: {file_path}"

        if not os.path.isfile(safe_path):
            return f"Error: Not a file: {file_path}"

        with open(safe_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        total_lines = len(lines)
        if start_line < 1:
            start_line = 1
        if end_line == -1 or end_line > total_lines:
            end_line = total_lines

        if start_line > total_lines:
            return f"Error: Start line {start_line} exceeds file length {total_lines}"

        # Adjust for 0-based indexing
        selected_lines = lines[start_line - 1 : end_line]

        # Add line numbers for context
        result = []
        for i, line in enumerate(selected_lines):
            result.append(f"{start_line + i}: {line.rstrip()}")

        return "\n".join(result)

    except Exception as e:
        return f"Error reading file: {str(e)}"


def edit_file_lines(
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
        safe_path = validate_path(file_path, base_dir)
        if not os.path.exists(safe_path):
            return f"Error: File not found: {file_path}"

        with open(safe_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

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
            # Replace lines[start-1 : end] with new content
            # Content might be multiple lines
            new_lines = [line + "\n" for line in content.splitlines()]
            if not content.endswith("\n") and content:
                # If content doesn't end with newline, the last line shouldn't have one if it's the EOF?
                # Actually, usually we want to preserve file structure.
                # Let's just ensure new_lines has \n except maybe last if intended.
                # For simplicity, splitlines() removes \n, so we add them back.
                pass

            # If content is empty string, it's a deletion
            if content == "":
                new_lines = []

            # Handle extending file if start > len(lines)?
            # For now, assume edits are within or at end of file.
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
        safe_path = validate_path(file_path, base_dir)
        if os.path.exists(safe_path):
            return "Error: File already exists"

        safe_write(file_path, content, base_dir)
        return f"Successfully created file: {file_path}"
    except Exception:
        return "Error creating file: Invalid path or permission denied"
