import concurrent.futures
import importlib
import inspect
import os
import pkgutil
import re
import subprocess
from typing import Any, Optional, Set, Type

import dspy
from pydantic import BaseModel
from rich.markdown import Markdown
from rich.progress import Progress
from rich.table import Table

from utils.context import ProjectContext
from utils.git import GitService
from utils.io.logger import console, logger
from utils.knowledge import KBPredict
from utils.todo import create_finding_todo


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
        r"=== ([^\s]+) \(Score:",  # ProjectContext format
    ]

    extensions = set()
    for pattern in file_patterns:
        for match in re.findall(pattern, code_content):
            if "." in match:
                # Extract extension and remove trailing non-alphanumeric (quotes, etc)
                ext = match.rsplit(".", 1)[-1].lower()
                ext = re.sub(r"[^a-z0-9]+$", "", ext)
                if ext:
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


def _validate_agent_class(
    name: str, obj: Any, module_name: str, full_module_name: str
) -> Optional[tuple[str, Type[dspy.Signature], Optional[Set[str]], str, str]]:
    """Validate and extract metadata from a potential reviewer class."""
    if not (
        inspect.isclass(obj)
        and issubclass(obj, dspy.Signature)
        and obj.__module__ == full_module_name
        and obj is not dspy.Signature
    ):
        return None

    # Extract metadata with safe fallbacks
    agent_name = getattr(obj, "__agent_name__", None)
    if not agent_name:
        agent_name = re.sub(r"(?<!^)(?=[A-Z])", " ", obj.__name__)

    applicable_langs = getattr(obj, "applicable_languages", None)
    category = getattr(obj, "__agent_category__", "code-review")
    severity = getattr(obj, "__agent_severity__", "p2")

    # Import shared constants
    from agents.review import VALID_CATEGORIES, VALID_SEVERITIES

    if category not in VALID_CATEGORIES:
        logger.warning(f"Skipping {agent_name}: Invalid category '{category}'")
        return None

    if severity not in VALID_SEVERITIES:
        logger.warning(f"Skipping {agent_name}: Invalid severity '{severity}'")
        return None

    # Ensure the agent has at least one output field to be useful
    if not obj.output_fields:
        logger.warning(f"Skipping reviewer {name} in {module_name}: No output fields defined.")
        return None

    return agent_name, obj, applicable_langs, category, severity


def discover_reviewers() -> list[tuple[str, Type[dspy.Signature], Optional[Set[str]], str, str]]:
    """
    Dynamically discover all review agents in the agents.review package.
    Expects agents to be dspy.Signature classes with:
    - __agent_name__: Human-readable name
    - __agent_category__: Category (e.g. security)
    - __agent_severity__: Priority (p1, p2, p3)
    - applicable_languages: Set of languages or None
    """
    reviewers = []
    import agents.review as review_pkg

    package_path = os.path.dirname(review_pkg.__file__)

    for _, module_name, is_pkg in pkgutil.iter_modules([package_path]):
        if is_pkg or module_name == "schema":
            continue

        full_module_name = f"agents.review.{module_name}"
        try:
            module = importlib.import_module(full_module_name)
            for name, obj in inspect.getmembers(module):
                try:
                    reviewer = _validate_agent_class(name, obj, module_name, full_module_name)
                    if reviewer:
                        reviewers.append(reviewer)
                except Exception as class_err:
                    logger.error(f"Error inspecting class {name} in {module_name}: {class_err}")
        except Exception as e:
            logger.error(f"Failed to load reviewer module {full_module_name}: {e}")

    return reviewers


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


def _gather_review_context(
    pr_url_or_id: str, project: bool = False
) -> tuple[str | None, str | None]:
    """
    Gather code diff and summary for review.

    Args:
        pr_url_or_id: PR number, URL, branch name, or 'latest'
        project: If True, review the entire project context

    Returns:
        tuple: (code_diff, worktree_path or None)
    """
    worktree_path: str | None = None
    code_diff: str | None = None

    try:
        if project:
            code_diff = _gather_project_context()
        elif pr_url_or_id == "latest":
            code_diff = _gather_local_changes()
        else:
            logger.info(f"Fetching diff for {pr_url_or_id}...", to_cli=True)
            code_diff = GitService.get_diff(pr_url_or_id)
            worktree_path = _setup_worktree(pr_url_or_id)

        if not code_diff:
            logger.error(f"No changes found to review for: {pr_url_or_id}!")
            return None, None

        return code_diff, worktree_path
    except Exception as e:
        logger.error(f"Error gathering review context: {e}")
        console.print("[yellow]Falling back to placeholder diff for demonstration...[/yellow]")
        code_diff = "# Placeholder diff (Context gathering failed)\n# Check your arguments"

    return code_diff, worktree_path


