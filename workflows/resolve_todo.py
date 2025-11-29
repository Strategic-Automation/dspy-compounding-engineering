"""
Resolve Todo Parallel Workflow

This workflow processes ready todos from code review findings and resolves them
systematically, supporting parallel execution where dependencies allow.

Based on the original compounding-engineering-plugin's resolve_todo_parallel command.
"""

import os
import re
import glob
import json
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import dspy
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm

from agents.workflow import TodoResolver, TodoDependencyAnalyzer
from utils.safe_io import safe_apply_operations, skip_ai_commands

console = Console()


def _parse_todo_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from todo file."""
    frontmatter = {}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            yaml_content = parts[1].strip()
            for line in yaml_content.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    # Handle lists
                    if value.startswith("[") and value.endswith("]"):
                        value = [v.strip() for v in value[1:-1].split(",")]
                    frontmatter[key] = value
    return frontmatter


def _get_ready_todos(pattern: Optional[str] = None) -> list[dict]:
    """Find all ready todos in the todos directory, optionally filtered by pattern."""
    todos_dir = "todos"
    if not os.path.exists(todos_dir):
        return []

    ready_files = glob.glob(os.path.join(todos_dir, "*-ready-*.md"))

    todos = []
    for file_path in sorted(ready_files):
        filename = os.path.basename(file_path)

        # Filter by pattern if provided
        if pattern and pattern.lower() not in filename.lower():
            continue

        with open(file_path, "r") as f:
            content = f.read()

        frontmatter = _parse_todo_frontmatter(content)

        # Extract ID from filename (handles both old and new formats)
        match = re.match(r"^(\d+)-ready-(.*)\.md$", filename)
        if match:
            todos.append({
                "id": match.group(1),
                "slug": match.group(2),
                "path": file_path,
                "frontmatter": frontmatter,
                "content": content
            })
    return todos


def _sanitize_branch_name(name: str) -> str:
    """Create a valid git branch name from a string."""
    sanitized = name.lower().replace(" ", "-")
    sanitized = re.sub(r'[^a-z0-9-]', '', sanitized)
    return sanitized[:50]


def _get_project_context() -> str:
    """Get basic project context by reading key files."""
    context_parts = []

    try:
        files = os.listdir(".")
        context_parts.append(f"Project files: {', '.join(f for f in files if not f.startswith('.'))}")
    except Exception:
        pass

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


def _create_worktree(branch_name: str) -> str:
    """Create an isolated git worktree for the resolution work."""
    worktree_dir = "worktrees"
    os.makedirs(worktree_dir, exist_ok=True)

    worktree_path = os.path.join(worktree_dir, branch_name)

    if os.path.exists(worktree_path):
        console.print(f"[yellow]Worktree {worktree_path} already exists. Reusing.[/yellow]")
        return worktree_path

    try:
        # Create the branch from current HEAD
        subprocess.run(
            ["git", "branch", branch_name],
            capture_output=True, check=False  # Ignore if branch exists
        )

        # Create the worktree
        subprocess.run(
            ["git", "worktree", "add", worktree_path, branch_name],
            capture_output=True, text=True, check=True
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
            capture_output=True, check=True
        )
        console.print(f"[green]✓ Removed worktree {worktree_path}[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[yellow]Warning: Could not remove worktree: {e}[/yellow]")


def _apply_resolution(resolution: dict, base_dir: str = ".") -> None:
    """Safely apply the resolution plan from TodoResolver."""
    console.print(Panel("Applying Resolution", style="bold green"))

    # Safely apply file operations
    operations = resolution.get("operations", [])
    safe_apply_operations(operations, base_dir)

    # Skip commands (security: don't run AI-suggested commands)
    commands = resolution.get("commands", [])
    skip_ai_commands(commands)

    console.print("[green]Resolution applied safely.[/green]")


def _mark_todo_complete(todo: dict, worktree_path: Optional[str] = None) -> str:
    """
    Mark a todo as complete by updating its file.

    Note: Todo files are always in the main repository, not in worktrees.
    Worktrees are only used for code changes.
    """
    # Update content
    new_content = todo['content'].replace("status: ready", "status: complete")

    # Add work log entry
    today = datetime.now().strftime("%Y-%m-%d")
    branch_info = f" (branch: {os.path.basename(worktree_path)})" if worktree_path else ""
    work_log_entry = f"""
### {today} - Resolved

**By:** Todo Resolver Agent{branch_info}

**Actions:**
- Issue analyzed and resolved
- Changes applied to codebase
- Status changed from ready → complete

