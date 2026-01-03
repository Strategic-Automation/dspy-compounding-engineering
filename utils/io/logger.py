import logging
import os
from typing import Optional

from loguru import logger as loguru_logger
from rich.console import Console

from utils.security.scrubber import scrubber

console = Console()

# Configure persistent file logging
LOG_FILE = "compounding.log"


class InterceptHandler(logging.Handler):
    """
    Redirects standard logging messages to Loguru.
    """

    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = loguru_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where the logged message originated
        # We look back 2 levels (emit -> logging -> caller)
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        # Apply scrubbing to the message before it reaches Loguru
        msg = scrubber.scrub(record.getMessage())
        loguru_logger.opt(depth=depth, exception=record.exc_info).log(level, msg)


_CONFIGURED = False


def configure_logging(log_path: Optional[str] = None):
    """Configures Loguru and intercept handlers. Lazily called or via bootstrap."""
    global _CONFIGURED, LOG_FILE
    if _CONFIGURED:
        return

    # Use environment override, passed path, or default
    env_path = os.getenv("COMPOUNDING_LOG_PATH")
    if env_path:
        LOG_FILE = env_path
    elif log_path:
        LOG_FILE = log_path

    # Ensure path is absolute for portability across nested directories
    LOG_FILE = os.path.abspath(LOG_FILE)

    # Atomic creation with restricted permissions (0600)
    try:
        # Use os.open to atomically create/open with 0600
        flags = os.O_CREAT | os.O_WRONLY | os.O_APPEND
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC

        fd = os.open(LOG_FILE, flags, 0o600)
        os.close(fd)

        # Ensure permissions (noop if already 0600)
    except Exception as e:
        msg = f"[bold yellow]WARNING: Could not secure audit log at {LOG_FILE}: {e}[/bold yellow]"
        console.print(msg)

    # Remove default handler (which prints to stderr)
    loguru_logger.remove()

    # Determine log level for FILE
    # Default to DEBUG to ensure full capture in file
    log_level_str = os.getenv("COMPOUNDING_LOG_LEVEL", "DEBUG").upper()

    # Add File Sink with rotation, retention, and a global scrubbing filter
    loguru_logger.add(
        LOG_FILE,
        level=log_level_str,
        rotation="10 MB",
        retention="1 week",
        # Loguru filter can't easily modify record, but our sink does
        filter=lambda record: scrubber.scrub(record["message"]) == record["message"] or True,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}"
        ),
        enqueue=False,  # Disable async queue to prevent shutdown hangs
    )

    loguru_logger.debug("Loguru File Sink initialized (enqueue=False)")

    # Intercept standard logging - capture INFO and above from libraries by default
    # but route EVERYTHING to Loguru for unified scrubbing
    # We clear existing handlers and force ours to be the only one
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(logging.INFO)

    # Squelch noisy libraries
    noisy_libs = [
        "httpx",
        "httpcore",
        "openai",
        "urllib3",
        "markdown_it",
        "rich",
        "dspy",
        "numexpr",
        "filelock",
        "litellm",
        "qdrant-client",
    ]
    for library in noisy_libs:
        logging.getLogger(library).setLevel(logging.WARNING)

    _CONFIGURED = True


