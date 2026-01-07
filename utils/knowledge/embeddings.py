import os
import threading
from typing import Any

from openai import OpenAI

from config import (
    resolve_embedding_config,
    settings,
)

from ..io.logger import console, logger

# Global Model Registry (Thread-Safe Singleton Pattern)
_MODEL_CACHE: dict[str, Any] = {}
_CACHE_LOCK = threading.Lock()
_PER_MODEL_LOCKS: dict[str, threading.Lock] = {}


def _get_model_lock(key: str) -> threading.Lock:
    """Get or create a granular lock for a specific model key."""
    with _CACHE_LOCK:
        if key not in _PER_MODEL_LOCKS:
            _PER_MODEL_LOCKS[key] = threading.Lock()
        return _PER_MODEL_LOCKS[key]


class EmbeddingProvider:
    """
    Manages embedding generation using OpenAI-compatible APIs or local FastEmbed.
    Implements thread-safe model caching to prevent redundant loads in parallel agents.
    """

    def __init__(self):
        self._resolve_config()
        self._init_clients()

    def _resolve_config(self) -> None:
        """Resolve provider, model, and API key from environment."""
        (
            self.embedding_provider,
            self.embedding_model_name,
            self.embedding_base_url,
        ) = resolve_embedding_config()

        # API Key Resolution
        primary_key = (
            "OPENROUTER_API_KEY" if self.embedding_provider == "openrouter" else "OPENAI_API_KEY"
        )
        self.embedding_api_key = os.getenv("EMBEDDING_API_KEY") or os.getenv(primary_key)

        # Auto-detect fallback if no API key for cloud providers
        if self.embedding_provider in ["openai", "openrouter"] and not self.embedding_api_key:
            if not settings.quiet:
                console.print(
                    f"[yellow]No API key found for {self.embedding_provider}. "
                    "Falling back to FastEmbed (local embeddings).[/yellow]"
                )
            self.embedding_provider = "fastembed"
            self.embedding_model_name = settings.dense_fallback_model_name

        # Use centralized vector size detection
        self.vector_size = settings.get_vector_size(self.embedding_model_name)

    def _get_cached_model(self, key: str, loader_func: Any, model_name: str) -> Any:
        """Generic thread-safe model caching helper with granular locking."""
        # Double-checked locking part 1: Quick check without lock
        if key in _MODEL_CACHE:
            logger.debug(f"Retrieved model {key} from cache")
            return _MODEL_CACHE[key]

        # Acquire granular lock for this specific model
        model_lock = _get_model_lock(key)
        with model_lock:
            # Double-checked locking part 2: check again inside lock
            if key in _MODEL_CACHE:
                return _MODEL_CACHE[key]

            logger.info(f"Loading model: {model_name}...", to_cli=True)
            try:
                model = loader_func(model_name=model_name)
                _MODEL_CACHE[key] = model
                logger.success(f"Model {model_name} loaded successfully")
                return model
            except Exception as e:
                logger.error(f"Failed to load model {model_name}", detail=str(e))
                raise e

    def _get_fastembed_model(self, model_name: str) -> Any:
        """Get or initialize a FastEmbed model from global cache."""
        from fastembed import TextEmbedding

        try:
            return self._get_cached_model(f"dense_{model_name}", TextEmbedding, model_name)
        except Exception:
            # Fallback to current dense fallback if failed
            if model_name == settings.dense_fallback_model_name:
                raise
            return self._get_fastembed_model(settings.dense_fallback_model_name)

    def _get_sparse_model(self) -> Any:
        """Get or initialize a SparseTextEmbedding model from global cache."""
        from fastembed import SparseTextEmbedding

        model_name = settings.sparse_model_name
        return self._get_cached_model(f"sparse_{model_name}", SparseTextEmbedding, model_name)

    def _init_clients(self) -> None:
        """Initialize remote API or local model clients."""
        if self.embedding_provider == "fastembed":
            self.fast_model = self._get_fastembed_model(self.embedding_model_name)
            self.client = None
        else:
            self.client = OpenAI(api_key=self.embedding_api_key, base_url=self.embedding_base_url)

    def get_embedding(self, text: str) -> list[float]:
        """Generate embedding for text using configured provider."""
        try:
            if self.embedding_provider == "fastembed":
                return list(self.fast_model.embed(text))[0].tolist()
            else:
                text = text.replace("\n", " ")
                response = self.client.embeddings.create(
                    input=[text], model=self.embedding_model_name
                )
                return response.data[0].embedding
        except Exception as e:
            logger.error("Failed to generate embedding", detail=str(e))
            raise e

    def get_sparse_embedding(self, text: str):
        """Generate sparse embedding for text using fastembed."""
        try:
            model = self._get_sparse_model()
            embedding = list(model.embed(text))[0]
            return {
                "indices": embedding.indices.tolist(),
                "values": embedding.values.tolist(),
            }
        except Exception as e:
            logger.error("Failed to generate sparse embedding", detail=str(e))
            return {"indices": [], "values": []}
