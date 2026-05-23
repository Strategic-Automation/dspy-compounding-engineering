"""
Sync workflow for creating/updating GitHub issues from todos.

This module parses todos/*.md files and synchronizes them with GitHub issues,
creating new issues for todos without existing links and updating existing ones.
"""

import glob
import os
import re
from typing import Optional

from rich.console import Console
from rich.table import Table

from utils.github import GitHubService
from utils.todo import parse_todo, serialize_todo

console = Console()


def _extract_title_from_body(body: str) -> str:
    """Extract the first H1 heading as the issue title."""
    lines = body.split("\n")
    for line in lines:
        if line.startswith("# "):
            return line[2:].strip()
    return "Untitled Todo"


def _map_priority_to_label(priority: str) -> str:
    """Map todo priority (p1, p2, p3) to GitHub label."""
    mapping = {"p1": "P1", "p2": "P2", "p3": "P3"}
    return mapping.get(priority.lower(), "P2")


def _map_tags_to_labels(tags: list[str], available_labels: list[str]) -> list[str]:
    """Map todo tags to existing GitHub labels (case-insensitive match)."""
    labels = []
    lower_available = {label.lower(): label for label in available_labels}

    for tag in tags:
        tag_lower = tag.lower()
        if tag_lower in lower_available:
            labels.append(lower_available[tag_lower])

    return labels


def _extract_github_issue_number(url_or_number: str) -> Optional[int]:
    """Extract issue number from URL or string."""
    if not url_or_number:
        return None

    # If it's just a number
    if isinstance(url_or_number, int):
        return url_or_number

    url_or_number = str(url_or_number)
    if url_or_number.isdigit():
        return int(url_or_number)

    # Extract from URL
    match = re.search(r"/issues/(\d+)", url_or_number)
    if match:
        return int(match.group(1))

    return None


def _build_issue_body(todo_body: str, file_path: str) -> str:
    """Build the GitHub issue body from todo content."""
    # Add source reference at the bottom
    source_ref = f"\n\n---\n_Source: `{file_path}`_"
    return todo_body + source_ref


def _update_todo_with_github_issue(file_path: str, issue_url: str) -> bool:
    """Update the todo file's frontmatter with the GitHub issue URL."""
    try:
        parsed = parse_todo(file_path)
        fm = parsed["frontmatter"]
        body = parsed["body"]

        fm["github_issue"] = issue_url

        new_content = serialize_todo(fm, body)
        with open(file_path, "w") as f:
            f.write(new_content)

        return True
    except Exception as e:
        console.print(f"[yellow]Warning: Could not update {file_path}: {e}[/yellow]")
        return False


def _sync_single_file(
    file_path: str, dry_run: bool, available_labels: list[str], results: dict
) -> None:
    """Process a single todo file and synchronize it with GitHub."""
    filename = os.path.basename(file_path)
    try:
        parsed = parse_todo(file_path)
        fm = parsed["frontmatter"]
        body = parsed["body"]

        # Extract metadata
        existing_issue = fm.get("github_issue")
        priority = fm.get("priority", "p2")
        tags = fm.get("tags", [])

        # Build title and body
        title = _extract_title_from_body(body)
        issue_body = _build_issue_body(body, file_path)

        # Build labels
        labels = [_map_priority_to_label(priority)]
        if available_labels:
            labels.extend(_map_tags_to_labels(tags, available_labels))

        # Check for existing issue
        issue_number = _extract_github_issue_number(existing_issue)

        if issue_number:
            _update_existing_issue(
                filename, file_path, issue_number, issue_body, title, dry_run, results
            )
        else:
            _create_new_issue(filename, file_path, title, issue_body, labels, dry_run, results)

    except Exception as e:
        console.print(f"[red]Error processing {filename}: {e}[/red]")
        results["errors"].append({"file": filename, "error": str(e)})


