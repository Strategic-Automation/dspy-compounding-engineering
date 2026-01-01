"""
Centralized tool factory for DSPy agents.

This module provides reusable tools for research agents and workflow agents,
ensuring consistent codebase exploration capabilities across the system.
"""

import dspy

from config import registry
from utils.io import list_directory, read_file_range, search_files
from utils.web.documentation import DocumentationFetcher

# --- Documentation Tools ---


def get_documentation_tool() -> dspy.Tool:
    """Returns a tool for fetching external documentation from URLs."""
    fetcher = DocumentationFetcher()

    def fetch_documentation(url: str) -> str:
        """
        Fetches and parses official documentation from a given URL.
        Use this to get up-to-date API references, guides, and examples.
        """
        return fetcher.fetch(url)

    return dspy.Tool(fetch_documentation)


def get_search_learnings_tool() -> dspy.Tool:
    """Returns a tool for retrieving codified best practices from the knowledge base."""

    def search_learnings(query: str) -> str:
        """
        Retrieve codified best practices, past review patterns, and architectural insights.
        Use this to ensure the new agent follows existing project standards.
        """
        kb = registry.get_kb()
        return kb.get_context_string(query)

    return dspy.Tool(search_learnings)


# --- Search Tools ---


def get_internet_search_tool() -> dspy.Tool:
    """Returns a tool for searching the live internet for current information."""

    def internet_search(query: str) -> str:
        """
        Search the internet for current best practices, standards, and information.
        Returns a list of relevant URLs with titles and sources.
        """
        from utils.search import search_web

        results = search_web(query)
        if not results:
            return "No search results found."

        output = []
        for r in results:
            title = r.get("title", "No Title")
            url = r.get("url", "No URL")
            source = r.get("source", "Unknown")
            output.append(f"- **{title}**\n  URL: {url}\n  Source: {source}")

        return "\n\n".join(output)

    return dspy.Tool(internet_search)


# --- Codebase Exploration Tools ---


def get_codebase_search_tool(base_dir: str = ".") -> dspy.Tool:
    """Returns a tool for searching strings/patterns in project files."""

    def search_codebase(query: str, path: str = ".") -> str:
        """
        Search for a string or pattern in project files using grep.
        Returns matching lines with file paths and line numbers.
        """
        return search_files(query=query, path=path, regex=False, base_dir=base_dir)

    return dspy.Tool(search_codebase)


def get_semantic_search_tool() -> dspy.Tool:
    """Returns a tool for semantic/vector search over the indexed codebase."""

    def semantic_search(query: str, limit: int = 5) -> str:
        """
        Search for relevant code using semantic/vector search.
        Returns the most relevant code snippets based on meaning, not just keywords.
        Use this to find files and code related to a concept or feature.
        """
        kb = registry.get_kb()
        results = kb.search_codebase(query, limit=limit)
        if not results:
            return (
                "No semantic matches found. Try a different query "
                "or use search_codebase for keyword search."
            )

        output = []
        for r in results:
            file_path = r.get("path", r.get("file_path", "unknown"))
            chunk = r.get("chunk_index", 0)
            content = r.get("content", "")[:500]  # Limit content preview
            score = r.get("score", 0)
            output.append(
                f"**{file_path}** (chunk {chunk}, score: {score:.2f}):\n```\n{content}\n```"
            )

        return "\n\n".join(output)

    return dspy.Tool(semantic_search)


def get_file_reader_tool(base_dir: str = ".") -> dspy.Tool:
    """Returns a tool for reading specific lines from a file."""

    def read_file(file_path: str, start_line: int = 1, end_line: int = 100) -> str:
        """
        Read specific lines from a file. Returns the content between
        start_line and end_line (inclusive, 1-indexed).
        """
        return read_file_range(
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            base_dir=base_dir,
        )

    return dspy.Tool(read_file)


