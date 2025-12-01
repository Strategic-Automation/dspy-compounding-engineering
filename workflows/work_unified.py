import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.panel import Panel
from agents.workflow.react_todo_resolver import ReActTodoResolver
from agents.workflow.work_agent import ReActPlanExecutor
from workflows.resolve_react import _get_ready_todos, _mark_todo_complete

console = Console()


def _sanitize_branch_name(name: str) -> str:
    """Create a valid git branch name from a string."""
    sanitized = name.lower().replace(" ", "-")
    sanitized = re.sub(r"[^a-z0-9-]", "", sanitized)
    return sanitized[:50]


def _create_worktree(branch_name: str) -> str:
    """Create an isolated git worktree for the resolution work."""
    worktree_dir = "worktrees"
    os.makedirs(worktree_dir, exist_ok=True)

    worktree_path = os.path.join(worktree_dir, branch_name)

    if os.path.exists(worktree_path):
        console.print(
            f"[yellow]Worktree {worktree_path} already exists. Reusing.[/yellow]"
        )
        return worktree_path

    try:
        # Create the branch from current HEAD
        subprocess.run(
            ["git", "branch", branch_name],
            capture_output=True,
            check=False,  # Ignore if branch exists
        )

        # Create the worktree
        subprocess.run(
            ["git", "worktree", "add", worktree_path, branch_name],
            capture_output=True,
            text=True,
            check=True,
        )
        console.print(f"[green]✓ Created worktree at {worktree_path}[/green]")
        return worktree_path

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to create worktree: {e.stderr}[/red]")
        raise


def _cleanup_worktree(worktree_path: str) -> None:
    """Remove a git worktree."""
    try:
        subprocess.run(
            ["git", "worktree", "remove", "--force", worktree_path],
            capture_output=True,
            check=True,
        )
        console.print(f"[green]✓ Removed worktree {worktree_path}[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[yellow]Warning: Could not remove worktree: {e}[/yellow]")


def _detect_input_type(pattern: str) -> str:
    """Detect whether input is todo, plan, or pattern."""
    if not pattern:
        return "help"

    # Check for todo patterns
    if re.match(r"^\d+$", pattern):  # "001", "002"
        return "todo"
    if pattern.lower() in ["p1", "p2", "p3"]:  # "p1", "p2"
        return "pattern"
    if "todo" in pattern.lower() and pattern.endswith(".md"):
        return "todo"

    # Check for plan patterns
    if "plan" in pattern.lower() and pattern.endswith(".md"):
        return "plan"

    return "unknown"


def run_unified_work(
    pattern: str = None,
    dry_run: bool = False,
    parallel: bool = True,
    max_workers: int = 3,
    in_place: bool = True,
) -> None:
    """
    Unified work command using DSPy ReAct for todo resolution and plan execution.
    """
    input_type = _detect_input_type(pattern)

    mode = "in-place" if in_place else "worktree"
    execution = "parallel" if parallel else "sequential"

    console.print(
        Panel.fit(
            "[bold]Compounding Engineering: Unified Work[/bold]\n"
            f"Pattern: {pattern} | Type: {input_type}\n"
            f"Mode: {mode} | Execution: {execution} | Dry Run: {dry_run}",
            border_style="blue",
        )
    )

    if input_type == "todo":
        _run_react_todo(pattern, dry_run, parallel, max_workers, in_place)
    elif input_type == "plan":
        _run_react_plan(pattern, dry_run, in_place)
    elif input_type == "pattern":
        _run_react_todo_batch(pattern, dry_run, parallel, max_workers, in_place)
    else:
        console.print(
            "[yellow]Unknown input type. Please provide a todo ID, plan file, or pattern.[/yellow]"
        )
        console.print("Examples:")
        console.print("  python cli.py work 001")
        console.print("  python cli.py work plans/feature.md")
        console.print("  python cli.py work p1")


