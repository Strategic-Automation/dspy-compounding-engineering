import hashlib
import os
import subprocess
import sys
import threading
from pathlib import Path

import dspy
from dotenv import load_dotenv
from rich.console import Console
from utils.io.logger import logger

console = Console()


def get_project_root() -> Path:
    """
    Get the project root directory, preferably the Git root.
    """
    try:
        from utils.io.safe import run_safe_command

        result = run_safe_command(
            ["git", "rev-parse", "--show-toplevel"], stderr=subprocess.STDOUT, text=True
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return Path(os.getcwd())


def get_project_hash() -> str:
    """
    Generate a stable, unique hash for the current project based on its root path.
    Uses SHA-256 and returns a 16-character prefix.
    """
    root_path = str(get_project_root().absolute())
    return hashlib.sha256(root_path.encode()).hexdigest()[:16]


def resolve_embedding_config() -> tuple[str, str, str | None]:
    """
    Centralized logic to determine embedding provider, model, and base URL.
    """
    lm_provider = os.getenv("DSPY_LM_PROVIDER", "openai")
    raw_provider = os.getenv("EMBEDDING_PROVIDER")
    model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    base_url = os.getenv("EMBEDDING_BASE_URL", None)

    if raw_provider:
        return raw_provider, model_name, base_url

    # Auto-infer
    if lm_provider == "openrouter" and os.getenv("OPENROUTER_API_KEY"):
        return "openrouter", model_name, base_url

    return "openai", model_name, base_url


class ServiceRegistry:
    """
    Registry for runtime service status and shared state.
    Replaces the global _SYSTEM_STATUS dictionary.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ServiceRegistry, cls).__new__(cls)
                    cls._instance._status = {
                        "qdrant_available": None,
                        "openai_key_available": None,
                        "embeddings_ready": None,
                        "learnings_ensured": False,
                        "codebase_ensured": False,
                    }
                    cls._instance.lock = threading.Lock()
        return cls._instance

    @property
    def status(self):
        return self._status

    def check_qdrant(self, force: bool = False) -> bool:
        """
        Check if Qdrant is available. Cached by default.
        """
        if self._status["qdrant_available"] is not None and not force:
            return self._status["qdrant_available"]

        from qdrant_client import QdrantClient

        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        try:
            client = QdrantClient(url=qdrant_url, timeout=1.0)
            client.get_collections()
            self._status["qdrant_available"] = True
        except Exception:
            self._status["qdrant_available"] = False
            # Only print if we are not in a quiet mode or explicitly checking
            if not os.getenv("COMPOUNDING_QUIET"):
                logger.warning(
                    "Qdrant not available. Falling back to simple keyword search."
                )
        return self._status["qdrant_available"]

    def check_api_keys(self, force: bool = False) -> bool:  # noqa: C901
        """
        Check if required API keys are available. Cached by default.
        """
        if self._status["openai_key_available"] is not None and not force:
            return self._status["openai_key_available"]

        provider = os.getenv("DSPY_LM_PROVIDER", "openai")
        emb_provider = os.getenv("EMBEDDING_PROVIDER")

        # Auto-infer embedding provider if not set
        if not emb_provider:
            if provider == "openrouter" and os.getenv("OPENROUTER_API_KEY"):
                emb_provider = "openrouter"
            elif provider == "openai" and os.getenv("OPENAI_API_KEY"):
                emb_provider = "openai"
            else:
                emb_provider = "openai"  # Default

        available = False

        # Check LM keys
        if provider == "openai":
            available = bool(os.getenv("OPENAI_API_KEY"))
        elif provider == "openrouter":
            available = bool(os.getenv("OPENROUTER_API_KEY"))
        elif provider == "anthropic":
            available = bool(os.getenv("ANTHROPIC_API_KEY"))
        elif provider == "ollama":
            available = True  # Local

        # Check Embedding keys if not using fastembed
        emb_available = True
        if emb_provider == "openai":
            emb_available = bool(os.getenv("OPENAI_API_KEY"))
        elif emb_provider == "openrouter":
            emb_available = bool(os.getenv("OPENROUTER_API_KEY"))

        if not available:
            logger.warning(f"No API key found for LM provider '{provider}'.")

        if not emb_available and emb_provider != "fastembed":
            logger.warning(f"No API key found for embedding provider '{emb_provider}'.")

        final_available = available and (emb_available or emb_provider == "fastembed")
        self._status["openai_key_available"] = final_available
        return final_available


def load_configuration(env_file: str | None = None) -> None:
    """
    Load environment variables from multiple sources in priority order.
    """
    sources = []

    # 1. Explicitly provided file
    if env_file and os.path.exists(env_file):
        sources.append((env_file, True))
    elif env_file:
        console.print(f"[bold red]Error:[/bold red] Specified env file '{env_file}' not found.")
        sys.exit(1)

    # 2. Environment variable pointer
    env_var_path = os.getenv("COMPOUNDING_ENV")
    if env_var_path and os.path.exists(env_var_path):
        sources.append((env_var_path, True))

    # 3. Local Git/CWD .env
    root = get_project_root()
    root_env = root / ".env"
    if root_env.exists():
        sources.append((str(root_env), True))

    # 4. Fallback to CWD if different from root
    cwd_env = Path(os.getcwd()) / ".env"
    if cwd_env.exists() and cwd_env != root_env:
        sources.append((str(cwd_env), True))

    # 5. Tool-specific global config
    tool_env = Path.home() / ".config" / "compounding" / ".env"
    if tool_env.exists():
        sources.append((str(tool_env), False))

    # 6. User home fallback
    home_env = Path.home() / ".env"
    if home_env.exists() and home_env != tool_env:
        sources.append((str(home_env), False))

    if not sources:
        return

    # Load the highest priority source with override=True
    primary_path, _ = sources[0]
    load_dotenv(dotenv_path=primary_path, override=True)

    # Load remaining as fallbacks
    for path, _ in sources[1:]:
        load_dotenv(dotenv_path=path, override=False)


# Context Management
CONTEXT_WINDOW_LIMIT = int(os.getenv("CONTEXT_WINDOW_LIMIT", "128000"))
CONTEXT_OUTPUT_RESERVE = int(os.getenv("CONTEXT_OUTPUT_RESERVE", "4096"))

# Tier 1 Files
TIER_1_FILES = [
    "pyproject.toml",
    "README.md",
    "Dockerfile",
    "docker-compose.yml",
    "requirements.txt",
    "package.json",
]


registry = ServiceRegistry()


def configure_dspy(env_file: str | None = None):
    # Load configuration before any other logic
    load_configuration(env_file)

    # Run system checks once at startup
    registry.check_qdrant()
    registry.check_api_keys()

    provider = os.getenv("DSPY_LM_PROVIDER", "openai")
    model_name = os.getenv("DSPY_LM_MODEL", "gpt-5.2")

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in environment variables or .env file.")
        lm = dspy.LM(model=model_name, api_key=api_key)
    elif provider == "anthropic":
        lm = dspy.LM(model=f"anthropic/{model_name}", api_key=os.getenv("ANTHROPIC_API_KEY"))
    elif provider == "ollama":
        # Use litellm's native Ollama support
        # Format: ollama/model_name
        lm = dspy.LM(model=f"ollama/{model_name}")
    elif provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            error_msg = (
                "OPENROUTER_API_KEY is not set in environment variables or "
                ".env file (required for OpenRouter)."
            )
            raise ValueError(error_msg)
        lm = dspy.LM(
            model=f"openai/{model_name}",
            api_key=api_key,
            api_base="https://openrouter.ai/api/v1",
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    dspy.settings.configure(lm=lm)
