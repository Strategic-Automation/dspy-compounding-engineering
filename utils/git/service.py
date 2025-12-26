import shutil
import subprocess

from .io.safe import run_safe_command


class GitService:
    """Helper service for Git and GitHub CLI operations."""

    IGNORE_FILES = [
        "uv.lock",
        "package-lock.json",
        "yarn.lock",
        "poetry.lock",
        "Gemfile.lock",
    ]

    @staticmethod
    def filter_diff(diff_text: str) -> str:
        """Filter out ignored files from a git diff."""
        if not diff_text:
            return ""

        sections = diff_text.split("diff --git ")
        filtered_sections = []

        for section in sections:
            if not section.strip():
                continue

            # First line usually: a/path/to/file b/path/to/file
            first_line = section.split("\n", 1)[0]

            is_ignored = False
            for ignored in GitService.IGNORE_FILES:
                if f"a/{ignored}" in first_line or f"b/{ignored}" in first_line:
                    is_ignored = True
                    break

            if not is_ignored:
                filtered_sections.append(section)

        if not filtered_sections:
            return ""

        # Reconstruct
        result = "diff --git " + "diff --git ".join(filtered_sections)
        # Handle case where split created an empty first element (common)
        if diff_text.startswith("diff --git") and not result.startswith("diff --git"):
            # If our reconstruction missed the prefix because the first section was filtered?
            # No, if we append "diff --git " to join, we are good.
            # But if the original text started with it, the first split element is empty string.
            pass

        return result

    @staticmethod
    def is_git_repo() -> bool:
        """Check if current directory is a git repo."""
        return (
            run_safe_command(
                ["git", "rev-parse", "--is-inside-work-tree"], capture_output=True
            ).returncode
            == 0
        )

    @staticmethod
    def get_diff(target: str = "HEAD") -> str:
        """Get git diff for a target (commit, branch, or staged)."""
        try:
            # If target is a URL or PR number, we need gh cli
            if target.startswith("http") or target.isdigit():
                return GitService.get_pr_diff(target)

            # Otherwise treat as local ref
            # Added -M for rename detection
            cmd = ["git", "diff", "-M", target, "--", "."]
            for ignore in GitService.IGNORE_FILES:
                cmd.append(f":!{ignore}")

            result = run_safe_command(cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError:
            return ""

    @staticmethod
    def get_file_status_summary(target: str = "HEAD") -> str:
        """
        Get a summary of file statuses (Added, Modified, Deleted, Renamed).
        Useful for providing high-level context to LLMs before the full diff.
        """
        try:
            cmd = ["git", "diff", "--name-status", "-M", target, "--", "."]
            for ignore in GitService.IGNORE_FILES:
                cmd.append(f":!{ignore}")

            result = run_safe_command(cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError:
            return "Could not retrieve file status summary."

    @staticmethod
    def get_pr_diff(pr_id_or_url: str) -> str:
        """Fetch PR diff using gh CLI."""
        if not shutil.which("gh"):
            raise RuntimeError("GitHub CLI (gh) is not installed")

        try:
            cmd = ["gh", "pr", "diff", pr_id_or_url]
            result = run_safe_command(cmd, capture_output=True, text=True, check=True)
            return GitService.filter_diff(result.stdout)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to fetch PR diff: {e.stderr}") from e

    @staticmethod
    def get_pr_details(pr_id_or_url: str) -> dict:
        """Fetch PR details (title, body, author) using gh CLI."""
        if not shutil.which("gh"):
            raise RuntimeError("GitHub CLI (gh) is not installed")

        try:
            cmd = [
                "gh",
                "pr",
                "view",
                pr_id_or_url,
                "--json",
                "title,body,author,number,url",
            ]
            # We'll parse the JSON output in the caller or add json import here
            # For simplicity returning raw stdout for now, caller can parse
            import json

            result = run_safe_command(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to fetch PR details: {e.stderr}") from e

    @staticmethod
    def get_current_branch() -> str:
        """Get current branch name."""
        try:
            result = run_safe_command(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "unknown"

    @staticmethod
    def get_pr_branch(pr_id_or_url: str) -> str:
        """Get the branch name for a PR using gh CLI."""
        if not shutil.which("gh"):
            raise RuntimeError("GitHub CLI (gh) is not installed")

        try:
            # Get the headRefName (branch name)
            cmd = ["gh", "pr", "view", pr_id_or_url, "--json", "headRefName"]
            import json

            result = run_safe_command(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            return data.get("headRefName", "")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to fetch PR branch: {e.stderr}") from e

    @staticmethod
    def checkout_pr_worktree(pr_id_or_url: str, worktree_path: str) -> None:
        """Checkout a PR into a worktree."""
        if not shutil.which("gh"):
            raise RuntimeError("GitHub CLI (gh) is not installed")

        try:
            # First, fetch the PR branch locally
            run_safe_command(["gh", "pr", "checkout", pr_id_or_url], check=True)

            # Get the branch name
            branch_name = GitService.get_pr_branch(pr_id_or_url)
            if not branch_name:
                raise RuntimeError("Could not determine branch name for PR")

            # Create worktree
            # Note: gh pr checkout switches the current branch, which might be annoying.
            # A better way for production might be to fetch the ref directly to a local branch
            # without checking it out, but gh pr checkout is the easiest way to ensure we have the
            # code. However, since we want to avoid disrupting the user, let's try to just fetch
            # it. Actually, 'gh pr checkout' modifies the current working directory.
            # To avoid this, we should just fetch the branch.

            # Alternative: git fetch origin pull/ID/head:BRANCHNAME
            # But we need the ID.
            # Let's stick to 'gh pr checkout' but we need to be careful.
            # Wait, if we are in a worktree, we can just create ANOTHER worktree from the branch.
            # But we need the branch to exist locally first.

            # Let's try to fetch without checkout if possible, but 'gh' doesn't make it easy.
            # Let's use the 'gh pr checkout' but then immediately switch back? No that's bad.

            # Better approach:
            # 1. Get branch name
            # 2. git fetch origin <branch_name> (if we know the remote branch name)
            # 3. git worktree add ...

            # Actually, 'gh pr checkout' is designed to switch context.
            # If we want to review WITHOUT switching context, we should:
            # 1. Get the headRefName and headRepositoryOwner
            # 2. git fetch https://github.com/OWNER/REPO.git branch:local-branch
            # 3. git worktree add ...

            # For now, let's assume the user is okay with us fetching the branch.
            # We can use 'git fetch origin pull/ID/head:pr-ID' if we have the numeric ID.
            # But pr_id_or_url might be a URL.

            # Let's use a safer approach:
            # 1. Get PR details to find the branch name.
            # 2. Fetch that branch.
            # 3. Create worktree.

            # Simplified for this iteration:
            # We will assume 'gh pr checkout' is acceptable to get the branch locally,
            # BUT we will do it in a way that doesn't switch the current HEAD if possible?
            # No, 'gh pr checkout' definitely switches.

            # Let's use 'gh pr view' to get the branch name, then 'git fetch origin branch_name'.
            # This assumes the branch is in the same repo (not a fork).
            # If it's a fork, it's more complex.

            # Let's just use 'gh pr checkout' but save the current branch first?
            # No, that's risky.

            # Let's try to use 'gh' to just fetch.
            # 'gh pr checkout <id> --detach' ? No.

            # Let's go with:
            # 1. Get branch name.
            # 2. git fetch origin <branch_name>:<branch_name>
            # This works for non-forks.

            # If we want to support forks, we really should use 'gh pr checkout'.
            # Let's stick to the plan: "Create isolated worktree".
            # If we use 'gh pr checkout', we change the current dir.
            # Maybe we can run 'gh pr checkout' INSIDE the new worktree?
            # No, you create a worktree from a branch.

            # Let's assume for now we just want to review LOCAL branches or fetch them if missing.
            # We'll implement a simple fetch:
            branch = GitService.get_pr_branch(pr_id_or_url)
            run_safe_command(["git", "fetch", "origin", branch], check=True)

            # Now create worktree
            cmd = ["git", "worktree", "add", worktree_path, branch]
            run_safe_command(cmd, check=True)

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to checkout PR worktree: {e.stderr}") from e

    @staticmethod
    def create_feature_worktree(branch_name: str, worktree_path: str) -> None:
        """Create a worktree for a feature branch (creating branch if needed)."""
        try:
            # Check if branch exists
            branch_exists = (
                run_safe_command(
                    ["git", "rev-parse", "--verify", branch_name], capture_output=True
                ).returncode
                == 0
            )

            cmd = ["git", "worktree", "add"]
            if not branch_exists:
                # Create new branch
                # Syntax: git worktree add -b <new_branch> <path> <start_point>
                # We'll default start_point to HEAD if not specified
                cmd.extend(["-b", branch_name, worktree_path])
            else:
                # Existing branch
                # Syntax: git worktree add <path> <branch>
                cmd.extend([worktree_path, branch_name])

            run_safe_command(cmd, check=True, capture_output=True)

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create feature worktree: {e.stderr}") from e
