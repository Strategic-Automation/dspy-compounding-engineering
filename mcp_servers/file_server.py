from mcp.server.fastmcp import FastMCP
import os

from utils.io import read_file_range, list_directory, edit_file_lines, create_file

mcp = FastMCP("File Server")


@mcp.tool()
def read_file(file_path: str, start_line: int = 1, end_line: int = 100) -> str:
    """
    Read specific lines from a file. Returns the content between
    start_line and end_line (inclusive, 1-indexed).
    """
    return read_file_range(
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
        base_dir="."
    )


@mcp.tool()
def list_dir(path: str = ".") -> str:
    """
    List files and directories at the given path.
    Returns a structured listing of the directory contents.
    """
    return list_directory(path=path, base_dir=".")


@mcp.tool()
def edit_file(file_path: str, edits: list) -> str:
    """
    Edit specific lines in a file. 'edits' is a list of dicts with
    'start_line', 'end_line', 'content' keys.

    CRITICAL: The 'content' MUST NOT include surrounding lines unless you
    INTEND to duplicate them. Only include the lines you want to change.
    """
    return edit_file_lines(file_path=file_path, edits=edits, base_dir=".")


@mcp.tool()
def create_new_file(file_path: str, content: str) -> str:
    """
    Create a new file with the given content.
    Returns a success message or error.
    """
    return create_file(file_path=file_path, content=content, base_dir=".")


if __name__ == "__main__":
    mcp.run()
