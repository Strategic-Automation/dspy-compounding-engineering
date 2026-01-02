import os
import re

from rich.console import Console

from agents.research.best_practices_researcher import BestPracticesResearcherModule
from agents.research.framework_docs_researcher import FrameworkDocsResearcherModule
from agents.research.repo_research_analyst import RepoResearchAnalystModule
from agents.workflow.plan_generator import PlanGenerator
from agents.workflow.spec_flow_analyzer import SpecFlowAnalyzer
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


def run_plan(feature_description: str):
    """Orchestrate the planning process."""
    plans_dir = "plans"
    os.makedirs(plans_dir, exist_ok=True)

    safe_name = _get_safe_name(feature_description)

    console.print(f"[bold]Planning Feature:[/bold] {feature_description}\n")

    # 1. Research Phase
    console.rule("Phase 1: Research")
    kb = KnowledgeBase()

    with console.status("Scanning project structure..."):
        semantic_results = kb.search_codebase(feature_description, limit=5)
        if semantic_results:
            console.print(f"[dim]Found {len(semantic_results)} semantic code matches[/dim]")

    with console.status("Running Research Agents..."):
        repo_research = KBPredict(
            RepoResearchAnalystModule,
            kb_tags=["planning", "repo-research"],
        )(feature_description=feature_description)
        console.print("[green]✓ Repo Research Complete[/green]")
        repo_md = repo_research.research_report.format_markdown()
        _save_stage_output(plans_dir, safe_name, "1-repo-research", repo_md)

        best_practices = KBPredict(
            BestPracticesResearcherModule,
            kb_tags=["planning", "best-practices"],
        )(topic=feature_description, repo_research=repo_md)
        console.print("[green]✓ Best Practices Research Complete[/green]")
        bp_md = best_practices.research_report.format_markdown()
        _save_stage_output(plans_dir, safe_name, "2-best-practices", bp_md)

        # Framework research now sees both local repo context and general best practices
        # We use explicit delimiters to prevent content injection/confusion
        framework_docs = KBPredict(
            FrameworkDocsResearcherModule,
            kb_tags=["planning", "framework-docs"],
        )(
            framework_or_library=feature_description,
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
        )(feature_description=feature_description, research_findings=research_summary)
    console.print("[green]✓ SpecFlow Analysis Complete[/green]")
    _save_stage_output(plans_dir, safe_name, "5-specflow-analysis", spec_flow.flow_analysis)

    # 3. Plan Generation
    console.rule("Phase 3: Plan Generation")
    with console.status("Generating Plan..."):
        planner = KBPredict(
            PlanGenerator,
            kb_tags=["planning", "architecture"],
            kb_query=feature_description,
        )
        plan_gen = planner(
            feature_description=feature_description,
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
