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

import dspy
from dotenv import load_dotenv
from rich.console import Console

console = Console()

# =============================================================================
# Project Utilities
# =============================================================================


def get_project_root() -> Path:
    """Get the project root directory, preferably the Git root."""
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
        """Check if Qdrant is available. Cached by default."""
        if self._status["qdrant_available"] is not None and not force:
            return self._status["qdrant_available"]

        from qdrant_client import QdrantClient

        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        try:
            client = QdrantClient(url=qdrant_url, timeout=1.0)
            client.get_collections()
            self._status["qdrant_available"] = True
        except Exception:
            from utils.io.logger import logger

            self._status["qdrant_available"] = False
            if not os.getenv("COMPOUNDING_QUIET"):
                logger.warning("Qdrant not available. Falling back to keyword search.")
        return self._status["qdrant_available"]

    def check_api_keys(self, force: bool = False) -> bool:  # noqa: C901
        """Check if required API keys are available. Cached by default."""
        if self._status["openai_key_available"] is not None and not force:
            return self._status["openai_key_available"]

        provider = os.getenv("DSPY_LM_PROVIDER", "openai")
        emb_provider = os.getenv("EMBEDDING_PROVIDER")

        if not emb_provider:
            if provider == "openrouter" and os.getenv("OPENROUTER_API_KEY"):
                emb_provider = "openrouter"
            elif provider == "openai" and os.getenv("OPENAI_API_KEY"):
                emb_provider = "openai"
            else:
                emb_provider = "openai"

        available = False
        if provider == "openai":
            available = bool(os.getenv("OPENAI_API_KEY"))
        elif provider == "openrouter":
            available = bool(os.getenv("OPENROUTER_API_KEY"))
        elif provider == "anthropic":
            available = bool(os.getenv("ANTHROPIC_API_KEY"))
        elif provider == "ollama":
            available = True

        emb_available = True
        if emb_provider == "openai":
            emb_available = bool(os.getenv("OPENAI_API_KEY"))
        elif emb_provider == "openrouter":
            emb_available = bool(os.getenv("OPENROUTER_API_KEY"))

        from utils.io.logger import logger

        if not available:
            logger.warning(f"No API key found for LM provider '{provider}'.")
        if not emb_available and emb_provider != "fastembed":
            logger.warning(f"No API key found for embedding provider '{emb_provider}'.")

        final_available = available and (emb_available or emb_provider == "fastembed")
        self._status["openai_key_available"] = final_available
        return final_available


registry = ServiceRegistry()


# =============================================================================
# Environment Loading
# =============================================================================


def load_configuration(env_file: str | None = None) -> None:
    """Load environment variables from multiple sources in priority order."""
    sources = []

    # 1. Explicitly provided file
    if env_file and os.path.exists(env_file):
        sources.append((env_file, True))
    elif env_file:
        console.print(f"[bold red]Error:[/bold red] Env file '{env_file}' not found.")
        sys.exit(1)

    # 2. COMPOUNDING_ENV pointer
    env_var_path = os.getenv("COMPOUNDING_ENV")
    if env_var_path and os.path.exists(env_var_path):
        sources.append((env_var_path, True))

    # 3. Project root .env
    root = get_project_root()
    root_env = root / ".env"
    if root_env.exists():
        sources.append((str(root_env), True))

    # 4. CWD .env (if different)
    cwd_env = Path(os.getcwd()) / ".env"
    if cwd_env.exists() and cwd_env != root_env:
        sources.append((str(cwd_env), True))

    # 5. Global config
    tool_env = Path.home() / ".config" / "compounding" / ".env"
    if tool_env.exists():
        sources.append((str(tool_env), False))

    # 6. Home fallback
    home_env = Path.home() / ".env"
    if home_env.exists() and home_env != tool_env:
        sources.append((str(home_env), False))

    if not sources:
        return

    primary_path, _ = sources[0]
    load_dotenv(dotenv_path=primary_path, override=True)

    for path, _ in sources[1:]:
        load_dotenv(dotenv_path=path, override=False)


# =============================================================================
# Context & Token Configuration
# =============================================================================

CONTEXT_WINDOW_LIMIT = int(os.getenv("CONTEXT_WINDOW_LIMIT", "128000"))
CONTEXT_OUTPUT_RESERVE = int(os.getenv("CONTEXT_OUTPUT_RESERVE", "4096"))
DEFAULT_MAX_TOKENS = int(os.getenv("DSPY_MAX_TOKENS", "16384"))

TIER_1_FILES = [
    "pyproject.toml",
    "README.md",
    "Dockerfile",
    "docker-compose.yml",
    "requirements.txt",
    "package.json",
]


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


def configure_dspy(env_file: str | None = None):
    """Configure DSPy with the appropriate LM provider and settings."""
    load_configuration(env_file)
    registry.check_qdrant()
    registry.check_api_keys()

    provider = os.getenv("DSPY_LM_PROVIDER", "openai")
    model_name = os.getenv("DSPY_LM_MODEL", "gpt-4.1")
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
