"""
Configuration module for Compounding Engineering.

Handles:
- Environment variable loading (.env files)
- DSPy LM configuration with auto-detected max_tokens
- Service registry for Qdrant and API key status
- Project root and hash utilities
"""

import hashlib
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

import dspy
from dotenv import load_dotenv

from utils.io.logger import configure_logging, console, logger

# =============================================================================
# Project Utilities
# =============================================================================


def get_project_root() -> Path:
    """
    Determine the root directory of the current project.

    The function attempts to locate the Git repository root.
    If Git metadata is unavailable, it falls back to the current
    working directory.

    Returns:
        Path: Absolute path to the project root directory.
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
    """Generate a stable hash for the current project based on its root path."""
    root_path = str(get_project_root().absolute())
    return hashlib.sha256(root_path.encode()).hexdigest()[:16]


# =============================================================================
# Embedding Configuration
# =============================================================================


def resolve_embedding_config() -> tuple[str, str, str | None]:
    """Determine embedding provider, model, and base URL from environment."""
    lm_provider = os.getenv("DSPY_LM_PROVIDER", "openai")
    raw_provider = os.getenv("EMBEDDING_PROVIDER")
    model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    base_url = os.getenv("EMBEDDING_BASE_URL", None)

    if raw_provider:
        return raw_provider, model_name, base_url

    if lm_provider == "openrouter" and os.getenv("OPENROUTER_API_KEY"):
        return "openrouter", model_name, base_url

    return "openai", model_name, base_url


# =============================================================================
# Service Registry (Singleton)
# =============================================================================


class ServiceRegistry:
    """Registry for runtime service status. Singleton pattern."""

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    # Initialize in a local variable first to ensure the singleton
                    # is fully formed before being exposed to other threads.
                    instance = super(ServiceRegistry, cls).__new__(cls)
                    instance._status = {
                        "qdrant_available": None,
                        "openai_key_available": None,
                        "embeddings_ready": None,
                        "learnings_ensured": False,
                        "codebase_ensured": False,
                        "kb_cache": None,
                    }
                    instance.lock = threading.RLock()

                    # Final assignment only after full initialization
                    cls._instance = instance

                    # Ensure logging is configured once at bootstrap with absolute path
                    root = get_project_root()
                    log_path = os.path.join(str(root), "compounding.log")
                    configure_logging(log_path=log_path)
        return cls._instance

    @property
    def status(self):
        with self.lock:
            return self._status.copy()

    def update_status(self, key: str, value: Any):
        """Update a status flag safely."""
        with self.lock:
            self._status[key] = value

    def reset(self):
        """Reset all status flags for testing."""
        with self.lock:
            self._status = {
                "qdrant_available": None,
                "openai_key_available": None,
                "embeddings_ready": None,
                "learnings_ensured": False,
                "codebase_ensured": False,
                "service_ready": False,
            }

    def check_qdrant(self, force: bool = False) -> bool:
        """Check if Qdrant is available. Cached by default."""
        with self.lock:
            if self._status["qdrant_available"] is not None and not force:
                return self._status["qdrant_available"]

            from qdrant_client import QdrantClient

            qdrant_url = settings.qdrant_url
            try:
                client = QdrantClient(url=qdrant_url, timeout=1.0)
                client.get_collections()
                self._status["qdrant_available"] = True
            except Exception:
                from utils.io.logger import logger

                self._status["qdrant_available"] = False
                if not settings.quiet:
                    logger.warning("Qdrant not available. Falling back to keyword search.")
            return self._status["qdrant_available"]

    def get_qdrant_client(self):
        """Returns a Qdrant client if available, or None."""
        with self.lock:
            if not self.check_qdrant():
                return None

            from qdrant_client import QdrantClient

            qdrant_url = settings.qdrant_url
            return QdrantClient(url=qdrant_url, timeout=2.0)

    def check_api_keys(self, force: bool = False) -> bool:
        """Check if required API keys are available. Cached by default."""
        with self.lock:
            if self._status["openai_key_available"] is not None and not force:
                return self._status["openai_key_available"]

        # Check LM provider keys
        lm_provider = settings.dspy_lm_provider
        lm_available = self._check_provider_key(lm_provider)

        # Check Embedding provider keys
        emb_provider, _, _ = resolve_embedding_config()
        emb_available = self._check_provider_key(emb_provider) or emb_provider == "fastembed"

        from utils.io.logger import logger

        if not lm_available:
            logger.warning(f"No API key found for LM provider '{lm_provider}'.")
        if not emb_available:
            logger.warning(f"No API key found for embedding provider '{emb_provider}'.")

        final_available = lm_available and emb_available
        with self.lock:
            self._status["openai_key_available"] = final_available
        return final_available

    def _check_provider_key(self, provider: str) -> bool:
        """Helper to check if a key exists for a given provider."""
        key_map = {
            "openai": "OPENAI_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "ollama": "True",  # Ollama doesn't need a key
        }
        env_var = key_map.get(provider)
        if env_var == "True":
            return True
        return bool(os.getenv(env_var)) if env_var else False

    def get_kb(self, force: bool = False):
        """Get or initialize the KnowledgeBase instance."""
        with self.lock:
            if self._status["kb_cache"] is None or force:
                from utils.knowledge import KnowledgeBase

                self._status["kb_cache"] = KnowledgeBase()
            return self._status["kb_cache"]


class AppConfig:
    """Unified configuration for Compounding Engineering."""

    def __init__(self):
        self.load()

    @staticmethod
    def _parse_int_env(key: str, default: int) -> int:
        """Safely parse an integer environment variable with a fallback."""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            return default

    def load(self):
        """Load settings from environment variables."""
        self.context_window_limit = self._parse_int_env("CONTEXT_WINDOW_LIMIT", 128000)
        self.context_output_reserve = self._parse_int_env("CONTEXT_OUTPUT_RESERVE", 4096)
        self.docs_max_tokens = self._parse_int_env("DOCS_MAX_TOKENS", 32768)
        self.default_max_tokens = self._parse_int_env("DSPY_MAX_TOKENS", 16384)

        self.quiet = bool(os.getenv("COMPOUNDING_QUIET"))
        self.log_path = os.getenv("COMPOUNDING_LOG_PATH", "compounding.log")
        self.log_level = os.getenv("COMPOUNDING_LOG_LEVEL", "INFO")
        self.qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.dspy_lm_provider = os.getenv("DSPY_LM_PROVIDER", "openai")
        self.dspy_lm_model = os.getenv("DSPY_LM_MODEL", "gpt-4.1")


# Global Registry and Config instances
registry = ServiceRegistry()
settings = AppConfig()

def load_configuration(env_file: str | None = None) -> None:
    """
    Load environment variables from multiple configuration sources.

    The configuration files are loaded in priority order, with higher
    priority sources overriding lower priority ones.

    Args:
        env_file (str | None): Optional path to a specific `.env` file.

    Returns:
        None
    """
    sources = []

# =============================================================================
# Environment Loading
# =============================================================================


def load_configuration(env_file: str | None = None) -> None:
    """Load environment variables from multiple sources in priority order."""
    root = get_project_root()
    home = Path.home()
    config_dir = home / ".config" / "compounding"

    # Define sources in priority order
    sources = [
        env_file,
        os.getenv("COMPOUNDING_ENV"),
        root / ".env",
        Path.cwd() / ".env",
        config_dir / ".env",
        home / ".env",
    ]

    seen_paths = set()
    for path_val in sources:
        if not path_val:
            continue

        path = Path(path_val).resolve()
        if path in seen_paths:
            continue

        if path.exists():
            # For simplicity, we override keys if it's the primary (first verified) source
            # or if it's explicitly provided. Otherwise, we just fill in the gaps.
            is_primary = not seen_paths
            load_dotenv(dotenv_path=path, override=is_primary)
            seen_paths.add(path)
            # Refresh settings after loading .env
            settings.load()
        elif path_val == env_file:
            console.print(f"[bold red]Error:[/bold red] Env file '{env_file}' not found.")
            sys.exit(1)


# =============================================================================
# Context & Token Configuration
# =============================================================================

# These are kept as properties that pull from the global 'settings' instance
# to maintain backward compatibility while centralizing loading.


def get_context_window_limit():
    return settings.context_window_limit


def get_context_output_reserve():
    return settings.context_output_reserve


def get_default_max_tokens():
    return settings.default_max_tokens


CONTEXT_WINDOW_LIMIT = settings.context_window_limit
CONTEXT_OUTPUT_RESERVE = settings.context_output_reserve
DEFAULT_MAX_TOKENS = settings.default_max_tokens

TIER_1_FILES = [
    "pyproject.toml",
    "README.md",
    "Dockerfile",
    "docker-compose.yml",
    "requirements.txt",
    "package.json",
]

# Sparse and Fallback Models
SPARSE_MODEL_NAME = "Qdrant/bm25"
DENSE_FALLBACK_MODEL_NAME = "jinaai/jina-embeddings-v2-small-en"


# =============================================================================
# Max Tokens Detection
# =============================================================================


def _get_openrouter_max_tokens(model_name: str) -> int | None:
    """Query OpenRouter API for model's context length and derive max tokens."""
    try:
        import httpx

        api_key = os.getenv("OPENROUTER_API_KEY")
        clean_name = model_name.replace(":free", "")

        resp = httpx.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            timeout=5.0,
        )
        if resp.status_code != 200:
            return None

        for m in resp.json().get("data", []):
            model_id = m.get("id", "")
            if model_id == model_name or model_id == clean_name or clean_name in model_id:
                ctx = m.get("context_length", 128000)
                max_out = min(ctx // 4, 32768)  # 1/4 of context, cap 32k
                console.print(
                    f"[dim]Model {model_name} OpenRouter context={ctx}, "
                    f"using max_tokens={max_out}[/dim]"
                )
                return max_out
        return None
    except Exception:
        return None


def get_model_max_tokens(model_name: str, provider: str = "openai") -> int:
    """
    Auto-detect max output tokens for a model.

    Detection order:
    1. Litellm model registry
    2. OpenRouter API (for openrouter provider)
    3. DSPY_MAX_TOKENS env var fallback
    """
    # Try litellm first
    try:
        import litellm

        lookup_map = {
            "openrouter": f"openrouter/{model_name}",
            "anthropic": f"anthropic/{model_name}",
            "ollama": f"ollama/{model_name}",
        }
        lookup_name = lookup_map.get(provider, model_name)

        model_info = litellm.get_model_info(lookup_name)
        max_output = model_info.get("max_output_tokens") or model_info.get(
            "max_tokens", DEFAULT_MAX_TOKENS
        )
        result = min(max_output, 32768)
        console.print(f"[dim]Model {lookup_name}: max_tokens={max_output}, using {result}[/dim]")
        return result
    except Exception:
        pass

    # OpenRouter API fallback
    if provider == "openrouter":
        or_result = _get_openrouter_max_tokens(model_name)
        if or_result:
            return or_result

    console.print(f"[dim]Model {model_name}: using default max_tokens={DEFAULT_MAX_TOKENS}[/dim]")
    return DEFAULT_MAX_TOKENS


# =============================================================================
# DSPy Configuration
# =============================================================================


def _configure_observability():
    """Initialize Langfuse observability if keys are present."""
    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        return

    # Map LANGFUSE_HOST to expected LANGFUSE_BASE_URL
    if os.getenv("LANGFUSE_HOST") and not os.getenv("LANGFUSE_BASE_URL"):
        os.environ["LANGFUSE_BASE_URL"] = os.environ["LANGFUSE_HOST"]

    try:
        from langfuse import get_client
        from openinference.instrumentation.dspy import DSPyInstrumentor

        # Initialize Langfuse client which registers the global OTEL TracerProvider
        get_client()

        # This automatically handles tracing via OpenTelemetry to Langfuse
        DSPyInstrumentor().instrument()

        if not os.getenv("COMPOUNDING_QUIET"):
            console.print("[dim]Langfuse observability (OpenInference) enabled.[/dim]")
    except ImportError:
        logger.warning("openinference-instrumentation-dspy not found. Tracing disabled.")
    except Exception as e:
        logger.error("Failed to initialize Langfuse tracing", detail=str(e))


def configure_dspy(env_file: str | None = None):
    """Configure DSPy with the appropriate LM provider and settings."""
    load_configuration(env_file)
    _configure_observability()

    registry.check_qdrant()
    registry.check_api_keys()

    provider = settings.dspy_lm_provider
    model_name = settings.dspy_lm_model
    max_tokens = get_model_max_tokens(model_name, provider)

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set.")
        lm = dspy.LM(model=model_name, api_key=api_key, max_tokens=max_tokens)

    elif provider == "anthropic":
        lm = dspy.LM(
            model=f"anthropic/{model_name}",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=max_tokens,
        )

    elif provider == "ollama":
        lm = dspy.LM(model=f"ollama/{model_name}", max_tokens=max_tokens)

    elif provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not set.")
        lm = dspy.LM(
            model=f"openai/{model_name}",
            api_key=api_key,
            api_base="https://openrouter.ai/api/v1",
            max_tokens=max_tokens,
        )

    else:
        raise ValueError(f"Unsupported provider: {provider}")

    dspy.settings.configure(lm=lm)
