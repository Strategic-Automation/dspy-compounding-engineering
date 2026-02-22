"""
Knowledge Gardening Service.

This module implements the core logic for the "Intelligent Knowledge Gardening" system.
It handles:
1. Scoring: Calculating importance scores for learning items.
2. Extraction: Extracting structured facts from raw learnings.
3. Compression: Tiered compression (Detailed, Compressed, Principle).
4. Deduplication: semantic deduplication using vector embeddings.
"""

from datetime import datetime
from typing import Any, Dict

import dspy
from rich.console import Console

from ..io.logger import logger
from .core import KnowledgeBase

console = Console()


class FactStatement(dspy.Signature):
    """
    Extract a structured fact statement from a learning item.
    """

    content = dspy.InputField(desc="The raw learning content.")

    fact_title = dspy.OutputField(desc="A concise title for the fact.")
    fact_category = dspy.OutputField(
        desc="The engineering category (e.g., Architecture, Security)."
    )
    fact_description = dspy.OutputField(
        desc="A clear, standalone statement of the engineering fact or principle."
    )


class KnowledgeGardener(dspy.Module):
    def __init__(self):
        super().__init__()
        # We reuse the agent defined in agents/knowledge_gardener.py for the main compression
        # but here we define helper modules for specific gardening tasks.
        self.fact_extractor = dspy.ChainOfThought(FactStatement)

    def extract_fact(self, content: str) -> Dict[str, str]:
        try:
            prediction = self.fact_extractor(content=content)
            return {
                "title": prediction.fact_title,
                "category": prediction.fact_category,
                "description": prediction.fact_description,
            }
        except Exception as e:
            logger.warning(f"Fact extraction failed: {e}")
            return {
                "title": "Extraction Failed",
                "category": "Unknown",
                "description": content[:200],
            }


