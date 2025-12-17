import os
import subprocess

from pydantic import BaseModel
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress
from rich.table import Table

from agents.review import (
    AgentNativeReviewer,
    ArchitectureStrategist,
    CodeSimplicityReviewer,
    DataIntegrityGuardian,
    DhhRailsReviewer,
    JulikFrontendRacesReviewer,
    KieranPythonReviewer,
    KieranRailsReviewer,
    KieranTypescriptReviewer,
    PatternRecognitionSpecialist,
    PerformanceOracle,
    SecuritySentinel,
)
from utils.context import ProjectContext
from utils.knowledge import KBPredict
from utils.todo import create_finding_todo

console = Console()


def convert_pydantic_to_markdown(model: BaseModel) -> str:  # noqa: C901
    """
    Convert any Pydantic model into a structured markdown report.
    Auto-detects findings lists and summary fields.
    """
    data = model.model_dump()
    parts = []

    # 1. Handle Summary Fields (High Priority)
    summary_keys = [
        "executive_summary",
        "architecture_overview",
        "summary",
        "overview",
        "assessment",
    ]
    for key in summary_keys:
        if key in data and isinstance(data[key], str):
            title = key.replace("_", " ").title()
            parts.append(f"# {title}\n\n{data[key]}\n")
            del data[key]  # Consumed

    # 2. Handle Findings List (Core Content)
    if "findings" in data and isinstance(data["findings"], list):
        findings = data["findings"]
        if findings:
            parts.append("## Detailed Findings\n")
            for f in findings:
                # Try to get title, fallback to generic
                f_title = f.get("title", "Untitled Finding")
                parts.append(f"### {f_title}\n")

                # Print other fields in list format
                for k, v in f.items():
                    if k == "title":
                        continue
                    label = k.replace("_", " ").title()
                    parts.append(f"- **{label}**: {v}")
                parts.append("")  # Spacing
        del data["findings"]

    # 3. Handle Remaining Fields (Generic Sections)
    for key, value in data.items():
        if key == "action_required":
            continue  # meaningful metadata but not report text

        if isinstance(value, str):
            title = key.replace("_", " ").title()
            parts.append(f"## {title}\n\n{value}\n")
        elif isinstance(value, (dict, list)):
            # Fallback for complex nested data
            import json

            title = key.replace("_", " ").title()
            json_str = json.dumps(value, indent=2)
            parts.append(f"## {title}\n\n```json\n{json_str}\n```\n")

    return "\n".join(parts)