**Learnings:**
- Automated resolution via resolve-todo workflow
"""

    if "## Work Log" in new_content:
        parts = new_content.split("## Work Log")
        if len(parts) == 2:
            new_content = parts[0] + "## Work Log" + work_log_entry + parts[1]
    else:
        new_content += "\n## Work Log" + work_log_entry

    # Create new filename (ready -> complete) - always in main repo
    old_path = todo['path']
    new_filename = os.path.basename(old_path).replace("-ready-", "-complete-")
    new_path = os.path.join(os.path.dirname(old_path), new_filename)

    # Ensure todos directory exists
    os.makedirs(os.path.dirname(new_path), exist_ok=True)

    # Write updated content
    with open(new_path, "w") as f:
        f.write(new_content)

    # Remove old file if different
    if old_path != new_path and os.path.exists(old_path):
        os.remove(old_path)

    console.print(f"[green]✓ Todo {todo['id']} marked complete: {new_path}[/green]")
    return new_path


def _resolve_single_todo(todo: dict, worktree_path: Optional[str] = None, dry_run: bool = False) -> dict:
    """Resolve a single todo using TodoResolver agent."""
    console.print(f"\n[bold cyan]Resolving Todo {todo['id']}: {todo['slug']}[/bold cyan]")

    # Get project context
    project_context = _get_project_context()

    # Extract affected files from todo content (look for file paths)
    affected_files_content = "No specific files identified."
    file_pattern = re.findall(r'`([^`]+\.[a-z]+)`', todo['content'])
    if file_pattern:
        affected_parts = []
        for fp in file_pattern[:5]:  # Limit to 5 files
            base = worktree_path if worktree_path else "."
            full_path = os.path.join(base, fp)
            if os.path.exists(full_path):
                try:
                    with open(full_path, "r") as f:
                        content = f.read()[:2000]
                    affected_parts.append(f"--- {fp} ---\n{content}")
                except Exception:
                    pass
        if affected_parts:
            affected_files_content = "\n\n".join(affected_parts)

    if dry_run:
        console.print(f"[yellow]DRY RUN: Would resolve todo {todo['id']}[/yellow]")
        console.print(f"  Content preview: {todo['content'][:200]}...")
        return {"status": "dry_run", "todo_id": todo['id']}

    # Invoke the TodoResolver agent
    try:
        resolver = dspy.Predict(TodoResolver)
        result = resolver(
            todo_content=todo['content'],
            todo_id=todo['id'],
            affected_files_content=affected_files_content,
            project_context=project_context
        )

        # Parse the resolution JSON
        resolution_text = result.resolution_json

        # Try to extract JSON from the response
        try:
            # Handle case where response might have markdown code blocks
            if "```json" in resolution_text:
                json_match = re.search(r'```json\s*(.*?)\s*```', resolution_text, re.DOTALL)
                if json_match:
                    resolution_text = json_match.group(1)
            elif "```" in resolution_text:
                json_match = re.search(r'```\s*(.*?)\s*```', resolution_text, re.DOTALL)
                if json_match:
                    resolution_text = json_match.group(1)

            resolution = json.loads(resolution_text)
        except json.JSONDecodeError:
            console.print(f"[yellow]Warning: Could not parse resolution JSON for todo {todo['id']}[/yellow]")
            resolution = {"operations": [], "summary": resolution_text}

        # Apply the resolution
        base_dir = worktree_path if worktree_path else "."
        _apply_resolution(resolution, base_dir)

        # Mark todo as complete
        _mark_todo_complete(todo, worktree_path)

        return {
            "status": "success",
            "todo_id": todo['id'],
            "summary": resolution.get("summary", "Resolved"),
            "operations_count": len(resolution.get("operations", []))
        }

    except Exception as e:
        console.print(f"[red]Error resolving todo {todo['id']}: {e}[/red]")
        return {"status": "error", "todo_id": todo['id'], "error": str(e)}


def _analyze_dependencies(todos: list[dict]) -> dict:
    """Analyze dependencies between todos and create execution plan."""
    if len(todos) <= 1:
        return {
            "execution_order": [{"batch": 1, "todos": [t['id'] for t in todos], "can_parallel": True}],
            "warnings": [],
            "mermaid_diagram": f"flowchart TD\n  A[Todo {todos[0]['id'] if todos else 'None'}]"
        }

    # Create summary for dependency analyzer
    todos_summary = json.dumps([{
        "id": t['id'],
        "slug": t['slug'],
        "priority": t['frontmatter'].get('priority', 'p2'),
        "tags": t['frontmatter'].get('tags', []),
        "dependencies": t['frontmatter'].get('dependencies', []),
        "content_preview": t['content'][:500]
    } for t in todos])

    try:
        analyzer = dspy.Predict(TodoDependencyAnalyzer)
        result = analyzer(todos_summary=todos_summary)

        # Parse the execution plan
        plan_text = result.execution_plan_json

        # Extract JSON
        try:
            if "```json" in plan_text:
                json_match = re.search(r'```json\s*(.*?)\s*```', plan_text, re.DOTALL)
                if json_match:
                    plan_text = json_match.group(1)
            elif "```" in plan_text:
                json_match = re.search(r'```\s*(.*?)\s*```', plan_text, re.DOTALL)
                if json_match:
                    plan_text = json_match.group(1)

            return json.loads(plan_text)
        except json.JSONDecodeError:
            pass
    except Exception as e:
        console.print(f"[yellow]Warning: Dependency analysis failed: {e}[/yellow]")

    # Default: all in parallel
    return {
        "execution_order": [{"batch": 1, "todos": [t['id'] for t in todos], "can_parallel": True}],
        "warnings": [],
        "mermaid_diagram": "flowchart TD\n  " + "\n  ".join([f"{t['id']}[Todo {t['id']}]" for t in todos])
    }


def _commit_and_push(worktree_path: str, todos: list[dict]) -> bool:
    """Commit changes and optionally push to remote."""
    try:
        # Stage all changes
        subprocess.run(["git", "add", "."], cwd=worktree_path, check=True)

        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=worktree_path, capture_output=True, text=True
        )

        if not result.stdout.strip():
            console.print("[yellow]No changes to commit.[/yellow]")
            return False

        # Create commit message
        todo_ids = ", ".join([t['id'] for t in todos])
        commit_msg = f"""fix: resolve todos {todo_ids}

