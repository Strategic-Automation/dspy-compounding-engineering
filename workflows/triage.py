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
import yaml
from filelock import FileLock
import tempfile
import frontmatter

console = Console()

def parse_todo(file_path: str) -> dict:
    post = frontmatter.load(file_path)
    return {'frontmatter': dict(post.metadata), 'body': post.content}


def serialize_todo(frontmatter_dict: dict, body: str) -> str:
    fm_yaml = yaml.dump(frontmatter_dict, default_flow_style=False, sort_keys=False)
    return f"---\n{fm_yaml}\n---\n{body}"


def atomic_update_todo(old_path: str, new_path: str, update_fn: callable) -> None:
    lock_path = old_path + '.lock'
    with FileLock(lock_path):
        parsed = parse_todo(old_path)
        updated = update_fn(parsed)
        content = serialize_todo(updated['frontmatter'], updated['body'])
        with tempfile.NamedTemporaryFile(mode='w', dir=os.path.dirname(new_path), delete=False, suffix='.md') as temp_f:
            temp_f.write(content)
            temp_path = temp_f.name
        os.replace(temp_path, new_path)
        os.remove(old_path)


def atomic_append_to_ai_md(entry: str) -> None:
    ai_md_path = "AI.md"
    lock_path = ai_md_path + '.lock'
    with FileLock(lock_path):
        if not os.path.exists(ai_md_path):
            header = """# AI System Learning Log\n\nThis file captures learnings from the AI-powered code review and triage system.\nEach entry documents decisions, patterns, and insights to improve future performance.\n\n"""
            current_content = header
        else:
            with open(ai_md_path, 'r') as f:
                current_content = f.read()
        new_content = current_content + entry
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.md') as temp_f:
            temp_f.write(new_content)
            temp_path = temp_f.name
        os.replace(temp_path, ai_md_path)


def consistency_check_todos(todos_dir: str) -> None:
    issue_to_files = {}
    for file_path in glob.glob(os.path.join(todos_dir, '*.md')):
        filename = os.path.basename(file_path)
        match = re.match(r'^(\d+)-', filename)
        if match:
            issue_id = match.group(1)
            issue_to_files.setdefault(issue_id, []).append(filename)
    duplicates = {iid: files for iid, files in issue_to_files.items() if len(files) > 1}
    if duplicates:
        console.print("[yellow]Warning: Duplicate issue IDs found:[/yellow]")
        for iid, files in duplicates.items():
            console.print(f"  Issue {iid}: {files}")
    console.print("[green]Consistency check passed.[/green]")


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


def _fill_recommended_action(content: str, solution_text: str = None) -> str:
    """Replace the 'Recommended Action' placeholder with actual recommendation."""
    placeholder = "*To be filled during triage.*"
    
    if solution_text:
        recommendation = solution_text
    else:
        recommendation = (
            "Implement the proposed solution from the code review finding (Option 1)."
        )

    return content.replace(placeholder, recommendation)


def _log_to_ai_md(finding_title: str, decision: str, learnings: str) -> None:
    """Log triage decisions and learnings to AI.md for system learning."""
    ai_md_path = "AI.md"
    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    entry = f"""
---

## [{today}] Triage Decision: {finding_title}

**Decision:** {decision}

**Learnings:**
{learnings}

"""
    
    # Create AI.md if it doesn't exist
    if not os.path.exists(ai_md_path):
        header = """# AI System Learning Log

This file captures learnings from the AI-powered code review and triage system.
Each entry documents decisions, patterns, and insights to improve future performance.

"""
        with open(ai_md_path, "w") as f:
            f.write(header)
    
    # Append the new entry
    with open(ai_md_path, "a") as f:
        f.write(entry)


