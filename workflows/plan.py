import os
import re

from rich.console import Console

from agents.research.best_practices_researcher import BestPracticesResearcherModule
from agents.research.framework_docs_researcher import FrameworkDocsResearcherModule
from agents.research.repo_research_analyst import RepoResearchAnalystModule
from agents.workflow.plan_generator import PlanGenerator
from agents.workflow.spec_flow_analyzer import SpecFlowAnalyzer
from config import settings
from utils.knowledge import KBPredict, KnowledgeBase

console = Console()


def _get_safe_name(description: str) -> str:
    """Generate a safe filename from description."""
    safe_name = description.lower()
    safe_name = re.sub(r"[^\w\s-]", "", safe_name)
    safe_name = re.sub(r"[\s_]+", "-", safe_name)
    safe_name = re.sub(r"-+", "-", safe_name).strip("-")
    return safe_name[:50]


def _save_stage_output(plans_dir: str, safe_name: str, stage: str, content: str):
    """Save intermediate stage output to file."""
    stage_dir = os.path.join(plans_dir, safe_name)
    os.makedirs(stage_dir, exist_ok=True)
    filepath = os.path.join(stage_dir, f"{stage}.md")
    with open(filepath, "w") as f:
        f.write(content)
    console.print(f"[dim]  → Saved {stage}.md[/dim]")


def _handle_github_issue(feature_description: str) -> tuple[str, dict]:
    """Handle fetching details if description is a GitHub issue."""
    from utils.git.service import GitService

    issue_details = {}
    target_description = feature_description
    is_issue = False

    if feature_description.isdigit() or feature_description.startswith("#"):
        is_issue = True
    else:
        from urllib.parse import urlparse

        try:
            parsed = urlparse(feature_description)
            # Check for valid GitHub issue URL structure
            is_github = parsed.netloc in ["github.com", "www.github.com"]
            has_issue_path = "/issues/" in parsed.path
            if parsed.scheme in ["http", "https"] and is_github and has_issue_path:
                is_issue = True
        except Exception as exc:
            console.print(
                f"[dim]  → Unable to parse GitHub issue from description: {exc}. "
                "Treating as non-issue description.[/dim]"
            )

    if is_issue:
        with console.status(f"Fetching GitHub issue {feature_description}..."):
            issue_id = feature_description.lstrip("#")
            # If it's a URL, the git service should handle extraction or we do it here
            if "/" in issue_id:
                issue_id = issue_id.rstrip("/").split("/")[-1]

            issue_details = GitService.get_issue_details(issue_id)
            if issue_details:
                title = issue_details.get("title", "")
                body = issue_details.get("body", "")
                target_description = f"Issue #{issue_details.get('number')}: {title}\n\n{body}"
                if title:
                    console.print(f"[green]✓ Fetched issue: {title}[/green]")
            else:
                msg = f"⚠ Could not fetch issue {feature_description}. Treating as raw description."
                console.print(f"[yellow]{msg}[/yellow]")

    return target_description, issue_details


def _handle_todo_file(feature_description: str, target_description: str) -> str:
    """Read todo file content if applicable."""
    is_todo_file = feature_description.endswith(".md") and (
        "todo" in feature_description.lower()
        or feature_description.startswith("todos/")
        or any(p in feature_description for p in ["-p1-", "-p2-", "-p3-"])
    )
    if is_todo_file:
        todo_path = feature_description
        if not os.path.isabs(todo_path):
            if os.path.exists(todo_path):
                pass
            elif os.path.exists(os.path.join("todos", todo_path)):
                todo_path = os.path.join("todos", todo_path)

        if os.path.exists(todo_path):
            try:
                with open(todo_path, "r") as f:
                    todo_content = f.read()
                console.print(f"[green]✓ Read todo file: {todo_path}[/green]")
                return (
                    f"CODE REVIEW FINDING (from {feature_description}):\n\n"
                    f"{todo_content}\n\n"
                    "TASK: Create an implementation plan to address the finding above. "
                    "Focus on the specific code changes needed."
                )
            except Exception as e:
                console.print(f"[yellow]⚠ Could not read todo file: {e}[/yellow]")

    return target_description


