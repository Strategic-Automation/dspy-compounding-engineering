import math
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from config import configure_dspy, settings
from utils.io import get_system_status, validate_agent_filters
from utils.knowledge import KnowledgeBase
from workflows.codify import run_codify
from workflows.generate_agent import run_generate_agent
from workflows.plan import run_plan
from workflows.review import run_review
from workflows.sync import run_sync
from workflows.triage import run_triage
from workflows.work import run_unified_work

console = Console()
app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]})


@app.callback()
def main(
    env_file: Annotated[
        Path | None,
        typer.Option(
            "--env-file",
            "-e",
            help="Explicit path to a .env file",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ] = None,
) -> None:
    """
    Compounding Engineering (DSPy Edition)
    """
    configure_dspy(env_file=str(env_file) if env_file else None)


@app.command()
def triage() -> None:
    """
    Triage and categorize findings for the CLI todo system.
    """
    run_triage()


@app.command()
def sync(
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Preview without creating issues"),
    pattern: str = typer.Option("*", "--pattern", "-p", help="Glob pattern to filter todos"),
) -> None:
    """
    Sync todos to GitHub issues.

    This command parses todos/*.md files with 'pending' or 'ready' status and:
    - Creates new GitHub issues for todos without a github_issue link
    - Updates existing issues when todo content has changed
    - Writes the GitHub issue URL back into the todo frontmatter

    Examples:
        compounding sync                  # Sync all pending/ready todos
        compounding sync --dry-run        # Preview what would be created
        compounding sync -p "*-p1-*"      # Only sync P1 priority todos
    """
    run_sync(dry_run=dry_run, pattern=pattern)


@app.command()
def plan(
    description: Annotated[
        str, typer.Argument(..., help="Feature description, GitHub issue ID, or URL")
    ],
) -> None:
    """
    Transform feature descriptions or GitHub issues into project plans.

    Examples:
        compounding plan "Add user authentication"
        compounding plan 30
        compounding plan https://github.com/user/repo/issues/30
    """
    run_plan(description)


@app.command()
def work(
    pattern: str | None = typer.Argument(None, help="Todo ID, plan file, or pattern"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Dry run mode"),
    sequential: bool = typer.Option(
        False,
        "--sequential",
        "-s",
        help="Execute todos sequentially instead of in parallel",
    ),
    max_workers: int = typer.Option(
        settings.cli_max_workers, "--workers", "-w", help="Maximum number of parallel workers"
    ),
    in_place: bool = typer.Option(
        True,
        "--in-place/--worktree",
        help="Apply changes in-place to current branch (default) or use isolated worktree",
    ),
) -> None:
    """
    Unified work command using DSPy ReAct.

    Automatically detects input type:
    - Todo ID: "001"
    - Plan file: "plans/feature.md"
    - Pattern: "p1", "security"

    **Migration Note**: This command replaces the old `resolve-todo` command.
    All todo resolution and plan execution now go through this unified interface.
    """
    # Validate pattern input for security
    if pattern:
        if len(pattern) > 256:
            raise typer.BadParameter("Pattern too long (max 256 characters)")
        if "\0" in pattern:
            raise typer.BadParameter("Null bytes not allowed in pattern")
        if ".." in pattern or pattern.startswith("/"):
            raise typer.BadParameter("Path traversal sequences not allowed")

    run_unified_work(
        pattern=pattern,
        dry_run=dry_run,
        parallel=not sequential,
        max_workers=max_workers,
        in_place=in_place,
    )


@app.command()
def review(
    pr_url_or_id: str = typer.Argument(
        "latest",
        help="PR number (e.g., 86), full URL, branch name, or 'latest' for local changes",
    ),
    project: bool = typer.Option(
        False, "--project", "-p", help="Review entire project instead of just changes"
    ),
    agent: Annotated[
        list[str] | None,
        typer.Option("--agent", "-a", help="Run only specific review agents (name or pattern)"),
    ] = None,
) -> None:
    """
    Perform exhaustive multi-agent code reviews.

    Args:
        pr_url_or_id: The target to review. Can be:
            - A PR ID (e.g., 86)
            - A full URL (e.g., https://github.com/user/project/pull/86)
            - A branch name (e.g., dev)
            - 'latest' (the default) to review unstaged/local changes

    Examples:
        compounding review              # Review local changes
        compounding review 86           # Review PR #86
        compounding review dev          # Review differences against dev
        compounding review --project    # Review entire project
        compounding review -a Security  # Run only security agent
    """
    # Sanitize and validate agent filter
    safe_agent_filter = validate_agent_filters(agent) if agent else None
    if agent and safe_agent_filter is None:
        return

    run_review(pr_url_or_id, project=project, agent_filter=safe_agent_filter)


@app.command()
def generate_agent(
    description: str = typer.Argument(
        ..., help="Natural language description of what the review agent should check for"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show what would be created without writing files",
    ),
) -> None:
    """
    Generate a new Review Agent from a natural language description.

    This meta-command creates new review agents for the multi-agent review system.
    It analyzes the description, designs an appropriate scanning protocol,
    and generates the agent code in agents/review/.

    Examples:
        compounding generate-agent "Check for SQL injection vulnerabilities"
        compounding generate-agent "Ensure all Python functions have docstrings"
        compounding generate-agent --dry-run "Audit for frontend race conditions"
    """
    run_generate_agent(description=description, dry_run=dry_run)


@app.command()
def codify(
    feedback: str = typer.Argument(..., help="The feedback, instruction, or learning to codify"),
    source: str = typer.Option(
        "manual_input",
        "--source",
        "-s",
        help="Source of the feedback (e.g., 'review', 'retro')",
    ),
) -> None:
    """
    Codify feedback into the knowledge base.

    This command uses the FeedbackCodifier agent to transform raw feedback
    into structured improvements (documentation, rules, patterns) and saves
    them to the persistent knowledge base.

    Examples:
        compounding codify "Always use strict typing in Python files"
        compounding codify "We should use factory pattern for creating agents" --source retro
    """
    run_codify(feedback=feedback, source=source)


@app.command()
def compress_kb(
    ratio: float = typer.Option(
        settings.kb_compress_ratio,
        "--ratio",
        "-r",
        help="Target compression ratio (0.0 to 1.0)",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show stats without modifying the file"
    ),
) -> None:
    """
    Compress the AI knowledge base (AI.md) using LLM.

    This command semantically compresses the knowledge base to reduce token usage
    while preserving key learnings and structure.
    """
    # Input validation for ratio parameter
    if not isinstance(ratio, (int, float)):
        raise ValueError("Ratio must be a number")
    if not (0.0 <= ratio <= 1.0):
        raise ValueError("Ratio must be between 0.0 and 1.0")
    if not math.isfinite(ratio):
        raise ValueError("Ratio must be a finite number (not NaN or infinity)")

    kb = KnowledgeBase()
    kb.compress_ai_md(ratio=ratio, dry_run=dry_run)


@app.command()
def garden(
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Simulate gardening without saving changes"
    ),
    deep: bool = typer.Option(
        False, "--deep", "-d", help="Enable deep mode (LLM-based fact extraction). Slow."
    ),
) -> None:
    """
    Tend to the Knowledge Base: Score, Extract, Tier, and Deduplicate.
    """
    from utils.knowledge.gardener import KnowledgeGardeningService

    gardener = KnowledgeGardeningService()
    gardener.garden(dry_run=dry_run, deep_mode=deep)


@app.command()
def index(
    root_dir: str = typer.Option(".", "--dir", "-d", help="Root directory to index"),
    recreate: Annotated[
        bool, typer.Option("--recreate", "-r", help="Force recreation of the vector collection")
    ] = False,
) -> None:
    """
    Index the codebase for semantic search using Vector Embeddings.
    Use this to enable agents to find relevant code snippets.
    Performs smart incremental indexing (skips unchanged files).
    """
    kb = KnowledgeBase()
    kb.index_codebase(root_dir=root_dir, force_recreate=recreate)


@app.command()
def status() -> None:
    """
    Check the current status of external services (Qdrant, API keys).
    """
    from rich.panel import Panel

    status_text = get_system_status()
    console.print(Panel(status_text, title="System Diagnostics", border_style="cyan"))


if __name__ == "__main__":
    app()
