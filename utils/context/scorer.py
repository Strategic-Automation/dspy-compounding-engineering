"""
Relevance Scorer module.

This module calculates relevance scores for files based on a task description.
It utilizes tiered logic:
1. Tier 1: Config/Critical files (Always relevant)
2. Tier 2: Content/Semantic match
3. Tier 3: General code
"""

import os

from config import TIER_1_FILES


class RelevanceScorer:
    """
    Scores files based on relevance to a task.
    """

    def __init__(self, embedding_provider=None):
        self.embedding_provider = embedding_provider

    def score(
        self,
        filepath: str,
        content: str,
        task: str,
        is_test_related: bool = False,
    ) -> float:
        """
        Legacy full-score method.
        """
        score = self.score_path(filepath, task, is_test_related)

        # Content keyword check (simple scan of first 1000 chars)
        task_keywords = {k.lower() for k in task.split() if len(k) > 3}
        preview = content[:1000].lower()
        if any(keyword in preview for keyword in task_keywords):
            score += 0.1

        return min(score, 0.95)

    def score_path(
        self,
        filepath: str,
        task: str,
        is_test_related: bool = False,
    ) -> float:
        """
        Score based only on file path and task description.
        Useful for metadata-first filtering.
        """
        filename = os.path.basename(filepath)

        # TIER 1: Critical Files
        if filename in TIER_1_FILES:
            return 1.0

        # TIER 2: Heuristic Relevance
        score = 0.1  # Base score

        # Boost test files if task is test-related
        if is_test_related and "test" in filepath.lower():
            score += 0.4

        # Boost matching filenames (simple keyword match)
        task_keywords = {k.lower() for k in task.split() if len(k) > 3}
        path_keywords = {
            k.lower()
            for k in filepath.replace("/", " ").replace("_", " ").replace(".", " ").split()
            if len(k) > 3
        }

        overlap = len(task_keywords.intersection(path_keywords))
        if overlap > 0:
            score += 0.3 + (0.1 * overlap)

        return min(score, 0.9)
