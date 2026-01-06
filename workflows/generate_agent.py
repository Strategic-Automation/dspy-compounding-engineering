"""
Generate Agent Workflow

This workflow generates new Review Agents for the Compounding Engineering
based on natural language descriptions.
"""

import os
from typing import Optional

import dspy
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax

from agents.workflow.agent_generator import AgentGenerator
from config import settings
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


def _validate_agent_path(file_name: str) -> Optional[str]:
    """Sanitize and validate agent file path strictly."""
    import re

    safe_file_name = os.path.basename(file_name)
    if not safe_file_name.endswith(".py"):
        safe_file_name += ".py"

    # Strict whitelisting: lowercase alphanumeric, underscores, and hyphens only
    if not re.match(r"^[a-z0-9_-]+\.py$", safe_file_name):
        console.print(
            f"[red]Error: Invalid file name '{safe_file_name}'. "
            "Only lowercase alphanumeric, underscores, and hyphens allowed.[/red]"
        )
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
            console.print(
                f"[red]Error: Path traversal detected or unauthorized location: "
                f"'{safe_file_name}'.[/red]"
            )
            return None
    except (ValueError, OSError):
        console.print(f"[red]Error: Invalid path detected for '{safe_file_name}'.[/red]")
        return None

    return real_file_path


def _clean_generated_code(code: str) -> str:
    """Clean LLM artifacts from generated code."""
    import re

    # Remove markdown code fences
    code = re.sub(r"^```python\s*\n?", "", code)
    code = re.sub(r"\n?```\s*$", "", code)

    # Remove LLM completion markers (e.g., [[ ## completed ## ]])
    code = re.sub(r"\[\[.*?\]\]", "", code)

    # Remove trailing whitespace from lines
    code = "\n".join(line.rstrip() for line in code.splitlines())

    # Ensure file ends with newline
    if not code.endswith("\n"):
        code += "\n"

    return code


def _verify_agent_code(spec_content: str) -> tuple[bool, str]:
    """Validate generated agent code. Returns (is_valid, cleaned_code)."""
    # Clean the code first
    cleaned = _clean_generated_code(spec_content)

    # Check for required elements
    if "review_report" not in cleaned or "dspy.Signature" not in cleaned:
        console.print(
            "[red]Error: Generated code missing required 'review_report' "
            "output field or 'dspy.Signature' class.[/red]"
        )
        return False, cleaned

    # Validate Python syntax
    try:
        compile(cleaned, "<generated>", "exec")
    except SyntaxError as e:
        console.print(f"[red]Error: Generated code has syntax error: {e}[/red]")
        return False, cleaned

    return True, cleaned


def _write_agent_file(file_path: str, content: str) -> bool:
    """Write agent file with confirmation."""
    if not Confirm.ask(f"Write {file_path}?", default=True):
        console.print("[yellow]Aborted.[/yellow]")
        return False

    try:
        # Create directory if needed
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        if os.path.exists(file_path):
            if not Confirm.ask(f"[yellow]{file_path} exists. Overwrite?[/yellow]", default=False):
                console.print(f"  [dim]Skipped: {file_path}[/dim]")
                return False

        # Final safety check before write
        base_dir = os.getcwd()
        target_dir = os.path.realpath(os.path.join(base_dir, "agents/review"))
        real_file_path = os.path.realpath(file_path)

        if os.path.commonpath([real_file_path, target_dir]) != target_dir:
            console.print(f"[red]Error: Unauthorized write location: {file_path}[/red]")
            return False

        # Write with restrictive permissions (0o644)
        import os as os_native

        mode = os_native.O_WRONLY | os_native.O_CREAT | os_native.O_TRUNC
        fd = os_native.open(file_path, mode, 0o644)
        with os_native.fdopen(fd, "w") as f:
            f.write(content)

        console.print(f"  [green]✓ Created: {file_path}[/green]")
        return True
    except Exception as e:
        console.print(f"  [red]✗ Failed {file_path}: {e}[/red]")
        return False


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

        # Get valid categories from shared constant
        from agents.review import VALID_CATEGORIES

        valid_categories = ", ".join(sorted(VALID_CATEGORIES))

        # Use ReAct to allow the generator to use tools
        generator = dspy.ReAct(AgentGenerator, tools=tools, max_iters=settings.generator_max_iters)
        result = generator(
            agent_description=description,
            existing_agents=existing_agents,
            valid_categories=valid_categories,
        )

        # Reconstruct Spec object from individual fields
        from agents.workflow.agent_generator import AgentFileSpec

        spec = AgentFileSpec(
            file_name=result.file_name,
            class_name=result.class_name,
            agent_name=result.agent_name,
            applicable_languages=result.applicable_languages,
            code_content=result.code_content,
        )

        if not spec.code_content:
            console.print("[red]Agent failed to return valid agent code.[/red]")
            return None

    console.print("[green]✓ Agent specification generated[/green]")

    # Phase 3: Review Specification
    console.rule("[bold]Phase 3: Review Specification[/bold]")

    console.print(f"[bold]Agent Name:[/bold] {spec.agent_name}")
    console.print(f"[bold]Class Name:[/bold] {spec.class_name}")
    console.print(f"[bold]File Name:[/bold] {spec.file_name}")
    console.print(f"[bold]Languages:[/bold] {spec.applicable_languages or 'All'}")

    # Phase 4: Code Preview & Validation
    console.rule("[bold]Phase 4: Code Preview[/bold]")

    file_path = _validate_agent_path(spec.file_name)
    if not file_path:
        return None

    is_valid, cleaned_code = _verify_agent_code(spec.code_content)
    if not is_valid:
        return None

    # Update spec with cleaned code
    spec.code_content = cleaned_code

    console.print(f"\n[bold cyan]agents/review/{os.path.basename(file_path)}[/bold cyan]")

    syntax = Syntax(cleaned_code, "python", theme="monokai", line_numbers=True)
    console.print(syntax)

    # Phase 5: Write files
    if dry_run:
        console.print("\n[yellow]DRY RUN - No files written[/yellow]")
        return spec

    console.rule("[bold]Phase 5: Write Files[/bold]")
    _write_agent_file(file_path, cleaned_code)

    # Summary
    console.rule("[bold]Summary[/bold]")

    console.print(f"\n[bold]Agent Created:[/bold] {spec.agent_name}")
    console.print(f"Location: {file_path}")

    console.print("\n[bold green]✓ Next steps:[/bold green]")
    console.print("The new agent is automatically discovered!")
    console.print(
        f"Test it by running: [cyan]compounding review latest --agent {spec.agent_name}[/cyan]"
    )
    console.print("Or run all agents: [cyan]compounding review latest[/cyan]")

    return spec
