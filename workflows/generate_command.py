"""
Generate Command Workflow

This workflow generates new CLI commands for the Compounding Engineering plugin
based on natural language descriptions.
"""

import os
import re

import dspy
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.table import Table

from agents.workflow import CommandGenerator

console = Console()


def _get_existing_commands() -> str:
    """Get list of existing CLI commands from cli.py."""
    commands = []

    if os.path.exists("cli.py"):
        with open("cli.py", "r") as f:
            content = f.read()

        # Find all @app.command() decorated functions
        pattern = r'@app\.command\(\)\s*\ndef\s+(\w+)\([^)]*\):\s*"""([^"]+)"""'
        matches = re.findall(pattern, content, re.DOTALL)

        for name, docstring in matches:
            # Convert function name to command name (underscores to hyphens)
            cmd_name = name.replace("_", "-")
            # Clean up docstring
            doc = docstring.strip().split("\n")[0]
            commands.append(f"- {cmd_name}: {doc}")

    return "\n".join(commands) if commands else "No existing commands found."


def _get_existing_agents() -> str:
    """Get list of existing agents."""
    agents = []

    agent_dirs = ["agents/review", "agents/research", "agents/workflow"]

    for agent_dir in agent_dirs:
        if os.path.exists(agent_dir):
            for filename in os.listdir(agent_dir):
                if filename.endswith(".py") and not filename.startswith("__"):
                    agent_name = filename[:-3]  # Remove .py
                    # Convert to class name format
                    class_name = "".join(word.title() for word in agent_name.split("_"))
                    category = agent_dir.split("/")[-1]
                    agents.append(
                        f"- {class_name} ({category}): {agent_dir}/{filename}"
                    )

    return "\n".join(agents) if agents else "No existing agents found."


def _get_project_structure() -> str:
    """Get project structure overview."""
    structure_parts = []

    # Key directories
    dirs_to_show = ["agents", "workflows", "utils"]

    for d in dirs_to_show:
        if os.path.exists(d):
            structure_parts.append(f"{d}/")
            for item in sorted(os.listdir(d)):
                if not item.startswith("__"):
                    item_path = os.path.join(d, item)
                    if os.path.isdir(item_path):
                        structure_parts.append(f"  {item}/")
                    else:
                        structure_parts.append(f"  {item}")

    # Read cli.py structure
    if os.path.exists("cli.py"):
        structure_parts.append("\ncli.py (entry point)")

    return "\n".join(structure_parts)