def _gather_project_context() -> str | None:
    """Helper to gather full project context."""
    logger.info("Gathering project files...", to_cli=True)
    context_service = ProjectContext()

    audit_task = (
        "Perform a comprehensive architectural, security, and code quality audit "
        "of the entire project. Prioritize core logic, configuration, and entry points."
    )
    code_diff = context_service.gather_smart_context(task=audit_task)
    if not code_diff:
        logger.error("No source files found to review!")
    else:
        logger.success(f"Gathered {len(code_diff):,} characters of project code")
    return code_diff


def _gather_local_changes() -> str | None:
    """Helper to gather local changes."""
    logger.info("Fetching local changes...", to_cli=True)
    code_diff = GitService.get_diff("HEAD")
    summary = GitService.get_file_status_summary("HEAD")

    if not code_diff:
        logger.warning("No changes found in HEAD. Checking staged changes...")
        code_diff = GitService.get_diff("--staged")
        summary = GitService.get_file_status_summary("--staged")

    if summary and code_diff:
        code_diff = f"FILE STATUS SUMMARY (Renames Detected):\n{summary}\n\nGIT DIFF:\n{code_diff}"
    return code_diff


def _setup_worktree(pr_url_or_id: str) -> str | None:
    """Helper to setup an isolated worktree for review."""
    # Determine if we should create a worktree (only for actual PRs/Branches, not local files)
    is_pr = pr_url_or_id.startswith("http") or pr_url_or_id.isdigit()
    is_remote_branch = "/" in pr_url_or_id and not os.path.exists(pr_url_or_id)
    is_file = os.path.isfile(pr_url_or_id)

    if not (is_pr or is_remote_branch) or is_file:
        return None

    try:
        # 1. Sanitize ID for safe path construction
        safe_id = "".join(c for c in pr_url_or_id if c.isalnum() or c in ("-", "_"))
        if not safe_id:
            from uuid import uuid4

            safe_id = str(uuid4())[:8]

        # 2. Resolve absolute worktree path and verify containment
        base_worktree_dir = os.path.abspath("worktrees")
        target_path = os.path.abspath(os.path.join(base_worktree_dir, f"review-{safe_id}"))

        if not target_path.startswith(base_worktree_dir):
            msg = f"Security: Malicious worktree path detected: {target_path}"
            raise ValueError(msg)

        if os.path.exists(target_path):
            console.print(f"[yellow]Worktree {target_path} already exists. Using it.[/yellow]")
            return target_path

        console.print(f"[cyan]Creating isolated worktree at {target_path}...[/cyan]")
        os.makedirs(base_worktree_dir, exist_ok=True)
        GitService.checkout_pr_worktree(pr_url_or_id, target_path)
        console.print("[green]✓ Worktree created[/green]")
        return target_path
    except Exception as e:
        console.print(
            f"[yellow]Warning: Could not create worktree (proceeding with diff only): {e}[/yellow]"
        )
        return None


def _filter_applicable_reviewers(
    review_config: list, detected_langs: set, agent_filter: Optional[list[str]]
) -> tuple[list, list]:
    """Filter reviewers based on languages and optional filter."""
    review_agents = []
    skipped_reviewers = []

    for name, cls, applicable_langs, category, severity in review_config:
        # Check if agent is in filter (case-insensitive)
        if agent_filter:
            matches_filter = False
            for f in agent_filter:
                if not f or len(f) > 50:
                    continue
                if re.search(rf"\b{re.escape(f)}\b", name, re.IGNORECASE):
                    matches_filter = True
                    break
            if not matches_filter:
                continue

        norm_langs = {lang.lower() for lang in applicable_langs} if applicable_langs else None
        if norm_langs is None or (norm_langs & detected_langs):
            review_agents.append((name, cls, category, severity))
        else:
            skipped_reviewers.append(name)

    return review_agents, skipped_reviewers


