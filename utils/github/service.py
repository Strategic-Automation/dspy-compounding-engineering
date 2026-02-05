"""GitHub service for issue CRUD operations via gh CLI."""

import json
import shutil
import subprocess
from typing import Optional

from utils.io.logger import logger
from utils.io.safe import run_safe_command


class GitHubService:
    """Service for GitHub issue operations using gh CLI."""

    @staticmethod
    def _check_gh_cli() -> None:
        """Verify gh CLI is available."""
        if not shutil.which("gh"):
            raise RuntimeError("GitHub CLI (gh) is not installed")

    @staticmethod
    def create_issue(
        title: str,
        body: str,
        labels: Optional[list[str]] = None,
    ) -> dict:
        """
        Create a new GitHub issue.

        Args:
            title: Issue title
            body: Issue body (markdown)
            labels: List of label names to apply

        Returns:
            Dict with 'number' and 'url' of created issue
        """
        GitHubService._check_gh_cli()

        cmd = ["gh", "issue", "create", "--title", title, "--body", body]

        if labels:
            for label in labels:
                cmd.extend(["--label", label])

        try:
            result = run_safe_command(cmd, capture_output=True, text=True, check=True)
            # gh issue create outputs the URL on success
            url = result.stdout.strip()
            # Extract issue number from URL
            number = url.rstrip("/").split("/")[-1]
            return {"number": int(number), "url": url}
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create issue: {e.stderr}")
            raise RuntimeError(f"Failed to create issue: {e.stderr}") from e

    @staticmethod
    def update_issue(
        issue_number: int,
        body: Optional[str] = None,
        title: Optional[str] = None,
        add_labels: Optional[list[str]] = None,
        remove_labels: Optional[list[str]] = None,
    ) -> bool:
        """
        Update an existing GitHub issue.

        Args:
            issue_number: The issue number to update
            body: New body content (optional)
            title: New title (optional)
            add_labels: Labels to add (optional)
            remove_labels: Labels to remove (optional)

        Returns:
            True if successful
        """
        GitHubService._check_gh_cli()

        cmd = ["gh", "issue", "edit", str(issue_number)]

        if body is not None:
            cmd.extend(["--body", body])

        if title is not None:
            cmd.extend(["--title", title])

        if add_labels:
            for label in add_labels:
                cmd.extend(["--add-label", label])

        if remove_labels:
            for label in remove_labels:
                cmd.extend(["--remove-label", label])

        try:
            run_safe_command(cmd, capture_output=True, text=True, check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to update issue {issue_number}: {e.stderr}")
            raise RuntimeError(f"Failed to update issue: {e.stderr}") from e

    @staticmethod
    def get_issue(issue_number: int) -> dict:
        """
        Get details of a GitHub issue.

        Args:
            issue_number: The issue number

        Returns:
            Dict with issue details (title, body, labels, state, url)
        """
        GitHubService._check_gh_cli()

        cmd = [
            "gh",
            "issue",
            "view",
            str(issue_number),
            "--json",
            "title,body,labels,state,url,number",
        ]

        try:
            result = run_safe_command(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            logger.debug(f"Failed to fetch issue {issue_number}: {e.stderr}")
            return {}

    @staticmethod
    def list_labels() -> list[str]:
        """
        List all available labels in the repository.

        Returns:
            List of label names
        """
        GitHubService._check_gh_cli()

        cmd = ["gh", "api", "repos/:owner/:repo/labels", "--jq", ".[].name"]

        try:
            result = run_safe_command(cmd, capture_output=True, text=True, check=True)
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
        except subprocess.CalledProcessError as e:
            logger.debug(f"Failed to list labels: {e.stderr}")
            return []

    @staticmethod
    def issue_exists(issue_number: int) -> bool:
        """Check if an issue exists and is accessible."""
        details = GitHubService.get_issue(issue_number)
        return bool(details.get("number"))
