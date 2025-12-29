import concurrent.futures
import os
import re
import subprocess
from typing import Any, Optional

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
from utils.git import GitService
from utils.io.logger import logger
from utils.knowledge import KBPredict
from utils.todo import create_finding_todo

console = Console()


def detect_languages(code_content: str) -> set[str]:
    """
    Detect programming languages from file paths in code content.
    Returns a set of detected language identifiers.
    """
    # Match file paths like "diff --git a/path/to/file.py" or "+++ b/file.ts"
    file_patterns = [
        r"diff --git a/([^\s]+)",
        r"\+\+\+ [ab]/([^\s]+)",
        r"--- [ab]/([^\s]+)",
        r"File: ([^\s]+)",
    ]

    extensions = set()
    for pattern in file_patterns:
        for match in re.findall(pattern, code_content):
            if "." in match:
                ext = match.rsplit(".", 1)[-1].lower()
                extensions.add(ext)

    # Map extensions to language identifiers
    lang_map = {
        "py": "python",
        "rb": "ruby",
        "ts": "typescript",
        "tsx": "typescript",
        "js": "javascript",
        "jsx": "javascript",
        "rs": "rust",
        "go": "go",
        "java": "java",
        "kt": "kotlin",
        "swift": "swift",
        "cs": "csharp",
        "cpp": "cpp",
        "c": "c",
        "h": "c",
        "hpp": "cpp",
    }

    languages = set()
    for ext in extensions:
        if ext in lang_map:
            languages.add(lang_map[ext])
        else:
            languages.add(ext)  # Keep unknown extensions as-is

    return languages


# Reviewer configuration: (name, class, applicable_languages)
# None for applicable_languages means universal (runs for all code)
REVIEWER_CONFIG = [
    ("Kieran Python Reviewer", KieranPythonReviewer, {"python"}),
    ("Kieran Rails Reviewer", KieranRailsReviewer, {"ruby"}),
    ("DHH Rails Reviewer", DhhRailsReviewer, {"ruby"}),
    ("Kieran TypeScript Reviewer", KieranTypescriptReviewer, {"typescript", "javascript"}),
    ("Julik Frontend Races Reviewer", JulikFrontendRacesReviewer, {"typescript", "javascript"}),
    ("Security Sentinel", SecuritySentinel, None),  # Universal
    ("Performance Oracle", PerformanceOracle, None),  # Universal
    ("Data Integrity Guardian", DataIntegrityGuardian, None),  # Universal
    ("Architecture Strategist", ArchitectureStrategist, None),  # Universal
    ("Pattern Recognition Specialist", PatternRecognitionSpecialist, None),  # Universal
    ("Code Simplicity Reviewer", CodeSimplicityReviewer, None),  # Universal
    ("Agent Native Reviewer", AgentNativeReviewer, None),  # Universal
]


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


def _gather_review_context(pr_url_or_id: str, project: bool = False) -> tuple[str, str | None]:
    """Gather code diff and summary for review."""
    worktree_path = None
    code_diff = None

    try:
        if project:
            # Full project review - gather all source files
            logger.info("Gathering project files...")
            context_service = ProjectContext()

            audit_task = (
                "Perform a comprehensive architectural, security, and code quality audit "
                "of the entire project. Prioritize core logic, configuration, and entry points."
            )
            code_diff = context_service.gather_smart_context(task=audit_task)
            if not code_diff:
                logger.error("No source files found to review!")
                return None, None
            logger.success(f"Gathered {len(code_diff):,} characters of project code")
        elif pr_url_or_id == "latest":
            # Default to checking current staged/unstaged changes or HEAD
            logger.info("Fetching local changes...")
            code_diff = GitService.get_diff("HEAD")
            summary = GitService.get_file_status_summary("HEAD")

            if not code_diff:
                logger.warning("No changes found in HEAD. Checking staged changes...")
                code_diff = GitService.get_diff("--staged")
                summary = GitService.get_file_status_summary("--staged")

            if summary and code_diff:
                code_diff = (
                    f"FILE STATUS SUMMARY (Renames Detected):\n{summary}\n\nGIT DIFF:\n{code_diff}"
                )
        else:
            # Fetch PR diff
            logger.info(f"Fetching diff for {pr_url_or_id}...")
            code_diff = GitService.get_pr_diff(pr_url_or_id)

            # Create isolated worktree for PR
            try:
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
                    "[yellow]Warning: Could not create worktree "
                    f"(proceeding with diff only): {e}[/yellow]"
                )

        if not code_diff:
            logger.error("No diff found to review!")
            return None, None

    except Exception as e:
        logger.error("Error fetching content", str(e))
        console.print("[yellow]Falling back to placeholder diff for demonstration...[/yellow]")
        code_diff = "# Placeholder diff (Git fetch failed)\n# Ensure git and gh CLI are installed"

    return code_diff, worktree_path


