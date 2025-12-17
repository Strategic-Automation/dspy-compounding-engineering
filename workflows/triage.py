import glob
import os
import re

from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.table import Table

from agents.workflow import TriageAgent
from utils.knowledge import KBPredict
from utils.todo import add_work_log_entry, complete_todo

console = Console()


def consistency_check_todos(todos_dir: str) -> None:
    issue_to_files = {}
    for file_path in glob.glob(os.path.join(todos_dir, "*.md")):
        filename = os.path.basename(file_path)
        match = re.match(r"^(\d+)-", filename)
        if match:
            issue_id = match.group(1)
            issue_to_files.setdefault(issue_id, []).append(filename)
    duplicates = {iid: files for iid, files in issue_to_files.items() if len(files) > 1}
    if duplicates:
        console.print("[yellow]Warning: Duplicate issue IDs found:[/yellow]")
        for iid, files in duplicates.items():
            console.print(f"  Issue {iid}: {files}")
    console.print("[green]Consistency check passed.[/green]")


def _fill_recommended_action(content: str, solution_text: str = None) -> str:
    """Replace the 'Recommended Action' placeholder with actual recommendation."""
    placeholder = "*To be filled during triage.*"

    if solution_text:
        recommendation = solution_text
    else:
        recommendation = "Implement the proposed solution from the code review finding (Option 1)."

    return content.replace(placeholder, recommendation)


