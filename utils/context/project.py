"""
Project Context Service

This module provides functionality to gather context about the project,
including reading key files (README, pyproject.toml) and gathering source code
for analysis.
"""

import os
from typing import List, Optional, Tuple

from rich.console import Console

from config import CONTEXT_OUTPUT_RESERVE, CONTEXT_WINDOW_LIMIT, TIER_1_FILES, get_project_root
from utils.context.scorer import RelevanceScorer
from utils.context.scrubber import scrubber
from utils.io.safe import validate_path
from utils.token.counter import TokenCounter

console = Console()


class ProjectContext:
    """
    Helper service for gathering project context and files.
    """

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = str(get_project_root())

        try:
            # Ensure base_dir is within a safe project path or CWD to prevent traversal
            # We use the project root if available, otherwise CWD.
            self.base_dir = validate_path(base_dir, base_dir=base_dir)
        except ValueError as e:
            # Re-raise with clear context
            raise ValueError(f"Security Error: ProjectContext restricted to {base_dir}. {e}") from e

        self.token_counter = TokenCounter()
        self.scorer = RelevanceScorer()

    def get_context(self) -> str:
        """
        Get basic project context by reading key files.

        Returns:
            String containing project context
        """
        context_parts = []

        try:
            files = os.listdir(self.base_dir)
            context_parts.append(
                f"Project files: {', '.join(f for f in files if not f.startswith('.'))}"
            )
        except Exception as e:
            # Best-effort: if we cannot list project files, continue without failing.
            console.log(f"Warning: unable to list project files in {self.base_dir!r}: {e}")

        key_files = ["README.md", "pyproject.toml", "package.json", "requirements.txt"]
        for kf in key_files:
            kf_path = os.path.join(self.base_dir, kf)
            if os.path.exists(kf_path):
                try:
                    with open(kf_path, "r") as f:
                        content = f.read()[:1000]
                    context_parts.append(f"\n--- {kf} ---\n{content}")
                except Exception:
                    pass

        return "\n".join(context_parts) if context_parts else "No project context available"

    def gather_project_files(self, max_file_size: int = 50000) -> str:
        """
        Legacy method alias for backward compatibility.
        """
        return self.gather_smart_context(task="", max_file_size=max_file_size)

    def gather_smart_context(
        self,
        task: str = "",
        max_file_size: int = 50000,
        budget: int = CONTEXT_WINDOW_LIMIT - CONTEXT_OUTPUT_RESERVE,
    ) -> str:
        """
        Gather project files intelligently based on task relevance and token budget.
        Uses a two-pass approach: 1. Filter by metadata/score, 2. Lazy load and fill budget.
        """
        project_content = []
        current_tokens = 0

        # 1. Collect Candidates (Metadata only)
        # (filepath, score, mtime, size)
        candidates: List[Tuple[str, float, float, int]] = []

        code_extensions = {".py", ".js", ".ts", ".tsx", ".jsx", ".rb", ".go", ".rs", ".java", ".kt"}
        config_extensions = {".toml", ".yaml", ".yml", ".json"}
        skip_dirs = {
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            "dist",
            "build",
            ".tox",
            ".mypy_cache",
            "worktrees",
            ".ruff_cache",
        }
        skip_files = {"uv.lock", "package-lock.json", "yarn.lock", "poetry.lock", "Gemfile.lock"}

        # Walk and collect candidates
        candidates = self._collect_context_candidates(
            code_extensions, config_extensions, skip_dirs, skip_files, task, max_file_size
        )

        # 2. Sort by Relevance
        candidates.sort(key=lambda x: x[1], reverse=True)

        # 3. Second Pass: Lazy Load, Scrub, and Fill Budget
        included_count = 0
        skipped_count = 0

        for filepath, score, _mtime, _size in candidates:
            try:
                # Lazy load content only for candidates
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # Scrub content for PII/Secrets
                scrubbed_content = scrubber.scrub(content)
                if len(scrubbed_content) > max_file_size:
                    scrubbed_content = scrubbed_content[:max_file_size] + "\n...[truncated]..."

                # Apply token budget check
                rel_path = os.path.relpath(filepath, self.base_dir)
                entry_text = f"=== {rel_path} (Score: {score:.2f}) ===\n{scrubbed_content}\n"
                entry_tokens = self.token_counter.count_tokens(entry_text)

                if current_tokens + entry_tokens <= budget:
                    project_content.append(entry_text)
                    current_tokens += entry_tokens
                    included_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                print(f"[yellow]Warning: Failed to process {filepath}: {e}[/yellow]")
                skipped_count += 1

        # Summary footer (not scored, usually fits)
        summary = (
            f"\n--- Context Summary ---\n"
            f"Files included: {included_count}\n"
            f"Files skipped (budget): {skipped_count}\n"
            f"Total tokens: {current_tokens}/{budget}\n"
        )
        project_content.append(summary)

        return "\n".join(project_content)

    def _collect_context_candidates(
        self,
        code_ext: set,
        config_ext: set,
        skip_dirs: set,
        skip_files: set,
        task: str,
        max_file_size: int,
    ) -> List[Tuple[str, float, float, int]]:
        """Collect and score candidates based on metadata."""
        candidates = []
        for root, dirs, files in os.walk(self.base_dir):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for filename in files:
                if filename in skip_files:
                    continue
                ext = os.path.splitext(filename)[1].lower()
                if ext in code_ext or ext in config_ext or filename in TIER_1_FILES:
                    filepath = os.path.join(root, filename)
                    if not self._is_safe_path(filepath):
                        continue
                    try:
                        stat = os.stat(filepath)
                        if stat.st_size > max_file_size * 2:
                            continue
                        rel_path = os.path.relpath(filepath, self.base_dir)
                        score = self.scorer.score_path(rel_path, task)
                        candidates.append((filepath, score, stat.st_mtime, stat.st_size))
                    except Exception as e:
                        print(f"[yellow]Warning: Failed to stat {filepath}: {e}[/yellow]")
        return candidates

    def _is_safe_path(self, filepath: str) -> bool:
        """Security: Ensure filepath is within base_dir."""
        abs_filepath = os.path.abspath(filepath)
        abs_base = os.path.abspath(self.base_dir)
        return os.path.commonpath([abs_filepath, abs_base]) == abs_base