def _execute_review_agents(code_diff: str, agent_filter: Optional[list[str]] = None) -> list[dict]:
    """Filter and run applicable review agents."""
    # Detect languages in the code
    detected_langs = detect_languages(code_diff)
    if detected_langs:
        console.print(f"[cyan]Detected languages:[/cyan] {', '.join(sorted(detected_langs))}")
    else:
        console.print(
            "[yellow]No specific languages detected, running universal reviewers[/yellow]"
        )

    # Discover reviewers dynamically
    review_config = discover_reviewers()

    # Filter reviewers based on detected languages and agent_filter
    review_agents, skipped_reviewers = _filter_applicable_reviewers(
        review_config, detected_langs, agent_filter
    )

    if skipped_reviewers:
        console.print(
            f"[dim]Skipping {len(skipped_reviewers)} reviewers "
            "(not applicable for detected languages)[/dim]"
        )

    console.print(f"[green]Running {len(review_agents)} applicable reviewers...[/green]\n")

    findings = []

    def run_single_agent(name, agent_cls, diff):
        try:
            predictor = KBPredict.wrap(
                agent_cls,
                kb_tags=["code-review", "code-review-patterns", name.lower().replace(" ", "-")],
            )
            return name, predictor(code_diff=diff)
        except Exception as e:
            return name, f"Error: {e}"

    with Progress() as progress:
        task = progress.add_task("[cyan]Running agents...", total=len(review_agents))

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_agent = {
                executor.submit(run_single_agent, name, cls, code_diff): (name, category, severity)
                for name, cls, category, severity in review_agents
            }

            for future in concurrent.futures.as_completed(future_to_agent):
                agent_name, agent_cat, agent_sev = future_to_agent[future]
                progress.update(task, description=f"[cyan]Completed {agent_name}...")
                progress.advance(task)

                try:
                    name, result = future.result()
                    if isinstance(result, str) and result.startswith("Error:"):
                        findings.append(
                            {
                                "agent": name,
                                "review": result,
                                "category": agent_cat,
                                "severity": agent_sev,
                            }
                        )
                        continue

                    # Process and format report
                    formatted_review = _process_agent_result(name, result)
                    formatted_review.update({"category": agent_cat, "severity": agent_sev})
                    findings.append(formatted_review)

                except Exception as e:
                    findings.append({"agent": agent_name, "review": f"Execution failed: {e}"})

    return findings


def _extract_report_data(result: Any) -> tuple[Optional[dict[str, Any]], Optional[Any]]:
    """
    Extract report data and report object from agent result.
    Prioritizes 'review_report' as the standard output field.
    """
    # If the result itself is a model (rare but possible)
    if hasattr(result, "model_dump"):
        return result.model_dump(), result
    if isinstance(result, dict):
        return result, None

    # Standard field for all unified agents
    standard_field = "review_report"

    # Check for the standard field
    if hasattr(result, standard_field):
        val = getattr(result, standard_field)
        if hasattr(val, "model_dump"):
            return val.model_dump(), val
        if isinstance(val, dict):
            return val, None

    # Log a warning if no report field was found
    logger.warning(
        f"No standard 'review_report' field found in agent result. "
        f"Output fields: {getattr(result, '_output_fields', 'unknown')}"
    )
    return None, None


def _render_findings(findings: list[dict[str, Any]]) -> list[str]:
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


def _render_extra_fields(data: dict[str, Any], captured_keys: set[str]) -> list[str]:
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


def _process_agent_result(name: str, result: Any) -> dict[str, Any]:
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


def _map_agent_to_todo(
    agent_name: str, discovered_metadata: Optional[dict] = None
) -> tuple[str, str]:
    """Map agent name to category and priority."""
    if discovered_metadata:
        return discovered_metadata.get("category", "code-review"), discovered_metadata.get(
            "severity", "p2"
        )

    return "code-review", "p2"


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

        cat_val = finding.get("category")
        sev_val = finding.get("severity")
        category, severity = _map_agent_to_todo(
            agent_name, {"category": cat_val, "severity": sev_val}
        )
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


def run_review(
    pr_url_or_id: str, project: bool = False, agent_filter: Optional[list[str]] = None
) -> None:
    """
    Perform exhaustive multi-agent code review.
    """
    if project:
        logger.info("Starting Full Project Review", to_cli=True)
    else:
        logger.info(f"Starting Code Review: {pr_url_or_id}", to_cli=True)

    # 1. Gather Context
    code_diff, worktree_path = _gather_review_context(pr_url_or_id, project)
    if not code_diff:
        return

    # 2. Run Agents
    console.rule("Running Review Agents")
    findings = _execute_review_agents(code_diff, agent_filter=agent_filter)

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
