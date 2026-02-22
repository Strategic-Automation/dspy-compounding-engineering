import asyncio
import io
import sys
from contextlib import redirect_stdout, redirect_stderr
from typing import Optional

from mcp.server.fastmcp import FastMCP

from config import configure_dspy
from workflows.plan import run_plan
from workflows.review import run_review
from workflows.sync import run_sync
from workflows.triage import run_triage
from workflows.work import run_unified_work

mcp = FastMCP("Compounding Engineering")


def _run_with_captured_output(func, *args, **kwargs) -> str:
    """Helper to run a synchronous CLI function and capture its stdout/stderr."""
    # Ensure DSPy is configured before running any workflow
    configure_dspy()
    
    f = io.StringIO()
    with redirect_stdout(f), redirect_stderr(f):
        try:
            func(*args, **kwargs)
        except Exception as e:
            print(f"ERROR: {e}")
    return f.getvalue()


@mcp.tool()
def compounding_review(target: str = "latest", project: bool = False, agent_filter: Optional[str] = None) -> str:
    """
    Perform exhaustive multi-agent code reviews.
    
    Args:
        target: The target to review. Can be a PR ID (e.g., '86'), full URL, 
               branch name, or 'latest' (the default) to review local changes.
        project: If True, review entire project instead of just changes.
        agent_filter: Optional pattern to run only specific review agents.
    """
    # agent_filter needs careful handling as CLI expects a list
    agent_list = [agent_filter] if agent_filter else None
    
    # We must validate it just like the CLI does
    from utils.io import validate_agent_filters
    safe_agent_filter = validate_agent_filters(agent_list) if agent_list else None
    
    return _run_with_captured_output(run_review, target, project=project, agent_filter=safe_agent_filter)


@mcp.tool()
def compounding_plan(description: str) -> str:
    """
    Transform feature descriptions or GitHub issues into project plans.
    
    Args:
        description: Feature description, GitHub issue ID, or URL.
    """
    return _run_with_captured_output(run_plan, description)


@mcp.tool()
def compounding_work(pattern: Optional[str] = None, dry_run: bool = False, sequential: bool = False, in_place: bool = True) -> str:
    """
    Unified work command using DSPy ReAct. Automatically detects input type
    (Todo ID, Plan file, or Pattern) and executes the resolution steps.
    
    Args:
        pattern: Todo ID, plan file, or pattern (e.g., 'p1', 'security').
        dry_run: Dry run mode (simulate changes).
        sequential: Execute todos sequentially instead of in parallel.
        in_place: Apply changes in-place to current branch (True, default) or use isolated worktree (False).
    """
    return _run_with_captured_output(
        run_unified_work,
        pattern=pattern,
        dry_run=dry_run,
        parallel=not sequential,
        max_workers=5,
        in_place=in_place,
    )


@mcp.tool()
def compounding_triage() -> str:
    """
    Triage and categorize findings for the CLI todo system. Note: This command is 
    typically interactive. In an MCP context, interactive tools may hang or require 
    specific client support.
    """
    return _run_with_captured_output(run_triage)


@mcp.tool()
def compounding_sync(dry_run: bool = False, pattern: str = "*") -> str:
    """
    Sync local Markdown todos to GitHub issues.
    
    Args:
        dry_run: Preview without creating issues.
        pattern: Glob pattern to filter todos (default: "*").
    """
    return _run_with_captured_output(run_sync, dry_run=dry_run, pattern=pattern)


def main():
    """Entry point for the console script."""
    mcp.run()


if __name__ == "__main__":
    main()