def _run_react_todo(
    pattern: str,
    dry_run: bool,
    parallel: bool = True,
    max_workers: int = 3,
    in_place: bool = True,
):
    """Run ReAct todo resolution for a specific todo."""
    # Get todos matching pattern
    todos = _get_ready_todos(pattern)
    if not todos:
        console.print(f"[yellow]No todo found matching '{pattern}'[/yellow]")
        return

    # Setup execution mode
    worktree_path = None
    if not in_place and not dry_run:
        branch_name = _sanitize_branch_name(f"work-{pattern}-{len(todos)}-todos")
        worktree_path = _create_worktree(branch_name)
        base_dir = worktree_path
    else:
        base_dir = "."

    # Define the resolution function for a single todo
    def resolve_todo_task(todo: dict) -> dict:
        """Resolve a single todo and return result."""
        console.print(
            f"\n[bold cyan]Resolving Todo {todo['id']}: {todo['slug']}[/bold cyan]"
        )

        if dry_run:
            console.print("[yellow]DRY RUN: Would resolve this todo.[/yellow]")
            return {"todo_id": todo["id"], "success": True, "dry_run": True}

        try:
            # Initialize resolver with correct base_dir
            resolver = ReActTodoResolver(base_dir=base_dir)

            result = resolver(todo_content=todo["content"], todo_id=todo["id"])

            if result.success_status:
                console.print(f"[green]Success:[/green] {result.resolution_summary}")
                # Mark todo complete in main repo (not worktree)
                # Note: _mark_todo_complete uses absolute paths or relative to CWD (which is now main repo)
                _mark_todo_complete(todo, result.resolution_summary)
                return {
                    "todo_id": todo["id"],
                    "success": True,
                    "summary": result.resolution_summary,
                }
            else:
                console.print(f"[red]Failed:[/red] {result.resolution_summary}")
                return {
                    "todo_id": todo["id"],
                    "success": False,
                    "summary": result.resolution_summary,
                }

        except Exception as e:
            console.print(f"[red]Error resolving todo {todo['id']}: {e}[/red]")
            return {"todo_id": todo["id"], "success": False, "error": str(e)}

    # Execute todos (parallel or sequential)
    try:
        if parallel and len(todos) > 1 and not dry_run:
            console.print(
                f"[dim]Executing {len(todos)} todos in parallel with {max_workers} workers[/dim]"
            )
            with ThreadPoolExecutor(
                max_workers=min(max_workers, len(todos))
            ) as executor:
                futures = {
                    executor.submit(resolve_todo_task, todo): todo for todo in todos
                }
                results = []
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
        else:
            # Sequential execution
            if len(todos) > 1:
                console.print(f"[dim]Executing {len(todos)} todos sequentially[/dim]")
            results = [resolve_todo_task(todo) for todo in todos]

        # Summary
        successful = sum(1 for r in results if r.get("success"))
        console.print(
            f"\n[bold]Summary:[/bold] {successful}/{len(results)} todos resolved successfully"
        )

    finally:
        # Cleanup worktree if used
        if worktree_path and not dry_run:
            _cleanup_worktree(worktree_path)


def _run_react_todo_batch(
    pattern: str,
    dry_run: bool,
    parallel: bool = True,
    max_workers: int = 3,
    in_place: bool = True,
):
    """Run ReAct todo resolution for a batch of todos."""
    # Reuse single todo logic as it handles lists
    _run_react_todo(pattern, dry_run, parallel, max_workers, in_place)


def _run_react_plan(plan_path: str, dry_run: bool, in_place: bool = True):
    """Run ReAct plan execution."""
    if not os.path.exists(plan_path):
        console.print(f"[red]Plan file not found: {plan_path}[/red]")
        return

    # Setup execution mode
    worktree_path = None
    if not in_place and not dry_run:
        plan_name = os.path.basename(plan_path).replace(".md", "")
        branch_name = _sanitize_branch_name(f"work-plan-{plan_name}")
        worktree_path = _create_worktree(branch_name)
        base_dir = worktree_path
    else:
        base_dir = "."

    with open(plan_path, "r") as f:
        content = f.read()

    console.print(f"\n[bold cyan]Executing Plan: {plan_path}[/bold cyan]")

    if dry_run:
        console.print("[yellow]DRY RUN: Would execute this plan.[/yellow]")
        return

    try:
        executor = ReActPlanExecutor(base_dir=base_dir)

        result = executor(plan_content=content, plan_path=plan_path)

        if result.success_status:
            console.print(f"[green]Success:[/green] {result.execution_summary}")
        else:
            console.print(f"[red]Failed:[/red] {result.execution_summary}")

    except Exception as e:
        console.print(f"[red]Error executing plan: {e}[/red]")
    finally:
        # Cleanup worktree if used
        if worktree_path and not dry_run:
            _cleanup_worktree(worktree_path)
