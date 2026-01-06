"""
Project Context Service

This module provides functionality to gather context about the project,
including reading key files (README, pyproject.toml) and gathering source code
for analysis.
"""

import os
from typing import List, Optional, Tuple

from rich.console import Console

from config import get_project_root, settings
from utils.context.scorer import RelevanceScorer
from utils.io.logger import logger
from utils.io.safe import run_safe_command, validate_path
from utils.security.scrubber import scrubber
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
            console.log(f"[warning]Failed to list project files in '{self.base_dir}': {e}")

        key_files = settings.project_key_files
        for kf in key_files:
            kf_path = os.path.join(self.base_dir, kf)
            if os.path.exists(kf_path):
                try:
                    with open(kf_path, "r") as f:
                        content = f.read()[:1000]
                    context_parts.append(f"\n--- {kf} ---\n{content}")
                except Exception as e:
                    console.log(f"[warning]Failed to read key project file '{kf_path}': {e}")

        return "\n".join(context_parts) if context_parts else "No project context available"

    def gather_smart_context(
        self,
        task: str = "",
        max_file_size: Optional[int] = None,
        budget: Optional[int] = None,
    ) -> str:
        """
        Gather project files intelligently based on task relevance and token budget.
        Uses a two-pass approach: 1. Filter by metadata/score, 2. Lazy load and fill budget.
        """
        from config import settings

        if budget is None:
            budget = settings.context_window_limit - settings.context_output_reserve

        if max_file_size is None:
            max_file_size = settings.project_context_max_file_size

        project_content = []
        current_tokens = 0

        # 1. Collect Candidates (Metadata only)
        # (filepath, score, mtime, size)
        candidates: List[Tuple[str, float, float, int]] = []

        code_extensions = settings.code_extensions
        config_extensions = settings.config_extensions
        skip_dirs = settings.skip_dirs
        skip_files = settings.skip_files

        # Walk and collect candidates
        candidates = self._collect_context_candidates(
            code_extensions, config_extensions, skip_dirs, skip_files, task, max_file_size
        )

        # 2. Sort by Relevance (Score DESC, Path ASC for determinstic behavior)
        candidates.sort(key=lambda x: (-x[1], x[0]))

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
                logger.warning(f"Failed to process {filepath}: {e}")
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

        # Try to use git to respect .gitignore
        git_files = self._get_git_files()

        if git_files is not None:
            for filepath in git_files:
                candidate = self._process_file_candidate(
                    filepath, code_ext, config_ext, skip_files, task, max_file_size
                )
                if candidate:
                    candidates.append(candidate)
        else:
            # Fallback to manual walk
            for root, dirs, files in os.walk(self.base_dir):
                dirs[:] = [d for d in dirs if d not in skip_dirs]
                for filename in files:
                    filepath = os.path.join(root, filename)
                    candidate = self._process_file_candidate(
                        filepath, code_ext, config_ext, skip_files, task, max_file_size
                    )
                    if candidate:
                        candidates.append(candidate)
        return candidates

    def _process_file_candidate(
        self,
        filepath: str,
        code_ext: set,
        config_ext: set,
        skip_files: set,
        task: str,
        max_file_size: int,
    ) -> Optional[Tuple[str, float, float, int]]:
        """Helper to validte and score a single file candidate."""
        filename = os.path.basename(filepath)
        if filename in skip_files:
            return None

        # Use settings from module scope (imported at top) or lazy import if needed.
        # Assuming settings is available via self or global import.
        # Using global settings as per existing code structure.

        ext = os.path.splitext(filename)[1].lower()
        if ext in code_ext or ext in config_ext or filename in settings.tier_1_files:
            if not self._is_safe_path(filepath):
                return None
            try:
                stat = os.stat(filepath)
                if stat.st_size > max_file_size * 2:
                    return None
                rel_path = os.path.relpath(filepath, self.base_dir)
                score = self.scorer.score_path(rel_path, task)
                return (filepath, score, stat.st_mtime, stat.st_size)
            except Exception as e:
                logger.warning(f"Failed to stat {filepath}: {e}")
                return None
        return None

    def _get_git_files(self) -> Optional[List[str]]:
        """Fetch all non-ignored files using git ls-files."""
        try:
            # -c: cached (tracked)
            # -o: others (untracked)
            # --exclude-standard: respect .gitignore
            cmd = ["git", "ls-files", "-c", "-o", "--exclude-standard"]
            result = run_safe_command(
                cmd, cwd=self.base_dir, capture_output=True, text=True, check=True
            )
            files = [f for f in result.stdout.splitlines() if f.strip()]
            return [os.path.join(self.base_dir, f) for f in files]
        except Exception as e:
            logger.debug(f"Git not available or not a repo at {self.base_dir}: {e}")
            return None

    def _is_safe_path(self, filepath: str) -> bool:
        """Security: Ensure filepath is within base_dir."""
        abs_filepath = os.path.abspath(filepath)
        abs_base = os.path.abspath(self.base_dir)
        return os.path.commonpath([abs_filepath, abs_base]) == abs_base
