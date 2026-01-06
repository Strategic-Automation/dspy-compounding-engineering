"""
Codebase Indexer module for Compounding Engineering.

This module manages the indexing of the codebase into Qdrant for semantic search.
It handles file crawling, chunking, embedding generation, and incremental updates.
"""

import glob
import os
import subprocess
import uuid
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
)
from rich.console import Console

from ..io.logger import logger
from ..io.safe import run_safe_command
from .embeddings import EmbeddingProvider
from .utils import CollectionManagerMixin

console = Console()


class CodebaseIndexer(CollectionManagerMixin):
    """
    Manages indexing of the codebase using vector embeddings.
    """

    def __init__(
        self,
        qdrant_client: QdrantClient,
        embedding_provider: EmbeddingProvider,
        collection_name: str = "codebase",
    ):
        self.client = qdrant_client
        self.embedding_provider = embedding_provider
        self.collection_name = collection_name
        self.vector_db_available = self.client is not None

        if self.vector_db_available:
            self._ensure_collection()

    def _ensure_collection(self, force_recreate: bool = False):
        """Ensure the Qdrant collection exists."""
        self.vector_db_available = self._safe_ensure_collection(
            collection_name=self.collection_name,
            vector_size=self.embedding_provider.vector_size,
            force_recreate=force_recreate,
            enable_sparse=False,  # Codebase currently only uses dense
            registry_flag="codebase_ensured",
        )

    def _get_indexed_files_metadata(self) -> Dict[str, float]:
        """
        Retrieve metadata for all indexed files to enable smart incremental indexing.
        Returns: Dict[file_path, last_modified_timestamp]
        """
        if not self.vector_db_available:
            return {}

        indexed_files = {}
        offset = None

        from config import settings

        while True:
            # Scroll through points to get paths and mtimes
            # We filter for points that are the 'first chunk' (chunk_index=0) to avoid duplicates
            # or we could just aggregate. Iterating chunk 0 is efficient.
            try:
                scroll_result = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(
                                key="type",
                                match=MatchValue(value="code_file"),
                            )
                        ]
                    ),
                    limit=settings.indexer_file_limit,
                    with_payload=True,
                    with_vectors=False,
                    offset=offset,
                )
                points, offset = scroll_result

                for point in points:
                    if point.payload and "path" in point.payload:
                        mtime = point.payload.get("last_modified", 0.0)
                        indexed_files[point.payload["path"]] = mtime

                if offset is None:
                    break
            except Exception:
                # If collection doesn't exist or other error
                break

        return indexed_files

    def _chunk_text(self, text: str, size: int = 2000, overlap: int = 200) -> List[str]:
        """Split text into chunks with overlap."""
        if not text:
            return []

        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + size
            chunk = text[start:end]
            chunks.append(chunk)
            start += size - overlap

        return chunks

    def _get_files_to_index(self, root_dir: str) -> List[str]:
        """Get list of files to index, preferably using git."""
        try:
            # 1. Get list of tracked and untracked files (excluding ignored)
            cmd = ["git", "ls-files", "--cached", "--others", "--exclude-standard"]
            result = run_safe_command(cmd, cwd=root_dir, capture_output=True, text=True, check=True)
            return result.stdout.splitlines()
        except subprocess.CalledProcessError:
            logger.warning("Not a git repository. Indexing all files...")
            # Fallback to glob
            return [
                os.path.relpath(f, root_dir)
                for f in glob.glob(os.path.join(root_dir, "**/*"), recursive=True)
                if os.path.isfile(f)
            ]
        except Exception as e:
            console.print(f"[red]Failed to list files: {e}[/red]")
            return []

    def _should_ignore(self, filepath: str) -> bool:
        """Check if a file should be ignored based on extension or directory."""
        ignore_exts = {
            ".pyc",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".ico",
            ".svg",
            ".woff",
            ".woff2",
            ".ttf",
            ".eot",
            ".mp4",
            ".mov",
            ".zip",
            ".tar",
            ".gz",
            ".pkl",
            ".bin",
            ".exe",
            ".dll",
            ".so",
            ".lock",
            ".pdf",
        }
        ignore_dirs = {
            "plans/",
            "todos/",
            "docs/",
            ".knowledge/",
            ".venv/",
            "site/",
            "qdrant_storage/",
        }

        _, ext = os.path.splitext(filepath)
        if ext.lower() in ignore_exts:
            return True

        if any(filepath.startswith(d) for d in ignore_dirs):
            return True

        return False

    def index_codebase(self, root_dir: str = ".", force_recreate: bool = False) -> None:
        """
        Index the codebase using vector embeddings.
        Uses smart indexing to skip unchanged files.
        """
        if force_recreate:
            self._ensure_collection(force_recreate=True)

        if not self.vector_db_available:
            logger.error("Vector DB not available. Cannot index codebase.")
            return

        files = self._get_files_to_index(root_dir)
        if not files:
            return

        # 2. Get current index state
        logger.info("Fetching existing index state...")
        indexed_files = self._get_indexed_files_metadata()

        # 3. Process files
        updated_count = 0
        skipped_count = 0

        with console.status(f"Indexing {len(files)} files...") as status:
            for filepath in files:
                if self._should_ignore(filepath):
                    continue

                full_path = os.path.join(root_dir, filepath)
                if not os.path.exists(full_path):
                    continue

                try:
                    if self._index_single_file(filepath, full_path, indexed_files):
                        updated_count += 1
                    else:
                        skipped_count += 1

                    status.update(f"Indexed: {filepath}")

                except Exception as e:
                    console.print(f"[dim red]Failed to index {filepath}: {e}[/dim red]")

        logger.success(f"Indexing complete. Updated: {updated_count}, Skipped: {skipped_count}")

    def _index_single_file(
        self, filepath: str, full_path: str, indexed_files: Dict[str, float]
    ) -> bool:
        """
        Index a single file if it has changed.
        Returns True if updated, False if skipped.
        """
        mtime = os.path.getmtime(full_path)

        # Check if needs update
        if filepath in indexed_files and indexed_files[filepath] >= mtime:
            return False

        # Read content
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # likely binary
            return False

        # Chunk content
        chunks = self._chunk_text(content)

        points = []
        for i, chunk in enumerate(chunks):
            # Create embedding
            vector = self.embedding_provider.get_embedding(chunk)

            # ID: uuid5(NAMESPACE_URL, file_path + chunk_index)
            # We include chunk index in ID to make it unique per chunk
            unique_str = f"{filepath}::{i}"
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_str))

            payload = {
                "path": filepath,
                "content": chunk,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "last_modified": mtime,
                "type": "code_file",  # Add type for filtering
            }

            points.append(PointStruct(id=point_id, vector=vector, payload=payload))

        if points:
            # Upsert new chunks (overwrites same IDs, handles expansion)
            self.client.upsert(collection_name=self.collection_name, points=points)

            # Clean up stale chunks (if file shrunk)
            # We delete points for this path where chunk_index >= current total_chunks
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(key="path", match=MatchValue(value=filepath)),
                        FieldCondition(key="chunk_index", range={"gte": len(chunks)}),
                    ]
                ),
            )
            return True

        return False

    def search_codebase(self, query: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search for relevant code snippets.
        """
        if not self.vector_db_available:
            return []

        from config import settings

        if limit is None:
            limit = settings.search_limit_codebase

        try:
            query_vector = self.embedding_provider.get_embedding(query)

            search_result = self.client.query_points(
                collection_name=self.collection_name, query=query_vector, limit=limit
            ).points

            # Returning chunks is usually better for specific context.
            results = []
            for hit in search_result:
                payload = hit.payload
                # Add score for context
                payload["score"] = hit.score
                results.append(payload)

            return results

        except Exception as e:
            logger.error("Codebase search failed", str(e))
            return []
