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
from typing import Any

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
    """Determine embedding provider, model, and base URL from centralized settings."""
    # Priority auto-override for OpenRouter
    if (
        settings.dspy_lm_provider == "openrouter"
        and os.getenv("OPENROUTER_API_KEY")
        and not os.getenv("EMBEDDING_PROVIDER")
    ):
        return "openrouter", settings.embedding_model, settings.embedding_base_url

    return (
        settings.embedding_provider,
        settings.embedding_model,
        settings.embedding_base_url,
    )


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

        # Embedding Settings
        self.embedding_provider = os.getenv("EMBEDDING_PROVIDER", "openai")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.embedding_base_url = os.getenv("EMBEDDING_BASE_URL")

        # Smart Defaults for Base URLs
        if not self.embedding_base_url:
            if self.embedding_provider == "openrouter":
                self.embedding_base_url = "https://openrouter.ai/api/v1"
            elif self.embedding_provider == "openai":
                self.embedding_base_url = "https://api.openai.com/v1"
        self.sparse_model_name = os.getenv("SPARSE_MODEL_NAME", "Qdrant/bm25")
        self.dense_fallback_model_name = os.getenv(
            "DENSE_FALLBACK_MODEL_NAME", "jinaai/jina-embeddings-v2-small-en"
        )

        # Knowledge Base Settings
        self.knowledge_dir_name = os.getenv("KNOWLEDGE_DIR", ".knowledge")
        self.kb_sync_batch_size = self._parse_int_env("KB_SYNC_BATCH_SIZE", 50)
        self.kb_sanitize_limit = self._parse_int_env("KB_SANITIZE_LIMIT", 30000)
        self.kb_compress_ratio = float(os.getenv("KB_COMPRESS_RATIO", "0.5"))

        # Knowledge Gardening Settings
        self.kg_importance_weight_recency = float(os.getenv("KG_WEIGHT_RECENCY", "0.3"))
        self.kg_importance_weight_impact = float(os.getenv("KG_WEIGHT_IMPACT", "0.5"))
        self.kg_importance_weight_pattern = float(os.getenv("KG_WEIGHT_PATTERN", "0.2"))
        self.kg_retention_days = self._parse_int_env("KG_RETENTION_DAYS", 90)
        self.kg_dedupe_threshold = float(os.getenv("KG_DEDUPE_THRESHOLD", "0.85"))

        # CLI & Agent Settings
        self.cli_max_workers = self._parse_int_env("COMPOUNDING_WORKERS", 3)
        self.agent_max_iters = self._parse_int_env("COMPOUNDING_AGENT_MAX_ITERS", 5)
        self.generator_max_iters = self._parse_int_env("COMPOUNDING_GENERATOR_MAX_ITERS", 10)
        self.executor_max_iters = self._parse_int_env("COMPOUNDING_EXECUTOR_MAX_ITERS", 20)
        self.review_max_workers = self._parse_int_env("COMPOUNDING_REVIEW_WORKERS", 5)

        # Search & Knowledge Limits
        self.search_limit_codebase = self._parse_int_env("COMPOUNDING_SEARCH_LIMIT_CODEBASE", 5)
        self.web_search_limit = self._parse_int_env("COMPOUNDING_WEB_SEARCH_LIMIT", 5)
        self.search_limit_default = self._parse_int_env("COMPOUNDING_SEARCH_LIMIT_DEFAULT", 50)
        self.indexer_file_limit = self._parse_int_env("COMPOUNDING_INDEXER_FILE_LIMIT", 10000)
        self.kb_legacy_search_limit = self._parse_int_env(
            "COMPOUNDING_KB_LEGACY_SEARCH_LIMIT", 1000
        )

        # Timeouts & Third-Party URLs
        self.file_lock_timeout = self._parse_int_env("COMPOUNDING_FILE_LOCK_TIMEOUT", 10)
        self.web_search_timeout = self._parse_int_env("COMPOUNDING_WEB_SEARCH_TIMEOUT", 10)
        self.jina_reader_url = os.getenv("COMPOUNDING_JINA_READER_URL", "https://r.jina.ai/")
        self.documentation_max_pages = self._parse_int_env("COMPOUNDING_DOC_MAX_PAGES", 10)
        self.agent_filter_regex = os.getenv("COMPOUNDING_AGENT_FILTER_REGEX", r"^[a-zA-Z0-9\-_ ]+$")

        # Project Context Settings
        self.project_context_max_file_size = self._parse_int_env(
            "COMPOUNDING_PROJECT_CONTEXT_MAX_FILE_SIZE", 50000
        )
        self.project_key_files = ["README.md", "pyproject.toml", "package.json", "requirements.txt"]

        # Knowledge Base Codification Settings
        self.kb_codify_tags = ["code-review-patterns", "triage-sessions", "work-resolutions"]
        self.codify_context_truncation = 1000
        self.review_finding_truncation = 800
        self.triage_finding_truncation = 500

        # Embedding Metadata
        self.embedding_dimension_map = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
            "mxbai-embed-large:latest": 1024,
            "nomic-embed-text": 768,
            "all-MiniLM-L6-v2": 384,
            "all-MiniLM-L12-v2": 384,
            "jinaai/jina-embeddings-v2-small-en": 512,
            "jinaai/jina-embeddings-v2-base-en": 768,
        }

        # File and Context Settings
        self.tier_1_files = {
            "README.md",
            "ARCHITECTURE.md",
            "CONTRIBUTING.md",
            "TODO.md",
            "AI.md",
            "pyproject.toml",
            "package.json",
            "requirements.txt",
            ".env.example",
            "config.py",
            "cli.py",
            "main.py",
        }

        # Centralized path and exclusion settings
        self.code_extensions = {
            ".py",
            ".js",
            ".ts",
            ".tsx",
            ".jsx",
            ".rb",
            ".go",
            ".rs",
            ".java",
            ".kt",
        }
        self.config_extensions = {".toml", ".yaml", ".yml", ".json"}
        self.skip_dirs = {
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            "dist",
            "build",
            ".tox",
            ".mypy_cache",
            "worktrees",
            ".ruff_cache",
            "qdrant_storage",
            "site",
            "plans",
            "todos",
            ".knowledge",
        }
        self.skip_files = {
            "uv.lock",
            "package-lock.json",
            "yarn.lock",
            "poetry.lock",
            "Gemfile.lock",
        }
        self.log_file = os.getenv("COMPOUNDING_LOG_PATH", "compounding.log")
        self.command_allowlist = set(
            os.getenv("COMMAND_ALLOWLIST", "git,gh,grep,ruff,uv,python").split(",")
        )

    def get_vector_size(self, model_name: str) -> int:
        """Detect vector size for a given model name with heuristics."""
        size = self.embedding_dimension_map.get(model_name)
        if size:
            return size

        # Heuristics
        lower_name = model_name.lower()
        if "nomic" in lower_name:
            return 768
        if "minilm" in lower_name:
            return 384
        if "mxbai" in lower_name:
            return 1024
        if "jina" in lower_name:
            return 512 if "small" in lower_name else 768

        return 1536  # Safe default for OpenAI-style embeddings


# Global Registry and Config instances
registry = ServiceRegistry()
settings = AppConfig()


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
            "max_tokens", settings.default_max_tokens
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

    console.print(
        f"[dim]Model {model_name}: using default max_tokens={settings.default_max_tokens}[/dim]"
    )
    return settings.default_max_tokens


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
