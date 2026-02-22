from mcp.server.fastmcp import FastMCP

from config import registry
from utils.io import search_files
from utils.search import internet_search as run_search

mcp = FastMCP("Search Server")


@mcp.tool()
def search_codebase(query: str, path: str = ".", limit: int = 50) -> str:
    """
    Search for a string or pattern in project files using grep.
    Returns matching lines with file paths and line numbers.
    """
    return search_files(query=query, path=path, regex=False, base_dir=".", limit=limit)


@mcp.tool()
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


@mcp.tool()
def internet_search(query: str) -> str:
    """
    Search the internet for current best practices, standards, and information.
    Returns a list of relevant URLs with titles and sources.
    """
    return run_search(query)


if __name__ == "__main__":
    mcp.run()