def get_directory_tool(base_dir: str = ".") -> dspy.Tool:
    """Returns a tool for listing directory contents."""

    def list_dir(path: str = ".") -> str:
        """
        List files and directories at the given path.
        Returns a structured listing of the directory contents.
        """
        return list_directory(path=path, base_dir=base_dir)

    return dspy.Tool(list_dir)


def get_gather_context_tool() -> dspy.Tool:
    """Returns a tool for gathering smart project context."""
    from utils.context import ProjectContext

    def gather_context(task: str) -> str:
        """
        Gathers comprehensive project context related to a specific task.
        Use this to quickly understand the current project state and relevant files.
        """
        ctx = ProjectContext()
        return ctx.gather_smart_context(task)

    return dspy.Tool(gather_context)


# --- Tool Bundles ---


def get_research_tools(base_dir: str = ".") -> list[dspy.Tool]:
    """
    Get the standard set of tools for research agents.
    Includes: documentation fetcher, semantic search, codebase grep, file reader.
    """
    return [
        get_documentation_tool(),
        get_search_learnings_tool(),  # Internal best practices
        get_internet_search_tool(),  # Live internet search
        get_semantic_search_tool(),  # Vector search for relevant code
        get_codebase_search_tool(base_dir),  # Grep-based keyword search
        get_file_reader_tool(base_dir),  # Read specific file sections
        get_audit_logs_tool(),
    ]


def get_work_tools(base_dir: str = ".") -> list[dspy.Tool]:
    """
    Get the standard set of tools for work/execution agents.
    Includes: codebase search, semantic search, file reader, directory listing.
    """
    return [
        get_search_learnings_tool(),
        get_codebase_search_tool(base_dir),
        get_semantic_search_tool(),
        get_file_reader_tool(base_dir),
        get_directory_tool(base_dir),
        get_audit_logs_tool(),
    ]


def get_file_editor_tool(base_dir: str = ".") -> dspy.Tool:
    """Returns a tool for editing specific lines in a file."""
    from utils.io import edit_file_lines

    def edit_file(file_path: str, edits: list) -> str:
        """
        Edit specific lines in a file. 'edits' is a list of dicts with
        'start_line', 'end_line', 'content' keys.

        CRITICAL: The 'content' MUST NOT include surrounding lines unless you
        INTEND to duplicate them. Only include the lines you want to change.
        """
        return edit_file_lines(file_path=file_path, edits=edits, base_dir=base_dir)

    return dspy.Tool(edit_file)


def get_file_creator_tool(base_dir: str = ".") -> dspy.Tool:
    """Returns a tool for creating new files."""
    from utils.io import create_file

    def create_new_file(file_path: str, content: str) -> str:
        """
        Create a new file with the given content.
        Returns a success message or error.
        """
        return create_file(file_path=file_path, content=content, base_dir=base_dir)

    return dspy.Tool(create_new_file)


def get_system_status_tool() -> dspy.Tool:
    """Returns a tool for checking system status."""
    from utils.io import get_system_status

    return dspy.Tool(get_system_status)


def get_audit_logs_tool() -> dspy.Tool:
    """Returns a tool for reading the system's audit logs."""
    from utils.io.logger import logger

    def get_audit_logs(limit: int = 100) -> str:
        """
        Retrieves the last N lines of the system's execution logs.
        Use this to audit your own past actions, see error details,
        or understand the full sequence of events in a workflow.
        """
        return logger.get_logs(limit=limit)

    return dspy.Tool(get_audit_logs)


def get_todo_resolver_tools(base_dir: str = ".") -> list[dspy.Tool]:
    """
    Get the full set of tools for todo resolution agents.
    Includes: directory listing, codebase search, semantic search, file reader,
    file editor, file creator, gather context, system status, and audit logs.
    """
    return [
        get_directory_tool(base_dir),
        get_codebase_search_tool(base_dir),
        get_semantic_search_tool(),
        get_file_reader_tool(base_dir),
        get_file_editor_tool(base_dir),
        get_file_creator_tool(base_dir),
        get_gather_context_tool(),
        get_system_status_tool(),
        get_audit_logs_tool(),
    ]
