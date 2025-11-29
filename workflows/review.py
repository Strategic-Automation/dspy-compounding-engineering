import os
import subprocess
import dspy
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress
from rich.table import Table
from agents.review import (
    KieranRailsReviewer,
    KieranTypescriptReviewer,
    KieranPythonReviewer,
    SecuritySentinel,
    CodeSimplicityReviewer,
    DhhRailsReviewer,
    PerformanceOracle,
    DataIntegrityGuardian,
    ArchitectureStrategist,
    PatternRecognitionSpecialist,
)
from utils.todo_service import create_finding_todo

console = Console()

def run_review(pr_url_or_id: str):
    """
    Perform exhaustive multi-agent code review.
    
    Args:
        pr_url_or_id: PR number, GitHub URL, branch name, or 'latest'
    """
    
    from utils.git_service import GitService
    import concurrent.futures
    
    console.print(f"[bold]Starting Code Review:[/bold] {pr_url_or_id}\n")
    
    worktree_path = None
    
    try:
        if pr_url_or_id == "latest":
            # Default to checking current staged/unstaged changes or HEAD
            console.print("[cyan]Fetching local changes...[/cyan]")
            code_diff = GitService.get_diff("HEAD")
            if not code_diff:
                console.print("[yellow]No changes found in HEAD. Checking staged changes...[/yellow]")
                code_diff = GitService.get_diff("--staged")
        else:
            # Fetch PR diff
            console.print(f"[cyan]Fetching diff for {pr_url_or_id}...[/cyan]")
            code_diff = GitService.get_pr_diff(pr_url_or_id)
            
            # Create isolated worktree for PR
            try:
                # Sanitize ID for path
                safe_id = "".join(c for c in pr_url_or_id if c.isalnum() or c in ('-', '_'))
                worktree_path = f"worktrees/review-{safe_id}"
                
                if os.path.exists(worktree_path):
                    console.print(f"[yellow]Worktree {worktree_path} already exists. Using it.[/yellow]")
                else:
                    console.print(f"[cyan]Creating isolated worktree at {worktree_path}...[/cyan]")
                    GitService.checkout_pr_worktree(pr_url_or_id, worktree_path)
                    console.print(f"[green]✓ Worktree created[/green]")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not create worktree (proceeding with diff only): {e}[/yellow]")
            
        if not code_diff:
            console.print("[red]No diff found to review![/red]")
            return
            
        # Truncate if too large (simple safety check)
        if len(code_diff) > 100000:
            console.print(f"[yellow]Warning: Diff is very large ({len(code_diff)} chars). Truncating...[/yellow]")
            code_diff = code_diff[:100000] + "\n...[truncated]..."
            
    except Exception as e:
        console.print(f"[red]Error fetching diff: {e}[/red]")
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
    ]
    
    findings = []
    
    def run_single_agent(name, agent_cls, diff):
        try:
            predictor = dspy.Predict(agent_cls)
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
                        findings.append({'agent': name, 'review': result})
                        continue

                    # Extract the review from the result
                    review_text = None
                    # Check all possible output fields
                    for field in [
                        'review_comments', 'security_report', 'performance_analysis',
                        'data_integrity_report', 'architecture_analysis', 'pattern_analysis',
                        'simplification_analysis', 'dhh_review'
                    ]:
                        if hasattr(result, field):
                            review_text = getattr(result, field)
                            break
                    
                    if review_text:
                        findings.append({
                            'agent': name,
                            'review': review_text
                        })
                        
                except Exception as e:
                    findings.append({'agent': agent_name, 'review': f"Execution failed: {e}"})

    console.rule("Review Complete")

    # Display findings
    console.print("\n[bold green]All review agents completed![/bold green]\n")

    for finding in findings:
        console.print(f"\n[bold cyan]## {finding['agent']}[/bold cyan]")
        console.print(Markdown(finding['review']))

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
        if not review_text or review_text.startswith("Error:") or review_text.startswith("Execution failed:"):
            continue

        # Skip findings that indicate no issues (common patterns)
        lower_review = review_text.lower()
        if any(phrase in lower_review for phrase in [
            "no issues found",
            "no concerns",
            "looks good",
            "no problems",
            "nothing to report",
            "no findings",
            "code looks clean",
        ]):
            console.print(f"  [dim]Skipped {agent_name}: No actionable findings[/dim]")
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
            created_todos.append({
                "path": todo_path,
                "agent": agent_name,
                "severity": severity,
            })

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

        console.print(f"\n[bold]Findings Summary:[/bold]")
        console.print(f"  Total Findings: {len(created_todos)}")
        if p1_count:
            console.print(f"  [red]🔴 CRITICAL (P1): {p1_count} - BLOCKS MERGE[/red]")
        if p2_count:
            console.print(f"  [yellow]🟡 IMPORTANT (P2): {p2_count} - Should Fix[/yellow]")
        if p3_count:
            console.print(f"  [blue]🔵 NICE-TO-HAVE (P3): {p3_count} - Enhancements[/blue]")
    else:
        console.print("[green]No actionable findings to create todos for.[/green]")

    # Cleanup worktree
    if worktree_path and os.path.exists(worktree_path):
        console.print(f"\n[yellow]Cleaning up worktree {worktree_path}...[/yellow]")
        try:
            subprocess.run(["git", "worktree", "remove", "--force", worktree_path],
                         check=True, capture_output=True)
            console.print("[green]✓ Worktree removed[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Failed to remove worktree: {e}[/red]")

    console.print("\n[bold]Next Steps:[/bold]")
    console.print("1. View pending todos: [cyan]ls todos/*-pending-*.md[/cyan]")
    console.print("2. Triage findings: [cyan]python cli.py triage[/cyan]")
    console.print("3. Work on approved items: [cyan]python cli.py work <plan_file>[/cyan]")
