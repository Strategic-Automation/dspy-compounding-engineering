import os
import re
import subprocess
from typing import Optional

import dspy
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from agents.workflow import TaskExecutor, TaskExtractor
from utils.safe_io import safe_apply_operations, skip_ai_commands

console = Console()


def _sanitize_branch_name(title: str) -> str:
    """Sanitize a title into a valid git branch name."""
    sanitized = title.lower().replace(" ", "-")
    sanitized = re.sub(r"[^a-z0-9-]", "", sanitized)
    return sanitized[:50]  # Limit length


def _get_project_context() -> str:
    """Get basic project context by listing files and reading key files."""
    context_parts = []

    # List top-level files
    try:
        files = os.listdir(".")
        context_parts.append(
            f"Project files: {', '.join(f for f in files if not f.startswith('.'))}"
        )
    except Exception:
        pass

    # Read key files for context
    key_files = ["README.md", "pyproject.toml", "package.json", "requirements.txt"]
    for kf in key_files:
        if os.path.exists(kf):
            try:
                with open(kf, "r") as f:
                    content = f.read()[:1000]
                context_parts.append(f"\n--- {kf} ---\n{content}")
            except Exception:
                pass

    return "\n".join(context_parts) if context_parts else "No project context available"


def _get_file_content(file_path: str, worktree_path: Optional[str] = None) -> str:
    """Read file content, optionally from a worktree."""
    target_path = os.path.join(worktree_path, file_path) if worktree_path else file_path
    if os.path.exists(target_path):
        try:
            with open(target_path, "r") as f:
                return f.read()
        except Exception:
            return ""
    return ""


def _run_tests(worktree_path: str) -> tuple[bool, str]:
    """Run tests in the worktree and return success status and output."""
    test_commands = [
        ["python", "-m", "pytest", ".", "-v"],
        ["python", "-m", "unittest"],
    ]
    outputs = []
    for cmd in test_commands:
        try:
            res = subprocess.run(
                cmd, cwd=worktree_path, capture_output=True, text=True, timeout=300
            )
            outputs.append(res.stdout + res.stderr)
            if res.returncode == 0:
                return True, res.stdout
        except Exception as e:
            outputs.append(str(e))
    return False, "\n".join(outputs)


def apply_task_resolution(resolution: dict, worktree_path: str) -> None:
    """Safely apply task resolution in worktree (new safe wrapper)."""
    console.print(Panel("Applying Task Resolution", style="bold green"))

    # Safe file ops
    safe_apply_operations(resolution.get("operations", []), worktree_path)

    # Skip commands
    skip_ai_commands(
        resolution.get("commands", []), "Disabled in worktree for security"
    )

    console.print("[green]Task resolution applied safely.[/green]")