Automated resolution of code review findings.

Resolved todos:
{chr(10).join(['- ' + t['slug'] for t in todos])}

🤖 Generated with Compounding Engineering CLI
"""

        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=worktree_path, check=True
        )
        console.print("[green]✓ Changes committed[/green]")
        return True

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to commit: {e}[/red]")
        return False


def run_resolve_todo(
    pattern: Optional[str] = None,
    dry_run: bool = False,
    parallel: bool = True,
    max_workers: int = 3
) -> None:
    """
    Main entrypoint for resolving todos.

    Args:
        pattern: Optional pattern to filter todos (e.g., '001' or 'security')
        dry_run: If True, show what would be done without applying changes
        parallel: If True, resolve todos in parallel where possible
        max_workers: Maximum number of parallel workers
    """
    console.print(Panel.fit(
        "[bold]Compounding Engineering: Resolve Todos[/bold]\n"
        f"Pattern: {pattern or 'all'} | Dry Run: {dry_run} | Parallel: {parallel}",
        border_style="blue"
    ))

    # Phase 1: Discover todos
    console.rule("[bold]Phase 1: Discovery[/bold]")
    todos = _get_ready_todos(pattern)

    if not todos:
        console.print("[yellow]No ready todos found matching the criteria.[/yellow]")
        console.print("\nTo see all todos: [cyan]ls todos/*.md[/cyan]")
        return

    # Display found todos
    table = Table(title=f"Found {len(todos)} Ready Todos")
    table.add_column("ID", style="cyan")
    table.add_column("Priority", style="yellow")
    table.add_column("Description", style="white")

    for todo in todos:
        priority = todo['frontmatter'].get('priority', 'p2')
        table.add_row(todo['id'], priority, todo['slug'][:50])

    console.print(table)

    if dry_run:
        console.print("\n[yellow]DRY RUN MODE - No changes will be made[/yellow]")

    # Phase 2: Analyze dependencies
    console.rule("[bold]Phase 2: Dependency Analysis[/bold]")

    with console.status("[cyan]Analyzing dependencies between todos...[/cyan]"):
        execution_plan = _analyze_dependencies(todos)

    # Display execution plan
    if execution_plan.get("mermaid_diagram"):
        console.print("\n[bold]Execution Order:[/bold]")
        console.print(Panel(execution_plan["mermaid_diagram"], title="Dependency Graph"))

    if execution_plan.get("warnings"):
        for warning in execution_plan["warnings"]:
            console.print(f"[yellow]⚠ {warning}[/yellow]")

    # Ask for confirmation
    if not dry_run:
        if not Confirm.ask("\nProceed with resolution?", default=True):
            console.print("[yellow]Aborted.[/yellow]")
            return

    # Phase 3: Setup worktree
    console.rule("[bold]Phase 3: Environment Setup[/bold]")

    worktree_path = None
    branch_name = None

    if not dry_run:
        # Create branch name from todos
        timestamp = datetime.now().strftime("%Y%m%d-%H%M")
        todo_ids = "-".join([t['id'] for t in todos[:3]])  # Limit to first 3 IDs
        branch_name = f"fix/todos-{todo_ids}-{timestamp}"
        branch_name = _sanitize_branch_name(branch_name)

        try:
            worktree_path = _create_worktree(branch_name)
            console.print(f"[green]Working in isolated worktree: {worktree_path}[/green]")
            console.print(f"[green]Branch: {branch_name}[/green]")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not create worktree, working in place: {e}[/yellow]")

    # Phase 4: Execute resolutions
    console.rule("[bold]Phase 4: Resolution[/bold]")

    results = []

    # Process by batch according to execution plan
    for batch_info in execution_plan.get("execution_order", [{"batch": 1, "todos": [t['id'] for t in todos]}]):
        batch_num = batch_info.get("batch", 1)
        batch_todo_ids = batch_info.get("todos", [])
        can_parallel = batch_info.get("can_parallel", True) and parallel

        batch_todos = [t for t in todos if t['id'] in batch_todo_ids]

        if not batch_todos:
            continue

        console.print(f"\n[bold]Batch {batch_num}:[/bold] {len(batch_todos)} todos")

        if can_parallel and len(batch_todos) > 1 and not dry_run:
            # Parallel execution
            with ThreadPoolExecutor(max_workers=min(max_workers, len(batch_todos))) as executor:
                futures = {
                    executor.submit(_resolve_single_todo, todo, worktree_path, dry_run): todo
                    for todo in batch_todos
                }
                for future in as_completed(futures):
                    todo = futures[future]
                    try:
                        result = future.result()
                        results.append(result)
                        if result['status'] == 'success':
                            console.print(f"  [green]✓ Todo {todo['id']}: {result.get('summary', 'Resolved')}[/green]")
                        else:
                            console.print(f"  [red]✗ Todo {todo['id']}: {result.get('error', 'Failed')}[/red]")
                    except Exception as e:
                        console.print(f"  [red]✗ Todo {todo['id']}: {e}[/red]")
                        results.append({"status": "error", "todo_id": todo['id'], "error": str(e)})
        else:
            # Sequential execution
            for todo in batch_todos:
                result = _resolve_single_todo(todo, worktree_path, dry_run)
                results.append(result)
                if result['status'] == 'success':
                    console.print(f"  [green]✓ Todo {todo['id']}: {result.get('summary', 'Resolved')}[/green]")
                elif result['status'] == 'dry_run':
                    console.print(f"  [yellow]○ Todo {todo['id']}: Would resolve[/yellow]")
                else:
                    console.print(f"  [red]✗ Todo {todo['id']}: {result.get('error', 'Failed')}[/red]")

    # Phase 5: Commit and summary
    console.rule("[bold]Phase 5: Summary[/bold]")

    success_count = sum(1 for r in results if r['status'] == 'success')
    error_count = sum(1 for r in results if r['status'] == 'error')

    summary_table = Table(title="Resolution Summary")
    summary_table.add_column("Metric", style="bold")
    summary_table.add_column("Count", justify="right")

    summary_table.add_row("Total Todos", str(len(todos)))
    summary_table.add_row("[green]Successful[/green]", f"[green]{success_count}[/green]")
    summary_table.add_row("[red]Failed[/red]", f"[red]{error_count}[/red]")

    console.print(summary_table)

    # Commit changes if not dry run and there were successes
    if not dry_run and success_count > 0 and worktree_path:
        if Confirm.ask("\nCommit changes?", default=True):
            resolved_todos = [t for t in todos if any(
                r['todo_id'] == t['id'] and r['status'] == 'success' for r in results
            )]
            _commit_and_push(worktree_path, resolved_todos)

            console.print("\n[bold]Next Steps:[/bold]")
            console.print(f"1. Review changes in worktree: [cyan]cd {worktree_path}[/cyan]")
            console.print(f"2. Push branch: [cyan]cd {worktree_path} && git push -u origin {branch_name}[/cyan]")
            console.print(f"3. Create PR: [cyan]gh pr create --title 'fix: resolve todos'[/cyan]")
            console.print(f"4. Clean up worktree: [cyan]git worktree remove {worktree_path}[/cyan]")
    elif dry_run:
        console.print("\n[yellow]DRY RUN complete. No changes were made.[/yellow]")

    console.print("\n[bold green]Done![/bold green]")
