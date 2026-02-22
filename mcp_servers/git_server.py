from mcp.server.fastmcp import FastMCP

from utils.git.service import GitService

mcp = FastMCP("Git Server")


@mcp.tool()
def get_file_status_summary(target: str = "HEAD") -> str:
    """
    Get a summary of file statuses (Added, Modified, Deleted, Renamed).
    Useful for providing high-level context to LLMs before the full diff.
    """
    return GitService.get_file_status_summary(target=target)


@mcp.tool()
def get_diff(target: str = "HEAD") -> str:
    """Get git diff for a target (commit, branch, staged, or file path)."""
    return GitService.get_diff(target=target)


@mcp.tool()
def get_current_branch() -> str:
    """Get current branch name."""
    return GitService.get_current_branch()


if __name__ == "__main__":
    mcp.run()
