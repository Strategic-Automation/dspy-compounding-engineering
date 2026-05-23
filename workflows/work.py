import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.panel import Panel

from agents.workflow.work_plan_executor import ReActPlanExecutor
from agents.workflow.work_todo_executor import ReActTodoResolver
from utils.git import GitService
from utils.todo import (
    analyze_dependencies,
    complete_todo,
    get_ready_todos,
    parse_todo,
)

console = Console()


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


def _run_react_todo(  # noqa: C901
    pattern: str,
    dry_run: bool,
    parallel: bool = True,
    max_workers: int = 3,
    in_place: bool = True,
):
    """Run ReAct todo resolution for a specific todo."""
    # Phase 1: Discover todos
    console.rule("[bold]Phase 1: Discovery[/bold]")
    todos = []

    # Use get_ready_todos from service
    todo_paths = get_ready_todos(pattern=pattern)

    for path in todo_paths:
        parsed = parse_todo(path)
        match = re.match(r"^(\d+)-ready-(.*)\.md$", os.path.basename(path))
        if match:
            todos.append(
                {
                    "id": match.group(1),
                    "slug": match.group(2),
                    "path": path,
                    "frontmatter": parsed["frontmatter"],
                    "content": parsed["body"],
                }
            )

    if not todos:
        console.print("[yellow]No ready todos found matching the criteria.[/yellow]")
        return

    console.print(f"[green]Found {len(todos)} ready todos.[/green]")
    for t in todos:
        console.print(f"- {t['id']}: {t['slug']}")

    # Phase 2: Setup worktree (if not in-place)
    worktree_path = None
    branch_name = None
    git_service = GitService()

    if not dry_run and not in_place:
        # Create branch name from todos
        todo_ids = "-".join([t["id"] for t in todos[:3]])
        branch_name = f"fix/todos-{todo_ids}"
        branch_name = GitService.sanitize_branch_name(branch_name)
        worktree_path = f"worktrees/{branch_name}"

        try:
            git_service.create_feature_worktree(branch_name, worktree_path)
            console.print(f"[green]Working in isolated worktree: {worktree_path}[/green]")
        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not create worktree, working in place: {e}[/yellow]"
            )
            worktree_path = None
    else:
        console.print("[dim]Phase 2: Setup Worktree (Skipped - Running In-Place)[/dim]")

    # Phase 3: Execute
    console.rule("[bold]Phase 3: Resolution[/bold]")

    def resolve_todo_task(todo):
        console.print(f"\n[bold cyan]Resolving Todo {todo['id']}: {todo['slug']}[/bold cyan]")

        if dry_run:
            return {"status": "dry_run", "todo_id": todo["id"]}

        try:
            # Use ReAct resolver
            resolver = ReActTodoResolver(base_dir=worktree_path or ".")
            result = resolver(todo_content=todo["content"], todo_id=todo["id"])

            # Mark complete using service
            complete_todo(
                todo["path"],
                resolution_summary=getattr(result, "resolution_summary", "Resolved via ReAct"),
                action_msg="Resolved via ReAct Agent",
            )

            # Codify learnings from successful resolution
            from utils.knowledge import codify_work_outcome

            try:
                codify_work_outcome(
                    todo_id=todo["id"],
                    todo_slug=todo["slug"],
                    resolution_summary=getattr(result, "resolution_summary", "Resolved via ReAct"),
                    operations_count=len(getattr(result, "files_modified", [])),
                    success=getattr(result, "success_status", False),
                )
            except Exception:
                pass  # Don't fail resolution if codification fails

            return {
                "status": "success" if getattr(result, "success_status", False) else "error",
                "todo_id": todo["id"],
                "summary": getattr(result, "resolution_summary", str(result)),
            }
        except Exception as e:
            return {"status": "error", "todo_id": todo["id"], "error": str(e)}

    try:
        # Analyze dependencies
        plan = analyze_dependencies(todos)
        if plan["mermaid_diagram"]:
            console.print(
                Panel(
                    plan["mermaid_diagram"],
                    title="Dependency Graph",
                    border_style="dim",
                )
            )

        results = []

        # Execute batches
        for batch in plan["execution_order"]:
            batch_ids = batch["todos"]
            batch_todos = [t for t in todos if t["id"] in batch_ids]

            if not batch_todos:
                continue

            console.print(
                f"\n[bold]Executing Batch {batch['batch']}[/bold] ({len(batch_todos)} todos)"
            )
            if "warning" in batch:
                console.print(f"[yellow]Warning: {batch['warning']}[/yellow]")

            try:
                if parallel and batch["can_parallel"] and len(batch_todos) > 1 and not dry_run:
                    console.print(
                        f"[dim]Executing {len(batch_todos)} todos in parallel "
                        f"with {max_workers} workers[/dim]"
                    )
                    with ThreadPoolExecutor(
                        max_workers=min(max_workers, len(batch_todos))
                    ) as executor:
                        futures = {
                            executor.submit(resolve_todo_task, todo): todo for todo in batch_todos
                        }
                        for future in as_completed(futures):
                            result = future.result()
                            results.append(result)
                            if result["status"] == "error":
                                failed_todo = futures[future]
                                console.print(
                                    f"[red]Failed to resolve todo {failed_todo['id']}: "
                                    f"{result.get('error')}[/red]"
                                )
                else:
                    # Sequential execution
                    if len(batch_todos) > 1:
                        console.print(f"[dim]Executing {len(batch_todos)} todos sequentially[/dim]")

                    for todo in batch_todos:
                        result = resolve_todo_task(todo)
                        results.append(result)
                        if result["status"] == "error":
                            console.print(
                                f"[red]Failed to resolve todo {todo['id']}: "
                                f"{result.get('error')}[/red]"
                            )

            except Exception as e:
                console.print(f"[red]Error executing batch {batch['batch']}: {e}[/red]")

        # Summary
        successful = sum(1 for r in results if r.get("status") == "success")
        console.print(
            f"\n[bold]Summary:[/bold] {successful}/{len(results)} todos resolved successfully"
        )

    finally:
        # Cleanup worktree if used
        if worktree_path and not dry_run:
            git_service.cleanup_worktree(worktree_path)


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
    git_service = GitService()

    if not in_place and not dry_run:
        plan_name = os.path.basename(plan_path).replace(".md", "")
        branch_name = GitService.sanitize_branch_name(f"work-plan-{plan_name}")
        worktree_path = f"worktrees/{branch_name}"

        try:
            git_service.create_feature_worktree(branch_name, worktree_path)
            base_dir = worktree_path
        except Exception as e:
            console.print(
                f"[yellow]Warning: Could not create worktree, working in place: {e}[/yellow]"
            )
            worktree_path = None
            base_dir = "."
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
            git_service.cleanup_worktree(worktree_path)