def run_triage():
    todos_dir = "todos"
    if not os.path.exists(todos_dir):
        console.print(
            f"[yellow]Directory '{todos_dir}' does not exist. Creating it...[/yellow]"
        )
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

    console.print(
        f"[bold]Found {len(pending_files)} pending items for triage.[/bold]\n"
    )

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
        console.print(f"\n[dim]Progress: {idx - 1}/{total_items} completed[/dim]")
        console.rule(f"[{idx}/{total_items}] Triaging: {filename}")

        # Use LLM to present the finding
        with console.status("Analyzing finding..."):
            response = triage_predictor(finding_content=content)

        console.print(Markdown(response.formatted_presentation))
        console.print("\n")

        # Debug: Show action_required value
        if hasattr(response, 'action_required'):
            if response.action_required:
                action_status = "⚠️  Action IS Required (code changes needed)"
            else:
                action_status = "✅ No Action Required (review passed)"
            console.print(f"[dim]Analysis: {action_status}[/dim]")
        else:
            console.print("[dim yellow]Warning: action_required field not present[/dim yellow]")

        # Content-based fallback analysis (extracted to helper)
        def suggests_no_action(content: str) -> bool:
            content_lower = content.lower()
            proposed_solution = ""
            if "proposed solution:" in content_lower:
                parts = content_lower.split("proposed solution:", 1)
                if len(parts) > 1:
                    proposed_solution = parts[1].split("\n\n")[0] if parts[1] else ""
            no_action_indicators = [
                "no fixes required",
                "no changes required",
                "no action required",
                "acknowledge clean review",
                "acknowledge the",
                "optionally document",
                "close the issue",
            ]
            action_indicators = [
                "implement",
                "refactor",
                "extract",
                "add",
                "fix",
                "update",
                "create",
                "modify",
                "strengthen",
                "improve",
            ]
            description_no_action = any(
                phrase in content_lower
                for phrase in [
                    "no vulnerabilities identified",
                    "no issues identified",
                    "passes all checks",
                    "all checks passed",
                ]
            )
            solution_suggests_no_action = (
                any(indicator in proposed_solution for indicator in no_action_indicators)
                and not any(indicator in proposed_solution for indicator in action_indicators)
            )
            return description_no_action or solution_suggests_no_action

        content_suggests_no_action = suggests_no_action(content)
        # Simplified: Trust action_required FIRST, fallback ONLY if missing; warn on mismatch
        should_auto_complete = (
            (hasattr(response, 'action_required') and not response.action_required) or
            (not hasattr(response, 'action_required') and content_suggests_no_action)
        )
        if (
            hasattr(response, 'action_required')
            and response.action_required
            and content_suggests_no_action
        ):
            console.print(
                "[yellow]⚠️ Warning: LLM action_required=True but content suggests no action. "
                "Trusting structured field (no override).[/yellow]"
            )
        # Auto-complete if no action required
        if should_auto_complete:
            console.print("[dim]🤖 Auto-completing: No action required[/dim]")
            
            if "-pending-" in filename:
                new_filename = filename.replace("-pending-", "-complete-")
                new_path = os.path.join(todos_dir, new_filename)
                resolution_section = "\n## Resolution Summary\n\n**Status:** ✅ Resolved (Auto-Triage)\n**Summary:** Automatically marked as complete - no action required based on finding analysis.\n"
                action_msg = "Auto-completed during triage (no action required)"
                def update_auto(parsed):
                    fm = dict(parsed['frontmatter'])
                    fm['status'] = 'complete'
                    new_body = parsed['body']
                    if "## Resolution Summary" not in new_body:
                        new_body = resolution_section + '\n' + new_body
                    temp_full = serialize_todo(fm, new_body)
                    updated_full = _add_work_log_entry(temp_full, action_msg)
                    post = frontmatter.loads(updated_full)
                    return {'frontmatter': dict(post.metadata), 'body': post.content}
                atomic_update_todo(file_path, new_path, update_auto)
                console.print(
                    f"[green]✅ Auto-Completed: {new_filename}[/green]"
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
                solution = response.proposed_solution if hasattr(response, 'proposed_solution') else None
                new_content = _fill_recommended_action(new_content, solution)
                
                new_content = _add_work_log_entry(
                    new_content, "Issue approved during triage session"
                )
                
                # Log to AI.md
                _log_to_ai_md(
                    finding_title=filename.replace(".md", ""),
                    decision="Approved for work",
                    learnings=f"Proposed solution: {solution}" if solution else "Standard approval"
                )

                with open(new_path, "w") as f:
                    f.write(new_content)

                os.remove(file_path)
                console.print(
                    f"[green]✅ Approved: {new_filename} - Status: ready[/green]"
                )
                approved_count += 1
                approved_todos.append(new_filename)
            else:
                console.print(
                    f"[red]Error: Filename format unexpected: {filename}[/red]"
                )

        elif choice == "complete":
            # Mark as complete immediately
            if "-pending-" in filename:
                new_filename = filename.replace("-pending-", "-complete-")
                new_path = os.path.join(todos_dir, new_filename)

                # Update status
                new_content = content.replace("status: pending", "status: complete")
                
                # Add resolution summary
                resolution_section = "\n## Resolution Summary\n\n**Status:** ✅ Resolved (Triage)\n**Summary:** Marked as complete during triage (no action required).\n"
                
                if new_content.startswith("---"):
                    parts = new_content.split("---", 2)
                    if len(parts) >= 3:
                        new_content = f"---{parts[1]}---{resolution_section}{parts[2]}"
                else:
                    new_content = resolution_section + new_content

                new_content = _add_work_log_entry(
                    new_content, "Issue marked complete during triage (no action required)"
                )

                with open(new_path, "w") as f:
                    f.write(new_content)

                os.remove(file_path)
                console.print(
                    f"[green]✅ Completed: {new_filename} - Status: complete[/green]"
                )
                # We don't add to approved_todos since it's already done
            else:
                console.print(
                    f"[red]Error: Filename format unexpected: {filename}[/red]"
                )

        elif choice == "all":
            # Accept all remaining items (including current one)
            console.print(
                f"\n[bold cyan]Accepting all {remaining} remaining items...[/bold cyan]"
            )

            # Process current file first
            remaining_files = [file_path] + pending_files[idx:]

            for remaining_path in remaining_files:
                with open(remaining_path, "r") as f:
                    remaining_content = f.read()
                remaining_filename = os.path.basename(remaining_path)

                if "-pending-" in remaining_filename:
                    new_filename = remaining_filename.replace("-pending-", "-ready-")
                    new_path = os.path.join(todos_dir, new_filename)

                    new_content = remaining_content.replace(
                        "status: pending", "status: ready"
                    )
                    
                    # Fill recommended action with proposed solution if available
                    solution = response.proposed_solution if hasattr(response, 'proposed_solution') else None
                    new_content = _fill_recommended_action(new_content, solution)
                    
                    new_content = _add_work_log_entry(
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
                new_filename = re.sub(
                    r"-pending-(p[123])-", f"-ready-{new_priority}-", filename
                )
                new_path = os.path.join(todos_dir, new_filename)

                # Update content
                new_content = content.replace("status: pending", "status: ready")
                new_content = re.sub(
                    r"priority: p[123]", f"priority: {new_priority}", new_content
                )
                
                # Fill recommended action with proposed solution
                solution = response.proposed_solution if hasattr(response, 'proposed_solution') else None
                new_content = _fill_recommended_action(new_content, solution)
                
                new_content = _add_work_log_entry(
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
    table.add_row(
        "[yellow]Skipped (deleted)[/yellow]", f"[yellow]{skipped_count}[/yellow]"
    )

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
    console.print(
        "   [cyan]git add todos/ && git commit -m 'chore: add triaged todos'[/cyan]"
    )
