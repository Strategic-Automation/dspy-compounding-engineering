import os
from typing import Optional
from rich.console import Console

console = Console()

class SystemLogger:
    """
    Centralized logger for Compounding Engineering.
    Respects COMPOUNDING_QUIET and provides consistent styling.
    """

    @staticmethod
    def _is_quiet() -> bool:
        return os.getenv("COMPOUNDING_QUIET", "false").lower() == "true"

    @staticmethod
    def info(msg: str):
        if not SystemLogger._is_quiet():
            console.print(f"[dim grey]INFO:[/dim grey] {msg}")

    @staticmethod
    def success(msg: str):
        if not SystemLogger._is_quiet():
            console.print(f"[green]✓ {msg}[/green]")

    @staticmethod
    def warning(msg: str):
        console.print(f"[yellow]⚠ WARNING:[/yellow] {msg}")

    @staticmethod
    def error(msg: str, detail: Optional[str] = None):
        console.print(f"[bold red]✗ ERROR:[/bold red] {msg}")
        if detail and not SystemLogger._is_quiet():
            console.print(f"[dim red]{detail}[/dim red]")

    @staticmethod
    def status(msg: str):
        """Returns a status context for rich."""
        return console.status(msg)

# Global singleton
logger = SystemLogger()
