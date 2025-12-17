import os
from typing import List

from openai import OpenAI
from rich.console import Console

console = Console()


class EmbeddingProvider:
    """
    Manages embedding generation using OpenAI-compatible APIs.
    """

    def __init__(self):
        # Initialize Embedding Configuration
        self.embedding_provider = os.getenv("EMBEDDING_PROVIDER", "openai")
        self.embedding_base_url = os.getenv("EMBEDDING_BASE_URL", None)
        self.embedding_api_key = os.getenv("EMBEDDING_API_KEY", os.getenv("OPENAI_API_KEY"))
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

        # Auto-detect fallback if no API key
        if self.embedding_provider == "openai" and not self.embedding_api_key:
            console.print("[yellow]No OpenAI API Key found. Falling back to FastEmbed.[/yellow]")
            self.embedding_provider = "fastembed"
            self.embedding_model_name = "jinaai/jina-embeddings-v2-small-en"

        # Configure Vector Size based on model (heuristic)
        if self.embedding_provider == "fastembed":
            self.vector_size = 512  # Default for Jina v2 small
        elif "nomic" in self.embedding_model_name:
            self.vector_size = 768
        elif "minilm" in self.embedding_model_name:
            self.vector_size = 384
        else:
            self.vector_size = 1536  # Default for OpenAI models

        # Allow override
        if os.getenv("EMBEDDING_DIMENSION"):
            self.vector_size = int(os.getenv("EMBEDDING_DIMENSION"))

        # Initialize Clients
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
            # Initialize OpenAI Client for Embeddings
            self.client = OpenAI(api_key=self.embedding_api_key, base_url=self.embedding_base_url)

    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using configured provider."""
        try:
            if self.embedding_provider == "fastembed":
                # fastembed returns generator
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

            # Use Qdrant's BM25 as default - lightweight and adequate for keyword matching
            self.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")

        try:
            # fastembed generator yields results, we take the first one
            embedding = list(self.sparse_model.embed(text))[0]
            # Convert to Qdrant SparseVector format (dict with indices and values)
            # fastembed returns a SparseEmbedding object which has .indices and .values
            return {"indices": embedding.indices.tolist(), "values": embedding.values.tolist()}
        except Exception as e:
            console.print(f"[red]Failed to generate sparse embedding: {e}[/red]")
            # Fallback to empty
            return {"indices": [], "values": []}