def _update_existing_issue(
    filename: str,
    file_path: str,
    issue_number: int,
    issue_body: str,
    title: str,
    dry_run: bool,
    results: dict,
) -> None:
    """Update an existing GitHub issue."""
    if dry_run:
        console.print(f"[cyan]Would update:[/cyan] {filename} → Issue #{issue_number}")
        results["updated"].append({"file": filename, "issue": issue_number})
    else:
        try:
            GitHubService.update_issue(
                issue_number=issue_number,
                body=issue_body,
                title=title,
            )
            console.print(f"[green]Updated:[/green] {filename} → Issue #{issue_number}")
            results["updated"].append({"file": filename, "issue": issue_number})
        except Exception as e:
            console.print(f"[red]Error updating {filename}: {e}[/red]")
            results["errors"].append({"file": filename, "error": str(e)})


def _create_new_issue(
    filename: str,
    file_path: str,
    title: str,
    issue_body: str,
    labels: list[str],
    dry_run: bool,
    results: dict,
) -> None:
    """Create a new GitHub issue."""
    if dry_run:
        console.print(f'[cyan]Would create:[/cyan] {filename} → "{title}"')
        console.print(f"  [dim]Labels: {', '.join(labels)}[/dim]")
        results["created"].append({"file": filename, "title": title})
    else:
        try:
            result = GitHubService.create_issue(
                title=title,
                body=issue_body,
                labels=labels,
            )
            issue_url = result["url"]
            issue_num = result["number"]

            # Update todo file with issue URL
            _update_todo_with_github_issue(file_path, issue_url)

            console.print(f"[green]Created:[/green] {filename} → Issue #{issue_num}")
            results["created"].append(
                {
                    "file": filename,
                    "issue": issue_num,
                    "url": issue_url,
                }
            )
        except Exception as e:
            console.print(f"[red]Error creating issue for {filename}: {e}[/red]")
            results["errors"].append({"file": filename, "error": str(e)})


def run_sync(
    dry_run: bool = False,
    pattern: str = "*",
    todos_dir: str = "todos",
) -> dict:
    """
    Synchronize todos to GitHub issues.

    Args:
        dry_run: If True, preview changes without creating issues
        pattern: Glob pattern to filter todo files
        todos_dir: Directory containing todo files

    Returns:
        Dict with 'created', 'updated', 'skipped' counts and lists
    """
    results = {
        "created": [],
        "updated": [],
        "skipped": [],
        "errors": [],
    }

    if not os.path.exists(todos_dir):
        console.print(f"[yellow]Directory '{todos_dir}' does not exist.[/yellow]")
        return results

    # Get available labels for mapping
    available_labels = []
    if not dry_run:
        try:
            available_labels = GitHubService.list_labels()
        except Exception as e:
            console.print(f"[yellow]Could not fetch labels: {e}[/yellow]")

    # Find todo files
    glob_pattern = os.path.join(todos_dir, f"{pattern}.md")
    todo_files = glob.glob(glob_pattern)

    # Filter for pending and ready status only
    syncable_files = []
    for file_path in todo_files:
        try:
            parsed = parse_todo(file_path)
            status = parsed["frontmatter"].get("status", "")
            if status in ("pending", "ready"):
                syncable_files.append(file_path)
        except Exception:
            continue

    if not syncable_files:
        console.print("[dim]No pending or ready todos found to sync.[/dim]")
        return results

    console.print(f"[bold]Found {len(syncable_files)} todos to sync.[/bold]\n")

    for file_path in sorted(syncable_files):
        _sync_single_file(file_path, dry_run, available_labels, results)

    # Print summary
    _print_summary(results, dry_run)

    return results


def _print_summary(results: dict, dry_run: bool) -> None:
    """Print a summary table of sync results."""
    console.print()
    console.rule("[bold]Sync Summary[/bold]")

    table = Table()
    table.add_column("Action", style="bold")
    table.add_column("Count", justify="right")

    prefix = "Would " if dry_run else ""

    table.add_row(f"[green]{prefix}Created[/green]", str(len(results["created"])))
    table.add_row(f"[blue]{prefix}Updated[/blue]", str(len(results["updated"])))
    table.add_row("[red]Errors[/red]", str(len(results["errors"])))

    console.print(table)

    if dry_run:
        console.print("\n[dim]Run without --dry-run to execute these changes.[/dim]")
