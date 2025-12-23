"""FastMCP Server for Compounding Engineering CLI

This MCP server exposes the Compounding Engineering CLI commands as extensible tools
for LLM applications, enabling programmatic access to the intelligent codebase analysis
and workflow automation capabilities.
"""

from fastmcp import FastMCP
import subprocess
import json
from typing import Optional
import os

# Initialize FastMCP server
mcp = FastMCP("Compounding Engineering MCP Server")

# Set working directory to the repository root (where cli.py is located)
REPO_ROOT = os.environ.get("COMPOUNDING_ROOT", ".")

def run_cli_command(command: str, *args, dry_run: bool = False) -> dict:
    """
    Helper function to run CLI commands safely
    
    Args:
        command: Main command name (e.g., "triage", "plan")
        *args: Additional arguments
        dry_run: If True, show what would be executed
    
    Returns:
        dict with status, output, and error information
    """
    try:
        cmd = ["python", f"{REPO_ROOT}/cli.py", command] + list(args)
        
        if dry_run:
            return {
                "status": "dry_run",
                "command": " ".join(cmd),
                "message": "Dry run mode - command would be executed"
            }
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=300  # 5 minute timeout
        )
        
        return {
            "status": "success" if result.returncode == 0 else "error",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "error": "Command execution timed out (5 minutes)"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# ============================================================================
# MCP TOOLS FOR COMPOUNDING ENGINEERING CLI COMMANDS
# ============================================================================

@mcp.tool
def triage() -> str:
    """
    Triage and categorize findings for the CLI todo system.
    
    This tool analyzes the current project state and categorizes findings into
    actionable items within the todo system.
    
    Returns:
        Analysis results with categorized findings
    """
    result = run_cli_command("triage")
    return json.dumps(result, indent=2)


@mcp.tool
def plan(feature_description: str) -> str:
    """
    Transform feature descriptions into well-structured project plans.
    
    Takes a natural language feature description and generates a comprehensive
    project plan with tasks, milestones, and implementation details.
    
    Args:
        feature_description: Natural language description of the feature to plan
    
    Returns:
        Generated project plan in structured format
    """
    result = run_cli_command("plan", feature_description)
    return json.dumps(result, indent=2)


@mcp.tool
def work(
    pattern: Optional[str] = None,
    dry_run: bool = False,
    sequential: bool = False,
    max_workers: int = 3,
    in_place: bool = True
) -> str:
    """
    Unified work command using DSPy ReAct for intelligent task execution.
    
    Automatically detects input type:
    - Todo ID: \"001\"
    - Plan file: \"plans/feature.md\"
    - Pattern: \"p1\", \"security\", etc.
    
    This replaces the old resolve-todo command and provides unified interface
    for all todo resolution and plan execution.
    
    Args:
        pattern: Todo ID, plan file path, or pattern to match
        dry_run: If True, show what would be executed without making changes
        sequential: If True, execute todos sequentially instead of in parallel
        max_workers: Maximum number of parallel workers (default: 3)
        in_place: If True, apply changes in-place to current branch (default)
                 If False, use isolated worktree
    
    Returns:
        Execution results with status and completion details
    """
    args = []
    if pattern:
        args.append(pattern)
    
    if dry_run:
        args.extend(["--dry-run"])
    if sequential:
        args.extend(["--sequential"])
    if max_workers != 3:
        args.extend(["--workers", str(max_workers)])
    if not in_place:
        args.append("--worktree")
    
    result = run_cli_command("work", *args)
    return json.dumps(result, indent=2)


@mcp.tool
def review(
    pr_url_or_id: str = "latest",
    project: bool = False
) -> str:
    """
    Perform exhaustive multi-agent code reviews.
    
    Conducts comprehensive code review using multiple specialized agents that
    analyze different aspects (security, performance, maintainability, etc.)
    
    Args:
        pr_url_or_id: PR number, URL, branch name, or 'latest' for local changes (default: \"latest\")
        project: If True, review entire project instead of just changes
    
    Returns:
        Detailed review report with findings and recommendations
    
    Examples:
        - review() # Review local changes
        - review(project=True) # Review entire project
        - review(\"123\") # Review PR #123
    """
    args = [pr_url_or_id]
    if project:
        args.append("--project")
    
    result = run_cli_command("review", *args)
    return json.dumps(result, indent=2)


@mcp.tool
def generate_command(
    description: str,
    dry_run: bool = False
) -> str:
    """
    Generate a new CLI command from natural language description.
    
    This meta-command creates new commands for the Compounding Engineering plugin.
    It analyzes the description, designs an appropriate workflow and agents,
    and generates all necessary code.
    
    Args:
        description: Natural language description of what the new command should do
        dry_run: If True, show what would be created without writing files
    
    Returns:
        Generation results with created files and code structure
    
    Examples:
        - generate_command(\"Create a command to format code\")
        - generate_command(\"Add a lint command that checks Python style\")
    """
    args = [description]
    if dry_run:
        args.append("--dry-run")
    
    result = run_cli_command("generate-command", *args)
    return json.dumps(result, indent=2)


@mcp.tool
def codify(
    feedback: str,
    source: str = "manual_input"
) -> str:
    """
    Codify feedback into the knowledge base.
    
    Transforms raw feedback, instructions, or learnings into structured improvements
    (documentation, rules, patterns) and saves them to the persistent knowledge base.
    
    Args:
        feedback: The feedback, instruction, or learning to codify
        source: Source of the feedback (e.g., 'review', 'retro', 'manual_input')
    
    Returns:
        Codification results with created/updated knowledge base entries
    
    Examples:
        - codify(\"Always use strict typing in Python files\")
        - codify(\"We should use factory pattern for creating agents\", source=\"retro\")
    """
    args = [feedback]
    if source != "manual_input":
        args.extend(["--source", source])
    
    result = run_cli_command("codify", *args)
    return json.dumps(result, indent=2)


@mcp.tool
def compress_kb(
    ratio: float = 0.5,
    dry_run: bool = False
) -> str:
    """
    Compress the AI knowledge base (AI.md) using LLM.
    
    Semantically compresses the knowledge base to reduce token usage
    while preserving key learnings and structure.
    
    Args:
        ratio: Target compression ratio between 0.0 and 1.0 (default: 0.5)
        dry_run: If True, show stats without modifying the file
    
    Returns:
        Compression results with before/after statistics
    """
    args = []
    if ratio != 0.5:
        args.extend(["--ratio", str(ratio)])
    if dry_run:
        args.append("--dry-run")
    
    result = run_cli_command("compress-kb", *args)
    return json.dumps(result, indent=2)


@mcp.tool
def index(root_dir: str = ".") -> str:
    """
    Index the codebase for semantic search using Vector Embeddings.
    
    Enables agents to find relevant code snippets through semantic search.
    Performs smart incremental indexing (skips unchanged files).
    
    Args:
        root_dir: Root directory to index (default: \".\")
    
    Returns:
        Indexing results with statistics and indexed files count
    """
    args = []
    if root_dir != ".":
        args.extend(["--dir", root_dir])
    
    result = run_cli_command("index", *args)
    return json.dumps(result, indent=2)


# ============================================================================
# SERVER INITIALIZATION
# ============================================================================

if __name__ == \"__main__\":
    # Support both stdio (default) and HTTP transports
    import sys
    
    # Use stdio transport by default for traditional MCP clients
    if len(sys.argv) > 1 and sys.argv[1] == \"--http\":
        mcp.run(transport=\"http\", port=8000)
    else:
        mcp.run(transport=\"stdio\")