class SystemLogger:
    """
    Centralized logger for Compounding Engineering.

    Design Philosophy:
    - CLI: clean, minimal, user-focused (Success, Warning, Error only).
    - File: comprehensive, detailed, developer-focused (Debug, Info, + CLI events).
    """

    # Pre-define injection markers for loop efficiency in get_logs
    _INJECTION_MARKERS = [
        "DSPy [Predict]",
        "HTTP Request:",
        "Thought:",
        "Action:",
        "Output:",
    ]

    @staticmethod
    def _is_quiet() -> bool:
        return os.getenv("COMPOUNDING_QUIET", "false").lower() == "true"

    @staticmethod
    def _log_to_all(
        level: str,
        msg: str,
        to_cli: bool = False,
        prefix: str = "",
        detail: Optional[str] = None,
    ):
        """Internal helper to scrub and route logs to both Loguru and CLI."""
        scrubbed_msg = scrubber.scrub(msg)
        scrubbed_detail = scrubber.scrub(detail) if detail else None

        # Route to Loguru
        log_msg = f"{scrubbed_msg} - {scrubbed_detail}" if scrubbed_detail else scrubbed_msg
        # Use depth=2 to skip _log_to_all and the specific log level method (info, success, etc.)
        # to correctly attribute the log to the actual call site.
        loguru_logger.opt(depth=2).log(level.upper(), log_msg)

        # Route to CLI
        # Errors and warnings bypass quiet mode to ensure visibility
        bypass_quiet = level.lower() in ["error", "warning"]
        if to_cli and (bypass_quiet or not SystemLogger._is_quiet()):
            cli_msg = f"{prefix} {scrubbed_msg}".strip()
            if level.lower() == "info":
                console.log(f"[dim]{cli_msg}[/dim]")
            elif level.lower() == "success":
                console.print(f"[green]{cli_msg}[/green]")
            elif level.lower() == "warning":
                console.print(f"[yellow]{prefix}:[/yellow] {scrubbed_msg}")
            elif level.lower() == "error":
                console.print(f"[bold red]{prefix}:[/bold red] {scrubbed_msg}")
                if scrubbed_detail:
                    console.print(f"[dim red]  {scrubbed_detail}[/dim red]")

    @staticmethod
    def info(msg: str, to_cli: bool = False):
        """Log info - writes to FILE. Optionally writes to CLI if to_cli=True."""
        SystemLogger._log_to_all("info", msg, to_cli=to_cli, prefix="ℹ")

    @staticmethod
    def debug(msg: str):
        """Debug log - writes to FILE ONLY. clean CLI."""
        # Debug messages go to file via _log_to_all but with to_cli=False
        SystemLogger._log_to_all("debug", msg, to_cli=False)

    @staticmethod
    def success(msg: str):
        """Success log - shows in CLI and writes to file."""
        SystemLogger._log_to_all("success", msg, to_cli=True, prefix="✓")

    @staticmethod
    def warning(msg: str):
        """Warning log - shows in CLI and writes to file."""
        SystemLogger._log_to_all("warning", msg, to_cli=True, prefix="⚠ WARNING")

    @staticmethod
    def error(msg: str, detail: Optional[str] = None):
        """Error log - shows in CLI and writes to file."""
        SystemLogger._log_to_all("error", msg, to_cli=True, prefix="✗ ERROR", detail=detail)

    @staticmethod
    def status(msg: str):
        """Returns a status context for rich spinners."""
        return console.status(msg)

    @staticmethod
    def get_logs(limit: int = 100) -> str:
        """
        Read the last N lines from the log file using a memory-efficient backward seek.
        Applies additional read-time scrubbing for agent safety.
        """
        if not os.path.exists(LOG_FILE):
            return "No logs found."

        try:
            lines = []
            buffer_size = 8192
            with open(LOG_FILE, "rb") as f:
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                pos = file_size

                while len(lines) <= limit and pos > 0:
                    read_size = min(buffer_size, pos)
                    pos -= read_size
                    f.seek(pos)
                    chunk = f.read(read_size)

                    # Convert bytes to string (handling potential split characters)
                    # We use 'ignore' to be safe with partial multibyte chars
                    text = chunk.decode("utf-8", "ignore")

                    chunk_lines = text.splitlines()
                    if not chunk_lines:
                        continue

                    # Handle the case where the first line of a chunk is part of
                    # the last line of the previous chunk (reading backward)
                    if lines and not chunk.endswith(b"\n") and not chunk.endswith(b"\r"):
                        lines[0] = chunk_lines[-1] + lines[0]
                        lines = chunk_lines[:-1] + lines
                    else:
                        lines = chunk_lines + lines

                # Apply "Read-time" scrubbing to protect agents from injection or leak
                final_lines = lines[-limit:]
                scrubbed_lines = []

                for line in final_lines:
                    # Block large hex strings, raw data dumps, or LLM internal headers
                    # Also redact agent markers to prevent indirect prompt injection
                    if any(marker in line for marker in SystemLogger._INJECTION_MARKERS):
                        scrubbed_lines.append("[PROTECTED BLOCK REDACTED]")
                        continue

                    # Use the standard scrubber for secrets (API keys, etc.)
                    scrubbed_lines.append(scrubber.scrub(line))

                return "\n".join(scrubbed_lines)

        except Exception as e:
            return f"Error reading logs: {e}"


# Global singleton
logger = SystemLogger()
