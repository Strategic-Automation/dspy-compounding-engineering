"Friday CLI - Main conversational interface with compounding support"

import os
import signal
import asyncio
import os
import signal
import asyncio
import logging
import time
from typing import Optional, List, Dict, Any
import json
from typing import Optional, List, Dict, Any
import json
import signal
import asyncio # New import

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.logging import RichHandler
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML

from friday.theme import FRIDAY_THEME, get_prompt_style, get_rich_theme, ASCII_ART
from friday.tools import ToolExecutor
from friday.context import ConversationContext
from friday.agent import FridayAgent
from friday.mcp import MCPManager # New Import

# Compounding Engineering Imports
try:
    from config import configure_dspy
    from workflows.codify import run_codify
    from workflows.generate_command import run_generate_command
    from workflows.plan import run_plan
    from workflows.review import run_review
    from workflows.triage import run_triage
    from workflows.work import run_unified_work
    from utils.knowledge_base import KnowledgeBase
except ImportError as e:
class FridayCLI:
    """Main Friday CLI application with enhanced error handling and user experience"""
    import sys
    print(f"DEBUG: Import failed in friday/cli.py: {e}", file=sys.stderr)
    def __init__(self):
        # Set up structured logging
        self._setup_logging()
        
        # Configure DSPy for compounding commands
        if configure_dspy:
            try:
                configure_dspy()
            except Exception as e:
                # Use a temporary console since self.console isn't init'd yet
                Console().print(f"[yellow]Warning: Failed to configure DSPy: {e}[/]")
                self.logger.warning(f"Failed to configure DSPy: {e}")
        
        self.workflows = {}  # Store compound workflows: {workflow_name: [commands]}
        # Load user config (~/.friday/config.json)
        # Initialize logger
        self.logger = logging.getLogger("friday.cli")
        
        # Determine theme profile from env or config
        theme_profile = os.getenv("FRIDAY_THEME_PROFILE") or (self.user_config.get("theme") if isinstance(self.user_config, dict) else None) or "dark"
        
        self.console = Console(theme=get_rich_theme(theme_profile), force_terminal=True)
        self.context = ConversationContext()
        self.tools = ToolExecutor(self.console)
        self.mcp_manager = MCPManager()
        self.agent = FridayAgent(self.console, self.tools, self.context, mcp_manager=self.mcp_manager)
        self.running = True
            try:
                configure_dspy()
            except Exception as e:
                # Use a temporary console since self.console isn't init'd yet
                Console().print(f"[yellow]Warning: Failed to configure DSPy: {e}[/]")

        self.workflows = {}  # Store compound workflows: {workflow_name: [commands]}
        # Load user config (~/.friday/config.json)
        self.user_config = self._load_user_config()

        # Determine theme profile from env or config
        theme_profile = os.getenv("FRIDAY_THEME_PROFILE") or (self.user_config.get("theme") if isinstance(self.user_config, dict) else None) or "dark"

        self.console = Console(theme=get_rich_theme(theme_profile), force_terminal=True)
        self.context = ConversationContext()
        self.tools = ToolExecutor(self.console)
        self.mcp_manager = MCPManager() # Initialize MCPManager
        self.agent = FridayAgent(self.console, self.tools, self.context, mcp_manager=self.mcp_manager) # Pass mcp_manager to agent
        self.running = True
        
        history_dir = os.path.expanduser("~/.friday")
        os.makedirs(history_dir, exist_ok=True)
        history_file = os.path.join(history_dir, "history")
        
        commands = [
            '/help', '/clear', '/context', '/history', '/compact',
            '/exit', '/quit', '/model', '/diff', '/status', '/files',
            '/compound', '/compound init', '/compound add', '/compound list',
            '/compound run', '/compound remove', '/compound clear',
            '/mcp', '/mcp add', '/mcp remove', '/mcp list', '/mcp connect' # Add MCP commands
        ]
        
        # Add compounding commands if available
        if configure_dspy:
            commands.extend([
                '/triage', '/plan', '/work', '/review', 
                '/generate', '/codify', '/compress'
            ])
            
        command_completer = WordCompleter(commands, ignore_case=True)
        
        def bottom_toolbar():
            # Show context stats in toolbar
            turn_count = len([m for m in self.context.messages if m.get("role") == "user"])
            file_count = len(self.context.files_mentioned)
            return HTML(f"<b><style bg='ansiblack' fg='ansicyan'> /help </style> <style fg='ansigray'>·</style> <style fg='ansigreen'>Ctrl+C</style> cancel <style fg='ansigray'>·</style> <style fg='ansired'>Ctrl+D</style> exit <style fg='ansigray'>│</style> <style fg='ansigray'>Turn {turn_count} · {file_count} files</style></b>")

        def make_rprompt():
            provider = os.getenv("DSPY_LM_PROVIDER", "openai")
            model = os.getenv("DSPY_LM_MODEL", "gpt-4o")
            # Shorten common model names
            model_short = model.replace("gpt-4o", "gpt-4o").replace("claude-3-5-sonnet", "claude-3.5")
            return HTML(f"<style fg='ansigray'>{provider}/{model_short}</style>")

        self.session = PromptSession(
            history=FileHistory(history_file),
            auto_suggest=AutoSuggestFromHistory(),
            style=get_prompt_style(os.getenv("FRIDAY_THEME_PROFILE") or (self.user_config.get("theme") if isinstance(self.user_config, dict) else None)),
            multiline=False,
            key_bindings=self._create_key_bindings(),
            completer=command_completer,
            complete_while_typing=True,
            bottom_toolbar=bottom_toolbar,
        )
        self._make_rprompt = make_rprompt
        
        signal.signal(signal.SIGINT, self._handle_interrupt)

    def _create_key_bindings(self) -> KeyBindings:
        """Create custom key bindings"""
        kb = KeyBindings()
        
        @kb.add('c-c')
        def _(event):
            """Handle Ctrl+C"""
    def _setup_logging(self):
        """Set up structured logging for debugging and monitoring"""
        logging.basicConfig(
            level=os.getenv("FRIDAY_LOG_LEVEL", "INFO").upper(),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                RichHandler(
                    console=self.console if hasattr(self, 'console') else Console(),
                    show_time=True,
                    show_path=False,
                    markup=True
                )
            ]
        )
        
        # Set up file logging as well
        log_dir = os.path.expanduser("~/.friday/logs")
        os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(
            os.path.join(log_dir, "friday.log"),
            encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
        logger = logging.getLogger("friday")
        logger.addHandler(file_handler)
        logger.setLevel(os.getenv("FRIDAY_LOG_LEVEL", "INFO").upper())
        
        self.logger = logger
        
        @kb.add('c-d')
        def _(event):
            """Handle Ctrl+D to exit"""
            self.running = False
            event.app.exit(result='/exit')
        
        return kb

    def _handle_interrupt(self, signum, frame):
        """Handle interrupt signal gracefully"""
        self.console.print("\n[dim]Use /exit or Ctrl+D to quit[/dim]")

    def _load_user_config(self):
        """Load user config from ~/.friday/config.json if present"""
        import json
        cfg_path = os.path.expanduser("~/.friday/config.json")
        if not os.path.exists(cfg_path):
            return {}
        try:
            with open(cfg_path, "r") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _print_banner(self):
        """Print the welcome banner with optional ASCII art.
        Controlled by env vars:
          - FRIDAY_NO_BANNER=1 -> skip all banner output
          - FRIDAY_MINIMAL=1   -> no ASCII art / tips, compact panel
        """
        # Feature toggles from env and ~/.friday/config.json
        def _is_true(val: str | None) -> bool:
            return str(val or "").strip().lower() in {"1", "true", "yes", "on"}

        # Read env first; fall back to config
        env_no_banner = os.getenv("FRIDAY_NO_BANNER")
        env_minimal = os.getenv("FRIDAY_MINIMAL")
        env_ascii_variant = os.getenv("FRIDAY_ASCII_VARIANT")  # block|compact

        cfg_banner = (self.user_config or {}).get("banner", {}) if hasattr(self, "user_config") else {}
        cfg_enabled = cfg_banner.get("enabled", True)
        cfg_minimal = cfg_banner.get("minimal", False)
        cfg_ascii_variant = cfg_banner.get("ascii", "compact")

        if _is_true(env_no_banner) or (env_no_banner is None and not cfg_enabled):
            return

        minimal_mode = _is_true(env_minimal) if env_minimal is not None else bool(cfg_minimal)
        ascii_variant = (env_ascii_variant or cfg_ascii_variant or "block").lower()

        try:
            from friday import __version__ as friday_version
        except Exception:
            friday_version = ""

        tips = [
            "Use /help to discover commands",
            "Press Ctrl+C to cancel current operation",
            "Press Ctrl+D or type /exit to quit",
            "Use /files **/*.py to list Python files",
            "Try /status or /diff to check Git state",
            "/plan turns ideas into actionable plans",
        ]
        tip = random.choice(tips)

        # Choose ASCII art variant
        if ascii_variant == "compact":
            ascii_art = f"[bold cyan]{ASCII_ART.get('friday_compact', 'FRIDAY')}[/]"
        else:
            ascii_art = f"[bold cyan]{ASCII_ART.get('friday', 'FRIDAY')}[/]"
        header = f"[header]FRIDAY[/] [muted]v{friday_version}[/]" if friday_version else "[header]FRIDAY[/]"
        
        # Get current Git info
        git_info = ""
        try:
            import subprocess
            branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=2
            ).stdout.strip()
            if branch:
                git_info = f" [muted]on[/] [accent]{branch}[/]"
        except Exception:
            pass

        # Build adaptive banner using Rich Panel
        if minimal_mode:
            body = "\n".join([
                f"{header}",
                "[subheader]AI-Powered Coding Assistant[/]",
                "[muted]Commands:[/] [command]/help[/] [muted]·[/] [command]/clear[/] [muted]·[/] [command]/exit[/]",
            ])
            # Minimal: no ASCII art, compact body
            self.console.print(Panel.fit(body, border_style="accent", padding=(0, 1)))
        else:
            body = "\n".join([
                f"{header}",
                "[subheader]AI-Powered Coding Assistant[/]",
                "",
                f"[muted]💡 {tip}[/]",
                "",
                "[command]/help[/]   [muted]Show available commands[/]",
                "[command]/clear[/]  [muted]Clear conversation[/]",
                "[command]/exit[/]   [muted]Exit Friday[/]",
            ])
            # Print ASCII art followed by adaptive panel
            self.console.print(ascii_art)
            self.console.print(Panel.fit(body, border_style="accent", padding=(0, 1)))

        cwd = os.getcwd()
        self.console.print(f"\n[muted]Working in[/] [path]{cwd}[/]{git_info}")
        self.console.print(f"[separator]{'─' * 60}[/]\n")

    def _print_help(self):
        """Print help information"""
        help_text = """[header]Commands[/]
  [command]/help[/]              [muted]Show this help message[/]
  [command]/clear[/]             [muted]Clear conversation history[/]
  [command]/context[/]           [muted]Show current context (files, git status)[/]
  [command]/history[/]           [muted]Show conversation history[/]
  [command]/compact[/]           [muted]Compact/summarize conversation history[/]
  [command]/model[/]             [muted]Show/change LLM model[/]
  [command]/diff[/]              [muted]Show git diff[/]
  [command]/status[/]            [muted]Show git status[/]
  [command]/files[/] [pattern]    [muted]List files matching pattern[/]
  [command]/compound[/]          [muted]Manage compound workflows[/]
  [command]/mcp[/]               [muted]Manage Model Context Protocol servers[/]
  [command]/exit[/], [command]/quit[/]       [muted]Exit Friday[/]

[header]Compounding Commands[/]
  [command]/triage[/]            [muted]Triage and categorize findings[/]
  [command]/plan[/] <desc>       [muted]Transform description into project plan[/]
  [command]/work[/] <pattern>    [muted]Execute work (ID, plan file, or pattern)[/]
  [command]/review[/] [target]   [muted]Review PR or local changes[/]
  [command]/generate[/] <desc>   [muted]Generate a new CLI command[/]
  [command]/codify[/] <feedback> [muted]Codify feedback into knowledge base[/]
  [command]/compress[/]          [muted]Compress knowledge base (AI.md)[/]

[header]Capabilities[/]
  [success]✓[/] Read and edit files with syntax highlighting
  [success]✓[/] Search codebase (grep, glob patterns)
  [success]✓[/] Execute shell commands safely
  [success]✓[/] Git operations (status, diff, log, commit)
  [success]✓[/] Create and manage project todos
  [success]✓[/] Generate feature plans and code reviews
  [success]✓[/] Explain and refactor code

[header]Examples[/]
  [prompt.arrow]›[/] [dim]"Read the main.py file and explain what it does"[/]
  [prompt.arrow]›[/] [dim]"/plan Add a new user authentication system"[/]
  [prompt.arrow]›[/] [dim]"/work p1"[/]
  [prompt.arrow]›[/] [dim]"/codify Always use type hints in Python functions"[/]
  [prompt.arrow]›[/] [dim]"/compound run my-workflow"[/]
  [prompt.arrow]›[/] [dim]"!ls -la" (Execute shell command)[/]

[header]Tips[/]
  [info]💡[/] Be specific about file paths and function names
  [info]💡[/] Ask follow-up questions for clarification
  [info]💡[/] Use Ctrl+C to cancel, Ctrl+D to exit
"""
        self.console.print(Panel(help_text, title="[header]Friday Help[/]", border_style="accent", padding=(1, 2)))

    def _print_context(self):
        """Print current context information"""
        import subprocess
        
        table = Table(title="[header]Current Context[/]", border_style="accent", show_header=True, header_style="bold subheader")
        table.add_column("Item", style="subheader", no_wrap=True)
        table.add_column("Value", style="white")
        
        table.add_row("📁 Working Directory", f"[path]{os.getcwd()}[/]")
        
        try:
            branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=5
            ).stdout.strip()
            table.add_row("🔀 Git Branch", f"[accent]{branch}[/]")
        except Exception:
            table.add_row("🔀 Git Branch", "[muted]Not a git repo[/]")
        
        try:
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, timeout=5
            ).stdout
            changed = len([line for line in status.strip().split('\n') if line])
            status_color = "warning" if changed > 0 else "success"
            table.add_row("📝 Changed Files", f"[{status_color}]{changed}[/]")
        except Exception:
            pass
        
        turns = len(self.context.messages)
        turn_color = "warning" if turns > 40 else "info" if turns > 20 else "muted"
        table.add_row("💬 Conversation Turns", f"[{turn_color}]{turns}[/]")
        
        files = len(self.context.files_mentioned)
        table.add_row("📄 Files in Context", f"[info]{files}[/]")
        
        provider = os.getenv("DSPY_LM_PROVIDER", "openai")
        model = os.getenv("DSPY_LM_MODEL", "gpt-4o")
        table.add_row("🤖 LLM Provider", f"[subheader]{provider}[/]/[muted]{model}[/]")
        
        self.console.print(table)

    def _print_history(self):
        """Print conversation history"""
        if not self.context.messages:
            self.console.print("[warning]⚠ No conversation history yet[/]")
            return
        
        table = Table(title="[header]Conversation History[/]", border_style="accent", show_header=True, header_style="bold subheader")
        table.add_column("#", style="muted", width=4)
        table.add_column("Role", style="subheader", width=10)
        table.add_column("Content", style="white")
        table.add_column("Time", style="muted", width=8)
        
        for i, msg in enumerate(self.context.messages[-10:], 1):
            role = msg.get("role", "unknown")
            role_icon = {"user": "👤", "assistant": "🤖", "tool": "🔧", "system": "⚙️"}.get(role, "•")
            content = msg.get("content", "")[:80]
            if len(msg.get("content", "")) > 80:
                content += "..."
            
            # Parse timestamp if available
            timestamp = msg.get("timestamp", "")
            if timestamp:
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%H:%M:%S")
                except Exception:
                    time_str = ""
            else:
                time_str = ""
            
            table.add_row(str(i), f"{role_icon} {role}", content, time_str)
        
        self.console.print(table)
        self.console.print(f"\n[muted]Showing last 10 of {len(self.context.messages)} messages[/]")

    async def _handle_command(self, command: str) -> bool: # Made async
        """Handle slash commands. Returns True if should continue, False to exit."""
        parts = command.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # Standard Commands
        if cmd in ["/exit", "/quit", "/q"]:
            self.console.print("\n[success]✓ Goodbye! Happy coding! 👋[/]")
            return False
        elif cmd == "/help":
            self._print_help()
        elif cmd == "/clear":
            self.context.clear()
            self.console.print("[success]✓ Conversation cleared[/]")
        elif cmd == "/context":
            self._print_context()
        elif cmd == "/history":
            self._print_history()
        elif cmd == "/compact":
            before = len(self.context.messages)
            self.context.compact()
            after = len(self.context.messages)
            self.console.print(f"[success]✓ Conversation compacted[/] [muted]{before} → {after} messages[/]")
        elif cmd == "/model":
            self._show_model_info()
    def _handle_file_error(self, error: Exception, operation: str, file_path: str = None):
        """Handle file-related errors with comprehensive error messages"""
        error_type = type(error).__name__
        
        if error_type == "FileNotFoundError":
            self.console.print(f"[error]✗ File not found:[/] {file_path}")
            self.logger.error(f"File not found: {file_path}")
        elif error_type == "PermissionError":
            self.console.print(f"[error]✗ Permission denied:[/] {file_path}")
            self.logger.error(f"Permission denied for {operation} on {file_path}")
        elif error_type == "IsADirectoryError":
            self.console.print(f"[error]✗ Expected file, got directory:[/] {file_path}")
            self.logger.error(f"Expected file, got directory: {file_path}")
        elif error_type == "NotADirectoryError":
            self.console.print(f"[error]✗ Expected directory, got file:[/] {file_path}")
            self.logger.error(f"Expected directory, got file: {file_path}")
        else:
            self.console.print(f"[error]✗ File operation error:[/] {str(error)}")
            self.logger.error(f"File operation error during {operation}: {str(error)}")
        
        # Provide helpful suggestions
        if error_type == "PermissionError":
            self.console.print(f"[info]💡 Try:[/] [command]chmod +r {file_path}[/] or run with elevated privileges")
        elif error_type == "FileNotFoundError":
            self.console.print(f"[info]💡 Check:[/] File path and working directory")
        
        return False
            self.tools.git_diff(args or "HEAD")
        elif cmd == "/status":
            self.tools.git_status()
        elif cmd == "/files":
            pattern = args or "*"
            self.tools.list_directory(".", pattern)
        elif cmd == "/compound":
            self._handle_compound_command(args)
        
        # Compounding Commands
        elif cmd == "/triage":
            self._run_safe(run_triage)
        elif cmd == "/plan":
            if not args:
                self.console.print("[warning]⚠ Usage:[/] [command]/plan[/] [muted]<feature description>[/]")
            else:
                self._run_safe(run_plan, args)
        elif cmd == "/work":
            self._run_safe(run_unified_work, pattern=args if args else None)
        elif cmd == "/review":
            self._run_safe(run_review, args if args else "latest")
    def _validate_input(self, input_str: str, input_type: str = "text", allowed_values: List[str] = None) -> Optional[str]:
        """Validate user input and provide helpful error messages"""
    def _run_safe(self, func, *args, **kwargs):
        """Run a workflow function safely with enhanced error handling"""
        if not configure_dspy:
            self.console.print("[error]✗ Error:[/] Compounding commands are not available (imports failed)")
            self.logger.error("Compounding commands not available - imports failed")
            return
        
        try:
            self.logger.info(f"Starting workflow: {func.__name__}")
            result = func(*args, **kwargs)
            self.logger.info(f"Completed workflow: {func.__name__}")
            return result
        except FileNotFoundError as e:
            self._handle_file_error(e, func.__name__)
        except PermissionError as e:
            self._handle_file_error(e, func.__name__)
        except ValueError as e:
            self.console.print(f"[error]✗ Invalid input:[/] {str(e)}")
            self.logger.error(f"Invalid input in {func.__name__}: {str(e)}")
        except Exception as e:
            self.console.print(f"[error]✗ Error executing workflow:[/] {e}")
            self.logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            if os.getenv("DEBUG") or os.getenv("FRIDAY_DEBUG"):
                import traceback
                self.console.print(f"[muted]{traceback.format_exc()}[/]")
            self.console.print(f"[warning]⚠ Input cannot be empty[/]")
            self.logger.warning("Empty input provided")
            return None
        
        if input_type == "path":
            # Basic path validation
            if not os.path.exists(input_str):
                self.console.print(f"[warning]⚠ Path does not exist:[/] {input_str}")
                self.logger.warning(f"Non-existent path provided: {input_str}")
                return None
        
        if allowed_values and input_str not in allowed_values:
            self.console.print(f"[warning]⚠ Invalid value:[/] {input_str}")
            self.console.print(f"[info]💡 Allowed values:[/] {', '.join(allowed_values)}")
            self.logger.warning(f"Invalid input value: {input_str}")
            return None
        
        return input_str.strip()
            if not args:
                self.console.print("[warning]⚠ Usage:[/] [command]/generate[/] [muted]<description>[/]")
            else:
                self._run_safe(run_generate_command, description=args)
        elif cmd == "/codify":
            if not args:
                self.console.print("[warning]⚠ Usage:[/] [command]/codify[/] [muted]<feedback>[/]")
            else:
                self._run_safe(run_codify, feedback=args)
        elif cmd in ["/compress", "/compress-kb"]:
            kb = KnowledgeBase()
            self._run_safe(kb.compress_ai_md)
        elif cmd == "/mcp":
            await self._handle_mcp_command(args)
            
        else:
            self.console.print(f"[warning]⚠ Unknown command:[/] [command]{command}[/]")
            self.console.print("[muted]Type[/] [command]/help[/] [muted]for available commands[/]")
        
        return True

    def _show_progress(self, task_name: str, total_steps: int = None):
        """Show progress indicator for long-running operations"""
        if total_steps:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                "•",
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                "•",
                TextColumn("[progress.completed]{task.completed}/{task.total}"),
                console=self.console
            ) as progress:
                task = progress.add_task(f"[cyan]{task_name}[/]", total=total_steps)
                while not progress.finished:
                    progress.update(task, advance=0.1)
                    time.sleep(0.1)
        else:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task(f"[cyan]{task_name}[/]")
                while not progress.finished:
                    progress.update(task, advance=1)
                    time.sleep(0.1)
        """Run a workflow function safely"""
        if not configure_dspy:
             self.console.print("[error]✗ Error:[/] Compounding commands are not available (imports failed)")
             return
             
        try:
            func(*args, **kwargs)
        except Exception as e:
            self.console.print(f"[error]✗ Error executing workflow:[/] {e}")
            if os.getenv("DEBUG") or os.getenv("FRIDAY_DEBUG"):
                import traceback
                self.console.print(f"[muted]{traceback.format_exc()}[/]")

    async def _handle_mcp_command(self, args: str): # New async method
        """Handle /mcp commands"""
        parts = args.strip().split(maxsplit=1)
        if not parts:
            self.console.print("[yellow]Usage: /mcp <subcommand> [args][/]")
            self.console.print("[dim]Subcommands: add, remove, list, connect[/dim]")
            return
        
        subcommand = parts[0].lower()
        sub_args = parts[1] if len(parts) > 1 else ""
        
        if subcommand == "add":
            self._mcp_add_server(sub_args)
        elif subcommand == "remove":
            self._mcp_remove_server(sub_args)
        elif subcommand == "list":
            self._mcp_list_servers()
        elif subcommand == "connect":
            await self._mcp_connect_server(sub_args)
        else:
            self.console.print(f"[yellow]Unknown /mcp subcommand: {subcommand}[/]")
            self.console.print("[dim]Available: add, remove, list, connect[/dim]")

    def _mcp_add_server(self, args: str):
        """Add an MCP server to configuration: /mcp add <name> <command> [args...]"""
        parts = args.strip().split(maxsplit=2)
        if len(parts) < 2:
            self.console.print("[yellow]Usage: /mcp add <name> <command> [args...][/]")
            return
        
        name = parts[0]
        command = parts[1]
        cmd_args = parts[2].split() if len(parts) > 2 else []
        
        self.mcp_manager.add_server(name, command, cmd_args)
        self.console.print(f"[green]MCP server '{name}' added.[/green]")

    def _mcp_remove_server(self, name: str):
        """Remove an MCP server from configuration: /mcp remove <name>"""
        if not name:
            self.console.print("[yellow]Usage: /mcp remove <name>[/]")
            return
        
        if name not in self.mcp_manager.servers:
            self.console.print(f"[yellow]Error: Server '{name}' not found.[/yellow]")
            return
        
        # Disconnect if connected
        if name in self.mcp_manager.sessions:
            # Need to figure out how to disconnect specific session cleanly
            # For now, just remove from config
            pass 
        
        self.mcp_manager.remove_server(name)
        self.console.print(f"[green]MCP server '{name}' removed.[/green]")

    def _mcp_list_servers(self):
        """List configured MCP servers: /mcp list"""
        if not self.mcp_manager.servers:
            self.console.print("[dim]No MCP servers configured.[/dim]")
            return
        
        table = Table(title="Configured MCP Servers", border_style="blue")
        table.add_column("Name", style="cyan")
        table.add_column("Command", style="white")
        table.add_column("Status", style="green")
        
        for name, cfg in self.mcp_manager.servers.items():
            status = "Connected" if name in self.mcp_manager.sessions else "Disconnected"
            table.add_row(name, f"{cfg.command} {' '.join(cfg.args)}", status)
            
        self.console.print(table)
        
        if self.mcp_manager.available_tools:
            self.console.print("\n[bold]Available MCP Tools:[/]")
            for tool in self.mcp_manager.available_tools:
                self.console.print(f"  - {tool['name']} (from {tool['server']})")

    async def _mcp_connect_server(self, name: str):
        """Connect to a specific MCP server: /mcp connect <name>"""
        if not name:
            self.console.print("[yellow]Usage: /mcp connect <name>[/]")
            return
        
        if name not in self.mcp_manager.servers:
            self.console.print(f"[yellow]Error: Server '{name}' not found in config.[/yellow]")
            return
        
        self.console.print(f"[cyan]Connecting to MCP server '{name}'...[/cyan]")
        try:
            await self.mcp_manager.connect_server(name)
            self.console.print(f"[green]Successfully connected to '{name}'.[/green]")
        except Exception as e:
            self.console.print(f"[red]Failed to connect to '{name}': {e}[/red]")

    async def _handle_compound_command(self, args: str): # Made async
        """Handle compound workflow commands"""
        parts = args.strip().split(maxsplit=1)
        if not parts:
            self.console.print("[yellow]Usage: /compound <subcommand> [args][/]")
            self.console.print("[dim]Subcommands: init, add, list, run, remove, clear[/dim]")
            return
        
        subcommand = parts[0].lower()
        sub_args = parts[1] if len(parts) > 1 else ""
        
        if subcommand == "init":
            self._compound_init(sub_args)
        elif subcommand == "add":
            self._compound_add(sub_args)
        elif subcommand == "list":
            self._compound_list(sub_args)
        elif subcommand == "run":
            await self._compound_run(sub_args)
        elif subcommand == "remove":
             self._compound_remove(sub_args)
        elif subcommand == "clear":
             self._compound_clear(sub_args)
        else:
            self.console.print(f"[yellow]Unknown compound subcommand: {subcommand}[/]")
            self.console.print("[dim]Available: init, add, list, run, remove, clear[/dim]")

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
    def _handle_interrupt(self, signum, frame):
        """Handle interrupt signal gracefully with logging"""
        self.console.print("\n[dim]Use /exit or Ctrl+D to quit[/dim]")
        self.logger.info("User interrupted operation")
            return
        
        self.console.print(f"[bold]Workflow '{workflow_name}':[/]")
        for i, cmd in enumerate(commands, 1):
            self.console.print(f"  {i}. [white]{cmd}[/]")

    async def _compound_run(self, workflow_name: str):
        """Run all commands in a compound workflow"""
        if not workflow_name:
            self.console.print("[yellow]Error: Workflow name is required[/]")
            self.console.print("[dim]Usage: /compound run <workflow_name>[/dim]")
    def _load_user_config(self):
        """Load user config from ~/.friday/config.json if present with error handling"""
        import json
        cfg_path = os.path.expanduser("~/.friday/config.json")
        if not os.path.exists(cfg_path):
            self.logger.info("No user config found, using defaults")
            return {}
        try:
            with open(cfg_path, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self.logger.info("User config loaded successfully")
                    return data
                else:
                    self.logger.warning("User config is not a valid dictionary")
                    return {}
        except json.JSONDecodeError as e:
            self.console.print(f"[warning]⚠ Invalid config file:[/] {cfg_path}")
            self.logger.error(f"Invalid JSON in config file: {str(e)}")
            return {}
        except PermissionError as e:
            self._handle_file_error(e, "reading config", cfg_path)
            return {}
        except Exception as e:
            self.console.print(f"[warning]⚠ Error loading config:[/] {str(e)}")
            self.logger.error(f"Error loading config: {str(e)}")
            return {}
        
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
                await self.agent.process_message(cmd) # Await process_message
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
            self.console.print("[yellow]Error: Invalid command index[/]")
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
        """Get the input prompt with current directory and context"""
        cwd = os.path.basename(os.getcwd())
        
        # Add conversation turn indicator
        turn = len([m for m in self.context.messages if m.get("role") == "user"])
        
        # Color-code prompt based on context size
        if turn > 40:
            turn_color = "warning"
        elif turn > 20:
            turn_color = "info"
        else:
            turn_color = "muted"
        
        return f"[prompt.path]{cwd}[/] [{turn_color}]#{turn}[/] [prompt.arrow]›[/] "

    async def run(self): # Made async
        """Main run loop"""
        self._print_banner()
        
        # Connect MCP servers on startup
        await self.mcp_manager.connect_all()

        while self.running:
            try:
                prompt_text = self._get_prompt()
                user_input = await self.session.prompt_async( # Use async prompt
                    prompt_text,
                    rprompt=self._make_rprompt(),
                )
                
                if user_input is None:
                    continue
                
                user_input = user_input.strip()
                
                if not user_input:
                    continue
                
                if user_input.startswith("/"):
                    if not await self._handle_command(user_input): # await _handle_command
                        break
                    continue
                
                if user_input.startswith("!"):
                    shell_cmd = user_input[1:].strip()
                    if shell_cmd:
                        self.tools.execute_command(shell_cmd) # execute_command is sync
                    continue
                
                await self.agent.process_message(user_input) # await process_message
                
            except KeyboardInterrupt:
                self.console.print("\n[warning]⚠ Interrupted[/] [muted]Use /exit or Ctrl+D to quit[/]")
                continue
            except EOFError:
                self.console.print("\n[success]✓ Goodbye! 👋[/]")
                break
            except Exception as e:
                self.console.print(f"[error]✗ Error:[/] {str(e)}")
                if os.getenv("DEBUG") or os.getenv("FRIDAY_DEBUG"):
                    import traceback
                    self.console.print(f"[muted]{traceback.format_exc()}[/]")
                continue

        await self.mcp_manager.cleanup() # Cleanup MCP connections
        self.context.save()