def run_review(pr_url_or_id: str, project: bool = False):  # noqa: C901
    """
    Perform exhaustive multi-agent code review.

    Args:
        pr_url_or_id: PR number, GitHub URL, branch name, or 'latest'
        project: If True, review entire project instead of just changes
    """

    import concurrent.futures

    from utils.git import GitService

    if project:
        console.print("[bold]Starting Full Project Review[/bold]\n")
    else:
        console.print(f"[bold]Starting Code Review:[/bold] {pr_url_or_id}\n")

    worktree_path = None

    try:
        if project:
            # Full project review - gather all source files
            console.print("[cyan]Gathering project files...[/cyan]")
            context_service = ProjectContext()
            code_diff = context_service.gather_project_files()
            if not code_diff:
                console.print("[red]No source files found to review![/red]")
                return
            console.print(
                f"[green]✓ Gathered {len(code_diff):,} characters of project code[/green]"
            )
        elif pr_url_or_id == "latest":
            # Default to checking current staged/unstaged changes or HEAD
            console.print("[cyan]Fetching local changes...[/cyan]")
            code_diff = GitService.get_diff("HEAD")
            summary = GitService.get_file_status_summary("HEAD")

            if not code_diff:
                console.print(
                    "[yellow]No changes found in HEAD. Checking staged changes...[/yellow]"
                )
                code_diff = GitService.get_diff("--staged")
                summary = GitService.get_file_status_summary("--staged")

            if summary and code_diff:
                code_diff = (
                    f"FILE STATUS SUMMARY (Renames Detected):\n{summary}\n\nGIT DIFF:\n{code_diff}"
                )
        else:
            # Fetch PR diff
            console.print(f"[cyan]Fetching diff for {pr_url_or_id}...[/cyan]")
            code_diff = GitService.get_pr_diff(pr_url_or_id)

            # Create isolated worktree for PR
            try:
                # Sanitize ID for path
                safe_id = "".join(c for c in pr_url_or_id if c.isalnum() or c in ("-", "_"))
                worktree_path = f"worktrees/review-{safe_id}"

                if os.path.exists(worktree_path):
                    console.print(
                        f"[yellow]Worktree {worktree_path} already exists. Using it.[/yellow]"
                    )
                else:
                    console.print(f"[cyan]Creating isolated worktree at {worktree_path}...[/cyan]")
                    GitService.checkout_pr_worktree(pr_url_or_id, worktree_path)
                    console.print("[green]✓ Worktree created[/green]")
            except Exception as e:
                console.print(
                    "[yellow]Warning: Could not create worktree (proceeding with diff only): "
                    f"{e}[/yellow]"
                )

        if not code_diff:
            console.print("[red]No diff found to review![/red]")
            return

        # Truncate if too large (simple safety check)
        MAX_DIFF_SIZE = 50000
        if len(code_diff) > MAX_DIFF_SIZE:
            console.print(
                f"[yellow]Warning: Content is very large ({len(code_diff)} chars). "
                f"Truncating to {MAX_DIFF_SIZE}...[/yellow]"
            )
            code_diff = code_diff[:MAX_DIFF_SIZE] + "\n...[truncated]..."

    except Exception as e:
        console.print(f"[red]Error fetching content: {e}[/red]")
        # Fallback for demo purposes if git fails
        console.print("[yellow]Falling back to placeholder diff for demonstration...[/yellow]")
        code_diff = """
        # Placeholder diff (Git fetch failed)
        # Ensure git and gh CLI are installed and configured
        """

    console.rule("Running Review Agents")

    # Define all review agents
    review_agents = [
        ("Kieran Rails Reviewer", KieranRailsReviewer),
        ("Kieran TypeScript Reviewer", KieranTypescriptReviewer),
        ("Kieran Python Reviewer", KieranPythonReviewer),
        ("Security Sentinel", SecuritySentinel),
        ("Performance Oracle", PerformanceOracle),
        ("Data Integrity Guardian", DataIntegrityGuardian),
        ("Architecture Strategist", ArchitectureStrategist),
        ("Pattern Recognition Specialist", PatternRecognitionSpecialist),
        ("Code Simplicity Reviewer", CodeSimplicityReviewer),
        ("DHH Rails Reviewer", DhhRailsReviewer),
        ("Agent Native Reviewer", AgentNativeReviewer),
        ("Julik Frontend Races Reviewer", JulikFrontendRacesReviewer),
    ]

    findings = []

    def run_single_agent(name, agent_cls, diff):
        try:
            # Use KB-augmented Predict to inject past learnings
            predictor = KBPredict(
                agent_cls,
                kb_tags=["code-review", name.lower().replace(" ", "-")],
            )

            return name, predictor(code_diff=diff)
        except Exception as e:
            return name, f"Error: {e}"

    with Progress() as progress:
        task = progress.add_task("[cyan]Running agents in parallel...", total=len(review_agents))

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all tasks
            future_to_agent = {
                executor.submit(run_single_agent, name, cls, code_diff): name
                for name, cls in review_agents
            }

            for future in concurrent.futures.as_completed(future_to_agent):
                agent_name = future_to_agent[future]
                progress.update(task, description=f"[cyan]Completed {agent_name}...")
                progress.advance(task)

                try:
                    name, result = future.result()

                    if isinstance(result, str) and result.startswith("Error:"):
                        findings.append({"agent": name, "review": result})
                        continue

                    review_text = None
                    action_required_val = None
                    report_data = None
                    report_obj = None  # Keep track for attribute access if needed

                    # 1. Attempt to find the report data (model or dict)
                    if hasattr(result, "model_dump"):
                        report_data = result.model_dump()
                        report_obj = result
                    elif isinstance(result, dict):
                        report_data = result
                    else:
                        # Scan common output fields for the report model
                        for field_name in [
                            "review_comments",
                            "security_report",
                            "performance_analysis",
                            "architecture_analysis",
                            "data_integrity_report",
                            "pattern_analysis",
                            "simplification_analysis",
                            "dhh_review",
                            "agent_native_analysis",
                            "race_condition_analysis",
                        ]:
                            if hasattr(result, field_name):
                                val = getattr(result, field_name)
                                if hasattr(val, "model_dump"):
                                    report_data = val.model_dump()
                                    report_obj = val
                                    break
                                elif isinstance(val, dict):
                                    report_data = val
                                    break

                    # 2. Render the report if found
                    if report_data:
                        data = report_data
                        parts = []

                        # A. Standard Sections
                        if "summary" in data:
                            parts.append(f"# Summary\n\n{data['summary']}\n")
                        elif "executive_summary" in data:
                            parts.append(f"# Summary\n\n{data['executive_summary']}\n")

                        if "analysis" in data:
                            parts.append(f"## Analysis\n\n{data['analysis']}\n")

                        if "findings" in data and isinstance(data["findings"], list):
                            found_list = data["findings"]
                            if found_list:
                                parts.append("## Detailed Findings\n")
                                for f in found_list:
                                    title = f.get("title", "Untitled Finding")
                                    severity = f.get("severity", "Medium")
                                    parts.append(f"### {title} ({severity})\n")
                                    if "description" in f:
                                        parts.append(f"{f['description']}\n")
                                    for k, v in f.items():
                                        if k in ["title", "description", "severity"]:
                                            continue
                                        label = k.replace("_", " ").title()
                                        parts.append(f"- **{label}**: {v}")
                                    parts.append("")

                        # B. Unique/Extra Sections
                        captured_keys = {
                            "summary",
                            "executive_summary",
                            "analysis",
                            "findings",
                            "action_required",
                        }
                        for key, value in data.items():
                            if key in captured_keys:
                                continue

                            if isinstance(value, str):
                                title = key.replace("_", " ").title()
                                parts.append(f"## {title}\n\n{value}\n")
                            elif isinstance(value, (dict, list)):
                                import json

                                title = key.replace("_", " ").title()
                                try:
                                    json_str = json.dumps(value, indent=2)
                                    parts.append(f"## {title}\n\n```json\n{json_str}\n```\n")
                                except Exception:
                                    parts.append(f"## {title}\n\n{str(value)}\n")
                            elif isinstance(value, (int, float, bool)):
                                title = key.replace("_", " ").title()
                                parts.append(f"## {title}\n\n{value}\n")

                        review_text = "\n".join(parts)
                        # Try to get action_required from dict or object
                        action_required_val = data.get("action_required")
                        if action_required_val is None and report_obj:
                            action_required_val = getattr(report_obj, "action_required", None)

                    # 3. Fallback
                    else:
                        review_text = str(result)

                    if review_text:
                        finding_data = {"agent": name, "review": review_text}
                        if action_required_val is not None:
                            finding_data["action_required"] = action_required_val
                        findings.append(finding_data)

                except Exception as e:
                    findings.append({"agent": agent_name, "review": f"Execution failed: {e}"})

    console.rule("Review Complete")

    # Display findings
    console.print("\n[bold green]All review agents completed![/bold green]\n")

    for finding in findings:
        console.print(f"\n[bold cyan]## {finding['agent']}[/bold cyan]")
        console.print(Markdown(finding["review"]))

    # Create pending todo files for all findings
    console.rule("Creating Todo Files")

    todos_dir = "todos"
    os.makedirs(todos_dir, exist_ok=True)

    created_todos = []
    p1_count = 0
    p2_count = 0
    p3_count = 0

    # Map agent names to categories and default severities
    agent_categories = {
        "Security Sentinel": ("security", "p1"),
        "Performance Oracle": ("performance", "p2"),
        "Data Integrity Guardian": ("data-integrity", "p1"),
        "Architecture Strategist": ("architecture", "p2"),
        "Pattern Recognition Specialist": ("patterns", "p3"),
        "Code Simplicity Reviewer": ("simplicity", "p3"),
        "DHH Rails Reviewer": ("rails", "p2"),
        "Kieran Rails Reviewer": ("rails", "p2"),
        "Kieran TypeScript Reviewer": ("typescript", "p2"),
        "Kieran Python Reviewer": ("python", "p2"),
        "Agent Native Reviewer": ("agent-native", "p2"),
        "Julik Frontend Races Reviewer": ("frontend", "p2"),
    }

    for finding in findings:
        agent_name = finding.get("agent", "Unknown")
        review_text = finding.get("review", "")

        # Skip error findings or empty reviews
        if (
            not review_text
            or review_text.startswith("Error:")
            or review_text.startswith("Execution failed:")
        ):
            continue

        # Check action_required field from agent
        action_required = finding.get("action_required")

        # If agent explicitly says no action required, skip it
        if action_required is False:
            console.print(
                f"  [dim]Skipped {agent_name}: No actionable findings (action_required=False)[/dim]"
            )
            continue

        # Get category and severity from agent
        category, severity = agent_categories.get(agent_name, ("code-review", "p2"))

        # Create a title from agent name
        title = f"{agent_name} Finding"

        # Build finding dict for todo creation
        finding_data = {
            "agent": agent_name,
            "review": review_text,
            "severity": severity,
            "category": category,
            "title": title,
            "effort": "Medium",
        }

        try:
            todo_path = create_finding_todo(finding_data, todos_dir=todos_dir)
            created_todos.append(
                {
                    "path": todo_path,
                    "agent": agent_name,
                    "severity": severity,
                }
            )

            if severity == "p1":
                p1_count += 1
            elif severity == "p2":
                p2_count += 1
            else:
                p3_count += 1

            console.print(f"  [green]✓[/green] Created: [cyan]{os.path.basename(todo_path)}[/cyan]")
        except Exception as e:
            console.print(f"  [red]✗ Failed to create todo for {agent_name}: {e}[/red]")

    # Summary table
    if created_todos:
        console.print()
        table = Table(title="📋 Created Todo Files")
        table.add_column("File", style="cyan")
        table.add_column("Agent", style="white")
        table.add_column("Priority", style="bold")

        for todo in created_todos:
            priority_style = {
                "p1": "[red]🔴 P1 CRITICAL[/red]",
                "p2": "[yellow]🟡 P2 IMPORTANT[/yellow]",
                "p3": "[blue]🔵 P3 NICE-TO-HAVE[/blue]",
            }.get(todo["severity"], todo["severity"])

            table.add_row(
                os.path.basename(todo["path"]),
                todo["agent"],
                priority_style,
            )

        console.print(table)

        console.print("\n[bold]Findings Summary:[/bold]")
        console.print(f"  Total Findings: {len(created_todos)}")
        if p1_count:
            console.print(f"  [red]🔴 CRITICAL (P1): {p1_count} - BLOCKS MERGE[/red]")
        if p2_count:
            console.print(f"  [yellow]🟡 IMPORTANT (P2): {p2_count} - Should Fix[/yellow]")
        if p3_count:
            console.print(f"  [blue]🔵 NICE-TO-HAVE (P3): {p3_count} - Enhancements[/blue]")
    else:
        console.print("[green]No actionable findings to create todos for.[/green]")

    # Extract and codify learnings from the review
    if findings:
        from utils.knowledge import codify_review_findings

        try:
            codify_review_findings(findings, len(created_todos))
        except Exception as e:
            console.print(f"[yellow]⚠ Could not codify review learnings: {e}[/yellow]")

    # Cleanup worktree
    if worktree_path and os.path.exists(worktree_path):
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

    console.print("\n[bold]Next Steps:[/bold]")
    console.print("1. View pending todos: [cyan]ls todos/*-pending-*.md[/cyan]")
    console.print("2. Triage findings: [cyan]python cli.py triage[/cyan]")
    console.print("3. Work on approved items: [cyan]python cli.py work <plan_file>[/cyan]")
