import os
import subprocess

from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress
from rich.table import Table

from agents.review import (
    ArchitectureStrategist,
    CodeSimplicityReviewer,
    DataIntegrityGuardian,
    DhhRailsReviewer,
    KieranPythonReviewer,
    KieranRailsReviewer,
    KieranTypescriptReviewer,
    PatternRecognitionSpecialist,
    PerformanceOracle,
    SecuritySentinel,
)
from utils.kb_module import KBPredict
from utils.project_context import ProjectContext
from utils.todo_service import create_finding_todo

console = Console()


def run_review(pr_url_or_id: str, project: bool = False):
    """
    Perform exhaustive multi-agent code review.

    Args:
        pr_url_or_id: PR number, GitHub URL, branch name, or 'latest'
        project: If True, review entire project instead of just changes
    """

    import concurrent.futures

    from utils.git_service import GitService

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
            if not code_diff:
                console.print(
                    "[yellow]No changes found in HEAD. Checking staged changes...[/yellow]"
                )
                code_diff = GitService.get_diff("--staged")
        else:
            # Fetch PR diff
            console.print(f"[cyan]Fetching diff for {pr_url_or_id}...[/cyan]")
            code_diff = GitService.get_pr_diff(pr_url_or_id)

            # Create isolated worktree for PR
            try:
                # Sanitize ID for path
                safe_id = "".join(
                    c for c in pr_url_or_id if c.isalnum() or c in ("-", "_")
                )
                worktree_path = f"worktrees/review-{safe_id}"

                if os.path.exists(worktree_path):
                    console.print(
                        f"[yellow]Worktree {worktree_path} already exists. Using it.[/yellow]"
                    )
                else:
                    console.print(
                        f"[cyan]Creating isolated worktree at {worktree_path}...[/cyan]"
                    )
                    GitService.checkout_pr_worktree(pr_url_or_id, worktree_path)
                    console.print("[green]✓ Worktree created[/green]")
            except Exception as e:
                console.print(
                    f"[yellow]Warning: Could not create worktree (proceeding with diff only): {e}[/yellow]"
                )

        if not code_diff:
            console.print("[red]No diff found to review![/red]")
            return

        # Truncate if too large (simple safety check)
        MAX_DIFF_SIZE = 50000
        if len(code_diff) > MAX_DIFF_SIZE:
            console.print(
                f"[yellow]Warning: Content is very large ({len(code_diff)} chars). Truncating to {MAX_DIFF_SIZE}...[/yellow]"
            )
            code_diff = code_diff[:MAX_DIFF_SIZE] + "\n...[truncated]..."

    except Exception as e:
        console.print(f"[red]Error fetching content: {e}[/red]")
        # Fallback for demo purposes if git fails
        console.print(
            "[yellow]Falling back to placeholder diff for demonstration...[/yellow]"
        )
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
        task = progress.add_task(
            "[cyan]Running agents in parallel...", total=len(review_agents)
        )

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

                    # Extract the review from the result
                    review_text = None
                    action_required_val = None

                    # NEW: specialized handling for SecuritySentinel (typed)
                    # Handle both spaced and unspaced names to be safe
                    if name in ["SecuritySentinel", "Security Sentinel"] and hasattr(
                        result, "security_report"
                    ):
                        report = result.security_report
                        # Check if it's a Pydantic model (it should be)
                        if hasattr(report, "model_dump"):
                            data = report.model_dump()
                            action_required_val = data.get("action_required", None)

                            # Convert structured report back to markdown for todo creation
                            title_block = f"# Security Audit: {data.get('executive_summary', 'Report')}\n\n"
                            matrix_block = (
                                f"## Risk Matrix\n{data.get('risk_matrix', 'N/A')}\n\n"
                            )

                            findings_block = "## Detailed Findings\n"
                            for f in data.get("findings", []):
                                findings_block += f"### {f.get('title', 'Untitled')}\n"
                                findings_block += (
                                    f"- **Severity**: {f.get('severity')}\n"
                                )
                                findings_block += (
                                    f"- **Description**: {f.get('description')}\n"
                                )
                                findings_block += (
                                    f"- **Location**: {f.get('location')}\n"
                                )
                                findings_block += f"- **Impact**: {f.get('impact')}\n"
                                findings_block += (
                                    f"- **Remediation**: {f.get('remediation')}\n\n"
                                )

                            review_text = title_block + matrix_block + findings_block
                        else:
                            # Fallback if somehow not pydantic
                            review_text = str(report)

                    else:
                        # Existing logic for other agents
                        # Check all possible output fields
                        for field in [
                            "review_comments",
                            "security_report",
                            "performance_analysis",
                            "data_integrity_report",
                            "architecture_analysis",
                            "pattern_analysis",
                            "simplification_analysis",
                            "dhh_review",
                        ]:
                            if hasattr(result, field):
                                val = getattr(result, field)
                                # SAFETY: Ensure we never look at a raw object as a string
                                if hasattr(val, "model_dump"):
                                    # It's a Pydantic model we didn't expect? Dump it to JSON/String
                                    import json

                                    review_text = f"```json\n{json.dumps(val.model_dump(), indent=2)}\n```"
                                else:
                                    review_text = str(val)
                                break

                    if review_text:
                        finding_data = {"agent": name, "review": review_text}

                        # Use extracted action_required if available, else look on result object
                        if action_required_val is not None:
                            finding_data["action_required"] = action_required_val
                        elif hasattr(result, "action_required"):
                            finding_data["action_required"] = result.action_required

                        findings.append(finding_data)

                except Exception as e:
                    findings.append(
                        {"agent": agent_name, "review": f"Execution failed: {e}"}
                    )

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

            console.print(
                f"  [green]✓[/green] Created: [cyan]{os.path.basename(todo_path)}[/cyan]"
            )
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
            console.print(
                f"  [yellow]🟡 IMPORTANT (P2): {p2_count} - Should Fix[/yellow]"
            )
        if p3_count:
            console.print(
                f"  [blue]🔵 NICE-TO-HAVE (P3): {p3_count} - Enhancements[/blue]"
            )
    else:
        console.print("[green]No actionable findings to create todos for.[/green]")

    # Extract and codify learnings from the review
    if findings:
        from utils.learning_extractor import codify_review_findings

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
    console.print(
        "3. Work on approved items: [cyan]python cli.py work <plan_file>[/cyan]"
    )
