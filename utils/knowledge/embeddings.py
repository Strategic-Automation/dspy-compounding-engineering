import os
from typing import List

from openai import OpenAI
from rich.console import Console

from config import resolve_embedding_config

console = Console()


class EmbeddingProvider:
    """
    Manages embedding generation using OpenAI-compatible APIs or local FastEmbed.
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
            self.embedding_model_name = "jinaai/jina-embeddings-v2-small-en"

        if self.embedding_provider == "openrouter" and not self.embedding_base_url:
            self.embedding_base_url = "https://openrouter.ai/api/v1"

    def _configure_vector_size(self) -> None:
        """Determine vector size based on model."""
        # Standard model dimension mapping
        DIMENSION_MAP = {
            # OpenAI Models
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
            # Nomic Models
            "nomic-embed-text": 768,
            # MiniLM Models
            "all-MiniLM-L6-v2": 384,
            "all-MiniLM-L12-v2": 384,
            # Jina Models
            "jinaai/jina-embeddings-v2-small-en": 512,
            "jinaai/jina-embeddings-v2-base-en": 768,
        }

        if self.embedding_provider == "fastembed":
            self.vector_size = DIMENSION_MAP.get(self.embedding_model_name, 512)
        else:
            # Exact match first
            if self.embedding_model_name in DIMENSION_MAP:
                self.vector_size = DIMENSION_MAP[self.embedding_model_name]
            # Heuristics
            elif "nomic" in self.embedding_model_name.lower():
                self.vector_size = 768
            elif "minilm" in self.embedding_model_name.lower():
                self.vector_size = 384
            else:
                if not os.getenv("COMPOUNDING_QUIET"):
                    console.print(
                        f"[yellow]Unknown embedding model '{self.embedding_model_name}'. "
                        "Defaulting to 1536 dimensions.[/yellow]"
                    )
                self.vector_size = 1536

        if os.getenv("EMBEDDING_DIMENSION"):
            self.vector_size = int(os.getenv("EMBEDDING_DIMENSION"))

    def _init_clients(self) -> None:
        """Initialize remote API or local model clients."""
        if self.embedding_provider == "fastembed":
            from fastembed import TextEmbedding

            try:
                self.fast_model = TextEmbedding(model_name=self.embedding_model_name)
            except Exception as e:
                console.print(f"[red]Failed to load FastEmbed model: {e}[/red]")
                # Fallback to a safe default if specific model fails
                self.fast_model = TextEmbedding(model_name="jinaai/jina-embeddings-v2-small-en")
                self.vector_size = 512
            self.client = None
        else:
            self.client = OpenAI(api_key=self.embedding_api_key, base_url=self.embedding_base_url)

    def get_embedding(self, text: str) -> List[float]:
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
            console.print(f"[red]Failed to generate embedding: {e}[/red]")
            raise e

    def get_sparse_embedding(self, text: str):
        """Generate sparse embedding for text using fastembed."""
        if not hasattr(self, "sparse_model"):
            from fastembed import SparseTextEmbedding

            self.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")

        try:
            embedding = list(self.sparse_model.embed(text))[0]
            return {"indices": embedding.indices.tolist(), "values": embedding.values.tolist()}
        except Exception as e:
            console.print(f"[red]Failed to generate sparse embedding: {e}[/red]")
            return {"indices": [], "values": []}
