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

from .compression import LLMKBCompressor

console = Console()


class KnowledgeDocumentation:
    """
    Manages the AI.md documentation file, including generation and compression.
    """

    COMPRESSION_THRESHOLD = 15000
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

    def update_ai_md(self, learnings: List[Dict[str, Any]]):
        """
        Regenerate AI.md from the provided list of learnings.
        """
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
                title = item.get("title") or item.get("feedback_summary", "Untitled")
                content += f"### {title}\n"
                description = item.get("description", "")
                if description:
                    content += f"{description}\n\n"
                else:
                    content += "\n"
                if item.get("codified_improvements"):
                    content += "**Improvements:**\n"
                    for imp in item["codified_improvements"]:
                        type_badge = f"[{imp.get('type', 'item').upper()}]"
                        content += (
                            f"- {type_badge} {imp.get('title', '')}: {imp.get('description', '')}\n"
                        )
                    content += "\n"
                content += "\n"
            content += "\n"

        try:
            tmp_path = self.ai_md_path + ".tmp"
            with open(tmp_path, "w") as f:
                f.write(content)
            os.replace(tmp_path, self.ai_md_path)
            console.print(f"[dim]Updated {self.ai_md_path}[/dim]")
        except Exception as e:
            console.print(f"[yellow]Failed to update AI.md: {e}[/yellow]")

    def compress_ai_md(self, ratio: float = 0.5, dry_run: bool = False) -> None:
        """
        Compress AI.md using LLM-based semantic compression.
        """
        if not (0.0 <= ratio <= 1.0):
            raise ValueError("Ratio must be between 0.0 and 1.0")

        if not os.path.exists(self.ai_md_path):
            return

        try:
            console.print(f"[cyan]Compressing AI.md (LLM-powered, target ratio {ratio})...[/cyan]")

            if not dry_run:
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                backups_dir = os.path.join(self.knowledge_dir, "backups")
                os.makedirs(backups_dir, exist_ok=True)
                backup_path = os.path.join(backups_dir, f"AI.md.backup.{timestamp}")
                shutil.copy2(self.ai_md_path, backup_path)
                console.print(f"[dim]Backup created at {backup_path}[/dim]")

            current_size = self.get_ai_md_size()

            with open(self.ai_md_path, "r") as f:
                content = f.read()

            content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
            cache_key = f"{content_hash}_{ratio}"

            if cache_key in self._compression_cache:
                console.print("[blue]Using cached compression result...[/blue]")
                compressed_content = self._compression_cache[cache_key]
            else:
                console.print("[cyan]Performing LLM compression...[/cyan]")
                compressor = LLMKBCompressor()
                compressed_content = compressor(content=content, ratio=ratio)
                self._compression_cache[cache_key] = compressed_content

            if not compressed_content or len(compressed_content) > len(content) * 1.2:
                raise ValueError("Compression produced invalid result")

            if dry_run:
                console.print("[yellow]Dry run: Skipping write to file.[/yellow]")
            else:
                tmp_path = self.ai_md_path + ".tmp"
                with open(tmp_path, "w") as f:
                    f.write(compressed_content)
                os.replace(tmp_path, self.ai_md_path)

            new_size = len(compressed_content)
            reduction = (1 - new_size / current_size) * 100
            console.print(
                f"[green]✓ AI.md compressed: {current_size:,} → {new_size:,} chars "
                f"({reduction:.1f}% reduction)[/green]"
            )

        except Exception as e:
            console.print(f"[red]LLM compression failed: {e}[/red]")
            raise

    def review_and_compress(self) -> None:
        """
        Auto-review AI.md quality and compress if needed.
        """
        size = self.get_ai_md_size()
        console.print(
            f"[dim]AI.md size: {size:,} chars (threshold: {self.COMPRESSION_THRESHOLD:,})[/dim]"
        )

        if size > self.COMPRESSION_THRESHOLD:
            self.compress_ai_md()
