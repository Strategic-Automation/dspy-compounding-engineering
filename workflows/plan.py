import os

from rich.console import Console

from agents.research import (
    BestPracticesResearcher,
    FrameworkDocsResearcher,
    RepoResearchAnalyst,
)
from agents.workflow import PlanGenerator, SpecFlowAnalyzer
from utils.knowledge import KBPredict, KnowledgeBase

console = Console()


def _get_file_listing(root_dir: str = ".", max_depth: int = 3) -> str:
    """Generate a tree-like file listing of the project."""
    lines = []

    def walk_dir(path: str, prefix: str = "", depth: int = 0):
        if depth > max_depth:
            return

        try:
            entries = sorted(os.listdir(path))
        except PermissionError:
            return

        # Filter out common non-essential directories and files
        skip_patterns = {
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            "dist",
            "build",
            "*.egg-info",
            ".tox",
            ".coverage",
            "htmlcov",
        }

        entries = [
            e
            for e in entries
            if not any(e == p or (p.startswith("*") and e.endswith(p[1:])) for p in skip_patterns)
        ]

        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "└── " if is_last else "├── "
            entry_path = os.path.join(path, entry)

            if os.path.isdir(entry_path):
                lines.append(f"{prefix}{connector}{entry}/")
                extension = "    " if is_last else "│   "
                walk_dir(entry_path, prefix + extension, depth + 1)
            else:
                lines.append(f"{prefix}{connector}{entry}")

    lines.append(os.path.basename(os.path.abspath(root_dir)) + "/")
    walk_dir(root_dir)

    return "\n".join(lines[:200])  # Limit to avoid token explosion


def _get_relevant_file_contents(max_chars: int = 10000) -> str:
    """Read content from key project files."""
    key_files = [
        "README.md",
        "CONTRIBUTING.md",
        "ARCHITECTURE.md",
        "pyproject.toml",
        "package.json",
        "requirements.txt",
        "setup.py",
        "Makefile",
        "Gemfile",
        "Cargo.toml",
        "go.mod",
    ]

    content_parts = []
    total_chars = 0

    for filename in key_files:
        if os.path.exists(filename) and total_chars < max_chars:
            try:
                with open(filename, "r", encoding="utf-8", errors="ignore") as f:
                    file_content = f.read()
                    # Truncate individual files to prevent one large file dominating
                    max_per_file = min(3000, max_chars - total_chars)
                    if len(file_content) > max_per_file:
                        file_content = file_content[:max_per_file] + "\n...[truncated]..."
                    content_parts.append(f"--- {filename} ---\n{file_content}")
                    total_chars += len(file_content)
            except Exception as e:
                # Intentionally skip unreadable files, but log for debugging.
                console.log(f"[yellow]Warning:[/yellow] Failed to read {filename}: {e}")

    return "\n\n".join(content_parts) if content_parts else "No key files found."


def run_plan(feature_description: str):
    plans_dir = "plans"
    if not os.path.exists(plans_dir):
        os.makedirs(plans_dir)

    console.print(f"[bold]Planning Feature:[/bold] {feature_description}\n")

    # 1. Research
    console.rule("Phase 1: Research")

    # Gather project context
    console.print("[cyan]Scanning project structure...[/cyan]")
    file_listing = _get_file_listing()
    relevant_contents = _get_relevant_file_contents()

    # Semantic Code Search
    console.print("[cyan]Searching for relevant code context (Semantic Search)...[/cyan]")
    kb = KnowledgeBase()
    # Search for code relevant to the feature description
    semantic_results = kb.search_codebase(feature_description, limit=5)

    if semantic_results:
        console.print(f"[dim]Found {len(semantic_results)} semantic code matches[/dim]")
        semantic_context = "\n\n## Relevant Code Snippets (Semantic Search)\n"
        for res in semantic_results:
            semantic_context += (
                f"\n### {res.get('path')} (score: {res.get('score', 0):.2f})\n"
                f"```\n{res.get('content')}\n```\n"
            )
        relevant_contents += semantic_context
    else:
        console.print("[dim]No semantic code matches found (or Vector DB not available)[/dim]")

    console.print(f"[dim]Found {len(file_listing.splitlines())} files/directories[/dim]")

    with console.status("Running Research Agents..."):
        # Parallel execution in theory, sequential here for simplicity
        repo_research = KBPredict(
            RepoResearchAnalyst,
            kb_tags=["planning", "repo-research"],
        )(
            feature_description=feature_description,
            file_listings=file_listing,
            relevant_file_contents=relevant_contents,
        )
        console.print("[green]✓ Repo Research Complete[/green]")

        best_practices = KBPredict(
            BestPracticesResearcher,
            kb_tags=["planning", "best-practices"],
        )(topic=feature_description)
        console.print("[green]✓ Best Practices Research Complete[/green]")

        framework_docs = KBPredict(
            FrameworkDocsResearcher,
            kb_tags=["planning", "framework-docs"],
        )(framework_or_library=feature_description)
        console.print("[green]✓ Framework Docs Research Complete[/green]")

    research_summary = f"""
        ## Repo Research
        {repo_research.research_summary}

        ## Best Practices
        {best_practices.research_findings}

        ## Framework Docs
        {framework_docs.documentation_summary}
    """

    # 2. SpecFlow Analysis
    console.rule("Phase 2: SpecFlow Analysis")
    with console.status("Analyzing User Flows..."):
        spec_flow = KBPredict(
            SpecFlowAnalyzer,
            kb_tags=["planning", "spec-flow"],
        )(feature_description=feature_description, research_findings=research_summary)
    console.print("[green]✓ SpecFlow Analysis Complete[/green]")

    # 3. Plan Generation
    console.rule("Phase 3: Plan Generation")
    with console.status("Generating Plan..."):
        # Use KB-augmented planning for better context
        planner = KBPredict(
            # Changed from PlannerAgent to PlanGenerator to match original call structure
            PlanGenerator,
            kb_tags=["planning", "architecture"],
            kb_query=feature_description,
        )
        plan_gen = planner(
            feature_description=feature_description,
            research_summary=research_summary,
            spec_flow_analysis=spec_flow.flow_analysis,
        )

    plan_content = plan_gen.plan_content

    # Save plan
    # Generate filename from description (simplified)
    filename = feature_description.lower().replace(" ", "-")[:50] + ".md"
    file_path = os.path.join(plans_dir, filename)

    with open(file_path, "w") as f:
        f.write(plan_content)

    console.print(f"\n[bold green]Plan created at: {file_path}[/bold green]")
    console.print("\n[bold]Next Steps:[/bold]")
    console.print(f"1. Review plan: [cyan]cat {file_path}[/cyan]")
    console.print(f"2. Execute plan: [cyan]python cli.py work {file_path}[/cyan]")
