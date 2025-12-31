"""
Generate Agent Workflow

This workflow generates new Review Agents for the Compounding Engineering
based on natural language descriptions.
"""

import os
import dspy
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax
from agents.workflow.agent_generator import AgentGenerator
from utils.agent.tools import get_research_tools

console = Console()


def _get_existing_review_agents() -> str:
    """Get list of existing review agents from agents/review/."""
    agents = []
    agent_dir = "agents/review"

    if os.path.exists(agent_dir):
        for filename in os.listdir(agent_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                agents.append(f"- {filename}")

    return "\n".join(agents) if agents else "No existing review agents found."


def run_generate_agent(description: str, dry_run: bool = False):
    """
    Generate a new review agent from a natural language description.

    Args:
        description: Description of what the review agent should check for
        dry_run: If True, show what would be created without writing files
    """
    console.print(
        Panel.fit(
            "[bold]Compounding Engineering: Generate Review Agent[/bold]\n"
            f"Creating agent for: {description[:50]}...",
            border_style="blue",
        )
    )

    # Phase 1: Gather context
    console.rule("[bold]Phase 1: Context Gathering[/bold]")

    with console.status("[cyan]Analyzing existing review agents...[/cyan]"):
        existing_agents = _get_existing_review_agents()

    console.print("[green]✓ Context gathered[/green]")
    console.print(f"[dim]Found {len(existing_agents.splitlines())} existing review agents[/dim]")

    # Phase 2: Generate agent specification
    console.rule("[bold]Phase 2: Agent Generation[/bold]")

    with console.status("[cyan]Generating agent code (with research)...[/cyan]"):
        # Use centralized research tools (web search, docs, codebase, etc.)
        tools = get_research_tools()

        # Use ReAct to allow the generator to use tools
        generator = dspy.ReAct(
            AgentGenerator, 
            tools=tools, 
            max_iters=10
        )
        result = generator(
            agent_description=description,
            existing_agents=existing_agents,
        )

        # Reconstruct Spec object from individual fields
        from agents.workflow.agent_generator import AgentFileSpec
        spec = AgentFileSpec(
            file_name=result.file_name,
            class_name=result.class_name,
            agent_name=result.agent_name,
            applicable_languages=result.applicable_languages,
            content=result.code_content
        )

        if not spec.content:
            console.print("[red]Agent failed to return valid agent code.[/red]")
            return None

    console.print("[green]✓ Agent specification generated[/green]")

    # Phase 3: Display specification
    console.rule("[bold]Phase 3: Review Specification[/bold]")

    console.print(f"[bold]Agent Name:[/bold] {spec.agent_name}")
    console.print(f"[bold]Class Name:[/bold] {spec.class_name}")
    console.print(f"[bold]File Name:[/bold] {spec.file_name}")
    console.print(f"[bold]Languages:[/bold] {spec.applicable_languages or 'All'}")

    # Phase 4: Preview code
    console.rule("[bold]Phase 4: Code Preview[/bold]")

    # Sanitize and validate file name strictly
    safe_file_name = os.path.basename(spec.file_name)
    if not safe_file_name.endswith(".py"):
        safe_file_name += ".py"
        
    # Strict whitelisting: only lowercase alphanumeric and underscores
    # This prevents directory traversal sequences and special shell characters
    import re
    if not re.match(r"^[a-z0-9_]+\.py$", safe_file_name):
        console.print(f"[red]Error: Invalid file name '{safe_file_name}'. Only lowercase alphanumeric and underscores allowed.[/red]")
        return None

    # Construct and canonicalize path
    base_dir = os.getcwd()
    target_dir = os.path.join(base_dir, "agents/review")
    file_path = os.path.join(target_dir, safe_file_name)
    
    # Fully resolve all paths to prevent symlink/traversal bypasses
    real_file_path = os.path.realpath(file_path)
    real_target_dir = os.path.realpath(target_dir)
    
    # Use commonpath to ensure real_file_path is strictly within real_target_dir
    try:
        if os.path.commonpath([real_file_path, real_target_dir]) != real_target_dir:
            console.print(f"[red]Error: Path traversal detected or unauthorized location: '{safe_file_name}'.[/red]")
            return None
    except ValueError:
        # Paths are on different drives or other OS level issues
        console.print(f"[red]Error: Cross-device or invalid path detected for '{safe_file_name}'.[/red]")
        return None
        
    # Basic content validation: ensure it's a valid DSPy signature with review_report
    if "review_report" not in spec.content or "dspy.Signature" not in spec.content:
        console.print("[red]Error: Generated code missing required 'review_report' output field or 'dspy.Signature' class.[/red]")
        return None

    console.print(f"\n[bold cyan]agents/review/{safe_file_name}[/bold cyan]")
    
    syntax = Syntax(spec.content, "python", theme="monokai", line_numbers=True)
    console.print(syntax)

    # Phase 5: Write files
    if dry_run:
        console.print("\n[yellow]DRY RUN - No files written[/yellow]")
        return spec

    console.rule("[bold]Phase 5: Write Files[/bold]")

    if not Confirm.ask(f"Write {file_path}?", default=True):
        console.print("[yellow]Aborted.[/yellow]")
        return spec

    try:
        # Create directory if needed
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        if os.path.exists(file_path):
            if not Confirm.ask(f"[yellow]{file_path} exists. Overwrite?[/yellow]", default=False):
                console.print(f"  [dim]Skipped: {file_path}[/dim]")
                return spec

        with open(file_path, "w") as f:
            f.write(spec.content)

        console.print(f"  [green]✓ Created: {file_path}[/green]")

    except Exception as e:
        console.print(f"  [red]✗ Failed {file_path}: {e}[/red]")
        return spec

    # Summary
    console.rule("[bold]Summary[/bold]")

    console.print(f"\n[bold]Agent Created:[/bold] {spec.agent_name}")
    console.print(f"Location: {file_path}")

    console.print("\n[bold green]✓ Next steps:[/bold green]")
    console.print("The new agent is automatically discovered!")
    console.print(f"Test it by running: [cyan]compounding review[/cyan]")

    return spec
