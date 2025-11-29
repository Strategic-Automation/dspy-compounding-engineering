import os
import glob
import re
from datetime import datetime
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.table import Table
import dspy
from agents.workflow import TriageAgent

console = Console()


def _add_work_log_entry(content: str, action: str) -> str:
    """Add a work log entry to the todo content."""
    today = datetime.now().strftime("%Y-%m-%d")

    work_log_entry = f"""
### {today} - Approved for Work

**By:** Triage System

**Actions:**
- {action}
- Status changed from pending → ready
- Ready to be picked up and worked on

**Learnings:**
- Approved during triage session
"""

    # Find the Work Log section and append
    if "## Work Log" in content:
        # Insert after the Work Log header
        parts = content.split("## Work Log")
        if len(parts) == 2:
            return parts[0] + "## Work Log" + work_log_entry + parts[1]

    # If no work log section, append at end
    return content + "\n" + work_log_entry


def run_triage():
    todos_dir = "todos"
    if not os.path.exists(todos_dir):
        console.print(f"[yellow]Directory '{todos_dir}' does not exist. Creating it...[/yellow]")
        os.makedirs(todos_dir)

    # Find pending todos
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

    triage_predictor = dspy.Predict(TriageAgent)

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
        console.print(f"\n[dim]Progress: {idx-1}/{total_items} completed[/dim]")
        console.rule(f"[{idx}/{total_items}] Triaging: {filename}")

        # Use LLM to present the finding
        with console.status("Analyzing finding..."):
            response = triage_predictor(finding_content=content)

        console.print(Markdown(response.formatted_presentation))
        console.print("\n")

        remaining = total_items - idx + 1
        choice = Prompt.ask(
            f"Action? ({remaining} remaining)",
            choices=["yes", "all", "next", "custom"],
            default="yes"
        )

        if choice == "yes":
            # Rename to ready
            if "-pending-" in filename:
                new_filename = filename.replace("-pending-", "-ready-")
                new_path = os.path.join(todos_dir, new_filename)

                # Update status in content and add work log entry
                new_content = content.replace("status: pending", "status: ready")
                new_content = _add_work_log_entry(new_content, "Issue approved during triage session")

                with open(new_path, "w") as f:
                    f.write(new_content)

                os.remove(file_path)
                console.print(f"[green]✅ Approved: {new_filename} - Status: ready[/green]")
                approved_count += 1
                approved_todos.append(new_filename)
            else:
                console.print(f"[red]Error: Filename format unexpected: {filename}[/red]")

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
                    new_content = _add_work_log_entry(new_content, "Issue approved (batch accept all)")

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
                default="skip"
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
                "Enter new priority",
                choices=["p1", "p2", "p3"],
                default="p2"
            )

            if "-pending-" in filename:
                # Replace old priority with new one
                new_filename = re.sub(r"-pending-(p[123])-", f"-ready-{new_priority}-", filename)
                new_path = os.path.join(todos_dir, new_filename)

                # Update content
                new_content = content.replace("status: pending", "status: ready")
                new_content = re.sub(r"priority: p[123]", f"priority: {new_priority}", new_content)
                new_content = _add_work_log_entry(new_content, f"Issue approved with custom priority: {new_priority}")

                with open(new_path, "w") as f:
                    f.write(new_content)

                os.remove(file_path)
                console.print(f"[green]✅ Approved (Custom {new_priority.upper()}): {new_filename}[/green]")
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

    console.print("\n[bold]Next Steps:[/bold]")
    console.print("1. View approved todos:")
    console.print("   [cyan]ls todos/*-ready-*.md[/cyan]")
    console.print("2. Start work on approved items:")
    console.print("   [cyan]python cli.py work <todo_file>[/cyan]")
    console.print("3. Or commit the todos:")
    console.print("   [cyan]git add todos/ && git commit -m 'chore: add triaged todos'[/cyan]")
