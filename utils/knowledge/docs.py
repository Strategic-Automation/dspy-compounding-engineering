"""
Knowledge Documentation Service.

This module handles the generation, maintenance, and compression of the
AI.md auto-generated documentation file.
"""

import hashlib
import os
import shutil
from datetime import datetime
from typing import Any, Dict, List

from rich.console import Console

from ..io.logger import logger
from .compression import LLMKBCompressor

console = Console()


class KnowledgeDocumentation:
    """
    Manages the AI.md documentation file, including generation and compression.
    """

    COMPRESSION_THRESHOLD = 500  # Always compress if content exists
    LLM_COMPRESSION_MIN_SIZE = 10000

    def __init__(self, knowledge_dir: str):
        self.knowledge_dir = knowledge_dir
        self.ai_md_path = os.path.join(self.knowledge_dir, "AI.md")
        self._compression_cache: Dict[str, str] = {}

    def get_ai_md_size(self) -> int:
        """
        Get current size of AI.md in characters.
        """
        if not os.path.exists(self.ai_md_path):
            return 0
        try:
            with open(self.ai_md_path, "r") as f:
                return len(f.read())
        except Exception:
            return 0

    def _log(self, message: str, color: str = "dim", silent: bool = False):
        """Helper to log messages if not in silent mode."""
        if not silent:
            if color == "red":
                logger.error(message)
            elif color == "yellow":
                logger.warning(message)
            elif color == "green":
                logger.success(message)
            else:
                logger.info(message)

    def _resolve_title(self, item: Dict[str, Any]) -> str:
        """Resolve a suitable title for a learning item."""
        title = item.get("title") or item.get("feedback_summary")
        description = item.get("description", "") or item.get("content", "")

        # If we have a good title already, return it
        if title and title.lower() != "untitled":
            return title

        # Infer from description or improvements
        candidate = None
        if description and isinstance(description, str):
            candidate = description
        elif item.get("codified_improvements"):
            # Try to use the first improvement
            first_imp = item["codified_improvements"][0]
            candidate = str(
                first_imp.get("title") or first_imp.get("description") or first_imp
            )

        if candidate:
            # cleanup candidate
            candidate = str(candidate).split("\n")[0].split(".")[0]
            title = (candidate[:60] + "...") if len(candidate) > 60 else candidate
            return title.strip() or "Untitled"

        return "Untitled"

    def _generate_markdown(self, learnings: List[Dict[str, Any]]) -> str:
        """Generate the AI.md content from learnings."""
        by_category = {}
        for learning in learnings:
            cat = learning.get("category", "General").title()
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(learning)

        content = "# AI Knowledge Base\n\n"
        content += "This file contains codified learnings and improvements for the AI system.\n"
        content += "It is automatically updated when new learnings are added.\n\n"

        for category, items in sorted(by_category.items()):
            content += f"## {category}\n\n"
            for item in items:
                title = self._resolve_title(item)
                description = item.get("description", "") or item.get("content", "")

                content += f"### {title}\n"
                if description:
                    content += f"{description}\n\n"
                else:
                    content += "\n"
                if item.get("codified_improvements"):
                    content += "**Improvements:**\n"
                    for imp in item["codified_improvements"]:
                        type_badge = f"[{imp.get('type', 'item').upper()}]"
                        title_str = imp.get("title", "")
                        desc_str = imp.get("description", "")
                        content += f"- {type_badge} {title_str}: {desc_str}\n"
                    content += "\n"
                content += "\n"
            content += "\n"
        return content

    def update_ai_md(self, learnings: List[Dict[str, Any]], silent: bool = False):
        """
        Regenerate AI.md from the provided list of learnings.
        Automatically compresses if content exceeds threshold.
        """
        content = self._generate_markdown(learnings)

        # Check size before writing
        if len(content) > self.COMPRESSION_THRESHOLD:
            try:
                msg = (
                    f"Content size ({len(content)} chars) exceeds threshold "
                    f"({self.COMPRESSION_THRESHOLD}). Compressing..."
                )
                self._log(msg, color="cyan", silent=silent)
                # Create backup of previous version if it exists
                if os.path.exists(self.ai_md_path):
                    self._create_backup(silent=silent)

                content = self._run_compression(content, ratio=0.5, silent=silent)
            except Exception as e:
                self._log(
                    f"Pre-write compression failed: {e}. Falling back to uncompressed.",
                    color="yellow",
                    silent=silent,
                )

        try:
            tmp_path = self.ai_md_path + ".tmp"
            with open(tmp_path, "w") as f:
                f.write(content)
            os.replace(tmp_path, self.ai_md_path)
            self._log(f"Updated {self.ai_md_path}", silent=silent)
        except Exception as e:
            self._log(f"Failed to update AI.md: {e}", color="yellow", silent=silent)

    def _create_backup(self, silent: bool = False):
        """Create a backup of AI.md."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backups_dir = os.path.join(self.knowledge_dir, "backups")
        os.makedirs(backups_dir, exist_ok=True)
        backup_path = os.path.join(backups_dir, f"AI.md.backup.{timestamp}")
        shutil.copy2(self.ai_md_path, backup_path)
        self._log(f"Backup created at {backup_path}", silent=silent)

    def _run_compression(self, content: str, ratio: float, silent: bool = False) -> str:
        """Run the LLM-based compression with caching."""
        content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
        cache_key = f"{content_hash}_{ratio}"

        if cache_key in self._compression_cache:
            self._log("Using cached compression result...", color="blue", silent=silent)
            return self._compression_cache[cache_key]

        self._log("Performing LLM compression...", color="dim", silent=silent)
        compressor = LLMKBCompressor()
        compressed_content = compressor(content=content, ratio=ratio)
        self._compression_cache[cache_key] = compressed_content
        return compressed_content

    def compress_ai_md(
        self, ratio: float = 0.5, dry_run: bool = False, silent: bool = False
    ) -> None:
        """
        Compress AI.md using LLM-based semantic compression.
        """
        if not (0.0 <= ratio <= 1.0):
            raise ValueError("Ratio must be between 0.0 and 1.0")

        if not os.path.exists(self.ai_md_path):
            return

        try:
            self._log(
                f"Compressing AI.md (LLM-powered, target ratio {ratio})...",
                color="cyan",
                silent=silent,
            )

            if not dry_run:
                self._create_backup(silent=silent)

            current_size = self.get_ai_md_size()
            with open(self.ai_md_path, "r") as f:
                content = f.read()

            compressed_content = self._run_compression(content, ratio, silent=silent)

            if not compressed_content or len(compressed_content) > len(content) * 1.2:
                raise ValueError("Compression produced invalid result")

            if dry_run:
                self._log("Dry run: Skipping write to file.", color="yellow", silent=silent)
            else:
                tmp_path = self.ai_md_path + ".tmp"
                with open(tmp_path, "w") as f:
                    f.write(compressed_content)
                os.replace(tmp_path, self.ai_md_path)

            new_size = len(compressed_content)
            reduction = (1 - new_size / current_size) * 100
            msg = (
                f"AI.md compressed: {current_size:,} → {new_size:,} chars "
                f"({reduction:.1f}% reduction)"
            )
            self._log(msg, color="green", silent=silent)

        except Exception as e:
            self._log(f"LLM compression failed: {e}", color="red", silent=silent)
            raise

    def review_and_compress(self, silent: bool = False) -> None:
        """
        Auto-review AI.md quality and compress if needed.
        """
        size = self.get_ai_md_size()
        self._log(
            f"AI.md size: {size:,} chars (threshold: {self.COMPRESSION_THRESHOLD:,})",
            silent=silent,
        )

        if size > self.COMPRESSION_THRESHOLD:
            self.compress_ai_md(silent=silent)
