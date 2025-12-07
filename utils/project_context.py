"""
Project Context Service

This module provides functionality to gather context about the project,
including reading key files (README, pyproject.toml) and gathering source code
for analysis.
"""

import os


class ProjectContext:
    """
    Helper service for gathering project context and files.
    """

    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir

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
        except Exception:
            pass

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
        Gather all relevant project files for full project review.
        
        Args:
            max_file_size: Maximum size of a file to include (in chars)
            
        Returns:
            Concatenated string of file contents
        """
        project_content = []

        # File extensions to include
        code_extensions = {
            ".py",
            ".js",
            ".ts",
            ".tsx",
            ".jsx",
            ".rb",
            ".go",
            ".rs",
            ".java",
            ".kt",
        }
        config_extensions = {".toml", ".yaml", ".yml", ".json"}

        # Directories to skip
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

        for root, dirs, files in os.walk(self.base_dir):
            # Filter out skip directories
            dirs[:] = [d for d in dirs if d not in skip_dirs]

            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext in code_extensions or ext in config_extensions:
                    filepath = os.path.join(root, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            # Skip very large files
                            if len(content) > max_file_size:
                                content = content[:max_file_size] + "\n...[truncated]..."
                            project_content.append(f"=== {filepath} ===\n{content}\n")
                    except Exception:
                        pass

        return "\n".join(project_content)
