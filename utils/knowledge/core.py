"""
Knowledge Base module for Compounding Engineering.

This module manages the persistent storage and retrieval of learnings,
enabling the system to improve over time by accessing past insights.
"""

import json
import os
import sqlite3
import uuid
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
from .utils import CollectionManagerMixin


class KnowledgeBase(CollectionManagerMixin):
    """
    Manages a collection of learnings stored in a local SQLite database and indexed in Qdrant.
    """

    MAX_COLLECTION_NAME_LENGTH = 60

    def __init__(
        self, knowledge_dir: Optional[str] = None, qdrant_client: Optional["QdrantClient"] = None
    ):
        from config import get_project_hash, get_project_root, registry

        if knowledge_dir is None:
            from config import settings

            knowledge_dir = os.path.join(str(get_project_root()), settings.knowledge_dir_name)

        self.knowledge_dir = os.path.abspath(knowledge_dir)
        self._ensure_knowledge_dir()

        # SQL Storage
        self.db_path = os.path.join(self.knowledge_dir, "knowledge.db")
        self._init_db()

        # Migration
        # self._migrate_legacy_files()

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
                # Check if we have data in SQL
                all_learnings = self.get_all_learnings()
                if all_learnings:
                    console.print("[yellow]Vector store empty. Syncing from SQLite...[/yellow]")
                    self._sync_to_qdrant(all_learnings)
        except Exception as e:
            logger.debug(f"Could not check collection count: {e}")

        logger.info("KnowledgeBase service is ready", to_cli=True)

    def _init_db(self):
        """Initialize SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learnings (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,  -- JSON blob for extra fields (tags, context, etc)
                    source TEXT,
                    created_at DATETIME,
                    updated_at DATETIME
                )
            """)
            conn.commit()

    # def _migrate_legacy_files(self):
    #     """Migrate existing .json files to SQLite and archive them."""
    #     json_files = glob.glob(os.path.join(self.knowledge_dir, "*.json"))
    #     if not json_files:
    #         return
    #
    #     archive_dir = os.path.join(self.knowledge_dir, "archive")
    #     os.makedirs(archive_dir, exist_ok=True)
    #
    #     migrated_count = 0
    #     console.print(f"[dim]Migrating {len(json_files)} legacy JSON files to SQLite...[/dim]")
    #
    #     files_to_archive = []
    #
    #     with sqlite3.connect(self.db_path) as conn:
    #         for filepath in json_files:
    #             try:
    #                 with open(filepath, "r") as f:
    #                     data = json.load(f)
    #
    #                 self._insert_learning_tx(conn, data)
    #                 files_to_archive.append(filepath)
    #             except Exception as e:
    #                 logger.error(f"Failed to migrate {filepath}: {e}")
    #
    #         # Commit first
    #         conn.commit()
    #
    #     # Archive files only after successful commit
    #     for filepath in files_to_archive:
    #         try:
    #             filename = os.path.basename(filepath)
    #             shutil.move(filepath, os.path.join(archive_dir, filename))
    #             migrated_count += 1
    #         except Exception as e:
    #             logger.error(f"Failed to archive {filepath}: {e}")
    #
    #     if migrated_count > 0:
    #         console.print(
    #             f"[green]Successfully migrated {migrated_count} files to knowledge.db[/green]"
    #         )

    def _insert_learning_tx(self, conn, learning: Dict[str, Any]):
        """Insert learning within an existing transaction context."""
        meta = learning.copy()
        # Pop standard columns to keep metadata clean, or duplicate?
        # Let's keep metadata inclusive for now or selective.
        # Actually, extracting specific fields and dumping the rest into metadata is cleaner.

        l_id = meta.pop("id")
        title = meta.pop("title", "Untitled")
        category = meta.pop("category", "general")

        # Handle content: it can be a string or a dict
        content_raw = meta.pop("content", "")
        if isinstance(content_raw, dict):
            # Storing as string representation for simple search,
            # but keeping structure in metadata might be valid.
            # However, schema says content is TEXT. Let's assume content is the "insight".
            # If content was a dict with summary, etc,
            # let's stringify it for the main text column.
            content_val = (
                content_raw.get("summary", "")
                or content_raw.get("description", "")
                or str(content_raw)
            )
            # Put original complex content back into metadata for full fidelity reconstruction
            meta["original_content_object"] = content_raw
        else:
            content_val = str(content_raw)

        source = meta.pop("source", "unknown")
        created_at = meta.pop("created_at", datetime.now().isoformat())
        updated_at = datetime.now().isoformat()

        metadata_json = json.dumps(meta)

        conn.execute(
            """
            INSERT OR REPLACE INTO learnings
            (id, title, category, content, metadata, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (l_id, title, category, content_val, metadata_json, source, created_at, updated_at),
        )

    def get_codify_lock_path(self) -> str:
        """Returns the path to the codify-specific lock file."""
        return os.path.join(self.knowledge_dir, "codify.lock")

    def get_lock(self, lock_type: str = "kb") -> "FileLock":
        """Returns a FileLock instance for the specified type ('kb' or 'codify')."""
        path = self.get_codify_lock_path() if lock_type == "codify" else self.lock_path
        return FileLock(path)

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
        from config import settings

        return text[: settings.kb_sanitize_limit]

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

    def _sync_to_qdrant(self, learnings: List[Dict[str, Any]], batch_size: Optional[int] = None):
        """Sync a list of learnings to Qdrant."""
        if batch_size is None:
            batch_size = settings.kb_sync_batch_size
        if not self.vector_db_available:
            return

        total_items = len(learnings)
        synced_count = 0

        # Iterate in batches
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

            # Use UUIDv5 for deterministic but unique point IDs
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(learning_id)))

            from qdrant_client.models import PointStruct

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

    def save_learning(
        self, learning: Dict[str, Any], silent: bool = False, update_docs: bool = True
    ) -> str:
        """
        Add a new learning item to the knowledge base (SQLite + Qdrant).
        """
        # Generate ID
        learning_id = learning.get("id")
        if not learning_id:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            random_suffix = os.urandom(4).hex()
            learning_id = f"{timestamp}-{random_suffix}"
            learning["id"] = learning_id

        if "created_at" not in learning:
            learning["created_at"] = datetime.now().isoformat()

        lock = self.get_lock()
        try:
            with lock:
                # 1. Save to SQLite (Source of Truth)
                with sqlite3.connect(self.db_path) as conn:
                    self._insert_learning_tx(conn, learning)
                    conn.commit()

                # 2. Index in Qdrant
                self._index_learning(learning)

                if not silent:
                    logger.success(f"Learning saved to DB ({learning_id})")

                # 3. Update Docs
                if update_docs:
                    self.docs_service.update_ai_md(self.get_all_learnings(), silent=silent)

            return learning_id
        except Exception as e:
            if not silent:
                console.print(f"[red]Failed to save learning: {e}[/red]")
            raise

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

            # Prepare Filter
            query_filter = None
            if tags:
                should_conditions = []
                for tag in tags:
                    should_conditions.append(
                        FieldCondition(key="tags", match=MatchValue(value=tag))
                    )
                    # Also check category
                    should_conditions.append(
                        FieldCondition(key="category", match=MatchValue(value=tag))
                    )

                query_filter = Filter(should=should_conditions)

            # Vector Search logic
            dense_vector = self.embedding_provider.get_embedding(query)
            sparse_vector = self.embedding_provider.get_sparse_embedding(query)

            search_result = self.client.query_points(
                collection_name=self.collection_name,
                prefetch=[
                    Prefetch(
                        query=dense_vector,
                        using=None,  # standard dense
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
            # Log failure before falling back
            logger.warning(f"Hybrid search failed: {e}. Falling back to local DB.")
            return self.search_local(query, tags, limit)

    def search_local(
        self, query: str = "", tags: List[str] = None, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Local search using SQLite LIKE queries.
        Replaces the old _legacy_search (file-based).
        """
        from config import settings

        if limit is None:
            limit = settings.search_limit_codebase

        results = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            sql = "SELECT * FROM learnings WHERE 1=1"
            params = []

            if query:
                # Simple keyword matching in title/content/desc
                sql += " AND (title LIKE ? OR content LIKE ? OR category LIKE ?)"
                wildcard = f"%{query}%"
                params.extend([wildcard, wildcard, wildcard])

            # If tags are provided, we'd need to parse metadata.
            # JSON_EXTRACT is available in newer sqlite, but for safety
            # let's filter in python or basic string matching on metadata.

            sql += " ORDER BY created_at DESC"

            cursor = conn.execute(sql, params)

            count = 0
            for row in cursor:
                learning = self._row_to_dict(row)

                # Manual Tag Filtering
                if tags:
                    learning_tags = learning.get("tags", [])
                    learning_tags.append(learning.get("category", ""))
                    if not any(tag.lower() in [t.lower() for t in learning_tags] for tag in tags):
                        continue

                results.append(learning)
                count += 1
                if limit and count >= limit:
                    break

        return results

    def get_all_learnings(self) -> List[Dict[str, Any]]:
        """Retrieve all learnings from SQLite."""
        results = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM learnings ORDER BY created_at DESC")
                for row in cursor:
                    results.append(self._row_to_dict(row))
        except Exception:
            return []
        return results

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to full learning dict, merging metadata."""
        data = {
            "id": row["id"],
            "title": row["title"],
            "category": row["category"],
            "content": row["content"],  # string
            "source": row["source"],
            "created_at": row["created_at"],
        }

        # Merge metadata
        if row["metadata"]:
            try:
                meta = json.loads(row["metadata"])

                # Reconstruct complex content if it was saved
                if "original_content_object" in meta:
                    data["content"] = meta.pop("original_content_object")

                # Merge rest
                data.update(meta)
            except Exception:
                pass

        return data
    def get_context_string(self, query: str = "", tags: List[str] = None) -> str:
        """
        Get a formatted string of relevant learnings for context injection.
        Wraps content in XML tags to prevent prompt injection.
        """
        logger.debug(f"Retrieving relevant context for query: {query[:100]}... Tags: {tags}")
        learnings = self.retrieve_relevant(query, tags)
        if not learnings:
            return "No relevant past learnings found."

        context = "## Relevant Past Learnings\\n\\n"
        for learning in learnings:
            title = learning.get('title', 'Untitled').replace("<", "&lt;")
            cat = learning.get('category', 'General').replace("<", "&lt;")

            content = learning.get("content", "")
            if isinstance(content, dict):
                content_str = content.get('summary', '')
            else:
                content_str = str(content)

            # Simple sanitization for XML structure
            content_str = content_str.replace("</context_item>", "")

            context += "<context_item>\\n"
            context += f"  <title>{title}</title>\\n"
            context += f"  <category>{cat}</category>\\n"
            context += f"  <content>\\n{content_str}\\n  </content>\\n"
            context += "</context_item>\\n\\n"

        return context

    def get_compounding_ai_prompt(self, limit: int = 20) -> str:
        """
        Get a formatted prompt suffix for auto-injection into ALL AI interactions.
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
            title = learning.get('title', 'Untitled').replace("<", "&lt;")
            prompt += "<system_learning>\\n"
            prompt += f"  <title>{title}</title>\\n"
            if learning.get("codified_improvements"):
                prompt += "  <improvements>\\n"
                for imp in learning["codified_improvements"]:
                    desc = imp.get('description', '').replace("<", "&lt;")
                    prompt += f"    <item>{desc}</item>\\n"
                prompt += "  </improvements>\\n"
            prompt += "</system_learning>\\n"

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