def run_generate_command(description: str, dry_run: bool = False):
    """
    Generate a new CLI command from a natural language description.

    Args:
        description: Natural language description of what the command should do
        dry_run: If True, show what would be created without writing files
    """
    console.print(
        Panel.fit(
            "[bold]Compounding Engineering: Generate Command[/bold]\n"
            f"Creating command from: {description[:50]}...",
            border_style="blue",
        )
    )

    # Phase 1: Gather context
    console.rule("[bold]Phase 1: Context Gathering[/bold]")

    with console.status("[cyan]Analyzing existing codebase...[/cyan]"):
        existing_commands = _get_existing_commands()
        existing_agents = _get_existing_agents()
        project_structure = _get_project_structure()

    console.print("[green]✓ Context gathered[/green]")
    console.print(
        f"[dim]Found {len(existing_commands.splitlines())} existing commands[/dim]"
    )
    console.print(
        f"[dim]Found {len(existing_agents.splitlines())} existing agents[/dim]"
    )

    # Phase 2: Generate command specification
    console.rule("[bold]Phase 2: Command Generation[/bold]")

    with console.status("[cyan]Generating command specification...[/cyan]"):
        # Use ChainOfThought for robust typed output
        generator = dspy.ChainOfThought(CommandGenerator)
        result = generator(
            command_description=description,
            existing_commands=existing_commands,
            existing_agents=existing_agents,
            project_structure=project_structure,
        )

        # Get typed result
        command_spec_obj = result.command_spec
        if not command_spec_obj:
            console.print(
                "[red]Agent failed to return a valid command specification.[/red]"
            )
            return None

        # Convert Pydantic to dict for existing display logic
        spec = command_spec_obj.model_dump()

    console.print("[green]✓ Command specification generated[/green]")

    # Phase 3: Display specification
    console.rule("[bold]Phase 3: Review Specification[/bold]")

    # Command overview
    table = Table(title=f"Command: {spec.get('command_name', 'unknown')}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Name", spec.get("command_name", "N/A"))
    table.add_row("Description", spec.get("description", "N/A"))

    args = spec.get("arguments", [])
    if args:
        args_str = ", ".join(f"{a['name']} ({a['type']})" for a in args)
        table.add_row("Arguments", args_str)

    options = spec.get("options", [])
    if options:
        opts_str = ", ".join(f"{o['name']}" for o in options)
        table.add_row("Options", opts_str)

    console.print(table)

    # Workflow steps
    console.print("\n[bold]Workflow Steps:[/bold]")
    for i, step in enumerate(spec.get("workflow_steps", []), 1):
        console.print(f"  {i}. {step}")

    # Agents needed
    agents_needed = spec.get("agents_needed", [])
    if agents_needed:
        console.print("\n[bold]Agents:[/bold]")
        for agent in agents_needed:
            status = (
                "[green]exists[/green]"
                if agent.get("exists")
                else "[yellow]new[/yellow]"
            )
            console.print(f"  • {agent['name']} ({status}): {agent['purpose']}")

    # Files to create
    files_to_create = spec.get("files_to_create", [])
    if files_to_create:
        console.print(f"\n[bold]Files to Create ({len(files_to_create)}):[/bold]")
        for f in files_to_create:
            console.print(f"  • {f['path']}")

    # Phase 4: Preview code
    console.rule("[bold]Phase 4: Code Preview[/bold]")

    for file_info in files_to_create:
        file_path = file_info.get("path", "unknown")
        content = file_info.get("content", "")

        console.print(f"\n[bold cyan]{file_path}[/bold cyan]")

        # Determine language for syntax highlighting
        if file_path.endswith(".py"):
            lang = "python"
        elif file_path.endswith(".md"):
            lang = "markdown"
        else:
            lang = "text"

        # Show preview (first 50 lines)
        preview_lines = content.split("\n")[:50]
        preview = "\n".join(preview_lines)
        if len(content.split("\n")) > 50:
            preview += "\n\n# ... (truncated for preview)"

        syntax = Syntax(preview, lang, theme="monokai", line_numbers=True)
        console.print(syntax)

    # CLI registration code
    cli_code = spec.get("cli_registration", "")
    if cli_code:
        console.print("\n[bold cyan]CLI Registration (add to cli.py):[/bold cyan]")
        syntax = Syntax(cli_code, "python", theme="monokai", line_numbers=True)
        console.print(syntax)

    # Phase 5: Write files
    if dry_run:
        console.print("\n[yellow]DRY RUN - No files written[/yellow]")
        return spec

    console.rule("[bold]Phase 5: Write Files[/bold]")

    if not Confirm.ask("Write these files?", default=True):
        console.print("[yellow]Aborted.[/yellow]")
        return spec

    written_files = []

    for file_info in files_to_create:
        file_path = file_info.get("path", "")
        content = file_info.get("content", "")

        if not file_path or not content:
            continue

        try:
            # Create directory if needed
            dir_path = os.path.dirname(file_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            # Check if file exists
            if os.path.exists(file_path):
                if not Confirm.ask(
                    f"[yellow]{file_path} exists. Overwrite?[/yellow]", default=False
                ):
                    console.print(f"  [dim]Skipped: {file_path}[/dim]")
                    continue

            with open(file_path, "w") as f:
                f.write(content)

            written_files.append(file_path)
            console.print(f"  [green]✓ Created: {file_path}[/green]")

        except Exception as e:
            console.print(f"  [red]✗ Failed {file_path}: {e}[/red]")

    # Summary
    console.rule("[bold]Summary[/bold]")

    console.print(f"\n[bold]Files Created:[/bold] {len(written_files)}")
    for f in written_files:
        console.print(f"  • {f}")

    console.print("\n[bold]Next Steps:[/bold]")
    console.print("1. Review the generated code")
    console.print("2. Add the CLI registration to cli.py:")
    console.print(
        f"   [cyan]{cli_code.split(chr(10))[0] if cli_code else 'See above'}[/cyan]"
    )
    console.print("3. Update __init__.py if new agents were created")
    console.print("4. Test the new command")

    return spec
