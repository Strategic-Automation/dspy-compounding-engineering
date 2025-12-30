import os
import threading
from typing import Any

from openai import OpenAI

from config import (
    DENSE_FALLBACK_MODEL_NAME,
    SPARSE_MODEL_NAME,
    resolve_embedding_config,
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
        self._configure_vector_size()
        self._init_clients()

    def _resolve_config(self) -> None:
        """Resolve provider, model, and API key from environment."""
        (
            self.embedding_provider,
            self.embedding_model_name,
            self.embedding_base_url,
        ) = resolve_embedding_config()

        # API Key Resolution
        self.embedding_api_key = os.getenv("EMBEDDING_API_KEY")
        if not self.embedding_api_key:
            if self.embedding_provider == "openrouter":
                self.embedding_api_key = os.getenv("OPENROUTER_API_KEY")
            else:
                self.embedding_api_key = os.getenv("OPENAI_API_KEY")

        # Auto-detect fallback if no API key for cloud providers
        is_cloud = self.embedding_provider in ["openai", "openrouter"]
        if is_cloud and not self.embedding_api_key:
            if not os.getenv("COMPOUNDING_QUIET"):
                console.print(
                    f"[yellow]No API key found for {self.embedding_provider}. "
                    "Falling back to FastEmbed (local embeddings).[/yellow]"
                )
            self.embedding_provider = "fastembed"
            self.embedding_model_name = DENSE_FALLBACK_MODEL_NAME

        if self.embedding_provider == "openrouter" and not self.embedding_base_url:
            self.embedding_base_url = "https://openrouter.ai/api/v1"

    def _configure_vector_size(self) -> None:
        """Determine vector size based on model."""
        DIMENSION_MAP = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
            "nomic-embed-text": 768,
            "all-MiniLM-L6-v2": 384,
            "all-MiniLM-L12-v2": 384,
            "jinaai/jina-embeddings-v2-small-en": 512,
            "jinaai/jina-embeddings-v2-base-en": 768,
        }

        # Simplified lookup
        name = self.embedding_model_name
        self.vector_size = DIMENSION_MAP.get(name)

        if not self.vector_size:
            # Fallback heuristics
            if "nomic" in name.lower():
                self.vector_size = 768
            elif "minilm" in name.lower():
                self.vector_size = 384
            else:
                self.vector_size = 1536

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
            # Fallback to Jina small if failed
            if model_name == DENSE_FALLBACK_MODEL_NAME:
                raise
            return self._get_fastembed_model(DENSE_FALLBACK_MODEL_NAME)

    def _get_sparse_model(self) -> Any:
        """Get or initialize a SparseTextEmbedding model from global cache."""
        from fastembed import SparseTextEmbedding

        return self._get_cached_model(
            f"sparse_{SPARSE_MODEL_NAME}", SparseTextEmbedding, SPARSE_MODEL_NAME
        )

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
