"""
Shared utilities for vector database collection management.
"""

from typing import Optional, Tuple

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, SparseIndexParams, SparseVectorParams, VectorParams
from rich.console import Console

console = Console()


class CollectionManagerMixin:
    """
    Mixin to provide shared collection management logic for vector base classes.
    """

    client: QdrantClient
    vector_db_available: bool

    def _safe_ensure_collection(
        self,
        collection_name: str,
        vector_size: int,
        force_recreate: bool = False,
        enable_sparse: bool = False,
        registry_flag: Optional[str] = None,
    ) -> bool:
        """
        Shared logic to ensure a Qdrant collection exists and has correct dimensions.
        """
        if not self.vector_db_available and not force_recreate:
            return False

        if self.client is None:
            return False

        from config import registry

        # 1. Check status (Narrow lock scope)
        with registry.lock:
            if registry_flag and registry.status.get(registry_flag) and not force_recreate:
                return True

        try:
            should_recreate = False
            # Network I/O happens outside the lock
            if self.client.collection_exists(collection_name):
                should_recreate, current_size = self._check_dimension_mismatch(
                    collection_name, vector_size, force_recreate
                )
                if current_size is None and not should_recreate:
                    # Invalid state but no force, we can't proceed with vector ops
                    self.vector_db_available = False
                    return False
                if should_recreate:
                    self.client.delete_collection(collection_name)

            if should_recreate or not self.client.collection_exists(collection_name):
                self._create_collection(collection_name, vector_size, enable_sparse)

            # 2. Update status (Narrow lock scope)
            if registry_flag:
                registry.update_status(registry_flag, True)
            return True
        except Exception as e:
            console.print(f"[red]Failed to ensure Qdrant collection '{collection_name}': {e}[/red]")
            return False

    def _check_dimension_mismatch(
        self, collection_name: str, expected_size: int, force_recreate: bool
    ) -> Tuple[bool, Optional[int]]:
        """Check if existing collection matches expected dimensions."""
        collection_info = self.client.get_collection(collection_name)
        vectors_config = collection_info.config.params.vectors

        # Handle both single vector and multiple vector configurations
        existing_size = None
        if isinstance(vectors_config, dict):
            if "" in vectors_config:
                existing_size = vectors_config[""].size
            elif len(vectors_config) == 1:
                existing_size = list(vectors_config.values())[0].size
        elif hasattr(vectors_config, "size"):
            existing_size = vectors_config.size

        if force_recreate:
            console.print(f"[yellow]Forcing recreation of '{collection_name}'...[/yellow]")
            return True, existing_size

        if existing_size is not None and existing_size != expected_size:
            error_msg = (
                f"Vector dimension mismatch for '{collection_name}' "
                f"(Expected {expected_size}, Found {existing_size}). "
                "Automatic recreation disabled to prevent data loss. "
                "Please run with --force-recreate if you intend to re-index."
            )
            console.print(f"[bold red]CRITICAL: {error_msg}[/bold red]")
            return False, None  # Flag as error

        return False, existing_size

    def _create_collection(self, collection_name: str, vector_size: int, enable_sparse: bool):
        """Create a new collection with specified config."""
        try:
            params = {
                "collection_name": collection_name,
                "vectors_config": VectorParams(size=vector_size, distance=Distance.COSINE),
            }
            if enable_sparse:
                params["sparse_vectors_config"] = {
                    "text-sparse": SparseVectorParams(index=SparseIndexParams(on_disk=False))
                }

            self.client.create_collection(**params)
        except Exception as e:
            # Ignore 409 Conflict - another thread might have created it
            if "409" not in str(e) and "already exists" not in str(e).lower():
                raise e