def run_triage():  # noqa: C901
    todos_dir = "todos"
    if not os.path.exists(todos_dir):
        console.print(f"[yellow]Directory '{todos_dir}' does not exist. Creating it...[/yellow]")
        os.makedirs(todos_dir)

    consistency_check_todos(todos_dir)
    # Pattern: *-pending-*.md
    pending_files = glob.glob(os.path.join(todos_dir, "*-pending-*.md"))

    # Sort by priority (p1 first, then p2, then p3) and then by ID
    def sort_key(filepath):
        filename = os.path.basename(filepath)
        # Extract priority
        priority_order = {"p1": 0, "p2": 1, "p3": 2}
        for p in ["p1", "p2", "p3"]:
            if f"-{p}-" in filename:
                priority = priority_order[p]
                break
        else:
            priority = 3
        # Extract ID
        match = re.match(r"^(\d+)-", filename)
        issue_id = int(match.group(1)) if match else 999
        return (priority, issue_id)

    pending_files.sort(key=sort_key)

    if not pending_files:
        console.print("[green]No pending todos found![/green]")
        return

    console.print(f"[bold]Found {len(pending_files)} pending items for triage.[/bold]\n")

    # Initialize KB-augmented triage predictor
    triage_predictor = KBPredict(
        TriageAgent,
        kb_tags=["triage", "code-review"],
    )

    approved_count = 0
    skipped_count = 0
    approved_todos = []
    skipped_items = []

    total_items = len(pending_files)

    for idx, file_path in enumerate(pending_files, 1):
        with open(file_path, "r") as f:
            content = f.read()

        filename = os.path.basename(file_path)

        # Show progress
        console.print(f"\n[dim]Progress: {idx - 1}/{total_items} completed[/dim]")
        console.rule(f"[{idx}/{total_items}] Triaging: {filename}")

        # Use LLM to present the finding
        with console.status("Analyzing finding..."):
            response = triage_predictor(finding_content=content)

        console.print(Markdown(response.formatted_presentation))
        console.print("\n")

        # Debug: Show action_required value
        if hasattr(response, "action_required"):
            if response.action_required:
                action_status = "⚠️  Action IS Required (code changes needed)"
            else:
                action_status = "✅ No Action Required (review passed)"
            console.print(f"[dim]Analysis: {action_status}[/dim]")
        else:
            console.print("[dim yellow]Warning: action_required field not present[/dim yellow]")

        should_auto_complete = hasattr(response, "action_required") and not response.action_required
        if should_auto_complete:
            console.print("[dim]🤖 Auto-completing: No action required[/dim]")

            if "-pending-" in filename:
                complete_todo(
                    file_path,
                    resolution_summary=(
                        "Automatically marked as complete - "
                        "no action required based on finding analysis."
                    ),
                    action_msg="Auto-completed during triage (no action required)",
                    rename_to_complete=True,
                )
                console.print(
                    f"[green]✅ Auto-Completed: {filename.replace('-pending-', '-complete-')} "
                    "- Status: complete[/green]"
                )
            continue

        remaining = total_items - idx + 1
        choice = Prompt.ask(
            f"Action? ({remaining} remaining)",
            choices=["yes", "all", "next", "custom", "complete"],
            default="yes",
        )

        if choice == "yes":
            # Rename to ready
            if "-pending-" in filename:
                new_filename = filename.replace("-pending-", "-ready-")
                new_path = os.path.join(todos_dir, new_filename)

                # Update status in content and add work log entry
                new_content = content.replace("status: pending", "status: ready")

                # Fill recommended action with the proposed solution from triage
                solution = (
                    response.proposed_solution if hasattr(response, "proposed_solution") else None
                )
                new_content = _fill_recommended_action(new_content, solution)

                new_content = add_work_log_entry(
                    new_content, "Issue approved during triage session"
                )

                with open(new_path, "w") as f:
                    f.write(new_content)

                os.remove(file_path)
                console.print(f"[green]✅ Approved: {new_filename} - Status: ready[/green]")
                approved_count += 1
                approved_todos.append(new_filename)

                # Codify triage decision
                from utils.knowledge import codify_triage_decision

                try:
                    codify_triage_decision(
                        finding_content=content,
                        decision="approved",
                        proposed_solution=solution,
                    )
                except Exception:
                    pass  # Don't fail triage if codification fails
        elif choice == "complete":
            if "-pending-" in filename:
                complete_todo(
                    file_path,
                    resolution_summary="Marked as complete during triage (no action required).",
                    action_msg="Issue marked complete during triage (no action required)",
                    rename_to_complete=True,
                )
                console.print(
                    f"[green]✅ Completed: {filename.replace('-pending-', '-complete-')} "
                    "- Status: complete[/green]"
                )
            else:
                console.print(f"[red]Error: Expected '-pending-' in {filename}[/red]")
        elif choice == "all":
            # Accept all remaining items (including current one)
            console.print(f"\n[bold cyan]Accepting all {remaining} remaining items...[/bold cyan]")

            # Process current file first
            remaining_files = [file_path] + pending_files[idx:]

            for remaining_path in remaining_files:
                with open(remaining_path, "r") as f:
                    remaining_content = f.read()
                remaining_filename = os.path.basename(remaining_path)

                if "-pending-" in remaining_filename:
                    new_filename = remaining_filename.replace("-pending-", "-ready-")
                    new_path = os.path.join(todos_dir, new_filename)

                    new_content = remaining_content.replace("status: pending", "status: ready")

                    # Fill recommended action with proposed solution if available
                    solution = (
                        response.proposed_solution
                        if hasattr(response, "proposed_solution")
                        else None
                    )
                    new_content = _fill_recommended_action(new_content, solution)

                    new_content = add_work_log_entry(
                        new_content, "Issue approved (batch accept all)"
                    )

                    with open(new_path, "w") as f:
                        f.write(new_content)

                    os.remove(remaining_path)
                    console.print(f"  [green]✅ {new_filename}[/green]")
                    approved_count += 1
                    approved_todos.append(new_filename)

            break  # Exit the loop since we processed all remaining

        elif choice == "next":
            # Ask if they want to delete or just skip
            delete_choice = Prompt.ask(
                "Remove this file or just skip to next?",
                choices=["skip", "remove"],
                default="skip",
            )

            if delete_choice == "remove":
                os.remove(file_path)
                console.print(f"[yellow]🗑️ Removed: {filename}[/yellow]")
                skipped_count += 1
                skipped_items.append(filename)
            else:
                console.print(f"[dim]⏭️ Skipped (kept): {filename}[/dim]")
                # File stays as pending - not counted as skipped

        elif choice == "custom":
            # Ask for custom priority
            new_priority = Prompt.ask(
                "Enter new priority", choices=["p1", "p2", "p3"], default="p2"
            )

            if "-pending-" in filename:
                # Replace old priority with new one
                new_filename = re.sub(r"-pending-(p[123])-", f"-ready-{new_priority}-", filename)
                new_path = os.path.join(todos_dir, new_filename)

                # Update content
                new_content = content.replace("status: pending", "status: ready")
                new_content = re.sub(r"priority: p[123]", f"priority: {new_priority}", new_content)

                # Fill recommended action with proposed solution
                solution = (
                    response.proposed_solution if hasattr(response, "proposed_solution") else None
                )
                new_content = _fill_recommended_action(new_content, solution)

                new_content = add_work_log_entry(
                    new_content, f"Issue approved with custom priority: {new_priority}"
                )

                with open(new_path, "w") as f:
                    f.write(new_content)

                os.remove(file_path)
                console.print(
                    f"[green]✅ Approved (Custom {new_priority.upper()}): {new_filename}[/green]"
                )
                approved_count += 1
                approved_todos.append(new_filename)

    # Final Summary
    console.rule("[bold green]Triage Complete[/bold green]")

    # Summary table
    table = Table(title="📋 Triage Summary")
    table.add_column("Metric", style="bold")
    table.add_column("Count", justify="right")

    table.add_row("Total Items", str(total_items))
    table.add_row("[green]Approved (ready)[/green]", f"[green]{approved_count}[/green]")
    table.add_row("[yellow]Skipped (deleted)[/yellow]", f"[yellow]{skipped_count}[/yellow]")

    console.print(table)

    if approved_todos:
        console.print("\n[bold green]Approved Todos (Ready for Work):[/bold green]")
        for todo in approved_todos:
            console.print(f"  • [cyan]{todo}[/cyan]")

    if skipped_items:
        console.print("\n[bold yellow]Skipped Items (Deleted):[/bold yellow]")
        for item in skipped_items:
            console.print(f"  • [dim]{item}[/dim]")

    # Codify batch triage session learnings
    if approved_count > 0 or skipped_count > 0:
        from utils.knowledge import codify_batch_triage_session

        try:
            codify_batch_triage_session(
                approved_count=approved_count,
                skipped_count=skipped_count,
                total_count=total_items,
                approved_todos=approved_todos,
            )
        except Exception as e:
            console.print(f"[dim yellow]⚠ Could not codify session: {e}[/dim yellow]")

    console.print("\n[bold]Next Steps:[/bold]")
    console.print("1. View approved todos:")
    console.print("   [cyan]ls todos/*-ready-*.md[/cyan]")
    console.print("2. Start work on approved items:")
    console.print("   [cyan]python cli.py work <todo_file>[/cyan]")
    console.print("3. Or commit the todos:")
    console.print("   [cyan]git add todos/ && git commit -m 'chore: add triaged todos'[/cyan]")
