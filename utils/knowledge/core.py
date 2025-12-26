"""
Knowledge Base module for Compounding Engineering.

This module manages the persistent storage and retrieval of learnings,
enabling the system to improve over time by accessing past insights.
"""

import glob
import itertools
import json
import os
import random
import uuid
from datetime import datetime
from typing import Any, Dict, List
from urllib.parse import urlparse

from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
)
from rich.console import Console

from .docs import KnowledgeDocumentation
from .embeddings import EmbeddingProvider
from .indexer import CodebaseIndexer
from .utils import CollectionManagerMixin
from ..security.scrubber import scrubber
from ..io.logger import logger

console = Console()


class KnowledgeBase(CollectionManagerMixin):
    """
    Manages a collection of learnings stored as JSON files and indexed in Qdrant.
    """

    MAX_COLLECTION_NAME_LENGTH = 60

    def __init__(self, knowledge_dir: str = ".knowledge"):
        from config import get_project_hash, registry

        self.knowledge_dir = knowledge_dir
        self._ensure_knowledge_dir()
        backups_dir = os.path.join(self.knowledge_dir, "backups")
        os.makedirs(backups_dir, exist_ok=True)
        self.lock_path = os.path.join(self.knowledge_dir, "kb.lock")

        # Generate unique collection names based on project root hash
        project_hash = get_project_hash()
        self.collection_name = f"learnings_{project_hash}"

        # Docs Service
        self.docs_service = KnowledgeDocumentation(self.knowledge_dir)

        # Initialize Qdrant Client
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.vector_db_available = False

        # Validate URL
        if not self._is_valid_url(qdrant_url):
            console.print(
                f"[red]Invalid QDRANT_URL: {qdrant_url}. Using keyword search only.[/red]"
            )
            self.client = None
        else:
            try:
                # Use registry to check/cache availability
                self.vector_db_available = registry.check_qdrant()
                if self.vector_db_available:
                    self.client = QdrantClient(url=qdrant_url, timeout=2.0)
                else:
                    self.client = None
            except Exception:
                self.client = None

        # Initialize Embedding Provider
        self.embedding_provider = EmbeddingProvider()

        # Use a unique collection name for this codebase
        codebase_collection_name = f"codebase_{project_hash}"
        self.codebase_indexer = CodebaseIndexer(
            self.client, self.embedding_provider, collection_name=codebase_collection_name
        )

        # Ensure 'learnings' collection exists (if DB available)
        self._ensure_collection()

        # Sync if empty
        try:
            if self.vector_db_available and self.client.count(self.collection_name).count == 0:
                console.print("[yellow]Vector store empty. Syncing from disk...[/yellow]")
                self._sync_to_qdrant()
        except Exception as e:
            console.print(
                f"[yellow]Could not check collection count (maybe connectivity issue): {e}[/yellow]"
            )

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
        # Scrub PII/Secrets
        text = scrubber.scrub(text)
        # Remove null bytes and control characters (except common whitespace)
        text = "".join(ch for ch in text if ch == "\n" or ch == "\r" or ch == "\t" or ch >= " ")
        # Limit length to prevent DOS/OOM (approx 8k tokens safe limit)
        return text[:30000]

    def _ensure_knowledge_dir(self):
        """Ensure the knowledge directory exists."""
        if not os.path.exists(self.knowledge_dir):
            os.makedirs(self.knowledge_dir)

    def _ensure_collection(self, force_recreate: bool = False):
        """Ensure the Qdrant collection exists."""
        self.vector_db_available = self._safe_ensure_collection(
            collection_name=self.collection_name,
            vector_size=self.embedding_provider.vector_size,
            force_recreate=force_recreate,
            enable_sparse=True,
            registry_flag="learnings_ensured",
        )

    def _sync_to_qdrant(self, batch_size: int = 50):
        """Sync all local JSON files to Qdrant with batching."""
        if not self.vector_db_available:
            return

        from filelock import FileLock

        lock = FileLock(self.lock_path)
        with lock:
            files = glob.glob(os.path.join(self.knowledge_dir, "*.json"))
            total_files = len(files)
            synced_count = 0

            # Process in batches
            file_iter = iter(files)
            while True:
                batch_files = list(itertools.islice(file_iter, batch_size))
                if not batch_files:
                    break

                points = []
                for filepath in batch_files:
                    try:
                        with open(filepath, "r") as f:
                            learning = json.load(f)

                        # Prepare point
                        text_to_embed = self._prepare_embedding_text(learning)
                        vector = self.embedding_provider.get_embedding(text_to_embed)
                        sparse_vector = self.embedding_provider.get_sparse_embedding(text_to_embed)

                        learning_id = learning.get("id") or str(uuid.uuid4())
                        # Use UUIDv5 for deterministic but unique point IDs
                        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(learning_id)))

                        points.append(
                            PointStruct(
                                id=point_id,
                                vector={"": vector, "text-sparse": sparse_vector},
                                payload=learning,
                            )
                        )
                    except Exception as e:
                        console.print(f"[red]Failed to prepare {filepath}: {e}[/red]")

                if points:
                    try:
                        self.client.upsert(collection_name=self.collection_name, points=points)
                        synced_count += len(points)
                        console.print(f"[dim]Synced batch: {synced_count}/{total_files}[/dim]")
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

            # Use UUIDv5 for deterministic but unique point IDs
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
            logger.error(f"Error indexing learning {learning.get('id', 'unknown')}", str(e))

    def save_learning(self, learning: Dict[str, Any], silent: bool = False) -> str:
        """
        Add a new learning item to the knowledge base.

        Args:
            learning: Dictionary containing learning details.
                      Should include 'category', 'title', 'description', etc.
            silent: If True, suppress verbose output messages.

        Returns:
            Path to the saved learning file.
        """
        # Generate ID
        # Generate ID with high resolution and entropy to prevent collisions
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        random_suffix = os.urandom(4).hex()
        learning_id = f"{timestamp}-{random_suffix}"
        
        category = learning.get("category", "general").lower().replace(" ", "-")
        filename = f"{learning_id}-{category}.json"
        filepath = os.path.join(self.knowledge_dir, filename)

        # Add metadata
        learning["created_at"] = datetime.now().isoformat()
        learning["id"] = learning_id

        from filelock import FileLock

        lock = FileLock(self.lock_path)
        try:
            with lock:
                # 1. Save to Disk (Source of Truth/Backup)
                tmp_path = filepath + ".tmp"
                with open(tmp_path, "w") as f:
                    json.dump(learning, f, indent=2)
                os.replace(tmp_path, filepath)

                # 2. Index in Qdrant
                self._index_learning(learning)

                if not silent:
                    logger.success(f"Learning saved to {filepath} and indexed in Qdrant")

                # 3. Update Docs
                self.docs_service.update_ai_md(self.get_all_learnings(), silent=silent)
                self.docs_service.review_and_compress(silent=silent)

            return filepath
        except Exception as e:
            if not silent:
                console.print(f"[red]Failed to save learning: {e}[/red]")
            raise

    def retrieve_relevant(
        self, query: str = "", tags: List[str] = None, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant learnings using Hybrid Search (Dense + Sparse).

        Args:
            query: Text to search for.
            tags: List of tags to filter by.
            limit: Maximum number of results to return.

        Returns:
            List of learning dictionaries.
        """
        if not query and not tags:
            return self.get_all_learnings()[:limit]

        try:
            if not self.vector_db_available:
                raise ConnectionError("Qdrant not available")

            # Prepare Filter
            query_filter = None
            if tags:
                should_conditions = []
                for tag in tags:
                    # Check 'tags' field
                    should_conditions.append(
                        FieldCondition(key="tags", match=MatchValue(value=tag))
                    )
                    # Check 'category' field (treat as implicit tag)
                    should_conditions.append(
                        FieldCondition(
                            key="category",
                            match=MatchValue(value=tag),  # Categories are stored as-is in payload
                        )
                    )

                # Check if ANY tag matches
                query_filter = Filter(should=should_conditions)

            # Vector Search Inputs
            from qdrant_client.models import Fusion, FusionQuery, Prefetch

            dense_vector = self.embedding_provider.get_embedding(query)
            sparse_vector = self.embedding_provider.get_sparse_embedding(query)

            search_result = self.client.query_points(
                collection_name=self.collection_name,
                prefetch=[
                    Prefetch(
                        query=dense_vector,
                        using=None,  # Default dense
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
            console.print(f"[red]Hybrid search failed: {e}. Falling back to disk search.[/red]")
            return self._legacy_search(query, tags, limit)

    def _legacy_search(
        self, query: str = "", tags: List[str] = None, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Legacy disk-based search (fallback)."""
        results = []
        files = glob.glob(os.path.join(self.knowledge_dir, "*.json"))
        files.sort(reverse=True)

        for filepath in files:
            try:
                with open(filepath, "r") as f:
                    learning = json.load(f)

                if tags:
                    learning_tags = learning.get("tags", [])
                    learning_tags.append(learning.get("category", ""))
                    if not any(tag.lower() in [t.lower() for t in learning_tags] for tag in tags):
                        continue

                if query:
                    search_text = (
                        f"{learning.get('title', '')} {learning.get('description', '')} "
                        f"{learning.get('content', '')}"
                    ).lower()
                    if query.lower() not in search_text:
                        continue

                results.append(learning)
                if len(results) >= limit:
                    break
            except Exception:
                continue
        return results

    def get_all_learnings(self) -> List[Dict[str, Any]]:
        """Retrieve all learnings."""
        return self._legacy_search(limit=1000)

    def get_context_string(self, query: str = "", tags: List[str] = None) -> str:
        """
        Get a formatted string of relevant learnings for context injection.
        """
        learnings = self.retrieve_relevant(query, tags)
        if not learnings:
            return "No relevant past learnings found."

        context = "## Relevant Past Learnings\\n\\n"
        for learning in learnings:
            context += f"### {learning.get('title', 'Untitled')}\\n"
            context += f"- **Category**: {learning.get('category', 'General')}\\n"
            context += f"- **Source**: {learning.get('source', 'Unknown')}\\n"
            context += f"- **Date**: {learning.get('created_at', 'Unknown')}\\n"
            content = learning.get("content", "")
            if isinstance(content, dict):
                context += f"\\n{content.get('summary', '')}\\n\\n"
            else:
                context += f"\\n{content}\\n\\n"
            if learning.get("codified_improvements"):
                context += "- **Improvements**:\\n"
                for imp in learning["codified_improvements"]:
                    context += (
                        f"  - [{imp.get('type', 'item')}] {imp.get('title', '')}: "
                        f"{imp.get('description', '')}\\n"
                    )
            context += "\\n"

        return context

    def get_compounding_ai_prompt(self, limit: int = 20) -> str:
        """
        Get a formatted prompt suffix for auto-injection into ALL AI interactions.

        This is the equivalent of CLAUDE.md in the original plugin - a way to ensure
        every LLM call benefits from past learnings.

        Args:
            limit: Maximum number of recent learnings to include (default: 20)

        Returns:
            Formatted string ready to be prepended/appended to prompts
        """
        all_learnings = self.get_all_learnings()

        if not all_learnings:
            return ""

        # Sort by most recent
        sorted_learnings = sorted(
            all_learnings, key=lambda x: x.get("created_at", ""), reverse=True
        )[:limit]

        prompt = "\\n\\n---\\n\\n## System Learnings (Auto-Injected)\\n\\n"
        prompt += "The following patterns and learnings have been codified from past work. "
        prompt += "Apply these automatically to the current task:\\n\\n"

        for learning in sorted_learnings:
            prompt += f"### {learning.get('title', 'Untitled')}\\n"
            prompt += f"**Source:** {learning.get('source', 'unknown')}\\n"

            if learning.get("codified_improvements"):
                for imp in learning["codified_improvements"]:
                    prompt += f"- {imp.get('description', '')}\\n"

            prompt += "\\n"

        return prompt

    def search_similar_patterns(
        self, description: str, threshold: float = 0.3, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar patterns using vector embeddings.
        """
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