class KnowledgeGardeningService:
    """
    Service to maintain the health and density of the Knowledge Base.
    """

    def __init__(self):
        from config import (
            registry,
            settings,
        )
        self.settings = settings
        self.registry = registry
        self.kb = KnowledgeBase()
        self.gardener_agent = KnowledgeGardener()

    def _calculate_importance_score(self, item: Dict[str, Any]) -> float:
        """
        Calculate importance score (0.0 - 1.0) based on Recency, Impact, and Pattern Strength.
        """
        # 1. Recency Score
        try:
            created_at = datetime.fromisoformat(item.get("created_at", datetime.now().isoformat()))
            age_days = (datetime.now() - created_at).days
            # Linear decay over retention period
            recency_score = max(0.0, 1.0 - (age_days / self.settings.kg_retention_days))
        except Exception:
            recency_score = 0.5

        # 2. Impact Score (Heuristic based on metadata)
        impact_score = 0.5  # Default
        if item.get("codified_improvements"):
            impact_score += 0.2
        if item.get("category") in ["security", "architecture"]:
            impact_score += 0.2
        if "critical" in str(item).lower():
            impact_score += 0.1
        impact_score = min(1.0, impact_score)

        # 3. Pattern Strength (Placeholder for now - could be frequency based)
        pattern_score = 0.5

        # Weighted Average
        total_score = (
            (recency_score * self.settings.kg_importance_weight_recency)
            + (impact_score * self.settings.kg_importance_weight_impact)
            + (pattern_score * self.settings.kg_importance_weight_pattern)
        )
        return round(min(1.0, max(0.0, total_score)), 2)

    def _determine_tier(self, score: float) -> str:
        """Determine compression tier based on importance score."""
        if score >= 0.8:
            return "detailed"
        elif score >= 0.5:
            return "compressed"
        else:
            return "principle"

    def _score_item(self, item: Dict[str, Any]) -> bool:
        """
        Phase 1: Calculate score and tier using local heuristics.
        Returns True if item was modified.
        """
        modified = False
        if "importance_score" not in item:
            score = self._calculate_importance_score(item)
            item["importance_score"] = score
            item["compression_tier"] = self._determine_tier(score)
            modified = True
        return modified

    def _extract_item(self, item: Dict[str, Any], dry_run: bool) -> bool:
        """
        Phase 3: LLM Extraction for a single item.
        Returns True if extraction occurred.
        """
        if "fact_statement" in item:
            return False

        # Expensive LLM transformation
        content_str = str(item.get("description", "")) + " " + str(item.get("content", ""))
        try:
            item["fact_statement"] = self.gardener_agent.extract_fact(content_str)
            if not dry_run:
                self.kb.save_learning(item, silent=True, update_docs=False)
            return True
        except Exception as e:
            logger.warning(f"Failed to extract fact for item {item.get('id')}: {e}")
            return False

    def _phase_scoring(self, all_learnings, progress, dry_run, stats):
        """Phase 1: Scoring (Local)"""
        total_items = len(all_learnings)
        task_score = progress.add_task(
            f"[cyan]Scoring {total_items} items...", total=total_items
        )
        for item in all_learnings:
            if self._score_item(item):
                stats["scored"] += 1
                if not dry_run:
                    # Save score immediately so it persists even if we crash later
                    self.kb.save_learning(item, silent=True, update_docs=False)
            progress.advance(task_score)

    def _compute_vectors(self, valid_descriptions, progress, task_dedupe):
        """Helper to compute vectors for descriptions."""
        vectors = []
        if self.kb.embedding_provider.embedding_provider == "fastembed":
            vectors = list(
                self.kb.embedding_provider.fast_model.embed(valid_descriptions)
            )
        else:
            for text in valid_descriptions:
                vectors.append(self.kb.embedding_provider.get_embedding(text))
                progress.advance(task_dedupe, advance=0.1)
        return vectors

    def _phase_dedup_in_memory(self, all_learnings, progress, dry_run, stats):
        """Fallback: In-Memory Deduplication"""
        console.print("[dim]Qdrant unavailable. Using in-memory vector search...[/dim]")

        task_dedupe = progress.add_task(
            "[magenta]Semantic Deduplication (In-Memory)...", total=len(all_learnings)
        )

        descriptions = [item.get("description", "") for item in all_learnings]
        valid_indices = [i for i, d in enumerate(descriptions) if d]
        valid_descriptions = [descriptions[i] for i in valid_indices]

        try:
            vectors = self._compute_vectors(valid_descriptions, progress, task_dedupe)

            import numpy as np

            if vectors:
                vec_array = np.array(list(vectors))
                norms = np.linalg.norm(vec_array, axis=1, keepdims=True)
                normalized = vec_array / (norms + 1e-10)
                sim_matrix = np.dot(normalized, normalized.T)

                rows, cols = sim_matrix.shape
                for i in range(rows):
                    idx_i = valid_indices[i]
                    item_i = all_learnings[idx_i]

                    if item_i.get("duplicate_of"):
                        continue

                    related_modified = False
                    current_related = set(item_i.get("related_ids", []))

                    for j in range(i + 1, cols):
                        if sim_matrix[i, j] >= self.settings.kg_dedupe_threshold:
                            idx_j = valid_indices[j]
                            item_j = all_learnings[idx_j]

                            if (
                                item_j.get("id")
                                and item_j.get("id") not in current_related
                            ):
                                current_related.add(item_j.get("id"))
                                related_modified = True

                    if related_modified:
                        item_i["related_ids"] = list(current_related)
                        stats["deduped"] += 1
                        if not dry_run:
                            self.kb.save_learning(
                                item_i, silent=True, update_docs=False
                            )
                    progress.advance(task_dedupe)
        except Exception as e:
            logger.warning(f"In-memory deduplication failed: {e}")

    def _phase_dedup_qdrant(self, all_learnings, progress, dry_run, stats):
        """Standard Qdrant Deduplication"""
        task_dedupe = progress.add_task(
            "[magenta]Semantic Deduplication (Qdrant)...", total=len(all_learnings)
        )
        for item in all_learnings:
            progress.advance(task_dedupe)
            if item.get("duplicate_of"):
                continue

            description = item.get("description", "")
            if not description:
                continue

            similars = self.kb.search_similar_patterns(
                description,
                threshold=self.settings.kg_dedupe_threshold,
                limit=5,
            )

            related_ids = item.get("related_ids", [])
            original_count = len(related_ids)

            for hit in similars:
                other = hit["learning"]
                if other.get("id") == item.get("id"):
                    continue

                if hit["similarity"] >= self.settings.kg_dedupe_threshold:
                    other_id = other.get("id")
                    if other_id and other_id not in related_ids:
                        related_ids.append(other_id)

            if len(related_ids) > original_count:
                item["related_ids"] = related_ids
                stats["deduped"] += 1
                if not dry_run:
                    self.kb.save_learning(item, silent=True, update_docs=False)

    def _phase_extraction(
        self, all_learnings, progress, dry_run, deep_mode, max_workers, stats
    ):
        """Phase 3: Selective Extraction (LLM)"""
        items_to_extract = []
        for item in all_learnings:
            if item.get("duplicate_of"):
                stats["skipped_extraction"] += 1
                continue

            score = item.get("importance_score", 0.0)
            if not deep_mode and score < 0.4:
                stats["skipped_extraction"] += 1
                continue

            if "fact_statement" not in item:
                items_to_extract.append(item)

        if items_to_extract:
            task_extract = progress.add_task(
                f"[yellow]Extracting Facts ({len(items_to_extract)} items)...",
                total=len(items_to_extract),
            )

            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers
            ) as executor:
                future_to_item = {
                    executor.submit(self._extract_item, item, dry_run): item
                    for item in items_to_extract
                }

                for future in concurrent.futures.as_completed(future_to_item):
                    try:
                        if future.result():
                            stats["extracted"] += 1
                    except Exception as e:
                        logger.error(f"Extraction failed: {e}")
                    finally:
                        progress.advance(task_extract)
        else:
             logger.info("No items needed extraction.")

    def garden(
        self, dry_run: bool = False, deep_mode: bool = False, max_workers: int = 10
    ) -> None:
        """
        Hybrid Gardening Loop:
        1. Score & Assess (Local/Fast)
        2. Deduplicate/Cluster (Local/Fast Embeddings)
        3. Selective Extraction (LLM/Slow) - Only for high-value, unique items

        Args:
            dry_run: Simulate without saving.
            deep_mode: If True, force extraction on ALL unique items regardless of score.
        """


        from rich.progress import (
            BarColumn,
            Progress,
            SpinnerColumn,
            TaskProgressColumn,
            TextColumn,
        )

        logger.info(f"Starting Hybrid Gardening (Deep Mode: {deep_mode})...")
        all_learnings = self.kb.get_all_learnings()

        stats = {"scored": 0, "deduped": 0, "extracted": 0, "skipped_extraction": 0}

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:

            # Phase 1: Scoring
            self._phase_scoring(all_learnings, progress, dry_run, stats)

            # Phase 2: Deduplication
            if not self.registry.check_qdrant():
                self._phase_dedup_in_memory(all_learnings, progress, dry_run, stats)
            else:
                self._phase_dedup_qdrant(all_learnings, progress, dry_run, stats)

            # Phase 3: Extraction
            self._phase_extraction(
                all_learnings, progress, dry_run, deep_mode, max_workers, stats
            )

        # Final Report
        console.rule("[bold green]Gardening Complete")
        console.print(f"Scored Items: {stats['scored']}")
        console.print(f"Deduplicated/Linked: {stats['deduped']}")
        console.print(f"Facts Extracted: {stats['extracted']}")
        console.print(f"Skipped Extraction: {stats['skipped_extraction']}")
        if dry_run:
            console.print("[yellow]DRY RUN: No changes saved.[/yellow]")
