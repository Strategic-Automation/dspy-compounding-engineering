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

        # Configure Vector Size based on model (heuristic)
        if "nomic" in self.embedding_model_name:
            self.vector_size = 768
        elif "minilm" in self.embedding_model_name:
            self.vector_size = 384
        else:
            self.vector_size = 1536  # Default for OpenAI models

        # Allow override
        if os.getenv("EMBEDDING_DIMENSION"):
            self.vector_size = int(os.getenv("EMBEDDING_DIMENSION"))

        # Initialize OpenAI Client for Embeddings
        self.client = OpenAI(api_key=self.embedding_api_key, base_url=self.embedding_base_url)

    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI-compatible client."""
        try:
            text = text.replace("\n", " ")
            response = self.client.embeddings.create(input=[text], model=self.embedding_model_name)
            return response.data[0].embedding
        except Exception as e:
            console.print(f"[red]Failed to generate embedding: {e}[/red]")
            raise e
