"""
Knowledge Base module for Compounding Engineering.

This module manages the persistent storage and retrieval of learnings,
enabling the system to improve over time by accessing past insights.
"""

import glob
import hashlib
import json
import os
import shutil
from datetime import datetime
from typing import Any, Dict, List

from rich.console import Console

console = Console()


class KnowledgeBase:
    """
    Manages a collection of learnings stored as JSON files.
    """

    def __init__(self, knowledge_dir: str = ".knowledge"):
        self.knowledge_dir = knowledge_dir
        self._ensure_knowledge_dir()
        backups_dir = os.path.join(self.knowledge_dir, "backups")
        os.makedirs(backups_dir, exist_ok=True)
        self.lock_path = os.path.join(self.knowledge_dir, "kb.lock")
    def _ensure_knowledge_dir(self):
        """Ensure the knowledge directory exists."""
        if not os.path.exists(self.knowledge_dir):
            os.makedirs(self.knowledge_dir)

    def add_learning(self, learning: Dict[str, Any]) -> str:
        """
        Add a new learning item to the knowledge base.

        Args:
            learning: Dictionary containing learning details.
                      Should include 'category', 'title', 'description', etc.

        Returns:
            Path to the saved learning file.
        """
        # Generate ID
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        category = learning.get("category", "general").lower().replace(" ", "-")
        filename = f"{timestamp}-{category}.json"
        filepath = os.path.join(self.knowledge_dir, filename)

        # Add metadata
        learning["created_at"] = datetime.now().isoformat()
        learning["id"] = timestamp

        try:
            tmp_path = filepath + '.tmp'
            with open(tmp_path, "w") as f:
                json.dump(learning, f, indent=2)
            os.replace(tmp_path, filepath)
            console.print(f"[green]✓ Learning saved to {filepath}[/green]")

            # Update AI.md
            self._update_ai_md()

            # Auto-compress if AI.md is getting large
            if self.get_ai_md_size() > 50000:  # 50KB threshold
                self.review_and_compress()

            return filepath
        except Exception as e:
            console.print(f"[red]Failed to save learning: {e}[/red]")
            raise
    def search_knowledge(
        self, query: str = "", tags: List[str] = None, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant learnings.

        Args:
            query: Text to search for in title/description (simple substring match for now).
            tags: List of tags to filter by.
            limit: Maximum number of results to return.

        Returns:
            List of learning dictionaries.
        """
        results = []
        files = glob.glob(os.path.join(self.knowledge_dir, "*.json"))

        # Sort by newest first
        files.sort(reverse=True)

        for filepath in files:
            try:
                with open(filepath, "r") as f:
                    learning = json.load(f)

                # Filter by tags
                if tags:
                    learning_tags = learning.get("tags", [])
                    # Also check category as a tag
                    learning_tags.append(learning.get("category", ""))

                    if not any(
                        tag.lower() in [t.lower() for t in learning_tags]
                        for tag in tags
                    ):
                        continue

                # Filter by query
                if query:
                    search_text = f"{learning.get('title', '')} {learning.get('description', '')} {learning.get('content', '')}".lower()
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
        return self.search_knowledge(limit=1000)

    def get_context_string(self, query: str = "", tags: List[str] = None) -> str:
        """
        Get a formatted string of relevant learnings for context injection.
        """
        learnings = self.search_knowledge(query, tags)
        if not learnings:
            return "No relevant past learnings found."

        context = "## Relevant Past Learnings\n\n"
        for learning in learnings:
            context += f"### {learning.get('title', 'Untitled')}\n"
            context += f"- **Category**: {learning.get('category', 'General')}\n"
            context += f"- **Source**: {learning.get('source', 'Unknown')}\n"
            context += f"- **Date**: {learning.get('created_at', 'Unknown')}\n"
            content = learning.get("content", "")
            if isinstance(content, dict):
                context += f"\n{content.get('summary', '')}\n\n"
            else:
                context += f"\n{content}\n\n"
            if learning.get("codified_improvements"):
                context += "- **Improvements**:\n"
                for imp in learning["codified_improvements"]:
                    context += f"  - [{imp.get('type', 'item')}] {imp.get('title', '')}: {imp.get('description', '')}\n"
            context += "\n"

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

        prompt = "\n\n---\n\n## System Learnings (Auto-Injected)\n\n"
        prompt += (
            "The following patterns and learnings have been codified from past work. "
        )
        prompt += "Apply these automatically to the current task:\n\n"

        for learning in sorted_learnings:
            prompt += f"### {learning.get('title', 'Untitled')}\n"
            prompt += f"**Source:** {learning.get('source', 'unknown')}\n"

            if learning.get("codified_improvements"):
                for imp in learning["codified_improvements"]:
                    prompt += f"- {imp.get('description', '')}\n"

            prompt += "\n"

        return prompt

    def search_similar_patterns(
        self, description: str, threshold: float = 0.3, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar patterns using basic text similarity.

        In a production system, this would use vector embeddings (OpenAI, local).
        For now, we use simple keyword-based Jaccard similarity.

        Args:
            description: Text to find similar learnings for
            threshold: Minimum similarity score (0.0 to 1.0, default: 0.3)
            limit: Maximum number of results

        Returns:
            List of dicts with 'learning' and 'similarity' keys, sorted by similarity
        """
        all_learnings = self.get_all_learnings()

        if not all_learnings:
            return []

        # Simple keyword-based similarity
        desc_words = set(description.lower().split())

        results = []
        for learning in all_learnings:
            learning_text = (
                f"{learning.get('title', '')} {learning.get('description', '')}"
            )

            # Also include improvement descriptions
            if learning.get("codified_improvements"):
                for imp in learning["codified_improvements"]:
                    learning_text += (
                        f" {imp.get('title', '')} {imp.get('description', '')}"
                    )

            learning_words = set(learning_text.lower().split())

            # Jaccard similarity: intersection / union
            intersection = desc_words.intersection(learning_words)
            union = desc_words.union(learning_words)

            if len(union) > 0:
                similarity = len(intersection) / len(union)

                if similarity >= threshold:
                    results.append({"learning": learning, "similarity": similarity})

        # Sort by similarity (highest first)
        results.sort(key=lambda x: x["similarity"], reverse=True)

        return results[:limit]

    def get_ai_md_size(self) -> int:
        """
        Get current size of AI.md in characters.
        
        Returns:
            Size in characters, or 0 if file doesn't exist
        """
        ai_md_path = os.path.join(self.knowledge_dir, "AI.md")
        if not os.path.exists(ai_md_path):
            return 0
        try:
            with open(ai_md_path, "r") as f:
                return len(f.read())
        except Exception:
            return 0

    def compress_ai_md(self) -> None:
        """
        Compress AI.md by consolidating similar learnings.
        
        This uses simple deduplication to:
        1. Group similar learnings by category
        2. Merge duplicate or near-duplicate patterns
        3. Preserve unique insights
        4. Maintain categorical structure
        
        Note: No backup is created - rely on git for version control.
        """
        ai_md_path = os.path.join(self.knowledge_dir, "AI.md")
        if not os.path.exists(ai_md_path):
            return
        
        try:
            console.print("[cyan]Compressing AI.md...[/cyan]")
            
            # Get all learnings
            learnings = self.get_all_learnings()
            
            # Group by category and consolidate
            by_category = {}
            for learning in learnings:
                cat = learning.get("category", "General").title()
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(learning)
            
            # For each category, consolidate similar items
            consolidated_learnings = []
            for category, items in by_category.items():
                # If category has many items, consolidate
                if len(items) > 5:
                    # Use simple deduplication for now
                    # In production, would use LLM to intelligently merge
                    seen_hashes = set()
                    for item in items:
                        content_str = json.dumps(item, sort_keys=True)
                        h = hashlib.md5(content_str.encode()).hexdigest()
                        if h not in seen_hashes:
                            consolidated_learnings.append(item)
                            seen_hashes.add(h)
                else:
                    consolidated_learnings.extend(items)
            
            # Save compressed JSON files (remove duplicates)
            # Keep only the consolidated learnings
            backups_dir = os.path.join(self.knowledge_dir, "backups")
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            for filepath in glob.glob(os.path.join(self.knowledge_dir, "*.json")):
                learning_id = os.path.basename(filepath).split("-")[0]
                if not any(l.get("id") == learning_id for l in consolidated_learnings):
                    backup_path = os.path.join(backups_dir, f"{timestamp}_{os.path.basename(filepath)}")
                    shutil.move(filepath, backup_path)
            
            # Regenerate AI.md
            self._update_ai_md()
            
            console.print(
                f"[green]✓ AI.md compressed: {len(learnings)} → {len(consolidated_learnings)} learnings[/green]"
            )
            
        except Exception as e:
            console.print(f"[yellow]Failed to compress AI.md: {e}[/yellow]")

    def review_and_compress(self) -> None:
        """
        Auto-review AI.md quality and compress if needed.
        
        This is called automatically when AI.md exceeds size threshold.
        """
        size = self.get_ai_md_size()
        console.print(f"[dim]AI.md size: {size:,} chars (threshold: 50,000)[/dim]")
        
        if size > 50000:
            self.compress_ai_md()

    def _update_ai_md(self):
        learnings = self.get_all_learnings()

        # Group by category
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
                # Use feedback_summary as title if title field is missing
                title = item.get("title") or item.get("feedback_summary", "Untitled")
                content += f"### {title}\n"

                # Add description if present
                description = item.get("description", "")
                if description:
                    content += f"{description}\n\n"
                else:
                    content += "\n"

                if item.get("codified_improvements"):
                    content += "**Improvements:**\n"
                    for imp in item["codified_improvements"]:
                        type_badge = f"[{imp.get('type', 'item').upper()}]"
                        content += f"- {type_badge} {imp.get('title', '')}: {imp.get('description', '')}\n"
                    content += "\n"
                content += "\n"
            content += "\n"

        ai_md_path = os.path.join(self.knowledge_dir, "AI.md")
        try:
            tmp_path = ai_md_path + '.tmp'
            with open(tmp_path, "w") as f:
                f.write(content)
            os.replace(tmp_path, ai_md_path)
            console.print(f"[dim]Updated {ai_md_path}[/dim]")
        except Exception as e:
            console.print(f"[yellow]Failed to update AI.md: {e}[/yellow]")