def _execute_review_agents(code_diff: str) -> list[dict]:
    """Filter and run applicable review agents."""
    # Detect languages in the code
    detected_langs = detect_languages(code_diff)
    if detected_langs:
        console.print(f"[cyan]Detected languages:[/cyan] {', '.join(sorted(detected_langs))}")
    else:
        console.print(
            "[yellow]No specific languages detected, running universal reviewers[/yellow]"
        )

    # Filter reviewers based on detected languages
    review_agents = []
    skipped_reviewers = []
    for name, cls, applicable_langs in REVIEWER_CONFIG:
        if applicable_langs is None or (applicable_langs & detected_langs):
            review_agents.append((name, cls))
        else:
            skipped_reviewers.append(name)

    if skipped_reviewers:
        console.print(
            f"[dim]Skipping {len(skipped_reviewers)} reviewers "
            "(not applicable for detected languages)[/dim]"
        )

    console.print(f"[green]Running {len(review_agents)} applicable reviewers...[/green]\n")

    findings = []

    def run_single_agent(name, agent_cls, diff):
        try:
            predictor = KBPredict(
                agent_cls,
                kb_tags=["code-review", name.lower().replace(" ", "-")],
            )
            return name, predictor(code_diff=diff)
        except Exception as e:
            return name, f"Error: {e}"

    with Progress() as progress:
        task = progress.add_task("[cyan]Running agents...", total=len(review_agents))

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
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

                    # Process and format report
                    formatted_review = _process_agent_result(name, result)
                    findings.append(formatted_review)

                except Exception as e:
                    findings.append({"agent": agent_name, "review": f"Execution failed: {e}"})

    return findings


def _extract_report_data(result) -> tuple[Optional[dict], Optional[Any]]:
    """Extract report data and report object from agent result."""
    if hasattr(result, "model_dump"):
        return result.model_dump(), result
    if isinstance(result, dict):
        return result, None

    # Scan common output fields for the report model
    fields = [
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
    ]
    for field_name in fields:
        if hasattr(result, field_name):
            val = getattr(result, field_name)
            if hasattr(val, "model_dump"):
                return val.model_dump(), val
            if isinstance(val, dict):
                return val, None
    return None, None


def _render_findings(findings: list) -> list[str]:
    """Render findings list into markdown parts."""
    parts = ["## Detailed Findings\n"]
    for f in findings:
        title = f.get("title", "Untitled Finding")
        severity = f.get("severity", "Medium")
        parts.append(f"### {title} ({severity})\n")
        if "description" in f:
            parts.append(f"{f['description']}\n")
        for k, v in f.items():
            if k not in ["title", "description", "severity"]:
                label = k.replace("_", " ").title()
                parts.append(f"- **{label}**: {v}")
        parts.append("")
    return parts


def _render_extra_fields(data: dict, captured_keys: set) -> list[str]:
    """Render remaining fields into markdown parts."""
    parts = []
    for key, value in data.items():
        if key in captured_keys:
            continue
        title = key.replace("_", " ").title()
        if isinstance(value, (dict, list)):
            import json

            try:
                json_str = json.dumps(value, indent=2)
                parts.append(f"## {title}\n\n```json\n{json_str}\n```\n")
            except Exception:
                parts.append(f"## {title}\n\n{str(value)}\n")
        else:
            parts.append(f"## {title}\n\n{value}\n")
    return parts


def _render_report_markdown(data: dict) -> str:
    """Render a report dictionary into a markdown string."""
    parts = []

    # Standard sections
    if "summary" in data:
        parts.append(f"# Summary\n\n{data['summary']}\n")
    elif "executive_summary" in data:
        parts.append(f"# Summary\n\n{data['executive_summary']}\n")

    if "analysis" in data:
        parts.append(f"## Analysis\n\n{data['analysis']}\n")

    if "findings" in data and isinstance(data["findings"], list) and data["findings"]:
        parts.extend(_render_findings(data["findings"]))

    # Any other keys
    captured_keys = {"summary", "executive_summary", "analysis", "findings", "action_required"}
    parts.extend(_render_extra_fields(data, captured_keys))

    return "\n".join(parts)


def _process_agent_result(name: str, result) -> dict:
    """Extract and format report from agent result."""
    report_data, report_obj = _extract_report_data(result)

    if report_data:
        review_text = _render_report_markdown(report_data)
        action_required_val = report_data.get("action_required")
        if action_required_val is None and report_obj:
            action_required_val = getattr(report_obj, "action_required", None)
    else:
        review_text = str(result)
        action_required_val = None

    finding_data = {"agent": name, "review": review_text}
    if action_required_val is not None:
        finding_data["action_required"] = action_required_val
    return finding_data


