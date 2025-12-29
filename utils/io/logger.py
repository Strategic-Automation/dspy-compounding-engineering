import logging
import os
from typing import Optional

from rich.console import Console

from utils.security.scrubber import scrubber

console = Console()

# Configure persistent file logging
LOG_FILE = "compounding.log"

# Ensure log file exists with restrictive permissions (0600)
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "a"):
        os.chmod(LOG_FILE, 0o600)

file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger_instance = logging.getLogger("compounding")
logger_instance.addHandler(file_handler)
logger_instance.setLevel(logging.INFO)


class SystemLogger:
    """
    Centralized logger for Compounding Engineering.
    Respects COMPOUNDING_QUIET and provides consistent styling and file persistence.
    """

    @staticmethod
    def _is_quiet() -> bool:
        return os.getenv("COMPOUNDING_QUIET", "false").lower() == "true"

    @staticmethod
    def info(msg: str):
        """Log info - writes to file and console (unless quiet mode)."""
        scrubbed_msg = scrubber.scrub(msg)
        logger_instance.info(scrubbed_msg)
        if not SystemLogger._is_quiet():
            console.print(f"[dim]INFO:[/dim] {scrubbed_msg}")

    @staticmethod
    def debug(msg: str):
        """Debug log - shows in console if not quiet, always goes to file."""
        scrubbed_msg = scrubber.scrub(msg)
        logger_instance.debug(scrubbed_msg)
        if not SystemLogger._is_quiet():
            console.print(f"[dim]{scrubbed_msg}[/dim]")

    @staticmethod
    def success(msg: str):
        """Success log - always shows in console with green checkmark."""
        scrubbed_msg = scrubber.scrub(msg)
        logger_instance.info(f"SUCCESS: {scrubbed_msg}")
        if not SystemLogger._is_quiet():
            console.print(f"[green]✓ {scrubbed_msg}[/green]")

    @staticmethod
    def warning(msg: str):
        """Warning log - always shows in console."""
        scrubbed_msg = scrubber.scrub(msg)
        logger_instance.warning(scrubbed_msg)
        console.print(f"[yellow]⚠ WARNING:[/yellow] {scrubbed_msg}")

    @staticmethod
    def error(msg: str, detail: Optional[str] = None):
        """Error log - always shows in console."""
        scrubbed_msg = scrubber.scrub(msg)
        scrubbed_detail = scrubber.scrub(detail) if detail else None

        if scrubbed_detail:
            logger_instance.error(f"{scrubbed_msg} - {scrubbed_detail}")
        else:
            logger_instance.error(scrubbed_msg)
        console.print(f"[bold red]✗ ERROR:[/bold red] {scrubbed_msg}")
        if scrubbed_detail and not SystemLogger._is_quiet():
            console.print(f"[dim red]  {scrubbed_detail}[/dim red]")

    @staticmethod
    def status(msg: str):
        """Returns a status context for rich spinners."""
        return console.status(msg)


# Global singleton
logger = SystemLogger()
