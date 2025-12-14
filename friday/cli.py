"""Friday CLI - Main conversational interface with compounding support"""

import os
import signal

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import WordCompleter

from friday.theme import FRIDAY_THEME, get_prompt_style
from friday.tools import ToolExecutor
from friday.context import ConversationContext
from friday.agent import FridayAgent


class FridayCLI:
    """Main Friday CLI application"""

        self.workflows = {}  # Store compound workflows: {workflow_name: [commands]}
        self.console = Console(theme=FRIDAY_THEME, force_terminal=True)
        self.context = ConversationContext()
        self.tools = ToolExecutor(self.console)
        self.agent = FridayAgent(self.console, self.tools, self.context)
        self.running = True
        
        history_dir = os.path.expanduser("~/.friday")
        os.makedirs(history_dir, exist_ok=True)
        history_file = os.path.join(history_dir, "history")
        
        command_completer = WordCompleter([
            '/help', '/clear', '/context', '/history', '/compact',
            '/exit', '/quit', '/model', '/diff', '/status', '/files',
            '/compound', '/compound init', '/compound add', '/compound list',
            '/compound run', '/compound remove', '/compound clear'
        ], ignore_case=True)
        
        self.session = PromptSession(
            history=FileHistory(history_file),
            auto_suggest=AutoSuggestFromHistory(),
            style=get_prompt_style(),
            multiline=False,
            key_bindings=self._create_key_bindings(),
            completer=command_completer,
            complete_while_typing=False,
        )
        
        signal.signal(signal.SIGINT, self._handle_interrupt)

    def _create_key_bindings(self) -> KeyBindings:
        """Create custom key bindings"""
        kb = KeyBindings()
        
        @kb.add('c-c')
        def _(event):
            """Handle Ctrl+C"""
            event.app.exit(result=None)
        
        @kb.add('c-d')
        def _(event):
            """Handle Ctrl+D to exit"""
            self.running = False
            event.app.exit(result='/exit')
        
        return kb

    def _handle_interrupt(self, signum, frame):
        """Handle interrupt signal gracefully"""
        self.console.print("\n[dim]Use /exit or Ctrl+D to quit[/dim]")

    def _print_banner(self):
        """Print the welcome banner"""
        banner = """
[bold blue]╭─────────────────────────────────────────────────────────────╮[/]
[bold blue]│[/]  [bold white]Friday[/] [dim]v0.1.0[/]                                             [bold blue]│[/]
[bold blue]│[/]  [cyan]AI-Powered Coding Assistant[/]                               [bold blue]│[/]
[bold blue]│[/]                                                             [bold blue]│[/]
[bold blue]│[/]  [dim]Type your request or use commands:[/]                        [bold blue]│[/]
[bold blue]│[/]    [green]/help[/]    [dim]Show available commands[/]                       [bold blue]│[/]
[bold blue]│[/]    [green]/clear[/]   [dim]Clear conversation[/]                            [bold blue]│[/]
[bold blue]│[/]    [green]/exit[/]    [dim]Exit Friday[/]                                   [bold blue]│[/]
[bold blue]╰─────────────────────────────────────────────────────────────╯[/]
"""
        self.console.print(banner)
        
        cwd = os.getcwd()
        self.console.print(f"[dim]Working directory:[/] [cyan]{cwd}[/]")
        self.console.print()

    def _print_help(self):
        """Print help information"""
        help_text = """
[bold]Commands:[/]
  [green]/help[/]              Show this help message
  [green]/clear[/]             Clear conversation history
  [green]/context[/]           Show current context (files, git status)
  [green]/history[/]           Show conversation history
  [green]/compact[/]           Compact/summarize conversation history
  [green]/model[/]             Show/change LLM model
  [green]/diff[/]              Show git diff
  [green]/status[/]            Show git status
  [green]/files[/] [pattern]    List files matching pattern
  [green]/exit[/], [green]/quit[/]       Exit Friday

[bold]Capabilities:[/]
  [cyan]•[/] Read and edit files with syntax highlighting
  [cyan]•[/] Search codebase (grep, glob patterns)
  [cyan]•[/] Execute shell commands safely
  [cyan]•[/] Git operations (status, diff, log, commit)
  [cyan]•[/] Create and manage project todos
  [cyan]•[/] Generate feature plans and code reviews
  [cyan]•[/] Explain and refactor code

[bold]Examples:[/]
  [dim]›[/] "Read the main.py file and explain what it does"
  [dim]›[/] "Find all TODO comments in the codebase"
  [dim]›[/] "Add error handling to the process_data function"
  [dim]›[/] "What changed in the last 5 commits?"
  [dim]›[/] "Create a unit test for the User class"

[bold]Tips:[/]
  [dim]•[/] Be specific about file paths and function names
  [dim]•[/] Ask follow-up questions for clarification
  [dim]•[/] Use Ctrl+C to cancel, Ctrl+D to exit
"""
        self.console.print(Panel(help_text, title="[bold]Friday Help[/]", border_style="blue"))

    def _print_context(self):
        """Print current context information"""
        import subprocess
        
        table = Table(title="Current Context", border_style="blue")
        table.add_column("Item", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Working Directory", os.getcwd())
        
        try:
            branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=5
            ).stdout.strip()
            table.add_row("Git Branch", branch)
        except Exception:
            table.add_row("Git Branch", "[dim]Not a git repo[/dim]")
        
        try:
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, timeout=5
            ).stdout
            changed = len([line for line in status.strip().split('\n') if line])
            table.add_row("Changed Files", str(changed))
        except Exception:
            pass
        
        table.add_row("Conversation Turns", str(len(self.context.messages)))
        table.add_row("Files in Context", str(len(self.context.files_mentioned)))
        
        provider = os.getenv("DSPY_LM_PROVIDER", "openai")
        model = os.getenv("DSPY_LM_MODEL", "gpt-4o")
        table.add_row("LLM Provider", f"{provider}/{model}")
        
        self.console.print(table)

    def _print_history(self):
        """Print conversation history"""
        if not self.context.messages:
            self.console.print("[dim]No conversation history yet[/dim]")
            return
        
        for i, msg in enumerate(self.context.messages[-10:], 1):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:200]
            
            if role == "user":
                self.console.print(f"[bold cyan]You:[/] {content}")
            else:
                self.console.print(f"[bold green]Friday:[/] {content}...")
            self.console.print()

    def _handle_command(self, command: str) -> bool:
        """Handle slash commands. Returns True if should continue, False to exit."""
        parts = command.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd in ["/exit", "/quit", "/q"]:
            self.console.print("\n[bold blue]Goodbye! Happy coding![/]")
            return False
        elif cmd == "/help":
            self._print_help()
        elif cmd == "/clear":
            self.context.clear()
            self.console.print("[green]Conversation cleared[/]")
        elif cmd == "/context":
            self._print_context()
        elif cmd == "/history":
            self._print_history()
        elif cmd == "/compact":
            self.context.compact()
            self.console.print("[green]Conversation history compacted[/]")
        elif cmd == "/model":
            self._show_model_info()
        elif cmd == "/diff":
            self.tools.git_diff(args or "HEAD")
        elif cmd == "/status":
            self.tools.git_status()
        elif cmd == "/files":
        elif cmd == "/compound":
            self._handle_compound_command(args)
        elif cmd.startswith("/compound "):
            self._handle_compound_command(command)
    def _handle_compound_command(self, command: str):
        """Handle compound workflow commands"""
        parts = command.strip().split(maxsplit=2)
        if len(parts) < 2:
            self.console.print("[yellow]Usage: /compound <subcommand> [args][/]")
            self.console.print("[dim]Subcommands: init, add, list, run, remove, clear[/dim]")
            return
        
        subcommand = parts[1].lower()
        args = parts[2] if len(parts) > 2 else ""
        
        if subcommand == "init":
            self._compound_init(args)
        elif subcommand == "add":
            self._compound_add(args)
        elif subcommand == "list":
            self._compound_list(args)
        elif subcommand == "run":
            self._compound_run(args)
         elif subcommand == "remove":
             self._compound_remove(args)
             self._compound_remove(args)
    def _compound_init(self, workflow_name: str):
        """Initialize a new compound workflow"""
        if not workflow_name:
            self.console.print("[yellow]Error: Workflow name is required[/]")
            self.console.print("[dim]Usage: /compound init <workflow_name>[/dim]")
            return
        
        if workflow_name in self.workflows:
            self.console.print(f"[yellow]Error: Workflow '{workflow_name}' already exists[/]")
            return
        
        self.workflows[workflow_name] = []
        self.console.print(f"[green]Workflow '{workflow_name}' initialized[/]")

    def _compound_add(self, args: str):
        """Add a command to a compound workflow"""
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            self.console.print("[yellow]Error: Workflow name and command are required[/]")
            self.console.print("[dim]Usage: /compound add <workflow_name> <command>[/dim]")
            return
        
        workflow_name, command = parts[0], parts[1]
        
        if workflow_name not in self.workflows:
            self.console.print(f"[yellow]Error: Workflow '{workflow_name}' does not exist[/]")
            return
        
        self.workflows[workflow_name].append(command)
        self.console.print(f"[green]Command added to workflow '{workflow_name}'[/]")

    def _compound_list(self, workflow_name: str):
        """List commands in a compound workflow"""
        if not workflow_name:
            # List all workflows
            if not self.workflows:
                self.console.print("[dim]No workflows defined[/dim]")
                return
            
            self.console.print("[bold]Available Workflows:[/]")
            for name in self.workflows.keys():
                count = len(self.workflows[name])
                self.console.print(f"  [cyan]{name}[/] ({count} commands)")
            return
        
        if workflow_name not in self.workflows:
            self.console.print(f"[yellow]Error: Workflow '{workflow_name}' does not exist[/]")
            return
        
        commands = self.workflows[workflow_name]
        if not commands:
            self.console.print(f"[dim]Workflow '{workflow_name}' is empty[/dim]")
            return
        
        self.console.print(f"[bold]Workflow '{workflow_name}':[/]")
        for i, cmd in enumerate(commands, 1):
            self.console.print(f"  {i}. [white]{cmd}[/]")

    def _compound_run(self, workflow_name: str):
        """Run all commands in a compound workflow"""
        if not workflow_name:
            self.console.print("[yellow]Error: Workflow name is required[/]")
            self.console.print("[dim]Usage: /compound run <workflow_name>[/dim]")
            return
        
        if workflow_name not in self.workflows:
            self.console.print(f"[yellow]Error: Workflow '{workflow_name}' does not exist[/]")
            return
        
        commands = self.workflows[workflow_name]
        if not commands:
            self.console.print(f"[dim]Workflow '{workflow_name}' is empty[/dim]")
            return
        
        self.console.print(f"[bold]Running workflow '{workflow_name}'...[/]")
        
        for i, cmd in enumerate(commands, 1):
            self.console.print(f"[dim]Executing command {i}/{len(commands)}:[/] [white]{cmd}[/]")
            try:
                # Execute the command through the agent
                self.agent.process_message(cmd)
            except Exception as e:
                self.console.print(f"[red]Error executing command {i}: {e}[/]")
                break
        
        self.console.print(f"[green]Workflow '{workflow_name}' completed[/]")

    def _compound_remove(self, args: str):
        """Remove a command from a compound workflow"""
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            self.console.print("[yellow]Error: Workflow name and command index are required[/]")
            self.console.print("[dim]Usage: /compound remove <workflow_name> <index>[/dim]")
            return
        
        workflow_name, index_str = parts[0], parts[1]
        
        try:
            index = int(index_str) - 1  # Convert to 0-based index
        except ValueError:
            self.console.print("[yellow]Error: Index must be a number[/]")
            return
        
        if workflow_name not in self.workflows:
            self.console.print(f"[yellow]Error: Workflow '{workflow_name}' does not exist[/]")
            return
        
        commands = self.workflows[workflow_name]
        if index < 0 or index >= len(commands):
            self.console.print(f"[yellow]Error: Invalid command index[/]")
            return
        
        removed_cmd = commands.pop(index)
        self.console.print(f"[green]Removed command from workflow '{workflow_name}': {removed_cmd}[/]")

    def _compound_clear(self, workflow_name: str):
        """Clear all commands from a compound workflow"""
        if not workflow_name:
            self.console.print("[yellow]Error: Workflow name is required[/]")
            self.console.print("[dim]Usage: /compound clear <workflow_name>[/dim]")
            return
        
        if workflow_name not in self.workflows:
            self.console.print(f"[yellow]Error: Workflow '{workflow_name}' does not exist[/]")
            return
        
        self.workflows[workflow_name] = []
        self.console.print(f"[green]Workflow '{workflow_name}' cleared[/]")
         elif subcommand == "clear":
             self._compound_clear(args)
        else:
            self.console.print(f"[yellow]Unknown compound subcommand: {subcommand}[/]")
            self.console.print("[dim]Available: init, add, list, run, remove, clear[/dim]")
        else:
            self.console.print(f"[yellow]Unknown command: {command}[/]")
            self.console.print("[dim]Type /help for available commands[/dim]")
        
        return True

    def _show_model_info(self):
        """Show current LLM model information"""
        provider = os.getenv("DSPY_LM_PROVIDER", "openai")
        model = os.getenv("DSPY_LM_MODEL", "gpt-4o")
        
        self.console.print("[bold]Current Model:[/]")
        self.console.print(f"  Provider: [cyan]{provider}[/]")
        self.console.print(f"  Model: [cyan]{model}[/]")
        self.console.print()
        self.console.print("[dim]To change, set environment variables:[/]")
        self.console.print("[dim]  DSPY_LM_PROVIDER=openai|anthropic|openrouter[/]")
        self.console.print("[dim]  DSPY_LM_MODEL=gpt-4o|claude-3-5-sonnet-20241022|etc[/]")

    def _get_prompt(self) -> str:
        """Get the input prompt with current directory"""
        cwd = os.path.basename(os.getcwd())
        return f"[{cwd}] › "

    def run(self):
        """Main run loop"""
        self._print_banner()
        
        while self.running:
            try:
                prompt_text = self._get_prompt()
                user_input = self.session.prompt(
                    prompt_text,
                    rprompt="",
                )
                
                if user_input is None:
                    continue
                
                user_input = user_input.strip()
                
                if not user_input:
                    continue
                
                if user_input.startswith("/"):
                    if not self._handle_command(user_input):
                        break
                    continue
                
                self.agent.process_message(user_input)
                
            except KeyboardInterrupt:
                self.console.print("\n[dim]Use /exit to quit[/dim]")
                continue
            except EOFError:
                self.console.print("\n[bold blue]Goodbye![/]")
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/]")
                continue

        self.context.save()
