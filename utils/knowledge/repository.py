"""
Knowledge Base Repository — SQLite persistence layer.

Separates pure SQL storage concerns from vector DB indexing and
document compression responsibilities (Pattern Recognition Specialist #013,
Kieran Python Reviewer architecture concern).

The KnowledgeBase class delegates to this repository for all SQLite operations,
keeping the storage layer independently testable and replaceable.
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..security.scrubber import scrubber
from ..io.logger import logger


class KnowledgeBaseStorage:
    """
    Handles all SQLite-backed persistence for the knowledge base.

    This class is responsible for:
    - Schema initialization and migration
    - CRUD operations on learnings
    - Metadata PII scrubbing before persistence
    - Local keyword search

    It does NOT handle:
    - Vector DB indexing (Qdrant)
    - Document compression (KnowledgeDocumentation)
    - Embedding generation
    """

    def __init__(self, knowledge_dir: str):
        self.knowledge_dir = knowledge_dir
        self.db_path = os.path.join(self.knowledge_dir, "knowledge.db")
        self._init_db()

    # -- Schema --

    def _init_db(self):
        """Initialize SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learnings (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    source TEXT,
                    created_at DATETIME,
                    updated_at DATETIME
                )
            """)
            conn.commit()

    # -- Helpers --

    def _scrub_metadata(self, meta: Dict[str, Any]) -> None:
        """Scrub PII from metadata values in-place before persistence."""
        pii_fields = {"email", "emails", "author", "authors", "contact", "contacts",
                       "phone", "phones", "url", "urls", "website", "name", "names"}
        for key in list(meta.keys()):
            if key not in pii_fields:
                continue
            value = meta[key]
            if isinstance(value, str):
                meta[key] = scrubber.scrub(value)
            elif isinstance(value, (list, tuple)):
                if value and isinstance(value[0], str):
                    meta[key] = [scrubber.scrub(v) if isinstance(v, str) else v for v in value]

    @staticmethod
    def _generate_id(title: str, content: str) -> str:
        """Generate a deterministic UUIDv5 ID from title + content."""
        id_seed = f"{title}:{content}".encode()
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, id_seed))

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to full learning dict, merging metadata."""
        data = {
            "id": row["id"],
            "title": row["title"],
            "category": row["category"],
            "content": row["content"],
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

    # -- CRUD --

    def insert_learning(self, learning: Dict[str, Any]) -> str:
        """
        Insert a learning record.

        Uses INSERT-only (not REPLACE) to prevent silent overwrites.
        Generates a deterministic UUIDv5 ID if none provided.
        Scrubs PII from metadata before storage.

        Returns the learning ID.
        """
        meta = learning.copy()

        l_id = meta.pop("id", None)
        if not l_id:
            l_id = self._generate_id(meta.get("title", ""), meta.get("content", ""))
            learning["id"] = l_id

        title = meta.pop("title", "Untitled")
        category = meta.pop("category", "general")
        content_raw = meta.pop("content", "")
        if isinstance(content_raw, dict):
            content_val = (
                content_raw.get("summary", "")
                or content_raw.get("description", "")
                or str(content_raw)
            )
            meta["original_content_object"] = content_raw
        else:
            content_val = str(content_raw)

        source = meta.pop("source", "unknown")
        created_at = meta.pop("created_at", datetime.now().isoformat())
        updated_at = datetime.now().isoformat()

        # PII Safety: scrub metadata before persisting
        self._scrub_metadata(meta)
        metadata_json = json.dumps(meta)

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO learnings
                    (id, title, category, content, metadata, source, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (l_id, title, category, content_val, metadata_json, source, created_at, updated_at),
                )
        except sqlite3.IntegrityError:
            logger.warning(f"Learning with ID {l_id} already exists; skipping insert.")

        return l_id

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

    def search_local(self, query: str = "", tags: List[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Local search using SQLite LIKE queries.
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
                sql += " AND (title LIKE ? OR content LIKE ? OR category LIKE ?)"
                wildcard = f"%{query}%"
                params.extend([wildcard, wildcard, wildcard])

            sql += " ORDER BY created_at DESC"

            cursor = conn.execute(sql, params)

            count = 0
            for row in cursor:
                learning = self._row_to_dict(row)

                # Manual tag filtering on metadata + category
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

    # -- Migration (stub, legacy JSON files already archived) --

    def migrate_legacy_files(self, knowledge_dir: str) -> int:
        """
        Migrate legacy .json files to SQLite. Returns count migrated.
        This is a no-op if migration was already performed or JSON files
        are absent.
        """
        import glob
        import shutil

        json_files = glob.glob(os.path.join(knowledge_dir, "*.json"))
        if not json_files:
            return 0

        archive_dir = os.path.join(knowledge_dir, "archive")
        os.makedirs(archive_dir, exist_ok=True)

        migrated_count = 0
        for filepath in json_files:
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                self.insert_learning(data)
                shutil.move(filepath, os.path.join(archive_dir, os.path.basename(filepath)))
                migrated_count += 1
            except Exception as e:
                logger.error(f"Failed to migrate {filepath}: {e}")

        return migrated_count