def run_plan(feature_description: str):
    """Orchestrate the planning process."""
    # 0. Handle Inputs
    target_description, issue_details = _handle_github_issue(feature_description)

    # 0b. Handle Todo Files if not already handled by issue logic
    if not issue_details:
        target_description = _handle_todo_file(feature_description, target_description)

    plans_dir = "plans"
    os.makedirs(plans_dir, exist_ok=True)

    # Use title for file naming if it's an issue
    naming_source = (
        issue_details.get("title", feature_description) if issue_details else feature_description
    )
    safe_name = _get_safe_name(naming_source)

    plan_title = feature_description if not issue_details else issue_details.get("title")
    console.print(f"[bold]Planning Feature:[/bold] {plan_title}\n")

    # 1. Research Phase
    console.rule("Phase 1: Research")
    kb = KnowledgeBase()

    with console.status("Scanning project structure..."):
        semantic_results = kb.search_codebase(
            target_description, limit=settings.search_limit_codebase
        )
        if semantic_results:
            console.print(f"[dim]Found {len(semantic_results)} semantic code matches[/dim]")

    with console.status("Running Research Agents..."):
        repo_research = KBPredict(
            RepoResearchAnalystModule,
            kb_tags=["planning", "repo-research"],
        )(feature_description=target_description)
        console.print("[green]✓ Repo Research Complete[/green]")
        repo_md = repo_research.research_report.format_markdown()
        _save_stage_output(plans_dir, safe_name, "1-repo-research", repo_md)

        best_practices = KBPredict(
            BestPracticesResearcherModule,
            kb_tags=["planning", "best-practices"],
        )(topic=target_description, repo_research=repo_md)
        console.print("[green]✓ Best Practices Research Complete[/green]")
        bp_md = best_practices.research_report.format_markdown()
        _save_stage_output(plans_dir, safe_name, "2-best-practices", bp_md)

        # Framework research now sees both local repo context and general best practices
        framework_docs = KBPredict(
            FrameworkDocsResearcherModule,
            kb_tags=["planning", "framework-docs"],
        )(
            framework_or_library=target_description,
            previous_research=(
                "--- START REPOSITORY CONTEXT ---\n"
                f"{repo_md}\n"
                "--- END REPOSITORY CONTEXT ---\n\n"
                "--- START BEST PRACTICES ---\n"
                f"{bp_md}\n"
                "--- END BEST PRACTICES ---"
            ),
        )
        console.print("[green]✓ Framework Docs Research Complete[/green]")
        fw_md = framework_docs.documentation_report.format_markdown()
        _save_stage_output(plans_dir, safe_name, "3-framework-docs", fw_md)

    research_summary = f"""
## Repo Research
{repo_md}

## Best Practices
{bp_md}

## Framework Docs
{fw_md}
    """
    _save_stage_output(plans_dir, safe_name, "4-research-summary", research_summary)

    # 2. SpecFlow Analysis
    console.rule("Phase 2: SpecFlow Analysis")
    with console.status("Analyzing User Flows..."):
        spec_flow = KBPredict(
            SpecFlowAnalyzer,
            kb_tags=["planning", "spec-flow"],
        )(feature_description=target_description, research_findings=research_summary)
    console.print("[green]✓ SpecFlow Analysis Complete[/green]")
    _save_stage_output(plans_dir, safe_name, "5-specflow-analysis", spec_flow.flow_analysis)

    # 3. Plan Generation
    console.rule("Phase 3: Plan Generation")
    with console.status("Generating Plan..."):
        planner = KBPredict(
            PlanGenerator,
            kb_tags=["planning", "architecture"],
            kb_query=target_description,
        )
        plan_gen = planner(
            feature_description=target_description,
            research_summary=research_summary,
            spec_flow_analysis=spec_flow.flow_analysis,
        )

    plan_content = plan_gen.plan_report.format_markdown()

    # Save final plan
    final_path = os.path.join(plans_dir, f"{safe_name}.md")
    with open(final_path, "w") as f:
        f.write(plan_content)
    _save_stage_output(plans_dir, safe_name, "6-final-plan", plan_content)

    console.print(f"\n[bold green]Plan created at: {final_path}[/bold green]")
    console.print(f"[dim]Stage outputs saved to: {plans_dir}/{safe_name}/[/dim]")
    console.print("\n[bold]Next Steps:[/bold]")
    console.print(f"1. Review plan: [cyan]cat {final_path}[/cyan]")
    console.print(f"2. Execute plan: [cyan]python cli.py work {final_path}[/cyan]")