def _map_agent_to_todo(agent_name: str) -> tuple[str, str]:
    """Map agent name to category and priority."""
    mapping = {
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
    return mapping.get(agent_name, ("code-review", "p2"))


def _display_todo_summary(created_todos: list[dict], counts: dict[str, int]) -> None:
    """Display a table and summary of created todos."""
    if not created_todos:
        console.print("[green]✓ Reviews completed - no issues requiring action[/green]")
        return

    table = Table(title="📋 Created Todo Files")
    table.add_column("File", style="cyan")
    table.add_column("Agent", style="white")
    table.add_column("Priority", style="bold")

    priority_styles = {
        "p1": "[red]🔴 P1 CRITICAL[/red]",
        "p2": "[yellow]🟡 P2 IMPORTANT[/yellow]",
        "p3": "[blue]🔵 P3 NICE-TO-HAVE[/blue]",
    }

    for todo in created_todos:
        style = priority_styles.get(todo["severity"], todo["severity"])
        table.add_row(os.path.basename(todo["path"]), todo["agent"], style)

    console.print(table)
    console.print("\n[bold]Findings Summary:[/bold]")
    console.print(f"  Total Findings: {len(created_todos)}")

    if counts["p1"]:
        console.print(f"  [red]🔴 CRITICAL (P1): {counts['p1']} - BLOCKS MERGE[/red]")
    if counts["p2"]:
        console.print(f"  [yellow]🟡 IMPORTANT (P2): {counts['p2']} - Should Fix[/yellow]")
    if counts["p3"]:
        console.print(f"  [blue]🔵 NICE-TO-HAVE (P3): {counts['p3']} - Enhancements[/blue]")

    console.print("\n[bold]Next Steps:[/bold]")
    console.print("1. Triage findings: [cyan]compounding triage[/cyan]")
    console.print("2. Work on approved items: [cyan]compounding work p1[/cyan]")


def _create_review_todos(findings: list[dict]) -> None:
    """Create pending todo files for findings."""
    console.rule("Creating Todo Files")
    todos_dir = "todos"
    os.makedirs(todos_dir, exist_ok=True)

    created_todos = []
    counts = {"p1": 0, "p2": 0, "p3": 0}

    for finding in findings:
        agent_name = finding.get("agent", "Unknown")
        review_text = finding.get("review", "")

        if not review_text or review_text.startswith(("Error:", "Execution failed:")):
            continue
        if finding.get("action_required") is False:
            continue

        category, severity = _map_agent_to_todo(agent_name)
        finding_data = {
            "agent": agent_name,
            "review": review_text,
            "severity": severity,
            "category": category,
            "title": f"{agent_name} Finding",
            "effort": "Medium",
        }

        try:
            todo_path = create_finding_todo(finding_data, todos_dir=todos_dir)
            created_todos.append({"path": todo_path, "agent": agent_name, "severity": severity})
            counts[severity] = counts.get(severity, 0) + 1
            console.print(f"  [green]✓[/green] Created: [cyan]{os.path.basename(todo_path)}[/cyan]")
        except Exception as e:
            console.print(f"  [red]✗ Failed to create todo for {agent_name}: {e}[/red]")

    _display_todo_summary(created_todos, counts)


def run_review(pr_url_or_id: str, project: bool = False):
    """
    Perform exhaustive multi-agent code review.
    """
    if project:
        logger.info("Starting Full Project Review")
    else:
        logger.info(f"Starting Code Review: {pr_url_or_id}")

    # 1. Gather Context
    code_diff, worktree_path = _gather_review_context(pr_url_or_id, project)
    if not code_diff:
        return

    # 2. Run Agents
    console.rule("Running Review Agents")
    findings = _execute_review_agents(code_diff)

    # 3. Display Results
    console.rule("Review Complete")
    console.print("\n[bold green]All review agents completed![/bold green]\n")
    for finding in findings:
        console.print(f"\n[bold cyan]## {finding['agent']}[/bold cyan]")
        console.print(Markdown(finding["review"]))

    # 4. Create Todos
    _create_review_todos(findings)

    # 5. Codify Learnings
    if findings:
        console.rule("Knowledge Base Update")
        from utils.knowledge import codify_review_findings

        try:
            codify_review_findings(findings, len(findings), silent=True)
            console.print(
                f"[green]✓ Patterns from {len(findings)} reviews saved to .knowledge/[/green]"
            )
        except Exception as e:
            console.print(f"[yellow]⚠ Could not codify review learnings: {e}[/yellow]")

    # 6. Cleanup
    if worktree_path and os.path.exists(worktree_path):
        console.print(f"\n[yellow]Cleaning up worktree {worktree_path}...[/yellow]")
        try:
            subprocess.run(
                ["git", "worktree", "remove", "--force", worktree_path],
                check=True,
                capture_output=True,
            )
            console.print("[green]✓ Worktree removed[/green]")
        except Exception as e:
            console.print(f"[red]Failed to remove worktree: {e}[/red]")

    console.print("\n[bold green]✓ Review complete[/bold green]")
