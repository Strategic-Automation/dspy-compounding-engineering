"""
Knowledge Base module for Compounding Engineering.

This module manages the persistent storage and retrieval of learnings,
enabling the system to improve over time by accessing past insights.

Architecture:
- KnowledgeBaseStorage (repository.py): Pure SQLite persistence, PII scrubbing, local search
- KnowledgeBase (core.py): Orchestrates storage + vector indexing + docs + embeddings
"""

import os
import uuid
import xml.sax.saxutils as xml_safe
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from urllib.parse import urlparse

from filelock import FileLock

if TYPE_CHECKING:
    from qdrant_client import QdrantClient

try:
    from qdrant_client.models import (
        FieldCondition,
        Filter,
        Fusion,
        FusionQuery,
        MatchValue,
        PointStruct,
        Prefetch,
    )
except ImportError:
    pass  # Handled by vector_db_available check

from config import settings

from ..io.logger import console, logger
from ..security.scrubber import scrubber
from .docs import KnowledgeDocumentation
from .embeddings import EmbeddingProvider
from .indexer import CodebaseIndexer
from .repository import KnowledgeBaseStorage
from .utils import CollectionManagerMixin


class KnowledgeBase(CollectionManagerMixin):
    """
    Manages a collection of learnings stored in a local SQLite database and indexed in Qdrant.

    Delegates all SQLite persistence to KnowledgeBaseStorage (repository pattern).
    """

    MAX_COLLECTION_NAME_LENGTH = 60

    def __init__(
        self, knowledge_dir: Optional[str] = None, qdrant_client: Optional["QdrantClient"] = None
    ):
        from config import get_project_hash, get_project_root, registry

        if knowledge_dir is None:
            knowledge_dir = os.path.join(str(get_project_root()), settings.knowledge_dir_name)

        self.knowledge_dir = os.path.abspath(knowledge_dir)
        self._ensure_knowledge_dir()

        # Delegate SQLite storage to repository
        self._storage = KnowledgeBaseStorage(self.knowledge_dir)

        backups_dir = os.path.join(self.knowledge_dir, "backups")
        os.makedirs(backups_dir, exist_ok=True)
        self.lock_path = os.path.join(self.knowledge_dir, "kb.lock")

        # Generate unique collection names based on project root hash
        project_hash = get_project_hash()
        self.collection_name = f"learnings_{project_hash}"

        # Docs Service
        self.docs_service = KnowledgeDocumentation(self.knowledge_dir)

        self.client = qdrant_client or registry.get_qdrant_client()
        self.vector_db_available = self.client is not None

        logger.debug(f"KnowledgeBase initialized (Vector DB Available: {self.vector_db_available})")

        # Initialize Embedding Provider
        self.embedding_provider = EmbeddingProvider()

        # Use a unique collection name for this codebase
        codebase_collection_name = f"codebase_{project_hash}"
        self.codebase_indexer = CodebaseIndexer(
            self.client, self.embedding_provider, collection_name=codebase_collection_name
        )

        # Ensure 'learnings' collection exists (if DB available)
        self._ensure_collection()

        # Sync if empty in Vector DB but present in SQL
        try:
            if self.vector_db_available and self.client.count(self.collection_name).count == 0:
                all_learnings = self.get_all_learnings()
                if all_learnings:
                    console.print("[yellow]Vector store empty. Syncing from SQLite...[/yellow]")
                    self._sync_to_qdrant(all_learnings)
        except Exception as e:
            logger.debug(f"Could not check collection count: {e}")

        logger.info("KnowledgeBase service is ready", to_cli=True)

    def _ensure_knowledge_dir(self):
        """Ensure the knowledge directory exists."""
        if not os.path.exists(self.knowledge_dir):
            os.makedirs(self.knowledge_dir)

    def get_lock(self, lock_type: str = "kb") -> "FileLock":
        """Returns a FileLock instance for the specified type ('kb' or 'codify')."""
        path = self.get_codify_lock_path() if lock_type == "codify" else self.lock_path
        return FileLock(path)

    def get_codify_lock_path(self) -> str:
        """Returns the path to the codify-specific lock file."""
        return os.path.join(self.knowledge_dir, "codify.lock")

    def _ensure_collection(self, force_recreate: bool = False):
        """Ensure the Qdrant collection exists."""
        self.vector_db_available = self._safe_ensure_collection(
            collection_name=self.collection_name,
            vector_size=self.embedding_provider.vector_size,
            force_recreate=force_recreate,
            enable_sparse=True,
            registry_flag="learnings_ensured",
        )

    # -- Delegated Storage Methods --

    def save_learning(
        self, learning: Dict[str, Any], silent: bool = False, update_docs: bool = True
    ) -> str:
        """Add a new learning item to the knowledge base (SQLite + Qdrant)."""
        lock = self.get_lock()
        try:
            with lock:
                learning_id = self._storage.insert_learning(learning)
                self._index_learning(learning)

                if not silent:
                    logger.success(f"Learning saved to DB ({learning_id})")

                if update_docs:
                    self.docs_service.update_ai_md(self.get_all_learnings(), silent=silent)

            return learning_id
        except Exception as e:
            if not silent:
                console.print(f"[red]Failed to save learning: {e}[/red]")
            raise

    def get_all_learnings(self) -> List[Dict[str, Any]]:
        """Retrieve all learnings from SQLite via repository."""
        return self._storage.get_all_learnings()

    def retrieve_relevant(
        self, query: str = "", tags: List[str] = None, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant learnings using Hybrid Search (Qdrant) with Local SQLite fallback.
        """
        if not query and not tags:
            return self.get_all_learnings()[:limit]

        try:
            if not self.vector_db_available:
                raise ConnectionError("Qdrant not available")

            query_filter = None
            if tags:
                should_conditions = []
                for tag in tags:
                    should_conditions.append(
                        FieldCondition(key="tags", match=MatchValue(value=tag))
                    )
                    should_conditions.append(
                        FieldCondition(key="category", match=MatchValue(value=tag))
                    )
                query_filter = Filter(should=should_conditions)

            dense_vector = self.embedding_provider.get_embedding(query)
            sparse_vector = self.embedding_provider.get_sparse_embedding(query)

            search_result = self.client.query_points(
                collection_name=self.collection_name,
                prefetch=[
                    Prefetch(
                        query=dense_vector,
                        using=None,
                        limit=limit * 2,
                        filter=query_filter,
                    ),
                    Prefetch(
                        query=sparse_vector,
                        using="text-sparse",
                        limit=limit * 2,
                        filter=query_filter,
                    ),
                ],
                query=FusionQuery(fusion=Fusion.RRF),
                limit=limit,
            ).points

            results = [hit.payload for hit in search_result]
            return results

        except Exception as e:
            logger.warning(
                f"Hybrid search failed (query='{query[:80]}...', tags={tags}): {e}. "
                "Falling back to local SQLite search.",
            )
            return self._storage.search_local(query, tags, limit)

    # -- Vector & Embedding Methods --

    def _sync_to_qdrant(self, learnings: List[Dict[str, Any]], batch_size: Optional[int] = None):
        """Sync a list of learnings to Qdrant."""
        if batch_size is None:
            batch_size = settings.kb_sync_batch_size
        if not self.vector_db_available:
            return

        total_items = len(learnings)
        synced_count = 0

        for i in range(0, total_items, batch_size):
            batch = learnings[i : i + batch_size]
            points = []

            for learning in batch:
                try:
                    text_to_embed = self._prepare_embedding_text(learning)
                    vector = self.embedding_provider.get_embedding(text_to_embed)
                    sparse_vector = self.embedding_provider.get_sparse_embedding(text_to_embed)

                    learning_id = learning.get("id") or str(uuid.uuid4())
                    point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(learning_id)))

                    points.append(
                        PointStruct(
                            id=point_id,
                            vector={"": vector, "text-sparse": sparse_vector},
                            payload=learning,
                        )
                    )
                except Exception as e:
                    console.print(
                        f"[red]Failed to prepare learning {learning.get('id')}: {e}[/red]"
                    )

            if points:
                try:
                    self.client.upsert(collection_name=self.collection_name, points=points)
                    synced_count += len(points)
                    console.print(f"[dim]Synced batch: {synced_count}/{total_items}[/dim]")
                except Exception as e:
                    console.print(f"[red]Failed to upsert batch: {e}[/red]")

        console.print(f"[green]Synced {synced_count} learnings to Qdrant.[/green]")

    def _prepare_embedding_text(self, learning: Dict[str, Any]) -> str:
        """Helper to create text for embedding."""
        text_parts = [str(learning.get("title", "")), str(learning.get("description", ""))]

        content = learning.get("content", "")
        if isinstance(content, dict):
            text_parts.append(str(content.get("summary", "")))
        else:
            text_parts.append(str(content))

        if learning.get("codified_improvements"):
            for imp in learning["codified_improvements"]:
                text_parts.append(f"{imp.get('title', '')} {imp.get('description', '')}")

        return " ".join([self._sanitize_text(p) for p in text_parts])

    def _index_learning(self, learning: Dict[str, Any]):
        """Index a single learning into Qdrant."""
        if not self.vector_db_available:
            return

        try:
            text_to_embed = self._prepare_embedding_text(learning)
            vector = self.embedding_provider.get_embedding(text_to_embed)
            sparse_vector = self.embedding_provider.get_sparse_embedding(text_to_embed)

            learning_id = learning.get("id")
            if not learning_id:
                learning_id = str(uuid.uuid4())

            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(learning_id)))

            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=point_id,
                        vector={"": vector, "text-sparse": sparse_vector},
                        payload=learning,
                    )
                ],
            )
        except Exception as e:
            logger.error(f"Error indexing learning {learning.get('id', 'unknown')}: {e}")

    def _is_valid_url(self, url: str) -> bool:
        """Validate Qdrant URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in ["http", "https"]
        except Exception:
            return False

    def _sanitize_text(self, text: str) -> str:
        """Sanitize and scrub text for embedding generation."""
        if not text:
            return ""
        text = scrubber.scrub(text)
        text = "".join(ch for ch in text if ch == "\n" or ch == "\r" or ch == "\t" or ch >= " ")
        return text[: settings.kb_sanitize_limit]

    def get_context_string(self, query: str = "", tags: List[str] = None) -> str:
        """
        Get a formatted string of relevant learnings for context injection.
        Wraps content in XML tags to prevent prompt injection.
        """
        learnings = self.retrieve_relevant(query, tags)
        if not learnings:
            return "No relevant past learnings found."

        context = "## Relevant Past Learnings\n\n"
        for learning in learnings:
            title = xml_safe.escape(str(learning.get("title", "Untitled")))
            cat = xml_safe.escape(str(learning.get("category", "General")))

            content = learning.get("content", "")
            if isinstance(content, dict):
                content_str = xml_safe.escape(str(content.get("summary", "")))
            else:
                content_str = xml_safe.escape(str(content))

            context += "<context_item>\n"
            context += f"  <title>{title}</title>\n"
            context += f"  <category>{cat}</category>\n"
            context += f"  <content>\n{content_str}\n  </content>\n"
            context += "</context_item>\n\n"

        return context

    def get_compounding_ai_prompt(self, limit: int = 20) -> str:
        """Get a formatted prompt suffix for auto-injection into ALL AI interactions."""
        all_learnings = self.get_all_learnings()

        if not all_learnings:
            return ""

        sorted_learnings = sorted(
            all_learnings, key=lambda x: x.get("created_at", ""), reverse=True
        )[:limit]

        prompt = "\n\n---\n\n## System Learnings (Auto-Injected)\n\n"
        prompt += "The following patterns and learnings have been codified from past work. "
        prompt += "Apply these automatically to the current task:\n\n"

        for learning in sorted_learnings:
            title = xml_safe.escape(str(learning.get("title", "Untitled")))
            prompt += "<system_learning>\n"
            prompt += f"  <title>{title}</title>\n"
            if learning.get("codified_improvements"):
                prompt += "  <improvements>\n"
                for imp in learning["codified_improvements"]:
                    desc = xml_safe.escape(str(imp.get("description", "")))
                    prompt += f"    <item>{desc}</item>\n"
                prompt += "  </improvements>\n"
            prompt += "</system_learning>\n"

        return prompt

    def search_similar_patterns(
        self, description: str, threshold: float = 0.3, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar patterns using vector embeddings."""
        learnings = self.retrieve_relevant(query=description, limit=limit)
        results = []
        for learning in learnings:
            results.append({"learning": learning, "similarity": 0.9})
        return results

    def index_codebase(self, root_dir: str = ".", force_recreate: bool = False) -> None:
        """Delegate to CodebaseIndexer."""
        self.codebase_indexer.index_codebase(root_dir, force_recreate=force_recreate)

    def search_codebase(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Delegate to CodebaseIndexer."""
        return self.codebase_indexer.search_codebase(query, limit)

    def compress_ai_md(self, ratio: float = 0.5, dry_run: bool = False) -> None:
        """Compress the AI.md knowledge base."""
        self.docs_service.compress_ai_md(ratio=ratio, dry_run=dry_run)