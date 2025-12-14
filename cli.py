from typing import Optional

import typer

from config import configure_dspy
from workflows.codify import run_codify
from workflows.generate_command import run_generate_command
from workflows.plan import run_plan
from workflows.review import run_review
from workflows.triage import run_triage
from workflows.work import run_unified_work
from utils.knowledge_base import KnowledgeBase

app = typer.Typer()


@app.callback()
def main():
    """
    Compounding Engineering Plugin (DSPy Edition)
    """
    configure_dspy()


@app.command()
def triage():
    """
    Triage and categorize findings for the CLI todo system.
    """
    run_triage()


@app.command()
def plan(feature_description: str):
    """
    Transform feature descriptions into well-structured project plans.
    """
    run_plan(feature_description)


@app.command()
def work(
    pattern: Optional[str] = typer.Argument(
        None, help="Todo ID, plan file, or pattern"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Dry run mode"),
    sequential: bool = typer.Option(
        False,
        "--sequential",
        "-s",
        help="Execute todos sequentially instead of in parallel",
    ),
    max_workers: int = typer.Option(
        3, "--workers", "-w", help="Maximum number of parallel workers"
    ),
    in_place: bool = typer.Option(
        True,
        "--in-place/--worktree",
        help="Apply changes in-place to current branch (default) or use isolated worktree",
    ),
):
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
        "latest", help="PR number, URL, branch name, or 'latest' for local changes"
    ),
    project: bool = typer.Option(
        False, "--project", "-p", help="Review entire project instead of just changes"
    ),
):
    """
    Perform exhaustive multi-agent code reviews.

    Examples:
        uv run python cli.py review              # Review local changes
        uv run python cli.py review --project    # Review entire project
        uv run python cli.py review 123          # Review PR #123
    """
    run_review(pr_url_or_id, project=project)


@app.command()
def generate_command(
    description: str = typer.Argument(
        ..., help="Natural language description of what the command should do"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show what would be created without writing files",
    ),
):
    """
    Generate a new CLI command from a natural language description.

    This meta-command creates new commands for the Compounding Engineering plugin.
    It analyzes the description, designs an appropriate workflow and agents,
    and generates all necessary code.

    Examples:
        python cli.py generate-command "Create a command to format code"
        python cli.py generate-command "Add a lint command that checks Python style"
        python cli.py generate-command --dry-run "Create a deployment workflow"
    """
    run_generate_command(description=description, dry_run=dry_run)


@app.command()
def codify(
    feedback: str = typer.Argument(
        ..., help="The feedback, instruction, or learning to codify"
    ),
    source: str = typer.Option(
        "manual_input",
        "--source",
        "-s",
        help="Source of the feedback (e.g., 'review', 'retro')",
    ),
):
    """
    Codify feedback into the knowledge base.

    This command uses the FeedbackCodifier agent to transform raw feedback
    into structured improvements (documentation, rules, patterns) and saves
    them to the persistent knowledge base.

    Examples:
        python cli.py codify "Always use strict typing in Python files"
        python cli.py codify "We should use factory pattern for creating agents" --source retro
    """
    run_codify(feedback=feedback, source=source)


@app.command()
def compress_kb(
    ratio: float = typer.Option(
        0.5, "--ratio", "-r", help="Target compression ratio (0.0 to 1.0)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show stats without modifying the file"
    ),
):
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
    if not (ratio == ratio and ratio != float("inf") and ratio != float("-inf")):
        raise ValueError("Ratio must be a finite number (not NaN or infinity)")

    kb = KnowledgeBase()
    kb.compress_ai_md(ratio=ratio, dry_run=dry_run)


if __name__ == "__main__":
    app()