def run_work(plan_file: str) -> None:
    """
    Execute a work plan from a file.

    Args:
        plan_file: Path to a plan or todo file to execute
    """
    console.print(
        Panel.fit(
            f"[bold]Compounding Engineering: Work Execution[/bold]\nPlan: {plan_file}",
            border_style="blue",
        )
    )

    # Validate file exists
    if not os.path.exists(plan_file):
        console.print(f"[red]Error: File not found: {plan_file}[/red]")

        # Check if this looks like a todo pattern and provide helpful guidance
        if re.match(r"^\d+$", plan_file) or plan_file.lower() in ["p1", "p2", "p3"]:
            console.print(
                "\n[yellow]💡 It looks like you're trying to resolve a todo.[/yellow]"
            )
            console.print(
                "\n[bold]The 'work' command is for executing plan files:[/bold]"
            )
            console.print(
                "  [cyan]uv run python cli.py work plans/my-feature.md[/cyan]"
            )
            console.print(
                "\n[bold]To resolve todos, use the 'work' command with a todo ID or pattern:[/bold]"
            )
            if re.match(r"^\d+$", plan_file):
                console.print(
                    f"  [cyan]uv run python cli.py work {plan_file}[/cyan]  [dim]# Resolve todo #{plan_file}[/dim]"
                )
            elif plan_file.lower() in ["p1", "p2", "p3"]:
                console.print(
                    f"  [cyan]uv run python cli.py work {plan_file}[/cyan]  [dim]# Resolve all {plan_file.upper()} todos[/dim]"
                )
            console.print(
                "  [cyan]uv run python cli.py work p1[/cyan]  [dim]# Resolve all P1 todos[/dim]"
            )
        else:
            console.print(
                "\n[yellow]💡 Make sure the plan file path is correct.[/yellow]"
            )
            console.print(
                "[dim]Example: uv run python cli.py work plans/my-feature.md[/dim]"
            )

        return

    # Read plan content
    with open(plan_file, "r") as f:
        plan_content = f.read()

    console.print(f"[cyan]Read plan file ({len(plan_content)} chars)[/cyan]")

    # Extract tasks from plan
    console.rule("[bold]Phase 1: Task Extraction[/bold]")

    try:
        # Use ChainOfThought for robust typed output
        extractor = dspy.ChainOfThought(TaskExtractor)
        result = extractor(
            plan_content=plan_content, project_context=_get_project_context()
        )

        # Get typed result
        task_list_obj = result.extraction_result
        if not task_list_obj:
            console.print("[yellow]No tasks extracted from plan.[/yellow]")
            tasks = []
        else:
            # Convert Pydantic to list of dicts for existing logic
            tasks = [t.model_dump() for t in task_list_obj.tasks]

        # Display tasks
        if tasks:
            table = Table(title="Extracted Tasks")
            table.add_column("#", style="cyan")
            table.add_column("Task", style="white")
            table.add_column("Priority", style="yellow")

            for i, task in enumerate(tasks, 1):
                if isinstance(task, dict):
                    table.add_row(
                        str(i),
                        task.get("name", str(task))[:50],
                        task.get("priority", "normal"),
                    )
                else:
                    table.add_row(str(i), str(task)[:50], "normal")

            console.print(table)
        else:
            console.print("[yellow]No tasks extracted from plan.[/yellow]")
            return

    except Exception as e:
        console.print(f"[red]Error extracting tasks: {e}[/red]")
        return

    # Confirm execution
    if not Confirm.ask("\nProceed with task execution?", default=True):
        console.print("[yellow]Aborted.[/yellow]")
        return

    # Execute tasks
    console.rule("[bold]Phase 2: Task Execution[/bold]")

    # Create isolated worktree for this plan
    from utils.git_service import GitService

    plan_name = os.path.splitext(os.path.basename(plan_file))[0]
    safe_name = _sanitize_branch_name(plan_name)
    branch_name = f"feature/{safe_name}"
    worktree_path = f"worktrees/{safe_name}"

    console.print(f"[cyan]Setting up isolated environment: {branch_name}[/cyan]")
    try:
        if os.path.exists(worktree_path):
            console.print(
                f"[yellow]Worktree {worktree_path} already exists. Using it.[/yellow]"
            )
        else:
            GitService.create_feature_worktree(branch_name, worktree_path)
            console.print(f"[green]✓ Worktree created at {worktree_path}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to create worktree: {e}[/red]")
        return

    project_context = _get_project_context()

    try:
        for i, task in enumerate(tasks, 1):
            task_name = (
                task.get("name", str(task)) if isinstance(task, dict) else str(task)
            )
            console.print(
                f"\n[bold cyan]Task {i}/{len(tasks)}: {task_name}[/bold cyan]"
            )

            try:
                # Prepare inputs for TaskExecutor
                task_obj = (
                    task
                    if isinstance(task, dict)
                    else {"name": str(task), "description": str(task)}
                )

                # Use ChainOfThought for robust typed output
                executor = dspy.ChainOfThought(TaskExecutor)
                result = executor(
                    task_title=task_obj.get("name", "Unknown Task"),
                    task_description=task_obj.get("description", str(task)),
                    task_files=str(task_obj.get("files", [])),
                    task_acceptance_criteria=str(
                        task_obj.get("acceptance_criteria", [])
                    ),
                    existing_code_context=project_context,
                    project_conventions="Follow existing patterns. Use Python 3.10+. Use Rich for CLI output.",
                )

                # Get typed result
                execution_obj = result.execution_result
                if not execution_obj:
                    console.print(
                        f"[yellow]Warning: Agent failed to return structure for task {i}[/yellow]"
                    )
                    continue

                # Convert Pydantic to dict for existing apply_task_resolution function
                resolution = execution_obj.model_dump()

                # Apply resolution in WORKTREE
                apply_task_resolution(resolution, worktree_path)

                # Run tests in WORKTREE
                console.print("[dim]Running tests...[/dim]")
                success, output = _run_tests(worktree_path)
                if success:
                    console.print("[green]✓ Tests passed[/green]")
                else:
                    console.print("[red]✗ Tests failed[/red]")
                    console.print(
                        Panel(
                            output[:500] + "...",
                            title="Test Output (Truncated)",
                            border_style="red",
                        )
                    )

                console.print(f"[green]✓ Task {i} completed[/green]")

            except Exception as e:
                console.print(f"[red]✗ Task {i} failed: {e}[/red]")

        console.print("\n[bold green]Work execution complete![/bold green]")
        console.print(f"[bold]Changes are in branch: [cyan]{branch_name}[/cyan][/bold]")
        console.print(f"To merge: [cyan]git merge {branch_name}[/cyan]")

    finally:
        # Cleanup worktree
        if os.path.exists(worktree_path):
            console.print(f"\n[yellow]Cleaning up worktree {worktree_path}...[/yellow]")
            try:
                subprocess.run(
                    ["git", "worktree", "remove", "--force", worktree_path],
                    check=True,
                    capture_output=True,
                )
                console.print("[green]✓ Worktree removed[/green]")
            except subprocess.CalledProcessError as e:
                console.print(f"[red]Failed to remove worktree: {e}[/red]")
